"""The contract every analyzer implements: ``analyze(ctx) -> list[Finding]``."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from luibui_scan.context import ScanContext
from luibui_scan.models import Ebene, Finding, Pruefumfang, ScanArt

ALL_SCOPES = frozenset(Pruefumfang)
ALL_ARTS = frozenset(ScanArt)


@dataclass(frozen=True, slots=True)
class AnalyzerInfo:
    """Static description of an analyzer, used by the pipeline to decide whether it runs."""

    name: str
    """Stable identifier, snake_case, e.g. 'a_dateien'."""
    titel: str
    """German label shown in the report, e.g. 'A – Dateien'."""
    ebenen: frozenset[Ebene]
    scopes: frozenset[Pruefumfang] = ALL_SCOPES
    """Scopes the analyzer can check; for others it is reported as 'nicht geprüft'."""
    scan_arts: frozenset[ScanArt] = ALL_ARTS
    """Scan types that include this analyzer (the quick scan runs a reduced set)."""
    needs_manifest: bool = False
    extra: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class Analyzer(Protocol):
    info: AnalyzerInfo

    def analyze(self, ctx: ScanContext) -> list[Finding]: ...
