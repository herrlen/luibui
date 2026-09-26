"""Pipeline runner: decides which analyzers apply, runs them, collects findings.

A failing analyzer is never silently skipped. It is reported in ``failed`` so that scoring can
refuse a green light for an incomplete scan.
"""

import logging
from dataclasses import dataclass, field

from luibui_scan.analyzers.base import Analyzer
from luibui_scan.analyzers.registry import AnalyzerRegistry, default_registry
from luibui_scan.context import ScanContext
from luibui_scan.models import Finding, Pruefumfang

log = logging.getLogger(__name__)

_SCOPE_LABEL = {
    Pruefumfang.PAKET: "Paket-Prüfung",
    Pruefumfang.AUSWAHL: "Dateiauswahl ohne Manifest",
    Pruefumfang.EINZELDATEI: "Einzeldatei-Prüfung",
}


@dataclass(frozen=True, slots=True)
class Skipped:
    analyzer: str
    titel: str
    grund: str


@dataclass(frozen=True, slots=True)
class Failed:
    analyzer: str
    titel: str
    fehler: str
    """Exception type only; messages may contain package content and stay in the log."""


@dataclass(slots=True)
class PipelineResult:
    findings: list[Finding] = field(default_factory=list)
    ran: list[str] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)
    failed: list[Failed] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.failed


def _skip_reason(analyzer: Analyzer, ctx: ScanContext) -> str | None:
    info = analyzer.info
    if ctx.scan_art not in info.scan_arts:
        return "nur im Intensivscan"
    if ctx.pruefumfang not in info.scopes:
        return _SCOPE_LABEL[ctx.pruefumfang]
    if info.needs_manifest and ctx.manifest is None:
        return "kein luibui.json"
    return None


def run_pipeline(ctx: ScanContext, registry: AnalyzerRegistry | None = None) -> PipelineResult:
    registry = default_registry if registry is None else registry
    result = PipelineResult()
    for analyzer in registry:
        info = analyzer.info
        reason = _skip_reason(analyzer, ctx)
        if reason is not None:
            result.skipped.append(Skipped(info.name, info.titel, reason))
            continue
        try:
            findings = analyzer.analyze(ctx)
        except Exception as exc:
            log.exception("analyzer %s failed", info.name)
            result.failed.append(Failed(info.name, info.titel, type(exc).__name__))
            continue
        for finding in findings:
            if not isinstance(finding, Finding):
                raise TypeError(f"Analyzer {info.name} lieferte {type(finding).__name__}")
            result.findings.append(
                finding if finding.analyzer else finding.model_copy(update={"analyzer": info.name})
            )
        result.ran.append(info.name)
    return result
