"""Analyzer C – Code (Prüfkatalog C01–C13, S2-1).

Two external tools, both only read and parse: Opengrep with our own rules (``rules/opengrep/``,
Python, JavaScript/TypeScript, Shell) and Bandit for Python. Bandit covers C01, C02, C11 and C13
for Python; the Opengrep rules cover those for JavaScript/TypeScript and C03–C12 everywhere.
"""

import re
from collections import defaultdict
from dataclasses import dataclass

from luibui_scan.analyzers._common import finding, masked, rules_dir
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import ScanContext
from luibui_scan.models import Ebene, Finding, ScanArt, Schwere
from luibui_scan.tools import bandit, opengrep

MAX_PER_RULE = 20
"""At most this many findings per rule; the rest is summed up in the last one."""


@dataclass(frozen=True, slots=True)
class Pruefung:
    schwere: Schwere
    titel: str
    erklaerung: str
    fix: str
    fix_prompt: str
    """Formatted with ``{ort}`` (file and line)."""
    normbezug: tuple[str, ...]


KATALOG: dict[str, Pruefung] = {
    "C01": Pruefung(
        Schwere.H,
        "Shell-Befehl aus veränderlichen Daten",
        "Der Code baut einen Shell-Befehl aus Daten zusammen, die von außen kommen können, etwa "
        "aus Tool-Parametern. Mit passenden Eingaben lassen sich so beliebige Befehle ausführen.",
        "Befehle als Liste ohne Shell aufrufen (`subprocess.run([...])`, `execFile`) und "
        "Eingaben vorher gegen eine Liste erlaubter Werte prüfen.",
        "Ersetze in {ort} den Shell-Aufruf durch einen Aufruf ohne Shell mit Argumentliste und "
        "prüfe alle Eingaben gegen erlaubte Werte.",
        ("OWASP-ASI05", "OWASP-LLM05"),
    ),
    "C02": Pruefung(
        Schwere.H,
        "Text wird als Code ausgeführt",
        "Der Code führt Text als Programm aus, etwa mit `eval`, `exec`, `pickle` oder `yaml.load` "
        "ohne SafeLoader. Kommt der Text von außen, läuft damit beliebiger Code.",
        "Auf `eval` und `exec` verzichten; Daten mit `json` oder `yaml.safe_load` lesen.",
        "Entferne in {ort} die Ausführung von Text als Code und lies Daten mit json oder "
        "yaml.safe_load.",
        ("OWASP-ASI05",),
    ),
    "C03": Pruefung(
        Schwere.K,
        "Lädt Code aus dem Netz und führt ihn aus",
        "Das Paket holt zur Laufzeit Code aus dem Internet und führt ihn aus. Was dort liegt, "
        "kann sich jederzeit ändern und ist nicht Teil dieser Prüfung.",
        "Den Code ins Paket aufnehmen oder als Abhängigkeit mit fester Version einbinden.",
        "Entferne in {ort} das Nachladen und Ausführen von Code aus dem Netz und lege den Code "
        "ins Paket.",
        ("OWASP-ASI05", "OWASP-LLM03"),
    ),
    "C04": Pruefung(
        Schwere.K,
        "Greift auf gespeicherte Zugangsdaten zu",
        "Der Code nennt Speicherorte von Zugangsdaten, zum Beispiel private SSH-Schlüssel, "
        "AWS-Zugangsdaten oder gespeicherte Browser-Passwörter. Ein Skill oder Tool braucht diese "
        "Dateien fast nie.",
        "Den Zugriff entfernen. Braucht das Tool einen Zugang, übergibt der Nutzer ihn "
        "ausdrücklich, etwa als Umgebungsvariable.",
        "Entferne in {ort} den Zugriff auf gespeicherte Zugangsdaten und lies einen benötigten "
        "Schlüssel aus einer Umgebungsvariable.",
        ("OWASP-ASI03", "OWASP-LLM02"),
    ),
    "C05": Pruefung(
        Schwere.K,
        "Schickt Zugangsdaten oder persönliche Inhalte ins Netz",
        "Daten aus Zugangsdateien, der Zwischenablage oder vom Bildschirm fließen in einen "
        "Netzaufruf. Das ist das typische Verhalten von Datendiebstahl.",
        "Den Versand entfernen.",
        "Entferne in {ort} den Versand von Zugangsdaten, Zwischenablage oder Bildschirminhalt.",
        ("OWASP-ASI02", "OWASP-LLM02"),
    ),
    "C06": Pruefung(
        Schwere.H,
        "Schickt alle Umgebungsvariablen ins Netz",
        "Der Code sammelt sämtliche Umgebungsvariablen und verschickt sie. Darin stehen meist "
        "API-Schlüssel und Tokens.",
        "Nur die einzelne benötigte Variable lesen und keine Umgebungsvariablen versenden.",
        "Lies in {ort} nur die benötigte Umgebungsvariable und versende keine davon.",
        ("OWASP-LLM02",),
    ),
    "C07": Pruefung(
        Schwere.K,
        "Richtet einen automatischen Neustart ein",
        "Der Code trägt sich in Autostart, Cron, einen Systemdienst oder ein Shell-Profil ein. So "
        "läuft er weiter, auch wenn der Skill gar nicht mehr benutzt wird.",
        "Den Eintrag entfernen. Soll etwas dauerhaft laufen, beschreibt die Doku das und der "
        "Nutzer richtet es selbst ein.",
        "Entferne in {ort} den Eintrag in Autostart, Cron, Systemdienst oder Shell-Profil.",
        ("OWASP-ASI06", "OWASP-ASI10"),
    ),
    "C08": Pruefung(
        Schwere.K,
        "Führt verschleierten Code aus",
        "Der Code entschlüsselt Inhalte erst zur Laufzeit, etwa aus Base64, Hex oder einem "
        "komprimierten Block, und führt sie dann aus. So bleibt verborgen, was tatsächlich "
        "passiert.",
        "Den Code im Klartext ins Paket legen.",
        "Ersetze in {ort} den verschlüsselten Code durch lesbaren Klartext.",
        ("OWASP-ASI05",),
    ),
    "C09": Pruefung(
        Schwere.K,
        "Verhalten ändert sich ab einem festen Datum",
        "Ab einem festgelegten Datum führt der Code Befehle aus oder löscht Dateien. Bis dahin "
        "wirkt er harmlos, auch in jeder Prüfung vor diesem Datum.",
        "Die Datumsbedingung entfernen oder in der Doku offenlegen, wozu sie dient.",
        "Entferne in {ort} die Datumsbedingung vor dem Ausführen oder Löschen.",
        ("OWASP-ASI10",),
    ),
    "C10": Pruefung(
        Schwere.K,
        "Typisches Schadmuster",
        "Der Code enthält ein bekanntes Muster von Schadsoftware: eine Fernsteuerung über das "
        "Netz (Reverse Shell), das Mitschneiden von Tastatureingaben oder das Schürfen von "
        "Kryptowährung.",
        "Das Paket nicht installieren und den Code entfernen.",
        "Entferne in {ort} die Fernsteuerung, das Mitschneiden von Eingaben oder den Miner.",
        ("OWASP-ASI10",),
    ),
    "C11": Pruefung(
        Schwere.M,
        "Unsichere Netzwerkverbindung",
        "Die Prüfung von TLS-Zertifikaten ist abgeschaltet, eine unverschlüsselte Verbindung "
        "wird genutzt, oder ein Server ist ohne Schutz aus jedem Netz erreichbar. Daten lassen "
        "sich dann mitlesen oder verändern.",
        "Zertifikate prüfen lassen, HTTPS verwenden und Server nur an `127.0.0.1` binden.",
        "Schalte in {ort} die Zertifikatsprüfung wieder ein und binde Server nur an 127.0.0.1.",
        ("OWASP-ASI07",),
    ),
    "C12": Pruefung(
        Schwere.H,
        "Dateipfad aus Tool-Parameter ohne Prüfung",
        "Ein Parameter, den die KI beim Aufruf des Tools setzt, wird direkt als Dateipfad "
        "benutzt. Mit `../` kommt man so an Dateien außerhalb des vorgesehenen Ordners, etwa an "
        "Schlüssel.",
        "Den Pfad mit `resolve()` normalisieren und prüfen, dass er im erlaubten Ordner liegt.",
        "Normalisiere in {ort} den Pfad mit resolve() und prüfe mit is_relative_to(), dass er "
        "im erlaubten Ordner liegt.",
        ("OWASP-ASI02", "OWASP-LLM06"),
    ),
    "C13": Pruefung(
        Schwere.N,
        "Code-Schwäche",
        "Bandit meldet eine Schwachstelle im Python-Code.",
        "Die Stelle prüfen und nach dem Hinweis anpassen.",
        "Prüfe {ort} und behebe die gemeldete Schwachstelle.",
        (),
    ),
}

# --- Bandit ------------------------------------------------------------------------------------

BANDIT_KATALOG: dict[str, str] = {
    **dict.fromkeys(("B601", "B602", "B604", "B605", "B609"), "C01"),
    **dict.fromkeys(("B102", "B301", "B302", "B307", "B506", "B614"), "C02"),
    **dict.fromkeys(("B104", "B312", "B321", "B323", "B501", "B502", "B503", "B504"), "C11"),
}
"""Bandit tests mapped to catalog IDs; every other reported test is C13."""

BANDIT_AUSGELASSEN = frozenset(
    {
        "B101",  # assert: harmless in scripts
        "B105", "B106", "B107",  # hard-coded passwords: B20 (gitleaks) checks secrets
        "B110", "B112",  # try/except/pass|continue: style
        "B311",  # random: only relevant for cryptography
        "B403", "B404", "B405", "B406", "B407", "B408", "B409", "B410", "B411",  # imports alone
        "B603", "B607",  # subprocess without shell, partial path: normal for tools
    }
)  # fmt: skip
"""Bandit tests that only produce noise for skills and tools."""

_STUFE = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


def _bandit_schwere(pruefung: str, schwere: str, sicherheit: str) -> Schwere:
    """Bandit's severity, capped by the catalog: C01/C02 up to H, C11 up to M, C13 always N."""
    if pruefung == "C13" or sicherheit == "LOW":
        return Schwere.N
    stufe = _STUFE.get(schwere, 1)
    if pruefung == "C11":
        return Schwere.M if stufe >= 2 else Schwere.N
    return {3: Schwere.H, 2: Schwere.M}.get(stufe, Schwere.N)


def _ort(datei: str, zeile: int | None) -> str:
    return f"{datei}, Zeile {zeile}" if zeile else datei


def _bandit(ctx: ScanContext) -> list[Finding]:
    findings = []
    for t in bandit.scan(ctx.root, rules_dir()):
        if t.test_id in BANDIT_AUSGELASSEN:
            continue
        pruefung = BANDIT_KATALOG.get(t.test_id, "C13")
        p = KATALOG[pruefung]
        findings.append(
            finding(
                rule_id=f"bandit:{t.test_id}",
                ebene=Ebene.C,
                schwere=_bandit_schwere(pruefung, t.schwere, t.sicherheit),
                titel=p.titel,
                erklaerung=f"{p.erklaerung} Hinweis von Bandit ({t.test_id}): {t.text}",
                datei=t.datei,
                zeile=t.zeile,
                beleg=masked(_zeile(t.code, t.zeile)),
                fix=p.fix,
                fix_prompt=p.fix_prompt.format(ort=_ort(t.datei, t.zeile)),
                normbezug=p.normbezug,
            )
        )
    return findings


def _zeile(code: str, zeile: int | None) -> str:
    """Bandit shows a few lines around the hit, each prefixed with its number."""
    for line in code.splitlines():
        nummer, _, text = line.partition(" ")
        if zeile is not None and nummer.isdigit() and int(nummer) == zeile:
            return text.strip()
    return code.strip().split("\n", 1)[0]


# --- Opengrep ----------------------------------------------------------------------------------

_SPRACHE = re.compile(r"-(py|js|sh|go|rb|php|rs|java|ps|andere)$")


def _opengrep(ctx: ScanContext) -> list[Finding]:
    findings = []
    for t in opengrep.scan(ctx.root, rules_dir()):
        rule_id = _SPRACHE.sub("", t.rule_id)
        teile = rule_id.split("-")
        p = KATALOG.get(teile[1]) if len(teile) > 2 and teile[0] == "LB" else None
        if p is None:
            continue  # only our own catalog rules
        findings.append(
            finding(
                rule_id=rule_id,
                ebene=Ebene.C,
                schwere=p.schwere,
                titel=p.titel,
                erklaerung=p.erklaerung,
                datei=t.datei,
                zeile=t.zeile,
                beleg=masked(t.code.strip()),
                fix=p.fix,
                fix_prompt=p.fix_prompt.format(ort=_ort(t.datei, t.zeile)),
                normbezug=p.normbezug,
            )
        )
    return findings


def _capped(findings: list[Finding]) -> list[Finding]:
    groups: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        groups[f.rule_id].append(f)
    out: list[Finding] = []
    for group in groups.values():
        if len(group) <= MAX_PER_RULE:
            out.extend(group)
            continue
        rest = len(group) - MAX_PER_RULE
        last = group[MAX_PER_RULE - 1]
        text = f"{last.erklaerung} Dazu {rest} weitere Stellen derselben Art."
        out.extend(group[: MAX_PER_RULE - 1])
        out.append(last.model_copy(update={"erklaerung": text}))
    return out


@register
class CodeAnalyzer:
    info = AnalyzerInfo(
        name="c_code",
        titel="C – Code",
        ebenen=frozenset({Ebene.C}),
        scan_arts=frozenset({ScanArt.INTENSIV, ScanArt.LOKAL}),
    )

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        # Opengrep first: its findings are the more specific ones for the same line.
        return _capped(_opengrep(ctx) + _bandit(ctx))
