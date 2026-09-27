"""One scan of a prepared scratch directory: inventory, context, pipeline, scoring.

Intake happens before (``luibui_scan.intake``). Shared by the CLI and, from S1-1 on, by the
worker.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from luibui_scan.analyzers.registry import AnalyzerRegistry, default_registry
from luibui_scan.context import ScanContext
from luibui_scan.intake.nested import expand_packages
from luibui_scan.inventory import Inventory, build_inventory
from luibui_scan.models import Pruefumfang, ScanArt
from luibui_scan.pipeline import PipelineResult, run_pipeline
from luibui_scan.scoring import Bewertung, bewerte

MANIFEST_NAME = "luibui.json"

_SCHNELL = {
    "a_dateien": "A – Dateien",
    "a_schadsoftware": "A08 – Bekannte Schadsoftware",
    "b_inhalte": "B – Versteckte Inhalte",
    "b_muster": "B – Anweisungsmuster",
    "secrets": "B20 – Secrets",
    "d_abhaengigkeiten": "D – Abhängigkeiten",
    "d_osv": "D – Bekannte Schwachstellen und Schadpakete (OSV)",
    "e_konfig": "E – MCP-Konfiguration und Werkzeugrechte",
}
ERWARTET: dict[ScanArt, dict[str, str]] = {
    ScanArt.SCHNELL: _SCHNELL,
    ScanArt.INTENSIV: {
        **_SCHNELL,
        "c_code": "C – Code",
        "e_mcp": "E – MCP",
        "g_dsgvo": "G – DSGVO",
    },
    ScanArt.LOKAL: {**_SCHNELL, "c_code": "C – Code", "e_mcp": "E – MCP", "g_dsgvo": "G – DSGVO"},
}
"""Analyzers each scan type must have (Konzept §2 and §4, Prüfkatalog). As long as one is not
built yet, the scan is incomplete and never green. Analyzers that exist but do not apply to the
scope (e.g. dependencies for a single file) are scope, not gaps."""


class Eingabe(StrEnum):
    """How the package arrived (``report.schema.json``, ``paket.quelle``)."""

    DATEI = "datei"
    AUSWAHL = "auswahl"
    TEXT = "text"
    ZIP = "zip"
    GIT = "git"
    LOKAL = "lokal"


@dataclass(frozen=True, slots=True)
class ScanResult:
    eingabe: Eingabe
    scan_art: ScanArt
    pruefumfang: Pruefumfang
    inventory: Inventory
    pipeline: PipelineResult
    bewertung: Bewertung
    fehlend: tuple[str, ...] = ()
    """Titles of expected checks that are not built yet (see ``ERWARTET``)."""


def pruefumfang_for(eingabe: Eingabe, inventory: Inventory) -> Pruefumfang:
    """Konzept §5: a package needs ``luibui.json`` at its top level; single inputs never are."""
    if eingabe in (Eingabe.DATEI, Eingabe.TEXT):
        return Pruefumfang.EINZELDATEI
    if any(e.path == MANIFEST_NAME for e in inventory.entries):
        return Pruefumfang.PAKET
    return Pruefumfang.AUSWAHL


def scan_prepared(
    root: Path,
    eingabe: Eingabe,
    scan_art: ScanArt,
    registry: AnalyzerRegistry | None = None,
    erwartet: Mapping[str, str] | None = None,
    options: Mapping[str, Any] | None = None,
) -> ScanResult:
    """Scan the files intake wrote to ``root``. Never executes anything from it.

    ``erwartet`` overrides ``ERWARTET`` (tests with their own registry pass ``{}``).
    """
    nested = expand_packages(root)
    inventory = build_inventory(root)
    umfang = pruefumfang_for(eingabe, inventory)
    ctx = ScanContext(
        root=root,
        scan_art=scan_art,
        pruefumfang=umfang,
        inventory=inventory.entries,
        pakettyp=inventory.pakettyp,
        options=dict(options or {}),
        entpackt=nested.entpackt,
        nicht_entpackt=nested.abgelehnt,
    )
    pipeline = run_pipeline(ctx, registry)
    names = {a.info.name for a in (default_registry if registry is None else registry)}
    expected = ERWARTET[scan_art] if erwartet is None else erwartet
    fehlend = tuple(titel for name, titel in expected.items() if name not in names)
    bewertung = bewerte(
        pipeline.findings,
        pruefumfang=umfang,
        # Presence decides the scope for now; validating luibui.json belongs to Ebene G.
        has_manifest=umfang is Pruefumfang.PAKET,
        # An analyzer failed, none ran or an expected one is missing: nothing may turn green.
        complete=pipeline.complete and bool(pipeline.ran) and not fehlend,
    )
    return ScanResult(eingabe, scan_art, umfang, inventory, pipeline, bewertung, fehlend)
