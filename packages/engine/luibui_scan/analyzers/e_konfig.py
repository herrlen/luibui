"""Analyzer E – MCP-Konfiguration und Werkzeugrechte (Prüfkatalog E08, E09; Scanner-Matrix AGT-04,
AGT-06).

Reads MCP client configurations (``.mcp.json``, ``claude_desktop_config.json`` and the like) and
the ``allowed-tools`` of commands, agents and skills. Everything is parsed as data; no server is
started and no remote URL is contacted (the check of running remote servers is S5-6).
"""

import re
from collections.abc import Iterator
from pathlib import PurePosixPath
from typing import Any

from luibui_scan.analyzers._a_ausfuehrung import _DANGEROUS_COMMAND
from luibui_scan.analyzers._common import file_name, finding, read_json, read_text, visible
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.models import Ebene, Finding, Schwere

_MCP_FILES = frozenset(
    {
        ".mcp.json",
        "mcp.json",
        "claude_desktop_config.json",
        "cline_mcp_settings.json",
        "mcp_config.json",
        "mcp_settings.json",
    }
)
_RUNNERS = {
    "npx": "npm",
    "bunx": "npm",
    "pnpm": "npm",
    "uvx": "PyPI",
    "pipx": "PyPI",
    "docker": "Docker",
    "podman": "Docker",
}
_LOCAL_HOST = re.compile(r"^https?://(localhost|127\.0\.0\.1|\[::1\]|0\.0\.0\.0)(:\d+)?(/|$)")
NORM = ("OWASP-ASI04", "OWASP-LLM03")


def _servers(data: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(data, dict):
        return {}
    for key in ("mcpServers", "servers", "mcp_servers"):
        value = data.get(key)
        if isinstance(value, dict):
            return {str(k): v for k, v in value.items() if isinstance(v, dict)}
    mcp = data.get("mcp")
    return _servers(mcp) if isinstance(mcp, dict) else {}


def _package(args: list[str], runner: str) -> str | None:
    """The first argument that is not an option (after ``run``/``dlx`` for docker and pnpm)."""
    skip_next = False
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg in ("run", "dlx", "exec") and i == 0:
            continue
        if runner in ("docker", "podman") and arg in ("-e", "--env", "-v", "--volume", "--name"):
            skip_next = True
            continue
        if arg.startswith("-"):
            continue
        return arg
    return None


def _runs_package(runner: str, args: list[str]) -> bool:
    if runner == "pnpm":
        return bool(args) and args[0] == "dlx"
    if runner in ("docker", "podman"):
        return bool(args) and args[0] == "run"
    if runner == "pipx":
        return bool(args) and args[0] == "run"
    return True


def _pinned(package: str, runner: str) -> bool:
    if runner in ("docker", "podman"):
        return "@sha256:" in package
    name = package[1:] if package.startswith("@") else package
    version = name.split("@", 1)[1] if "@" in name else ""
    if runner in ("uvx", "pipx"):
        version = package.split("==", 1)[1] if "==" in package else version
    return bool(re.match(r"^\d+\.\d+", version))


def _e09(ctx: ScanContext, entry: InventoryEntry) -> Iterator[Finding]:
    for name, server in _servers(read_json(ctx, entry)).items():
        command = server.get("command")
        raw_args = server.get("args")
        args = [str(a) for a in raw_args] if isinstance(raw_args, list) else []
        url = server.get("url") or server.get("serverUrl")
        if isinstance(command, str):
            line = " ".join([command, *args])
            runner = PurePosixPath(command).name.lower().removesuffix(".cmd").removesuffix(".exe")
            if _DANGEROUS_COMMAND.search(line):
                yield _finding(
                    entry,
                    "startbefehl",
                    Schwere.K,
                    f"MCP-Server „{name}“ lädt beim Start Code nach oder verschleiert ihn",
                    "Der Startbefehl lädt etwas herunter und führt es aus oder dekodiert Code. Das "
                    "läuft mit den Rechten des Nutzers, sobald der Client startet.",
                    line,
                )
            elif runner in _RUNNERS and _runs_package(runner, args):
                package = _package(args, runner)
                if package is None:
                    continue
                if _pinned(package, runner):
                    yield _finding(
                        entry,
                        "fremdes-paket",
                        Schwere.I,
                        f"MCP-Server „{name}“ lädt {package} beim Start",
                        f"Das Paket kommt beim Start aus {_RUNNERS[runner]} und ist nicht Teil "
                        "dieser Prüfung. Die Version ist festgelegt.",
                        line,
                    )
                else:
                    yield _finding(
                        entry,
                        "fremdes-paket",
                        Schwere.H,
                        f"MCP-Server „{name}“ lädt ungeprüft die neueste Version von {package}",
                        f"Bei jedem Start holt der Client die jeweils neueste Version aus "
                        f"{_RUNNERS[runner]} und führt sie aus. Wird das Paket übernommen, läuft "
                        "fremder Code ohne Rückfrage.",
                        line,
                    )
        if isinstance(url, str):
            if url.startswith("http://") and not _LOCAL_HOST.match(url):
                yield _finding(
                    entry,
                    "unverschluesselt",
                    Schwere.M,
                    f"MCP-Server „{name}“ ohne Verschlüsselung",
                    "Die Verbindung läuft über `http://`. Anfragen, Antworten und Zugangsdaten "
                    "können unterwegs mitgelesen oder verändert werden.",
                    url,
                )
            elif url.startswith("https://") and not _LOCAL_HOST.match(url):
                yield _finding(
                    entry,
                    "entfernt",
                    Schwere.I,
                    f"Entfernter MCP-Server „{name}“ nicht geprüft",
                    "Der Server läuft bei einem fremden Anbieter. Was er tut und wohin er Daten "
                    "schickt, ist nicht Teil dieser Prüfung.",
                    url,
                )


def _finding(
    entry: InventoryEntry, art: str, schwere: Schwere, titel: str, erklaerung: str, beleg: str
) -> Finding:
    return finding(
        rule_id=f"LB-E09-{art}",
        ebene=Ebene.E,
        schwere=schwere,
        titel=titel[:200],
        erklaerung=erklaerung,
        datei=entry.path,
        zeile=None,
        beleg=visible(beleg, 300),
        fix=(
            "Pakete mit fester Version starten (z. B. `npx paket@1.2.3`, `uvx paket==1.2.3`, "
            "Docker-Abbild mit `@sha256:`), keine Befehle, die nachladen, und nur `https://`."
        ),
        fix_prompt=f"Lege in {entry.path} für jeden MCP-Server eine feste Version fest.",
        normbezug=NORM,
    )


# --- E08 tool rights -------------------------------------------------------------------------

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(\n|\Z)", re.S)
_TOOLS_LINE = re.compile(r"^(allowed-tools|allowed_tools|tools)\s*:\s*(.*)$", re.M)
_TOO_WIDE = re.compile(r"\bBash\s*\(\s*\*\s*\)|\bBash\b(?!\s*\()|(^|[\s,\[\"'])\*($|[\s,\]\"'])")


def _e08(ctx: ScanContext, entry: InventoryEntry) -> Iterator[Finding]:
    text = read_text(ctx, entry, 64 * 1024)
    head = _FRONTMATTER.match(text)
    if head is None:
        return
    for m in _TOOLS_LINE.finditer(head.group(1)):
        value = m.group(2)
        if not value.strip():
            # YAML list on the following lines
            rest = head.group(1)[m.end() :]
            items = re.match(r"((?:\n\s*-\s*[^\n]*)+)", rest)
            value = items.group(1) if items else ""
        wide = _TOO_WIDE.search(value)
        if wide is None:
            continue
        yield finding(
            rule_id="LB-E08-werkzeugrechte",
            ebene=Ebene.E,
            schwere=Schwere.M,
            titel="Zu weit gefasste Werkzeugrechte",
            erklaerung=(
                "Der Befehl, Agent oder Skill darf ohne Rückfrage beliebige Shell-Befehle oder "
                "alle Werkzeuge nutzen. Eine eingeschleuste Anweisung hätte damit freie Hand."
            ),
            datei=entry.path,
            zeile=text.count("\n", 0, head.start(1) + m.start()) + 1,
            beleg=visible(m.group(0).strip(), 200),
            fix="Nur die nötigen Befehle erlauben, z. B. `Bash(npm test:*)` statt `Bash(*)`.",
            fix_prompt=f"Beschränke in {entry.path} `{m.group(1)}` auf die nötigen Befehle.",
            normbezug=("OWASP-ASI03", "OWASP-LLM06"),
        )
        return


@register
class KonfigAnalyzer:
    info = AnalyzerInfo(
        name="e_konfig",
        titel="E – MCP-Konfiguration und Werkzeugrechte",
        ebenen=frozenset({Ebene.E}),
    )

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        findings: list[Finding] = []
        for entry in ctx.inventory:
            if entry.kind != "text":
                continue
            name = file_name(entry).lower()
            if name in _MCP_FILES:
                findings.extend(_e09(ctx, entry))
            elif name.endswith((".md", ".mdc")):
                findings.extend(_e08(ctx, entry))
        return findings
