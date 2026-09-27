"""Analyzer C – Container und CI (Prüfkatalog C14, C15; Scanner-Matrix COD-08, COD-09).

Own rules over Dockerfiles, Compose files and CI workflows. They cover what gives a package or a
pull request power over the host or the repository. The full code analysis of Ebene C (C01–C13,
S2-1/S2-2) is a separate analyzer; this one does not replace it.
"""

import re
from collections.abc import Iterator
from pathlib import PurePosixPath

from luibui_scan.analyzers._a_ausfuehrung import _SCRIPT_RISK
from luibui_scan.analyzers._common import file_name, finding, read_text, visible
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.models import Ebene, Finding, Schwere

MAX = 1024 * 1024

# --- C14 containers --------------------------------------------------------------------------

_COMPOSE_RISK = re.compile(
    r"^\s*(privileged\s*:\s*true\b|network_mode\s*:\s*[\"']?host\b|pid\s*:\s*[\"']?host\b"
    r"|-\s*[\"']?/var/run/docker\.sock\b|-\s*[\"']?/:/|cap_add\s*:\s*\[?[^\n]*\b(ALL|SYS_ADMIN)\b"
    r"|-\s*[\"']?(ALL|SYS_ADMIN)[\"']?\s*$|security_opt\s*:[^\n]*unconfined)",
    re.MULTILINE,
)
_COMPOSE_NAMES = re.compile(r"^(docker-)?compose(\.[\w-]+)?\.ya?ml$|^podman-compose\.ya?ml$")
_DOCKERFILE_NAMES = re.compile(r"^(Dockerfile|Containerfile)(\.[\w.-]+)?$|\.dockerfile$", re.I)
_DOCKER_RUN_RISK = re.compile(
    r"^\s*(RUN|CMD|ENTRYPOINT)\b[^\n]*(" + _SCRIPT_RISK.pattern + ")", re.MULTILINE | re.IGNORECASE
)


def _c14(ctx: ScanContext, entry: InventoryEntry, name: str) -> Iterator[Finding]:
    if _COMPOSE_NAMES.match(name):
        text = read_text(ctx, entry, MAX)
        m = _COMPOSE_RISK.search(text)
        titel = "Container bekommt Zugriff auf den Rechner"
        erklaerung = (
            "Die Compose-Datei startet einen Container mit Host-Rechten, dem Docker-Socket, dem "
            "Host-Netz oder dem ganzen Dateisystem. Wer den Container kontrolliert, kontrolliert "
            "damit den Rechner."
        )
    elif _DOCKERFILE_NAMES.search(name):
        text = read_text(ctx, entry, MAX)
        m = _DOCKER_RUN_RISK.search(text)
        titel = "Container-Build lädt Code herunter und führt ihn aus"
        erklaerung = (
            "Beim Bauen des Abbilds wird ein Skript aus dem Netz geladen und ungeprüft ausgeführt. "
            "Was es tut, kann sich jederzeit ändern."
        )
    else:
        return
    if m is None:
        return
    line = text.count("\n", 0, m.start()) + 1
    yield finding(
        rule_id="LB-C14-container",
        ebene=Ebene.C,
        schwere=Schwere.H,
        titel=titel,
        erklaerung=erklaerung,
        datei=entry.path,
        zeile=line,
        beleg=visible(text.split("\n")[line - 1].strip()),
        fix="Nur die nötigen Rechte vergeben; Installationsskripte mit Prüfsumme herunterladen.",
        fix_prompt=f"Entferne in {entry.path}, Zeile {line}, die Host-Rechte bzw. das Nachladen.",
        normbezug=("OWASP-ASI05",),
    )


# --- C15 CI workflows ------------------------------------------------------------------------

_UNTRUSTED = re.compile(
    r"\$\{\{\s*github\.(event\.(issue\.(title|body)|pull_request\.(title|body|head\.ref|head\.label)"
    r"|comment\.body|review\.body|review_comment\.body|discussion\.(title|body)"
    r"|pages\.[^}]*\.page_name|commits\.[^}]*\.(message|author\.(name|email))|head_commit\."
    r"(message|author\.(name|email)))|head_ref)\s*\}\}"
)
_RUN_LINE = re.compile(r"^(\s*)(-\s+)?run\s*:\s*(.*)$", re.MULTILINE)
_PRT = re.compile(r"^\s*pull_request_target\s*:|on\s*:\s*\[?[^\n]*\bpull_request_target\b", re.M)
_HEAD_CHECKOUT = re.compile(
    r"ref\s*:\s*\$\{\{\s*github\.(event\.pull_request\.head\.(sha|ref)|head_ref)\s*\}\}"
)


def _run_blocks(text: str) -> Iterator[tuple[int, str]]:
    """Every ``run:`` step with its block, as (offset, text)."""
    for m in _RUN_LINE.finditer(text):
        indent = len(m.group(1)) + len(m.group(2) or "")
        end = m.end()
        if m.group(3).strip() in ("|", ">", "|-", ">-", "|+", ""):
            for line in text[m.end() :].split("\n")[1:]:
                if line.strip() and len(line) - len(line.lstrip()) <= indent:
                    break
                end += len(line) + 1
        yield m.start(), text[m.start() : end]


def _c15(ctx: ScanContext, entry: InventoryEntry) -> Iterator[Finding]:
    path = entry.path.lower()
    workflow = (".github/workflows/" in f"/{path}" or path.startswith(".forgejo/workflows/")) and (
        path.endswith((".yml", ".yaml"))
    )
    if not workflow and PurePosixPath(path).name != ".gitlab-ci.yml":
        return
    text = read_text(ctx, entry, MAX)
    for offset, block in _run_blocks(text):
        m = _UNTRUSTED.search(block)
        if m:
            line = text.count("\n", 0, offset + m.start()) + 1
            yield _c15_finding(
                entry,
                line,
                "Workflow setzt fremden Text direkt in einen Befehl ein",
                "Titel, Beschreibung oder Branch-Name eines Issues oder Pull Requests landen "
                "ungefiltert in einem Shell-Befehl. Wer einen solchen Text schreibt, führt Befehle "
                "mit den Rechten des Workflows aus (Script Injection).",
                text.split("\n")[line - 1].strip(),
            )
            break
    if _PRT.search(text):
        head = _HEAD_CHECKOUT.search(text)
        if head:
            line = text.count("\n", 0, head.start()) + 1
            yield _c15_finding(
                entry,
                line,
                "pull_request_target checkt fremden Code aus",
                "Der Workflow läuft mit Schreibrechten und Secrets des Repositorys, lädt aber den "
                "Code aus dem Pull Request. Ein fremder Pull Request kann so Secrets stehlen "
                "(„Pwn Request“).",
                text.split("\n")[line - 1].strip(),
            )


def _c15_finding(
    entry: InventoryEntry, line: int, titel: str, erklaerung: str, beleg: str
) -> Finding:
    return finding(
        rule_id="LB-C15-ci-workflow",
        ebene=Ebene.C,
        schwere=Schwere.H,
        titel=titel,
        erklaerung=erklaerung,
        datei=entry.path,
        zeile=line,
        beleg=visible(beleg),
        fix=(
            "Fremde Texte nur über Umgebungsvariablen (`env:`) an Befehle geben und bei "
            "`pull_request_target` keinen Code aus dem Pull Request auschecken."
        ),
        fix_prompt=f"Behebe in {entry.path}, Zeile {line}, die unsichere Verwendung.",
        normbezug=("OWASP-ASI04",),
    )


@register
class KonfigCodeAnalyzer:
    info = AnalyzerInfo(
        name="c_konfig", titel="C – Container und CI-Workflows", ebenen=frozenset({Ebene.C})
    )

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        findings: list[Finding] = []
        for entry in ctx.inventory:
            if entry.kind != "text" or entry.size > MAX:
                continue
            findings.extend(_c14(ctx, entry, file_name(entry)))
            findings.extend(_c15(ctx, entry))
        return findings
