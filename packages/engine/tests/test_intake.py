"""S1-2: hostile archives, selections and texts are refused before anything leaves the scratch."""

import io
import stat
import unicodedata
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from luibui_scan.intake import (
    DEFAULT_LIMITS,
    Ablehnung,
    IntakeRejectedError,
    Limits,
    accept_directory,
    accept_file,
    accept_selection,
    accept_text,
    extract_zip,
)
from luibui_scan.intake.paths import check_path
from luibui_scan.intake.sources import TEXT_NAME

SMALL = replace(DEFAULT_LIMITS, auswahl_dateien=3, zip_eintraege=3, tiefe=3)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    d = tmp_path / "scratch"
    d.mkdir()
    return d


def make_zip(tmp_path: Path, entries: list[zipfile.ZipInfo | tuple[str, bytes]]) -> Path:
    path = tmp_path / "upload.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in entries:
            if isinstance(entry, zipfile.ZipInfo):
                zf.writestr(entry, b"echo harmlos")
            else:
                zf.writestr(entry[0], entry[1])
    return path


def rejected(reason: Ablehnung, fn: object, *args: object) -> IntakeRejectedError:
    with pytest.raises(IntakeRejectedError) as exc:
        fn(*args)  # type: ignore[operator]
    assert exc.value.grund is reason
    return exc.value


def tree(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


# --- paths -----------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["SKILL.md", "src/server.py", "a/b/c", "ümlaut ä.md", ".hidden"])
def test_valid_paths(name: str) -> None:
    assert check_path(name, DEFAULT_LIMITS) == name


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("../evil", Ablehnung.PFAD_AUSSERHALB),
        ("a/../../evil", Ablehnung.PFAD_AUSSERHALB),
        ("/etc/cron.d/x", Ablehnung.PFAD_AUSSERHALB),
        ("C:/Windows/x", Ablehnung.PFAD_AUSSERHALB),
        ("c:x", Ablehnung.PFAD_AUSSERHALB),
        ("a\\..\\b", Ablehnung.UNGUELTIGER_NAME),
        ("a\x00.md", Ablehnung.UNGUELTIGER_NAME),
        ("a\nb.md", Ablehnung.UNGUELTIGER_NAME),
        ("a\x1b[31m.md", Ablehnung.UNGUELTIGER_NAME),
        ("", Ablehnung.UNGUELTIGER_NAME),
        ("a//b", Ablehnung.UNGUELTIGER_NAME),
        ("./a", Ablehnung.UNGUELTIGER_NAME),
        ("a/", Ablehnung.UNGUELTIGER_NAME),
        ("x" * 256, Ablehnung.NAME_ZU_LANG),
        ("/".join(["abcdefgh"] * 120), Ablehnung.NAME_ZU_LANG),
        ("/".join(["d"] * 21), Ablehnung.ZU_TIEF),
    ],
)
def test_invalid_paths(name: str, reason: Ablehnung) -> None:
    rejected(reason, check_path, name, DEFAULT_LIMITS)


def test_bidi_in_name_is_left_to_the_analyzer() -> None:
    name = "evil\u202egpj.md"
    assert check_path(name, DEFAULT_LIMITS) == name


# --- ZIP -------------------------------------------------------------------------------------


def test_benign_zip(tmp_path: Path, root: Path) -> None:
    archive = make_zip(tmp_path, [("SKILL.md", b"# Skill\n"), ("src/a.py", b"print(1)\n")])
    assert extract_zip(archive, root) == ["SKILL.md", "src/a.py"]
    assert tree(root) == ["SKILL.md", "src/a.py"]
    assert (root / "src/a.py").read_bytes() == b"print(1)\n"
    assert stat.S_IMODE((root / "SKILL.md").stat().st_mode) == 0o600
    assert stat.S_IMODE((root / "src").stat().st_mode) == 0o700


def test_zip_directory_entries(tmp_path: Path, root: Path) -> None:
    archive = make_zip(tmp_path, [("docs/", b""), ("docs/a.md", b"a")])
    assert extract_zip(archive, root) == ["docs/a.md"]


def test_nested_archive_stays_packed(tmp_path: Path, root: Path) -> None:
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as zf:
        zf.writestr("inner.md", b"x")
    archive = make_zip(tmp_path, [("inner.zip", inner.getvalue())])
    assert extract_zip(archive, root) == ["inner.zip"]
    assert tree(root) == ["inner.zip"]


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("../../app/main.py", Ablehnung.PFAD_AUSSERHALB),
        ("/etc/passwd", Ablehnung.PFAD_AUSSERHALB),
        ("a\\..\\..\\b", Ablehnung.UNGUELTIGER_NAME),
    ],
)
def test_zip_slip_is_refused_before_writing(
    tmp_path: Path, root: Path, name: str, reason: Ablehnung
) -> None:
    archive = make_zip(tmp_path, [("first.md", b"ok"), (name, b"echo harmlos")])
    rejected(reason, extract_zip, archive, root)
    assert tree(root) == []
    assert sorted(p.name for p in tmp_path.rglob("*") if p.is_file()) == ["upload.zip"]


def patch(archive: Path, old: bytes, new: bytes) -> None:
    archive.write_bytes(archive.read_bytes().replace(old, new))


def test_nul_in_zip_name(tmp_path: Path, root: Path) -> None:
    """zipfile would silently cut the name at NUL; the original name must be checked."""
    archive = make_zip(tmp_path, [("safe.md#../../x", b"x")])
    patch(archive, b"safe.md#", b"safe.md\x00")
    exc = rejected(Ablehnung.PFAD_AUSSERHALB, extract_zip, archive, root)
    assert exc.pfad == "safe.md\x00../../x"


def test_nul_in_zip_name_without_traversal(tmp_path: Path, root: Path) -> None:
    archive = make_zip(tmp_path, [("safe.md#.sh", b"x")])
    patch(archive, b"safe.md#", b"safe.md\x00")
    rejected(Ablehnung.UNGUELTIGER_NAME, extract_zip, archive, root)


@pytest.mark.parametrize("mode", [stat.S_IFLNK | 0o777, stat.S_IFCHR | 0o644, stat.S_IFIFO | 0o644])
def test_symlink_and_special_entries(tmp_path: Path, root: Path, mode: int) -> None:
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = mode << 16
    archive = make_zip(tmp_path, [info])
    rejected(Ablehnung.VERKNUEPFUNG, extract_zip, archive, root)
    assert not (root / "link").exists()


def test_windows_reparse_point(tmp_path: Path, root: Path) -> None:
    info = zipfile.ZipInfo("junction")
    info.create_system = 0
    info.external_attr = 0x400
    rejected(Ablehnung.VERKNUEPFUNG, extract_zip, make_zip(tmp_path, [info]), root)


def test_encrypted_entry(tmp_path: Path, root: Path) -> None:
    archive = make_zip(tmp_path, [("secret.md", b"x")])
    data = bytearray(archive.read_bytes())
    cd = data.rfind(b"PK\x01\x02")
    data[cd + 8] |= 0x1  # general purpose flag, bit 0 = encrypted
    archive.write_bytes(bytes(data))
    rejected(Ablehnung.VERSCHLUESSELT, extract_zip, archive, root)


@pytest.mark.parametrize(
    "names",
    [
        ["README.md", "readme.md"],
        [unicodedata.normalize("NFC", "ä.md"), unicodedata.normalize("NFD", "ä.md")],
        ["a", "a/b.md"],
        ["a/b.md", "a"],
    ],
)
def test_colliding_names(tmp_path: Path, root: Path, names: list[str]) -> None:
    archive = make_zip(tmp_path, [(n, b"x") for n in names])
    rejected(Ablehnung.DOPPELTER_NAME, extract_zip, archive, root)


def test_exact_duplicate_entries(tmp_path: Path, root: Path) -> None:
    path = tmp_path / "dup.zip"
    with (
        pytest.warns(UserWarning, match="Duplicate name"),
        zipfile.ZipFile(path, "w") as zf,
    ):
        zf.writestr("SKILL.md", b"harmlos")
        zf.writestr("SKILL.md", b"anders")
    rejected(Ablehnung.DOPPELTER_NAME, extract_zip, path, root)


def test_zip_bomb_single_entry(tmp_path: Path, root: Path) -> None:
    archive = make_zip(tmp_path, [("bomb.txt", b"\0" * (2 * 1024 * 1024))])
    rejected(Ablehnung.KOMPRESSIONSRATE, extract_zip, archive, root)
    assert tree(root) == []


def test_zip_bomb_many_small_entries(tmp_path: Path, root: Path) -> None:
    entries = [(f"f{i}.txt", b"\0" * 200_000) for i in range(20)]
    rejected(Ablehnung.KOMPRESSIONSRATE, extract_zip, make_zip(tmp_path, entries), root)


def test_small_repetitive_file_passes(tmp_path: Path, root: Path) -> None:
    archive = make_zip(tmp_path, [("SKILL.md", b"# Skill\n" + b" " * 20_000 + b"text\n" * 300)])
    assert extract_zip(archive, root) == ["SKILL.md"]


def test_unpacked_size_limit(tmp_path: Path, root: Path) -> None:
    limits = replace(DEFAULT_LIMITS, zip_entpackt_bytes=1000)
    archive = make_zip(tmp_path, [("a.bin", bytes(range(256)) * 3), ("b.bin", bytes(range(256)))])
    rejected(Ablehnung.ZU_GROSS, extract_zip, archive, root, limits)


def test_packed_size_limit(tmp_path: Path, root: Path) -> None:
    archive = make_zip(tmp_path, [("a.md", b"x")])
    limits = replace(DEFAULT_LIMITS, zip_gepackt_bytes=10)
    rejected(Ablehnung.ZU_GROSS, extract_zip, archive, root, limits)


def test_entry_limit(tmp_path: Path, root: Path) -> None:
    archive = make_zip(tmp_path, [(f"{i}.md", b"x") for i in range(4)])
    rejected(Ablehnung.ZU_VIELE_DATEIEN, extract_zip, archive, root, SMALL)


def test_depth_limit(tmp_path: Path, root: Path) -> None:
    archive = make_zip(tmp_path, [("a/b/c/d.md", b"x")])
    rejected(Ablehnung.ZU_TIEF, extract_zip, archive, root, SMALL)


def test_lying_size_header(tmp_path: Path, root: Path) -> None:
    """The central directory claims fewer bytes than the data holds; zipfile's CRC check fails."""
    archive = make_zip(tmp_path, [("a.md", b"A" * 5000)])
    data = bytearray(archive.read_bytes())
    cd = data.rfind(b"PK\x01\x02")
    data[cd + 24 : cd + 28] = (10).to_bytes(4, "little")
    archive.write_bytes(bytes(data))
    rejected(Ablehnung.DEFEKTES_ARCHIV, extract_zip, archive, root)


def test_overlapping_entries(tmp_path: Path, root: Path) -> None:
    archive = make_zip(tmp_path, [("a.md", b"A" * 100), ("b.md", b"B" * 100)])
    data = bytearray(archive.read_bytes())
    second_cd = data.rfind(b"PK\x01\x02")
    data[second_cd + 42 : second_cd + 46] = (0).to_bytes(4, "little")
    archive.write_bytes(bytes(data))
    rejected(Ablehnung.DEFEKTES_ARCHIV, extract_zip, archive, root)


def test_not_a_zip(tmp_path: Path, root: Path) -> None:
    path = tmp_path / "x.zip"
    path.write_bytes(b"LUIBUI-TESTFIXTURE: kein Archiv")
    rejected(Ablehnung.DEFEKTES_ARCHIV, extract_zip, path, root)


def test_existing_symlink_in_root_is_not_followed(tmp_path: Path, root: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "a").symlink_to(outside)
    archive = make_zip(tmp_path, [("a/x.md", b"x")])
    rejected(Ablehnung.VERKNUEPFUNG, extract_zip, archive, root)
    assert list(outside.iterdir()) == []


# --- single file, selection, text ------------------------------------------------------------


def test_single_file(root: Path) -> None:
    assert accept_file("SKILL.md", io.BytesIO(b"# Skill"), root) == "SKILL.md"
    assert tree(root) == ["SKILL.md"]


@pytest.mark.parametrize("name", ["../x.md", "dir/x.md", "", "a\x00b"])
def test_single_file_bad_name(root: Path, name: str) -> None:
    with pytest.raises(IntakeRejectedError):
        accept_file(name, io.BytesIO(b"x"), root)
    assert tree(root) == []


def test_single_file_size_counted_while_writing(root: Path) -> None:
    limits = replace(DEFAULT_LIMITS, einzeldatei_bytes=100)
    rejected(Ablehnung.ZU_GROSS, accept_file, "a.bin", io.BytesIO(b"x" * 101), root, limits)


def test_selection_keeps_relative_paths(root: Path) -> None:
    items = [("plugin/SKILL.md", io.BytesIO(b"a")), ("plugin/src/x.py", io.BytesIO(b"b"))]
    assert accept_selection(items, root) == ["plugin/SKILL.md", "plugin/src/x.py"]
    assert tree(root) == ["plugin/SKILL.md", "plugin/src/x.py"]


@pytest.mark.parametrize(
    ("paths", "reason"),
    [
        (["ok.md", "../../etc/cron.d/x"], Ablehnung.PFAD_AUSSERHALB),
        (["Ok.md", "ok.md"], Ablehnung.DOPPELTER_NAME),
        (["a.md", "b.md", "c.md", "d.md"], Ablehnung.ZU_VIELE_DATEIEN),
        (["a/b/c/d.md"], Ablehnung.ZU_TIEF),
    ],
)
def test_selection_manipulated_paths(root: Path, paths: list[str], reason: Ablehnung) -> None:
    items = [(p, io.BytesIO(b"x")) for p in paths]
    rejected(reason, accept_selection, items, root, SMALL)
    assert not (root.parent / "etc").exists()


def test_selection_total_size(root: Path) -> None:
    limits = replace(DEFAULT_LIMITS, auswahl_bytes=150)
    items = [("a", io.BytesIO(b"x" * 100)), ("b", io.BytesIO(b"x" * 100))]
    rejected(Ablehnung.ZU_GROSS, accept_selection, items, root, limits)


def test_text(root: Path) -> None:
    assert accept_text("# Skill\nHallo \U000e0041", root) == TEXT_NAME
    assert (root / TEXT_NAME).read_text("utf-8") == "# Skill\nHallo \U000e0041"


def test_text_limit(root: Path) -> None:
    limits = Limits(text_bytes=10)
    rejected(Ablehnung.ZU_GROSS, accept_text, "ä" * 6, root, limits)


def test_rejection_text_has_no_package_content() -> None:
    exc = IntakeRejectedError(Ablehnung.PFAD_AUSSERHALB, "<img src=x onerror=alert(1)>")
    assert "<img" not in exc.text
    assert "'<img" in str(exc)


# --- local folder (CLI) ----------------------------------------------------------------------


def test_directory_is_copied_like_a_selection(tmp_path: Path, root: Path) -> None:
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "SKILL.md").write_bytes(b"# Skill")
    (src / "sub/a.py").write_bytes(b"print(1)")
    (src / ".git/hooks").mkdir(parents=True)
    (src / ".git/hooks/pre-commit").write_bytes(b"echo harmlos")
    assert accept_directory(src, root) == ["SKILL.md", "sub/a.py"]
    assert tree(root) == ["SKILL.md", "sub/a.py"]


def test_directory_symlink_is_refused(tmp_path: Path, root: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.md").write_bytes(b"x")
    (src / "passwd").symlink_to("/etc/passwd")
    rejected(Ablehnung.VERKNUEPFUNG, accept_directory, src, root)
    assert not (root / "passwd").exists()


def test_directory_limits_apply(tmp_path: Path, root: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    for i in range(4):
        (src / f"{i}.md").write_bytes(b"x")
    rejected(Ablehnung.ZU_VIELE_DATEIEN, accept_directory, src, root, SMALL)
