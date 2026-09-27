"""Scanner-Matrix ARC-01, AGT-09, BIN-02: tar archives and package formats inside the package."""

import io
import tarfile
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from luibui_scan.intake import DEFAULT_LIMITS, Ablehnung, IntakeRejectedError, extract_archive
from luibui_scan.intake.nested import expand_packages
from luibui_scan.models import ScanArt
from luibui_scan.scan import Eingabe, scan_prepared


@pytest.fixture
def root(tmp_path: Path) -> Path:
    d = tmp_path / "scratch"
    d.mkdir()
    return d


def make_tar(
    tmp_path: Path, members: list[tuple[tarfile.TarInfo, bytes | None]], mode: str
) -> Path:
    path = tmp_path / "upload.tar"
    with tarfile.open(path, mode) as tf:
        for info, data in members:
            tf.addfile(info, io.BytesIO(data) if data is not None else None)
    return path


def regular(name: str, data: bytes) -> tuple[tarfile.TarInfo, bytes]:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    return info, data


@pytest.mark.parametrize("mode", ["w", "w:gz", "w:bz2", "w:xz"])
def test_tar_is_unpacked(tmp_path: Path, root: Path, mode: str) -> None:
    archive = make_tar(
        tmp_path, [regular("SKILL.md", b"# Skill\n"), regular("a/b.txt", b"x")], mode
    )
    assert extract_archive(archive, root) == ["SKILL.md", "a/b.txt"]
    assert (root / "a" / "b.txt").read_bytes() == b"x"


@pytest.mark.parametrize(
    "kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE]
)
def test_tar_links_and_devices_are_refused(tmp_path: Path, root: Path, kind: bytes) -> None:
    link = tarfile.TarInfo("geheim")
    link.type = kind
    link.linkname = "/etc/passwd"
    archive = make_tar(tmp_path, [regular("ok.txt", b"x"), (link, None)], "w")
    with pytest.raises(IntakeRejectedError) as exc:
        extract_archive(archive, root)
    assert exc.value.grund is Ablehnung.VERKNUEPFUNG
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("name", ["../aussen.txt", "/etc/cron.d/x"])
def test_tar_paths_outside_are_refused(tmp_path: Path, root: Path, name: str) -> None:
    archive = make_tar(tmp_path, [regular(name, b"x")], "w")
    with pytest.raises(IntakeRejectedError) as exc:
        extract_archive(archive, root)
    assert exc.value.grund is Ablehnung.PFAD_AUSSERHALB


def test_tar_bomb_is_refused_before_writing(tmp_path: Path, root: Path) -> None:
    archive = make_tar(tmp_path, [regular("null.bin", b"\0" * (3 * 1024 * 1024))], "w:gz")
    with pytest.raises(IntakeRejectedError) as exc:
        extract_archive(archive, root)
    assert exc.value.grund is Ablehnung.KOMPRESSIONSRATE
    assert list(root.iterdir()) == []


def test_tar_too_many_members(tmp_path: Path, root: Path) -> None:
    archive = make_tar(tmp_path, [regular(f"{i}.txt", b"x") for i in range(4)], "w")
    with pytest.raises(IntakeRejectedError) as exc:
        extract_archive(archive, root, replace(DEFAULT_LIMITS, zip_eintraege=3))
    assert exc.value.grund is Ablehnung.ZU_VIELE_DATEIEN


def test_unknown_archive_is_refused(tmp_path: Path, root: Path) -> None:
    archive = tmp_path / "x.7z"
    archive.write_bytes(b"7z\xbc\xaf\x27\x1c" + b"\0" * 64)
    with pytest.raises(IntakeRejectedError) as exc:
        extract_archive(archive, root)
    assert exc.value.grund is Ablehnung.DEFEKTES_ARCHIV


def zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_package_formats_are_unpacked_one_level(root: Path) -> None:
    inner = zip_bytes({"tief.txt": b"x"})
    (root / "dist").mkdir()
    (root / "dist" / "paket-1.0-py3-none-any.whl").write_bytes(
        zip_bytes({"paket/__init__.py": b"", "innen.zip": inner})
    )
    (root / "anderes.zip").write_bytes(inner)
    result = expand_packages(root)
    assert result.entpackt == ("dist/paket-1.0-py3-none-any.whl",)
    assert (root / "dist" / "paket-1.0-py3-none-any.whl.inhalt" / "paket" / "__init__.py").exists()
    # Only one level: the archive inside the wheel and plain ZIPs stay packed.
    assert not (root / "dist" / "paket-1.0-py3-none-any.whl.inhalt" / "innen.zip.inhalt").exists()
    assert not (root / "anderes.zip.inhalt").exists()


def test_taken_target_name_keeps_the_archive_packed(root: Path) -> None:
    (root / "x.dxt").write_bytes(zip_bytes({"manifest.json": b"{}"}))
    (root / "x.dxt.inhalt").mkdir()
    (root / "x.dxt.inhalt" / "gefaelscht.txt").write_bytes(b"x")
    assert expand_packages(root).entpackt == ()


def test_nested_package_shares_the_package_limits(root: Path) -> None:
    (root / "gross.vsix").write_bytes(zip_bytes({f"{i}.txt": b"x" for i in range(5)}))
    result = expand_packages(root, replace(DEFAULT_LIMITS, zip_eintraege=3))
    assert result.entpackt == ()
    assert result.abgelehnt == (("gross.vsix", "zu_viele_dateien"),)
    assert not (root / "gross.vsix.inhalt").exists()


def test_scan_reports_the_content_of_a_wheel(root: Path) -> None:
    (root / "evil.whl").write_bytes(zip_bytes({"evil.pth": b"import os; os.system('echo hi')\n"}))
    result = scan_prepared(root, Eingabe.ZIP, ScanArt.SCHNELL)
    paths = {e.path for e in result.inventory.entries}
    assert "evil.whl.inhalt/evil.pth" in paths
    assert not any(f.rule_id == "LB-A07-archiv-im-paket" for f in result.pipeline.findings)


def test_scan_reports_a_package_that_stayed_packed(root: Path) -> None:
    (root / "kaputt.whl").write_bytes(b"PK\x03\x04" + b"\0" * 40)
    result = scan_prepared(root, Eingabe.ZIP, ScanArt.SCHNELL)
    assert any(f.rule_id == "LB-A07-archiv-im-paket" for f in result.pipeline.findings)
