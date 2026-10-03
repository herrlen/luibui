"""Analyzer A, YARA part: patterns of malware in program files (Prüfkatalog C10, A04;
Scanner-Matrix BIN-01; S4-10).

Own YARA-X rules (``rules/yara``) on files that are not text: executables and other binary
files. Text files are covered by Opengrep and the content rules; documentation that quotes a
reverse shell must not trigger here. Without binaries ``yr`` is not even started. ClamAV is
deferred (docs/log.md, 03.10.2026).
"""

from luibui_scan.analyzers._common import finding, rules_dir
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import ScanContext
from luibui_scan.inventory import EXECUTABLE_KINDS
from luibui_scan.models import Ebene, Finding, Schwere
from luibui_scan.tools import yara

ARTEN = EXECUTABLE_KINDS | {"binary"}
_ERKLAERUNG = {
    "LB-C10-krypto-miner": "Die Datei enthält Merkmale eines Krypto-Miners (Pool-Adressen oder "
    "bekannte Miner-Namen). Ein Skill oder MCP-Server braucht so etwas nicht.",
    "LB-C10-reverse-shell": "Die Datei enthält Befehle, mit denen sich eine fremde Maschine eine "
    "Shell auf dem Rechner des Nutzers holen kann.",
    "LB-C10-ransomware": "Die Datei enthält Text einer Lösegeldforderung für verschlüsselte "
    "Dateien.",
    "LB-C10-keylogger": "Die Datei nutzt Schnittstellen, mit denen sich Tastatureingaben "
    "mitlesen lassen.",
    "LB-C10-anti-analyse": "Die Datei prüft, ob sie in einem Debugger oder einer virtuellen "
    "Maschine läuft. Schadsoftware tut das, um sich bei einer Prüfung harmlos zu geben.",
    "LB-A04-gepackt": "Die Programmdatei ist mit UPX gepackt. Gepackter Code lässt sich nicht "
    "statisch prüfen und verbirgt so, was er tut.",
}
_SCHWERE = {"K": Schwere.K, "H": Schwere.H, "M": Schwere.M}


@register
class YaraAnalyzer:
    info = AnalyzerInfo(
        name="a_yara",
        titel="A – Schadmuster in Programmdateien",
        ebenen=frozenset({Ebene.A, Ebene.C}),
    )

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        dateien = [e.path for e in ctx.inventory if e.kind in ARTEN and e.size > 0]
        findings = []
        for t in yara.scan(ctx.root, sorted(dateien), rules_dir()):
            schwere = _SCHWERE.get(t.schwere, Schwere.M)
            ebene = Ebene.C if t.regel.startswith("LB-C") else Ebene.A
            findings.append(
                finding(
                    rule_id=t.regel,
                    ebene=ebene,
                    schwere=schwere,
                    titel=t.titel or "Schadmuster in Programmdatei",
                    erklaerung=_ERKLAERUNG.get(
                        t.regel, "Eine YARA-Regel von luibui hat in der Datei angeschlagen."
                    ),
                    datei=t.datei,
                    zeile=None,
                    beleg=f"YARA-Regel {t.regel}",
                    fix="Die Programmdatei entfernen und, wenn nötig, aus offenem Quellcode bauen.",
                    fix_prompt=f"Entferne {t.datei} aus dem Paket.",
                    normbezug=("OWASP-ASI10",) if ebene is Ebene.C else ("OWASP-ASI04",),
                )
            )
        return findings
