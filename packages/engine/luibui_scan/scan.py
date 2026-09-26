"""One scan of a prepared scratch directory: inventory, context, pipeline.

Intake happens before (``luibui_scan.intake``), scoring after (S1-10). Shared by the CLI and,
from S1-1 on, by the worker.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from luibui_scan.analyzers.registry import AnalyzerRegistry
from luibui_scan.context import ScanContext
from luibui_scan.inventory import Inventory, build_inventory
from luibui_scan.models import Pruefumfang, ScanArt
from luibui_scan.pipeline import PipelineResult, run_pipeline

MANIFEST_NAME = "luibui.json"


class Eingabe(StrEnum):
    """How the package arrived (``report.schema.json``, ``paket.eingabe``)."""

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
    return ScanResult(eingabe, scan_art, umfang, inventory, run_pipeline(ctx, registry))
