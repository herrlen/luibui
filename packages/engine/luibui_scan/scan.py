"""One scan of a prepared scratch directory: inventory, context, pipeline, scoring.

Intake happens before (``luibui_scan.intake``). Shared by the CLI and, from S1-1 on, by the
worker.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from luibui_scan.analyzers.registry import AnalyzerRegistry
from luibui_scan.context import ScanContext
from luibui_scan.inventory import Inventory, build_inventory
from luibui_scan.models import Pruefumfang, ScanArt
from luibui_scan.pipeline import PipelineResult, run_pipeline
from luibui_scan.scoring import Bewertung, bewerte

MANIFEST_NAME = "luibui.json"


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
) -> ScanResult:
    """Scan the files intake wrote to ``root``. Never executes anything from it."""
    inventory = build_inventory(root)
    umfang = pruefumfang_for(eingabe, inventory)
    ctx = ScanContext(
        root=root,
        scan_art=scan_art,
        pruefumfang=umfang,
        inventory=inventory.entries,
        pakettyp=inventory.pakettyp,
    )
    pipeline = run_pipeline(ctx, registry)
    bewertung = bewerte(
        pipeline.findings,
        pruefumfang=umfang,
        # Presence decides the scope for now; validating luibui.json belongs to Ebene G.
        has_manifest=umfang is Pruefumfang.PAKET,
        # An analyzer failed or none ran: nothing may turn green.
        complete=pipeline.complete and bool(pipeline.ran),
    )
    return ScanResult(eingabe, scan_art, umfang, inventory, pipeline, bewertung)
