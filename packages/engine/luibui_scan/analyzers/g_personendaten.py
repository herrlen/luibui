"""Analyzer G, part 2: lists of people in data files and personal data in notebook outputs
(Prüfkatalog G07, Scanner-Matrix DAT-01 and COD-02, S3-13).

The regular expressions for e-mail addresses and IBANs run in ``a_dateien`` on every data file.
This analyzer adds what they cannot find: a table column full of names of people. Data files
(CSV, TSV, JSON Lines) are split into columns, and every value goes on its own line to Presidio
with the German spaCy model. A column counts when at least five values and at least half of its
values are mostly a name. Whole files are not sent: read as running text, the model calls
countries, airports and currencies persons (measured on public code lists and the Anthropic
cookbook, docs/log.md 02.10.2026). For the same reason notebook outputs get only the regular
expressions, which ``a_dateien`` does not run on them.

Presidio is slow (about 75 s per MB on 1.5 CPU) and large, so it gets a sample: the first 64 KB of
each file, at most 256 KB per check, at most 200 distinct values per column. Without data files
it is never started. One G07 finding per file, M on the GDPR axis, never blocking.
"""

import csv
import io
import json
from pathlib import PurePosixPath

from luibui_scan.analyzers._a_dokumente import DATA_EXT, MAX_DOC, regex_arten
from luibui_scan.analyzers._common import finding, read_json, read_text, visible
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.models import Achse, Ebene, Finding, ScanArt, Schwere
from luibui_scan.tools import presidio

STICHPROBE_DATEI = 64 * 1024
STICHPROBE_GESAMT = 256 * 1024
MIN_PROBE = 4 * 1024
"""Less budget than this left: further files are not sent."""
MAX_WERTE = 200
"""Distinct values per column that go to Presidio."""
MAX_SPALTEN = 50
MIN_PERSONEN = 5
MIN_ANTEIL = 0.5
"""A column is a list of people when at least this share of its values are names."""


def _ausgaben(ctx: ScanContext, entry: InventoryEntry) -> str:
    """Text of all saved outputs of an ``.ipynb``: streams and plain-text results."""
    data = read_json(ctx, entry)
    cells = data.get("cells") if isinstance(data, dict) else None
    if not isinstance(cells, list):
        return ""
    teile: list[str] = []
    for cell in cells:
        outputs = cell.get("outputs") if isinstance(cell, dict) else None
        if not isinstance(outputs, list):
            continue
        for out in outputs:
            if not isinstance(out, dict):
                continue
            text = out.get("text")
            if text is None and isinstance(out.get("data"), dict):
                text = out["data"].get("text/plain")
            if isinstance(text, list):
                text = "".join(str(t) for t in text)
            if isinstance(text, str):
                teile.append(text)
    return "\n".join(teile)


def _stichprobe(text: str, grenze: int) -> str:
    """The first ``grenze`` characters, cut at the last line break so no row is split."""
    if len(text) <= grenze:
        return text
    cut = text.rfind("\n", 0, grenze)
    return text[: cut if cut > 0 else grenze]


def _wert(raw: object) -> str | None:
    """A value that could be a name: short text with letters, not a number or an identifier."""
    if not isinstance(raw, str):
        return None
    wert = " ".join(raw.split())
    if not 3 <= len(wert) <= 80 or not any(c.isalpha() for c in wert):
        return None
    if sum(c.isdigit() for c in wert) > len(wert) // 3 or "@" in wert or "/" in wert:
        return None
    return wert


def _spalten(text: str, ext: str) -> dict[str, list[str]]:
    """Distinct candidate values per column, in order of appearance."""
    roh: dict[str, list[object]] = {}
    if ext in (".jsonl", ".ndjson"):
        for zeile in text.splitlines():
            try:
                obj = json.loads(zeile)
            except ValueError:
                continue
            if isinstance(obj, dict):
                for k, v in list(obj.items())[:MAX_SPALTEN]:
                    roh.setdefault(str(k), []).append(v)
    else:
        if ext == ".tsv":
            trenner = "\t"
        else:
            try:
                trenner = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|").delimiter
            except csv.Error:
                trenner = ","
        zeilen = csv.reader(io.StringIO(text), delimiter=trenner)
        kopf = next(zeilen, [])
        for row in zeilen:
            for i, v in enumerate(row[:MAX_SPALTEN]):
                name = kopf[i] if i < len(kopf) and kopf[i].strip() else f"Spalte {i + 1}"
                roh.setdefault(name, []).append(v)
    spalten: dict[str, list[str]] = {}
    for name, werte in roh.items():
        sauber = list(dict.fromkeys(w for w in map(_wert, werte) if w))[:MAX_WERTE]
        if len(sauber) >= MIN_PERSONEN:
            spalten[name] = sauber
    return spalten


def _befund(datei: str, arten: list[str], notebook: bool, stichprobe: bool) -> Finding:
    wo = (
        "Die gespeicherten Ausgaben des Notebooks enthalten"
        if notebook
        else ("Die Datendatei enthält")
    )
    zusatz = " (geprüft wurde der Anfang der Datei)" if stichprobe else ""
    return finding(
        rule_id="LB-G07-personenbezogene-daten",
        ebene=Ebene.G,
        schwere=Schwere.M,
        achse=Achse.DSGVO,
        titel="Datei enthält personenbezogene Daten",
        erklaerung=(
            f"{wo} {' und '.join(arten)}{zusatz}. Echte Personendaten gehören nicht in ein "
            "veröffentlichtes Paket, auch nicht als Beispiel."
            + ("" if notebook else " Namen werden automatisch erkannt; erfundene Namen zählen mit.")
        ),
        datei=datei,
        zeile=None,
        beleg=visible(", ".join(arten) + " (Werte nicht angezeigt)"),
        fix=(
            "Notebook-Ausgaben vor dem Veröffentlichen leeren und echte Daten durch erfundene "
            "ersetzen."
            if notebook
            else "Die Daten durch erfundene Beispiele ersetzen (z. B. Adressen unter example.org)."
        ),
        fix_prompt=(
            f"Leere in {datei} alle gespeicherten Ausgaben und ersetze echte Personendaten."
            if notebook
            else f"Ersetze in {datei} alle echten Personendaten durch erfundene Werte."
        ),
        normbezug=("DSGVO-Art-5",),
    )


@register
class PersonendatenAnalyzer:
    info = AnalyzerInfo(
        name="g_personendaten",
        titel="G – Personendaten in Daten und Notebooks",
        ebenen=frozenset({Ebene.G}),
        scan_arts=frozenset({ScanArt.INTENSIV, ScanArt.LOKAL}),
    )

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        findings: list[Finding] = []
        texte: dict[str, str] = {}
        spalte_von: dict[str, tuple[str, str]] = {}
        gekuerzt: dict[str, bool] = {}
        gesamt = 0
        for entry in sorted(ctx.inventory, key=lambda e: e.path):
            if entry.kind != "text" or entry.size > MAX_DOC:
                continue
            ext = PurePosixPath(entry.path).suffix.lower()
            if ext == ".ipynb":
                arten = regex_arten(_ausgaben(ctx, entry))
                if arten:
                    findings.append(_befund(entry.path, arten, notebook=True, stichprobe=False))
                continue
            if ext not in DATA_EXT or STICHPROBE_GESAMT - gesamt < MIN_PROBE:
                continue
            text = read_text(ctx, entry, MAX_DOC)
            if regex_arten(text):
                continue  # a_dateien reports this file already
            probe = _stichprobe(text, min(STICHPROBE_DATEI, STICHPROBE_GESAMT - gesamt))
            gesamt += len(probe)
            gekuerzt[entry.path] = len(probe) < len(text)
            for name, werte in _spalten(probe, ext).items():
                key = str(len(texte))
                texte[key] = "\n".join(werte)
                spalte_von[key] = (entry.path, name)
        treffer: dict[str, list[str]] = {}
        for key, anzahl in presidio.zaehlen(texte, ctx.root.parent).items():
            gesamt_werte, personen = anzahl.get("werte", 0), anzahl.get("personen", 0)
            if personen >= MIN_PERSONEN and personen >= MIN_ANTEIL * gesamt_werte:
                datei, spalte = spalte_von[key]
                treffer.setdefault(datei, []).append(
                    f"in der Spalte „{spalte[:40]}“ {personen} von {gesamt_werte} Werten "
                    "mit Personennamen"
                )
        for datei, arten in sorted(treffer.items()):
            findings.append(_befund(datei, arten[:3], notebook=False, stichprobe=gekuerzt[datei]))
        return findings
