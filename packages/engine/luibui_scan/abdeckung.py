"""Which checks ran for which kind of file (report field ``abdeckung``).

Derived from the analyzers that actually ran, so the report never claims more than was checked:
a failed or skipped analyzer moves its check to ``offen`` with the reason.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath

from luibui_scan.analyzers._common import MAX_TEXT_BYTES, TEXT_KINDS
from luibui_scan.analyzers.b_muster import INSTRUCTION_SUFFIXES, LOCKFILES
from luibui_scan.context import InventoryEntry
from luibui_scan.models import Pakettyp, Pruefumfang
from luibui_scan.scan import ScanResult

DATEITYP = "Dateityp und Tarnung"
SCHADSOFTWARE = "Bekannte Schadsoftware"
SECRETS = "Zugangsdaten im Klartext"
VERSTECKT = "Versteckte Zeichen und kodierte Inhalte"
ANWEISUNGEN = "Anweisungen an die KI (Prompt-Injection)"
CODE = "Was der Code tut"
CODE_GRUND = (
    "Was der Code tut: Grundmuster (Nachladen, Zugangsdaten, Autostart, Verschleierung, "
    "Schadmuster, Shell-Aufrufe)"
)
KOMMENTARE = "Anweisungen an die KI in Kommentaren und Docstrings"
MCP = "MCP-Tools: versteckte Anweisungen, Shadowing, Anmeldung, Token"
MCP_ABGLEICH = "MCP-Tools: Beschreibung passt zum Code"
ENDPUNKTE = "DSGVO: Endpunkte und Drittländer"
MANIFEST = "DSGVO: Abgleich mit luibui.json (Endpunkte, Rechte, Datenkategorien)"

ANALYZER: dict[str, str] = {
    DATEITYP: "a_dateien",
    SCHADSOFTWARE: "a_schadsoftware",
    SECRETS: "secrets",
    VERSTECKT: "b_inhalte",
    ANWEISUNGEN: "b_muster",
    CODE: "c_code",
    CODE_GRUND: "c_code",
    KOMMENTARE: "b_muster",
    MCP: "e_mcp",
    MCP_ABGLEICH: "e_mcp",
    ENDPUNKTE: "g_dsgvo",
    MANIFEST: "g_dsgvo",
}

TITEL = {"c_code": "C – Code", "e_mcp": "E – MCP", "g_dsgvo": "G – DSGVO"}
"""Analyzers that only the intensive scan runs, with their titles in ``scan.ERWARTET``."""

_PYTHON = frozenset({".py", ".pyw"})
"""Bandit checks ``*.py`` and ``*.pyw``; stubs (``.pyi``) contain no behaviour."""
_JS = frozenset({".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts"})
_SHELL = frozenset({".sh", ".bash", ".zsh"})
_WEB = frozenset({".html", ".htm", ".css", ".svg", ".xml"})
_WEITERE = frozenset(
    {".go", ".rb", ".php", ".rs", ".java", ".kt", ".cs", ".ps1", ".psm1", ".bat", ".cmd"}
)
"""Languages with basic rules (rules/opengrep/LB-CXX-*); no data flow or path checks."""
_SHEBANG_ART = {
    "python": "Python",
    "shell": "Shell-Skripte",
    "javascript": "JavaScript und TypeScript",
    "typescript": "JavaScript und TypeScript",
}
_CODE_ARTEN = ("Python", "JavaScript und TypeScript", "Shell-Skripte")

ARTEN = (
    "Anweisungen und Doku",
    "Konfiguration und Daten",
    "Python",
    "JavaScript und TypeScript",
    "Shell-Skripte",
    "Weitere Programmiersprachen",
    "Anderer Code",
    "Web-Dateien",
    "Binärdateien, Bilder und Archive",
    "macOS-Begleitdateien",
)
_ANWEISUNG = frozenset({".md", ".mdx", ".mdc", ".markdown", ".txt", ".prompt", ".rst", ""})
_KEIN_CODE = frozenset({None, "markdown", "json", "yaml", "toml", "sql"})


@dataclass(frozen=True, slots=True)
class Abdeckung:
    dateiart: str
    dateien: int
    geprueft: tuple[str, ...]
    offen: tuple[str, ...]
    """Checks that apply but did not run for this kind, each with its reason."""

    def to_json_dict(self) -> dict[str, object]:
        return {
            "dateiart": self.dateiart,
            "dateien": self.dateien,
            "geprueft": list(self.geprueft),
            "offen": list(self.offen),
        }


def dateiart(entry: InventoryEntry) -> str:
    """By extension, the way the code tools choose files; a script without extension by its
    shebang (Opengrep reads those too)."""
    path = PurePosixPath(entry.path)
    suffix = path.suffix.lower()
    if entry.kind == "appledouble":
        return "macOS-Begleitdateien"
    if entry.kind not in TEXT_KINDS and entry.kind != "leer":
        return "Binärdateien, Bilder und Archive"
    if suffix in _PYTHON:
        return "Python"
    if suffix in _JS:
        return "JavaScript und TypeScript"
    if suffix in _SHELL:
        return "Shell-Skripte"
    if not suffix and entry.kind == "script" and entry.sprache in _SHEBANG_ART:
        return _SHEBANG_ART[entry.sprache]
    if suffix in _WEITERE:
        return "Weitere Programmiersprachen"
    if suffix in _WEB:
        return "Web-Dateien"
    if entry.kind == "script" or entry.sprache not in _KEIN_CODE:
        return "Anderer Code"
    if suffix in _ANWEISUNG:
        return "Anweisungen und Doku"
    return "Konfiguration und Daten"


_MIT_TOOLS = frozenset({Pakettyp.MCP_SERVER, Pakettyp.PLUGIN, Pakettyp.GEMISCHT})


def _vorgesehen(
    art: str, entries: list[InventoryEntry], pakettyp: Pakettyp, manifest: bool
) -> list[tuple[str, str | None]]:
    """Checks for this kind of file; a reason instead of ``None`` means: not for this kind."""
    checks: list[tuple[str, str | None]] = [(DATEITYP, None), (SCHADSOFTWARE, None)]
    if art in ("Binärdateien, Bilder und Archive", "macOS-Begleitdateien"):
        return checks
    checks.append((SECRETS, None))
    checks.append((VERSTECKT, None))
    anweisung = any(
        PurePosixPath(e.path).suffix.lower() in INSTRUCTION_SUFFIXES
        and PurePosixPath(e.path).name.lower() not in LOCKFILES
        and e.kind == "text"
        for e in entries
    )
    if art in ("Anweisungen und Doku", "Konfiguration und Daten") or anweisung:
        checks.append((ANWEISUNGEN, None))
    if art in (*_CODE_ARTEN, "Weitere Programmiersprachen"):
        checks.append((KOMMENTARE, None))
    if art in _CODE_ARTEN:
        checks.append((CODE, None))
    elif art == "Weitere Programmiersprachen":
        checks.append((CODE_GRUND, None))
        checks.append((CODE, "Datenfluss und Pfadprüfung (C05, C06, C12) nur für Python und JS"))
    elif art == "Anderer Code":
        checks.append((CODE, "für diese Programmiersprache noch nicht"))
    if pakettyp in _MIT_TOOLS and art in ("Python", "JavaScript und TypeScript"):
        checks.append((MCP, None))
        checks.append((MCP_ABGLEICH, None))
    elif pakettyp in _MIT_TOOLS and art in ("Weitere Programmiersprachen", "Anderer Code"):
        checks.append((MCP, "für diese Programmiersprache noch nicht"))
    if art in (*_CODE_ARTEN, "Weitere Programmiersprachen", "Konfiguration und Daten"):
        checks.append((ENDPUNKTE, None))
        checks.append((MANIFEST, None if manifest else "nur mit luibui.json"))
    elif art == "Anderer Code":
        checks.append((ENDPUNKTE, "für diese Programmiersprache noch nicht"))
    return checks


def abdeckung(result: ScanResult) -> list[Abdeckung]:
    ran = set(result.pipeline.ran)
    grund = {f.analyzer: "fehlgeschlagen" for f in result.pipeline.failed}
    grund |= {s.analyzer: s.grund for s in result.pipeline.skipped}
    fehlend = set(result.fehlend)
    by_art: dict[str, list[InventoryEntry]] = {}
    for entry in result.inventory.entries:
        by_art.setdefault(dateiart(entry), []).append(entry)
    gross = Counter(
        dateiart(e) for e in result.inventory.entries
        if e.kind in TEXT_KINDS and e.size > MAX_TEXT_BYTES
    )  # fmt: skip
    out = []
    for art in ARTEN:
        entries = by_art.get(art)
        if not entries:
            continue
        geprueft, offen = [], []
        manifest = result.pruefumfang is Pruefumfang.PAKET
        for check, nicht_hier in _vorgesehen(art, entries, result.inventory.pakettyp, manifest):
            name = ANALYZER[check]
            if nicht_hier:
                offen.append(f"{check}: {nicht_hier}")
            elif name in ran:
                geprueft.append(check)
            elif name in grund:
                offen.append(f"{check}: {grund[name]}")
            elif name in TITEL and TITEL[name] in fehlend:
                offen.append(f"{check}: noch nicht eingebaut")
            elif name in TITEL:
                offen.append(f"{check}: nur im Intensivscan")
        if gross[art]:
            offen.append(f"Inhalt von {gross[art]} Datei(en) über 5 MB nicht gelesen")
        out.append(Abdeckung(art, len(entries), tuple(geprueft), tuple(offen)))
    return out
