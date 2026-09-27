"""Analyzer B20 – Secrets (S1-8): gitleaks through its adapter, values always masked.

An unavailable gitleaks makes the analyzer fail, so the scan is incomplete and never green.
"""

import re

from luibui_scan.analyzers._common import finding, visible
from luibui_scan.analyzers.a_dateien import rules_dir
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import ScanContext
from luibui_scan.models import Ebene, Finding, Schwere
from luibui_scan.tools import gitleaks

_SAMPLE_PATH = re.compile(
    r"(^|/)(tests?|__tests__|spec|fixtures?|examples?|samples?|docs?|testdata|mocks?)(/|$)"
    r"|\.(md|rst|txt)$|(^|/)\.env\.(example|sample|template)$",
    re.IGNORECASE,
)
_RULE_ID = re.compile(r"[^a-z0-9._-]+")


def _mask(match: str) -> str:
    """gitleaks already redacts; anything that still looks like a long token is cut to 4 chars."""
    masked = re.sub(r"[A-Za-z0-9+/_\-]{20,}", lambda m: m.group()[:4] + "…", match)
    return visible(masked, 200)


@register
class SecretsAnalyzer:
    info = AnalyzerInfo(name="secrets", titel="B20 – Secrets", ebenen=frozenset({Ebene.B}))

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        findings = []
        for leak in gitleaks.scan(ctx.root, rules_dir()):
            sample = bool(_SAMPLE_PATH.search(leak.datei))
            rule = _RULE_ID.sub("-", leak.rule_id.lower()).strip("-") or "unbekannt"
            findings.append(
                finding(
                    rule_id=f"gitleaks:{rule}",
                    ebene=Ebene.B,
                    schwere=Schwere.H if sample else Schwere.K,
                    titel=f"Zugangsdaten im Paket: {leak.beschreibung or leak.rule_id}"[:200],
                    erklaerung=(
                        "Im Paket steht etwas, das wie ein echter Schlüssel, ein Token oder ein "
                        "Passwort aussieht. Wer das Paket bekommt, bekommt auch diesen Zugang."
                        + (
                            " Die Datei liegt in einem Beispiel-, Test- oder Doku-Bereich; prüfe, "
                            "ob der Wert wirklich nur ein Platzhalter ist."
                            if sample
                            else ""
                        )
                    ),
                    datei=leak.datei,
                    zeile=leak.zeile,
                    beleg=_mask(leak.match),
                    fix=(
                        "Den Wert sofort beim Anbieter widerrufen und neu erzeugen, dann aus dem "
                        "Paket entfernen und nur über Umgebungsvariablen einlesen."
                    ),
                    fix_prompt=(
                        f"Entferne das Secret aus {leak.datei}"
                        + (f", Zeile {leak.zeile}" if leak.zeile else "")
                        + ", lies es stattdessen aus einer Umgebungsvariable und ergänze "
                        ".env.example ohne Wert."
                    ),
                    normbezug=("OWASP-LLM02", "DSGVO-Art-32"),
                )
            )
        return findings
