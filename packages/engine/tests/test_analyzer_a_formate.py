"""Scanner-Matrix INV-01, BIN-01, COD-10, ARC-02, ARC-03 (Prüfkatalog A04, A06, A13–A15)."""

import importlib.util
import io
import pickle
import zipfile
from pathlib import Path

import pytest

from luibui_scan.analyzers.a_dateien import DateienAnalyzer
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory, detect_kind
from luibui_scan.models import Finding, Pruefumfang, ScanArt, Schwere


def analyze(tmp_path: Path, files: dict[str, bytes | str]) -> list[Finding]:
    for rel, content in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)
    inv = build_inventory(tmp_path)
    ctx = ScanContext(
        root=tmp_path,
        scan_art=ScanArt.INTENSIV,
        pruefumfang=Pruefumfang.PAKET,
        inventory=inv.entries,
    )
    return DateienAnalyzer().analyze(ctx)


def rules(findings: list[Finding]) -> list[str]:
    return sorted(f.rule_id for f in findings)


def by_rule(findings: list[Finding], rule: str) -> Finding:
    return next(f for f in findings if f.rule_id == rule)


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32 + b"IEND\xaeB`\x82"


def zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


# --- INV-01: type by content -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("head", "kind"),
    [
        (pickle.dumps({"a": 1}, protocol=2), "pickle"),
        (pickle.dumps({"a": 1}, protocol=4), "pickle"),
        ((7).to_bytes(8, "little") + b'{"a":1}', "safetensors"),
        (b"GGUF\x03\x00\x00\x00" + b"\x00" * 16, "gguf"),
        (b"\x89HDF\r\n\x1a\n" + b"\x00" * 16, "hdf5"),
        (b"\x1c\x00\x00\x00TFL3" + b"\x00" * 16, "tflite"),
        (b"!<arch>\ndebian-binary   ", "deb"),
        (b"\xed\xab\xee\xdb\x03\x00" + b"\x00" * 16, "rpm"),
        (importlib.util.MAGIC_NUMBER + b"\x00" * 12 + b"\xe3\x00\x00", "pyc"),
        (b"ab\r\nnur Text, kein Bytecode", "text"),
        (b"\x80\x02 kein pickle? doch", "pickle"),
    ],
)
def test_detect_kind_by_content(head: bytes, kind: str) -> None:
    assert detect_kind(head) == kind


# --- BIN-01, COD-10 --------------------------------------------------------------------------


def test_deb_and_rpm_are_programs(tmp_path: Path) -> None:
    found = analyze(tmp_path, {"x.deb": b"!<arch>\ndebian-binary   " + b"\0" * 40})
    assert by_rule(found, "LB-A04-programmdatei").schwere is Schwere.H


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("setup.msi", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 64),
        ("app.apk", zip_bytes({"AndroidManifest.xml": b"x"})),
        ("tool.dmg", b"\x78\xda" + b"\0" * 64),
    ],
)
def test_installers_are_reported(tmp_path: Path, name: str, content: bytes) -> None:
    assert "LB-A04-installationspaket" in rules(analyze(tmp_path, {name: content}))


def test_text_named_like_an_installer_is_not(tmp_path: Path) -> None:
    assert "LB-A04-installationspaket" not in rules(analyze(tmp_path, {"notes.pkg": "nur Text"}))


def test_bytecode_without_source_is_found_by_content(tmp_path: Path) -> None:
    pyc = importlib.util.MAGIC_NUMBER + b"\x00" * 12 + b"\xe3\x00\x00\x00"
    assert "LB-A06-kompiliert-ohne-quelle" in rules(analyze(tmp_path, {"hilfe.dat": pyc}))


# --- ARC-02: A13 -----------------------------------------------------------------------------


def test_git_attribute_driver(tmp_path: Path) -> None:
    found = analyze(tmp_path, {".gitattributes": "*.md text\n*.txt filter=evil\n"})
    f = by_rule(found, "LB-A13-git-treiber")
    assert (f.schwere, f.zeile) == (Schwere.M, 2)


def test_git_attributes_without_driver_and_lfs_filter(tmp_path: Path) -> None:
    text = "* text=auto\n*.bin filter=lfs diff=lfs merge=lfs -text\n# filter=x\n"
    assert "LB-A13-git-treiber" not in rules(analyze(tmp_path, {".gitattributes": text}))


def test_lfs_pointer_is_marked_unchecked(tmp_path: Path) -> None:
    pointer = "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 12\n"
    found = analyze(tmp_path, {"model.bin": pointer, "README.md": "# ok"})
    assert by_rule(found, "LB-A13-lfs-zeiger").schwere is Schwere.I


# --- ARC-03: A14 -----------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["rechnung.pdf.exe", "Foto.JPG.scr", "docs/liesmich.txt.js"])
def test_double_extension(tmp_path: Path, name: str) -> None:
    assert by_rule(analyze(tmp_path, {name: "x"}), "LB-A14-doppelendung").schwere is Schwere.M


@pytest.mark.parametrize("name", ["con", "NUL.txt", "a/com1.md", "lpt9"])
def test_reserved_windows_names(tmp_path: Path, name: str) -> None:
    assert "LB-A14-reservierter-name" in rules(analyze(tmp_path, {name: "x"}))


@pytest.mark.parametrize("name", ["jquery.min.js", "setup.cfg.txt", "console.md", "a/nullable.py"])
def test_ordinary_names(tmp_path: Path, name: str) -> None:
    assert not any(r.startswith("LB-A14") for r in rules(analyze(tmp_path, {name: "x"})))


# --- INV-01: A15 -----------------------------------------------------------------------------


def test_png_with_zip_is_a_polyglot(tmp_path: Path) -> None:
    found = analyze(tmp_path, {"bild.png": PNG + zip_bytes({"a.sh": b"echo hi"})})
    assert by_rule(found, "LB-A15-angehaengte-daten").schwere is Schwere.H


def test_png_with_appended_bytes(tmp_path: Path) -> None:
    found = analyze(tmp_path, {"bild.png": PNG + b"A" * 2048})
    assert by_rule(found, "LB-A15-angehaengte-daten").schwere is Schwere.M


def test_plain_png_and_pdf(tmp_path: Path) -> None:
    pdf = b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    found = analyze(tmp_path, {"bild.png": PNG, "doc.pdf": pdf})
    assert "LB-A15-angehaengte-daten" not in rules(found)
