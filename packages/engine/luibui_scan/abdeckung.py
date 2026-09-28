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
from luibui_scan.scan import ScanResult

DATEITYP = "Dateityp und Tarnung"
SCHADSOFTWARE = "Bekannte Schadsoftware"
SECRETS = "Zugangsdaten im Klartext"
VERSTECKT = "Versteckte Zeichen und kodierte Inhalte"
ANWEISUNGEN = "Anweisungen an die KI (Prompt-Injection)"
CODE = "Was der Code tut"

ANALYZER: dict[str, str] = {
    DATEITYP: "a_dateien",
    SCHADSOFTWARE: "a_schadsoftware",
    SECRETS: "secrets",
    VERSTECKT: "b_inhalte",
    ANWEISUNGEN: "b_muster",
    CODE: "c_code",
}

_PYTHON = frozenset({".py", ".pyw"})
"""Bandit checks ``*.py`` and ``*.pyw``; stubs (``.pyi``) contain no behaviour."""
_JS = frozenset({".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts"})
_SHELL = frozenset({".sh", ".bash", ".zsh"})
_WEB = frozenset({".html", ".htm", ".css", ".svg", ".xml"})

ARTEN = (
    "Anweisungen und Doku",
    "Konfiguration und Daten",
    "Python",
    "JavaScript und TypeScript",
    "Shell-Skripte",
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
    """By extension only: the code tools choose files by extension, so a script without one
    counts as "Anderer Code" and never as checked code."""
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
    if suffix in _WEB:
        return "Web-Dateien"
    if entry.kind == "script" or entry.sprache not in _KEIN_CODE:
        return "Anderer Code"
    if suffix in _ANWEISUNG:
        return "Anweisungen und Doku"
    return "Konfiguration und Daten"


def _vorgesehen(art: str, entries: list[InventoryEntry]) -> list[tuple[str, str | None]]:
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
    else:
        checks.append((ANWEISUNGEN, "nur im Klartext von Doku- und Konfigurationsdateien"))
    if art in ("Python", "JavaScript und TypeScript", "Shell-Skripte"):
        checks.append((CODE, None))
    elif art == "Anderer Code":
        checks.append((CODE, "für diese Programmiersprache noch nicht"))
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
        for check, nicht_hier in _vorgesehen(art, entries):
            name = ANALYZER[check]
            if nicht_hier:
                offen.append(f"{check}: {nicht_hier}")
            elif name in ran:
                geprueft.append(check)
            elif name in grund:
                offen.append(f"{check}: {grund[name]}")
            elif name == "c_code" and "C – Code" in fehlend:
                offen.append(f"{check}: noch nicht eingebaut")
            elif name == "c_code":
                offen.append(f"{check}: nur im Intensivscan")
        if gross[art]:
            offen.append(f"Inhalt von {gross[art]} Datei(en) über 5 MB nicht gelesen")
        out.append(Abdeckung(art, len(entries), tuple(geprueft), tuple(offen)))
    return out
