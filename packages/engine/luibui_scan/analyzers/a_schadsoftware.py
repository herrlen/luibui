"""Analyzer A08 – bekannte Schadsoftware (Prüfkatalog A08, Scanner-Matrix MAL-01).

Compares the SHA-256 of every file with the known-malware lists (``luibui_scan.malware``). A
separate analyzer so that a missing or outdated list shows up as "fehlgeschlagen" for exactly this
check and never as a clean result, while the other file checks still run.
"""

from luibui_scan.analyzers._common import finding
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import ScanContext
from luibui_scan.malware import db_status, known_malware
from luibui_scan.models import Ebene, Finding, Schwere
from luibui_scan.tools import ToolError


@register
class SchadsoftwareAnalyzer:
    info = AnalyzerInfo(
        name="a_schadsoftware", titel="A08 – Bekannte Schadsoftware", ebenen=frozenset({Ebene.A})
    )

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        status = db_status()
        if status.problem:
            raise ToolError(status.problem)
        bad = known_malware()
        return [
            finding(
                rule_id="LB-A08-bekannte-schadsoftware",
                ebene=Ebene.A,
                schwere=Schwere.K,
                titel="Bekannte Schadsoftware",
                erklaerung=(
                    "Der Hash der Datei steht auf der Liste bekannter Schadsoftware. Die Datei "
                    "wird nicht gespeichert."
                ),
                datei=entry.path,
                zeile=None,
                beleg=f"SHA-256 {entry.sha256}",
                fix="Die Datei entfernen und die Herkunft des Pakets prüfen.",
                fix_prompt=f"Entferne {entry.path}; sie ist als Schadsoftware bekannt.",
                normbezug=("OWASP-ASI04", "OWASP-LLM03"),
            )
            for entry in ctx.inventory
            if entry.sha256 in bad
        ]
