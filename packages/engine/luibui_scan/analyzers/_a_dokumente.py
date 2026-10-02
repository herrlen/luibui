"""Analyzer A, part 5: documents, images, tables and notebooks (Prüfkatalog A03, A20, A21, B21,
G08; Scanner-Matrix DOC-01 bis DOC-04, DAT-02, COD-02).

Only bytes and XML text are searched. No PDF, Office or image library parses the files, so a
malformed file cannot attack a parser. Office files are ZIP containers read in memory.
"""

import re
import zipfile
from collections.abc import Iterator
from pathlib import PurePosixPath
from typing import Literal

from luibui_scan.analyzers._a_ausfuehrung import _SCRIPT_RISK
from luibui_scan.analyzers._common import finding, read_bytes, read_json, read_text, visible
from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.models import Achse, Ebene, Finding, Schwere

MAX_DOC = 10 * 1024 * 1024
MAX_XML = 2 * 1024 * 1024

# --- A21 PDF -------------------------------------------------------------------------------

_PDF_NAME = re.compile(rb"/([A-Za-z0-9#]+)")
_PDF_ACTIVE = {
    b"JavaScript": "JavaScript",
    b"JS": "JavaScript",
    b"Launch": "Programmstart (/Launch)",
    b"EmbeddedFile": "eingebettete Datei",
    b"RichMedia": "Flash/Rich Media",
    b"XFA": "XFA-Formular",
}
_PDF_AUTO = {b"OpenAction": "Aktion beim Öffnen", b"AA": "automatische Aktion"}


def _pdf_names(data: bytes) -> set[bytes]:
    """PDF names, with ``#xx`` escapes resolved (``/J#61vaScript`` is ``/JavaScript``)."""
    names: set[bytes] = set()
    for m in _PDF_NAME.finditer(data):
        raw = m.group(1)
        if b"#" in raw:
            raw = re.sub(rb"#([0-9A-Fa-f]{2})", lambda h: bytes([int(h.group(1), 16)]), raw)
        names.add(raw)
    return names


def _a21_pdf(ctx: ScanContext, entry: InventoryEntry) -> Iterator[Finding]:
    names = _pdf_names(read_bytes(ctx, entry, MAX_DOC))
    active = sorted({label for n, label in _PDF_ACTIVE.items() if n in names})
    auto = sorted({label for n, label in _PDF_AUTO.items() if n in names})
    if not active and not auto:
        return
    yield finding(
        rule_id="LB-A21-pdf-aktiv",
        ebene=Ebene.A,
        schwere=Schwere.H if active else Schwere.M,
        titel="PDF mit aktiven Inhalten" if active else "PDF führt beim Öffnen eine Aktion aus",
        erklaerung=(
            "Das PDF enthält Bestandteile, die beim Öffnen Code ausführen, Programme starten oder "
            "Dateien mitbringen können. Ein Handbuch oder Beispiel braucht das nicht."
            + " Komprimierte Objektströme werden nicht entpackt, die Liste kann unvollständig sein."
        ),
        datei=entry.path,
        zeile=None,
        beleg=", ".join([*active, *auto]),
        fix="Das PDF ohne Skripte, Aktionen und Anhänge neu exportieren.",
        fix_prompt=f"Exportiere {entry.path} neu als einfaches PDF ohne Skripte und Anhänge.",
        normbezug=("OWASP-ASI05",),
    )


# --- A21 Office ------------------------------------------------------------------------------

_OOXML = frozenset(
    {".docx", ".docm", ".dotx", ".dotm", ".xlsx", ".xlsm", ".xltm", ".pptx", ".pptm", ".potm"}
)
_OLE_EXT = frozenset({".doc", ".dot", ".xls", ".xlt", ".ppt", ".pot", ".msg"})
_EXTERNAL_TEMPLATE = re.compile(
    r'Type="[^"]*/(attachedTemplate|oleObject|frame|subDocument)"[^>]*TargetMode="External"'
    r'|TargetMode="External"[^>]*Type="[^"]*/(attachedTemplate|oleObject|frame|subDocument)"'
)
_DDE = re.compile(r"\bDDE(AUTO)?\b|\bddeService=", re.IGNORECASE)
_VBA_OLE = ("_VBA_PROJECT".encode("utf-16-le"), b"Attribute VB_Name")


def _office_problems(ctx: ScanContext, entry: InventoryEntry) -> list[str]:
    problems: list[str] = []
    try:
        with zipfile.ZipFile(ctx.resolve(entry.path)) as zf:
            for info in zf.infolist():
                name = info.filename.lower()
                if name.endswith("vbaproject.bin"):
                    problems.append("Makros (VBA)")
                elif name.endswith((".rels", ".xml")) and info.file_size <= MAX_XML:
                    with zf.open(info) as src:
                        text = src.read(MAX_XML).decode("utf-8", errors="replace")
                    if name.endswith(".rels") and _EXTERNAL_TEMPLATE.search(text):
                        problems.append("externe Vorlage oder eingebettetes Objekt aus dem Netz")
                    elif _DDE.search(text) and ("instr" in text or "ddeLink" in text):
                        problems.append("DDE-Feld, das Programme starten kann")
    except (zipfile.BadZipFile, NotImplementedError, EOFError, OSError):
        return ["Datei ließ sich nicht lesen"]
    return sorted(set(problems))


def _a21_office(ctx: ScanContext, entry: InventoryEntry, ext: str) -> Iterator[Finding]:
    if ext in _OOXML and entry.kind == "zip":
        problems = _office_problems(ctx, entry)
    elif ext in _OLE_EXT and entry.kind == "ole":
        data = read_bytes(ctx, entry, MAX_DOC)
        problems = ["Makros (VBA)"] if any(m in data for m in _VBA_OLE) else []
    else:
        return
    if not problems:
        return
    yield finding(
        rule_id="LB-A21-office-aktiv",
        ebene=Ebene.A,
        schwere=Schwere.H,
        titel="Office-Dokument mit Makros oder Nachladen",
        erklaerung=(
            "Das Dokument kann beim Öffnen Code ausführen oder Inhalte aus dem Netz laden. So "
            "werden Schadprogramme über harmlos wirkende Dokumente verteilt."
        ),
        datei=entry.path,
        zeile=None,
        beleg=", ".join(problems),
        fix="Das Dokument ohne Makros und externe Verknüpfungen neu speichern (z. B. als .docx).",
        fix_prompt=f"Speichere {entry.path} ohne Makros und externe Verknüpfungen neu.",
        normbezug=("OWASP-ASI05",),
    )


# --- B21 SVG and XML -----------------------------------------------------------------------

_SVG_ACTIVE = re.compile(
    r"<script\b|\son[a-z]+\s*=|(href|src)\s*=\s*[\"']\s*javascript:|<foreignObject\b",
    re.IGNORECASE,
)
_XXE = re.compile(r"<!ENTITY\s+%?\s*\S+\s+(SYSTEM|PUBLIC)\b", re.IGNORECASE)


def _b21(ctx: ScanContext, entry: InventoryEntry, ext: str) -> Iterator[Finding]:
    if entry.kind != "text" or ext not in (".svg", ".xml", ".xsl", ".xslt", ".plist"):
        return
    text = read_text(ctx, entry, MAX_XML)
    m = _XXE.search(text) or (_SVG_ACTIVE.search(text) if ext == ".svg" else None)
    if m is None:
        return
    xxe = m.re is _XXE
    line = text.count("\n", 0, m.start()) + 1
    yield finding(
        rule_id="LB-B21-aktive-inhalte",
        ebene=Ebene.B,
        schwere=Schwere.M,
        titel="XML lädt externe Dateien (XXE)" if xxe else "SVG-Bild enthält Skript",
        erklaerung=(
            "Eine externe Entität liest beim Verarbeiten Dateien oder Adressen ein (XML External "
            "Entity). So lassen sich lokale Dateien auslesen."
            if xxe
            else "Das Bild führt JavaScript aus, sobald es im Browser oder in einer Vorschau "
            "geöffnet wird."
        ),
        datei=entry.path,
        zeile=line,
        beleg=visible(text.split("\n")[line - 1]),
        fix="Externe Entitäten entfernen."
        if xxe
        else "Skripte und Ereignisse aus dem SVG entfernen.",
        fix_prompt=f"Entferne in {entry.path}, Zeile {line}, "
        + ("die externe Entität." if xxe else "das Skript."),
        normbezug=("OWASP-LLM05",),
    )


# --- G08 location in photos ----------------------------------------------------------------


def _tiff_has_gps(tiff: bytes) -> bool:
    """True if the Exif block points to a GPS directory with a latitude or longitude."""
    if len(tiff) < 8 or tiff[:2] not in (b"II", b"MM"):
        return False
    order: Literal["little", "big"] = "little" if tiff[:2] == b"II" else "big"

    def u16(o: int) -> int:
        return int.from_bytes(tiff[o : o + 2], order) if o + 2 <= len(tiff) else -1

    def u32(o: int) -> int:
        return int.from_bytes(tiff[o : o + 4], order) if o + 4 <= len(tiff) else -1

    def entries(offset: int) -> Iterator[tuple[int, int]]:
        count = u16(offset)
        if count < 0 or count > 512:
            return
        for i in range(count):
            base = offset + 2 + 12 * i
            if base + 12 > len(tiff):
                return
            yield u16(base), u32(base + 8)

    ifd0 = u32(4)
    gps = next((value for tag, value in entries(ifd0) if tag == 0x8825), None)
    if gps is None or gps <= 0:
        return False
    return any(tag in (0x0002, 0x0004) for tag, _ in entries(gps))


def _exif_blocks(data: bytes, kind: str) -> Iterator[bytes]:
    if kind == "jpeg":
        pos = 2
        while pos + 4 <= len(data) and data[pos] == 0xFF:
            marker = data[pos + 1]
            size = int.from_bytes(data[pos + 2 : pos + 4], "big")
            if marker == 0xE1 and data[pos + 4 : pos + 10] == b"Exif\x00\x00":
                yield data[pos + 10 : pos + 2 + size]
            if marker in (0xDA, 0xD9) or size < 2:
                return
            pos += 2 + size
    elif kind == "png":
        pos = 8
        while pos + 8 <= len(data):
            size = int.from_bytes(data[pos : pos + 4], "big")
            ctype = data[pos + 4 : pos + 8]
            if ctype == b"eXIf":
                yield data[pos + 8 : pos + 8 + size]
            if ctype == b"IEND":
                return
            pos += 12 + size


def _g08(ctx: ScanContext, entry: InventoryEntry) -> Iterator[Finding]:
    if entry.kind not in ("jpeg", "png") or entry.size > MAX_DOC:
        return
    data = read_bytes(ctx, entry, MAX_DOC)
    if not any(_tiff_has_gps(block) for block in _exif_blocks(data, entry.kind)):
        return
    yield finding(
        rule_id="LB-G08-standort-im-bild",
        ebene=Ebene.G,
        schwere=Schwere.M,
        achse=Achse.DSGVO,
        titel="Foto enthält Standortdaten",
        erklaerung=(
            "In den Exif-Daten des Bildes stehen GPS-Koordinaten. Sie verraten, wo das Foto "
            "aufgenommen wurde, oft die Wohnung oder das Büro einer Person."
        ),
        datei=entry.path,
        zeile=None,
        beleg="Exif: GPS-Koordinaten vorhanden (Werte nicht angezeigt)",
        fix="Die Metadaten entfernen, z. B. mit `exiftool -gps:all= bild.jpg`.",
        fix_prompt=f"Entferne die GPS-Daten aus {entry.path}.",
        normbezug=("DSGVO-Art-5",),
    )


# --- A20 formulas in tables ----------------------------------------------------------------

_FORMULA = re.compile(r"(?:^|[,;\t])\s*\"?([=+\-@][A-Za-z_][A-Za-z0-9_.]*\s*\()", re.MULTILINE)
_FORMULA_RISK = re.compile(
    r"^[=+\-@]\s*(HYPERLINK|WEBSERVICE|IMPORTXML|IMPORTDATA|IMPORTHTML|IMPORTRANGE|IMAGE|"
    r"CALL|REGISTER|EXEC|DDE|cmd)\b",
    re.IGNORECASE,
)


def _a20(ctx: ScanContext, entry: InventoryEntry, ext: str) -> Iterator[Finding]:
    if entry.kind != "text" or ext not in (".csv", ".tsv"):
        return
    text = read_text(ctx, entry, MAX_DOC)
    hits = list(_FORMULA.finditer(text))
    if not hits:
        return
    risky = [m for m in hits if _FORMULA_RISK.match(m.group(1))] or [
        m for m in hits if "|" in text[m.start(1) : text.find("\n", m.start(1))]
    ]
    m = (risky or hits)[0]
    line = text.count("\n", 0, m.start(1)) + 1
    yield finding(
        rule_id="LB-A20-formel-in-tabelle",
        ebene=Ebene.A,
        schwere=Schwere.H if risky else Schwere.N,
        titel="Tabelle enthält Formeln, die Daten senden oder Befehle starten"
        if risky
        else "Tabelle enthält Formeln",
        erklaerung=(
            f"{len(hits)} Zellen beginnen mit einer Formel. Öffnet jemand die Datei in einer "
            "Tabellenkalkulation, werden sie ausgeführt"
            + (
                " und können Daten an fremde Adressen schicken oder Programme starten."
                if risky
                else "."
            )
        ),
        datei=entry.path,
        zeile=line,
        beleg=visible(text.split("\n")[line - 1]),
        fix="Formeln als Text ablegen (Apostroph voranstellen) oder entfernen.",
        fix_prompt=(
            f"Stelle in {entry.path} jeder Zelle, die mit =, +, - oder @ beginnt, ein ' voran."
        ),
        normbezug=("OWASP-LLM05",),
    )


# --- A03 notebooks -------------------------------------------------------------------------

_SHELL_CELL = re.compile(r"^\s*(!|%%(bash|sh|script)|%(system|sx)\b)", re.MULTILINE)


def _notebook(ctx: ScanContext, entry: InventoryEntry, ext: str) -> Iterator[Finding]:
    if ext != ".ipynb" or entry.kind != "text":
        return
    data = read_json(ctx, entry)
    cells = data.get("cells") if isinstance(data, dict) else None
    if not isinstance(cells, list):
        return
    for index, cell in enumerate(cells, start=1):
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        source = cell.get("source")
        code = "".join(source) if isinstance(source, list) else str(source or "")
        if not _SHELL_CELL.search(code):
            continue
        m = _SCRIPT_RISK.search(code)
        if m is None:
            continue
        yield finding(
            rule_id="LB-A03-installationsskript",
            ebene=Ebene.A,
            schwere=Schwere.H,
            titel="Notebook-Zelle lädt Code herunter und führt ihn aus",
            erklaerung=(
                "Eine Shell-Zelle des Notebooks lädt Code aus dem Netz und führt ihn aus, sobald "
                "jemand das Notebook durchlaufen lässt."
            ),
            datei=entry.path,
            zeile=None,
            beleg=visible(f"Zelle {index}: {m.group(0)}"),
            fix="Abhängigkeiten über den Paketmanager mit fester Version installieren.",
            fix_prompt=f"Ersetze in {entry.path}, Zelle {index}, das Nachladen.",
            normbezug=("OWASP-ASI05", "OWASP-LLM03"),
        )
        return


# --- G07 personal data in data files -------------------------------------------------------

_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]{1,64}@([A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,24}(?![\w-])")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?\b")
_EXAMPLE_DOMAIN = re.compile(r"@(.+\.)?(example|invalid|test|localhost)(\.[a-z]+)?$", re.I)
DATA_EXT = frozenset({".csv", ".tsv", ".jsonl", ".ndjson"})
MIN_EMAILS = 5


def _iban_ok(raw: str) -> bool:
    iban = raw.replace(" ", "")
    if not 15 <= len(iban) <= 34:
        return False
    digits = "".join(str(int(c, 36)) for c in iban[4:] + iban[:4])
    return int(digits) % 97 == 1


def regex_arten(text: str) -> list[str]:
    """What the regular expressions find, e.g. ['7 E-Mail-Adressen']; empty below the thresholds.
    Shared with ``g_personendaten``, which only reports where this finds nothing."""
    emails = {
        m.group(0).lower() for m in _EMAIL.finditer(text) if not _EXAMPLE_DOMAIN.search(m.group(0))
    }
    ibans = {m.group(0).replace(" ", "") for m in _IBAN.finditer(text) if _iban_ok(m.group(0))}
    arten = []
    if len(emails) >= MIN_EMAILS:
        arten.append(f"{len(emails)} E-Mail-Adressen")
    if ibans:
        arten.append(f"{len(ibans)} gültige IBAN")
    return arten


def _g07(ctx: ScanContext, entry: InventoryEntry, ext: str) -> Iterator[Finding]:
    if entry.kind != "text" or ext not in DATA_EXT:
        return
    arten = regex_arten(read_text(ctx, entry, MAX_DOC))
    if not arten:
        return
    yield finding(
        rule_id="LB-G07-personenbezogene-daten",
        ebene=Ebene.G,
        schwere=Schwere.M,
        achse=Achse.DSGVO,
        titel="Datei enthält personenbezogene Daten",
        erklaerung=(
            f"Die Datendatei enthält {' und '.join(arten)}. Echte Kundendaten gehören nicht in ein "
            "veröffentlichtes Paket, auch nicht als Beispiel."
        ),
        datei=entry.path,
        zeile=None,
        beleg=", ".join(arten) + " (Werte nicht angezeigt)",
        fix="Die Daten durch erfundene Beispiele ersetzen (z. B. Adressen unter example.org).",
        fix_prompt=f"Ersetze in {entry.path} alle echten Personendaten durch erfundene Werte.",
        normbezug=("DSGVO-Art-5",),
    )


def _dokumente(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        if entry.size > MAX_DOC:
            continue
        ext = PurePosixPath(entry.path).suffix.lower()
        if entry.kind == "pdf":
            yield from _a21_pdf(ctx, entry)
        yield from _a21_office(ctx, entry, ext)
        yield from _b21(ctx, entry, ext)
        yield from _g08(ctx, entry)
        yield from _a20(ctx, entry, ext)
        yield from _notebook(ctx, entry, ext)
        yield from _g07(ctx, entry, ext)
