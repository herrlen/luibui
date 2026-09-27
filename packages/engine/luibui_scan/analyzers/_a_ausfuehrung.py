"""Analyzer A, part 1: things that run by themselves (Prüfkatalog A02, A03)."""

import re
from collections.abc import Iterator
from typing import Any

from luibui_scan.analyzers._common import file_name, finding, read_json, read_text, visible
from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.models import Ebene, Finding, Schwere

_DANGEROUS_COMMAND = re.compile(
    r"(curl|wget|invoke-webrequest|iwr|irm)\b[^\n]*\|\s*(sudo\s+)?(ba|z|da)?sh\b"
    r"|\b(curl|wget)\b[^\n]*(-o|--output|>)\s*\S+[^\n]*(&&|;)\s*(sh|bash|chmod|\./)"
    r"|base64\s+(-d|--decode)|\beval\b|\bnc\s+-e\b|/dev/tcp/|python[0-9.]*\s+-c\b"
    r"|node\s+-e\b|powershell[^\n]*-enc",
    re.IGNORECASE,
)
_INSTALL_HOOKS = ("preinstall", "install", "postinstall")

# --- A02 autostart ---------------------------------------------------------------------------


def _commands(obj: Any) -> Iterator[str]:
    """Every string value stored under a key named 'command' (hooks, tasks)."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in ("command", "args") and isinstance(value, str):
                yield value
            elif key == "args" and isinstance(value, list):
                yield " ".join(str(v) for v in value)
            else:
                yield from _commands(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _commands(item)


def _autostart(
    entry: InventoryEntry, art: str, commands: list[str], erklaerung: str
) -> Finding | None:
    if not commands:
        return None
    dangerous = [c for c in commands if _DANGEROUS_COMMAND.search(c)]
    shown = dangerous[0] if dangerous else commands[0]
    return finding(
        rule_id=f"LB-A02-{art}",
        ebene=Ebene.A,
        schwere=Schwere.K if dangerous else Schwere.H,
        titel=(
            "Automatisch startender Befehl lädt Code nach oder verschleiert ihn"
            if dangerous
            else "Befehle, die ohne Zutun des Nutzers laufen"
        ),
        erklaerung=erklaerung
        + (
            " Mindestens ein Befehl lädt etwas herunter und führt es aus oder dekodiert Code."
            if dangerous
            else " Prüfe, ob jeder dieser Befehle nötig und harmlos ist."
        ),
        datei=entry.path,
        zeile=None,
        beleg=visible(shown, 300),
        fix="Automatisch laufende Befehle entfernen oder auf ein lokales Skript beschränken.",
        fix_prompt=(
            f"Prüfe in {entry.path} jeden automatisch ausgeführten Befehl. Entferne Befehle, die "
            "etwas herunterladen, dekodieren oder außerhalb des Projekts schreiben."
        ),
        normbezug=("OWASP-ASI05", "OWASP-LLM03"),
    )


def _a02(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        path = entry.path.lower()
        name = file_name(entry).lower()
        f: Finding | None = None
        if path.endswith((".claude/settings.json", ".claude/settings.local.json")) or (
            name == "hooks.json"
        ):
            data = read_json(ctx, entry)
            hooks = data.get("hooks") if isinstance(data, dict) else None
            f = _autostart(
                entry,
                "claude-hooks",
                list(_commands(hooks)),
                "Hooks von Claude Code führen Befehle bei Ereignissen automatisch aus, etwa bei "
                "jedem Tool-Aufruf oder Sitzungsstart.",
            )
        elif path.endswith(".vscode/tasks.json"):
            data = read_json(ctx, entry)
            tasks = data.get("tasks", []) if isinstance(data, dict) else []
            auto = [
                t
                for t in tasks
                if isinstance(t, dict)
                and isinstance(t.get("runOptions"), dict)
                and t["runOptions"].get("runOn") == "folderOpen"
            ]
            f = _autostart(
                entry,
                "vscode-folderopen",
                list(_commands(auto)),
                "Diese VS-Code-Aufgaben starten beim Öffnen des Ordners von selbst.",
            )
        elif name == "package.json":
            data = read_json(ctx, entry)
            scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
            if isinstance(scripts, dict):
                cmds = [str(scripts[h]) for h in _INSTALL_HOOKS if isinstance(scripts.get(h), str)]
                f = _autostart(
                    entry,
                    "npm-install-skript",
                    cmds,
                    "npm führt `preinstall`, `install` und `postinstall` bei der Installation "
                    "automatisch aus.",
                )
        elif path.startswith(".git/hooks/") or "/.git/hooks/" in path:
            if not name.endswith(".sample"):
                f = _autostart(
                    entry,
                    "git-hook",
                    [read_text(ctx, entry, 4096)],
                    "Git-Hooks laufen bei Git-Befehlen automatisch.",
                )
        elif name == ".envrc":
            f = _autostart(
                entry,
                "envrc",
                [read_text(ctx, entry, 4096)],
                "direnv führt `.envrc` beim Betreten des Ordners aus, sobald es erlaubt wurde.",
            )
            if f is not None and f.schwere is Schwere.H:
                f = f.model_copy(update={"schwere": Schwere.M})
        if f is not None:
            yield f


# --- A03 install scripts ---------------------------------------------------------------------

_INSTALL_NAMES = re.compile(r"^(install|setup|bootstrap|get)[-_.]?\w*\.(sh|ps1|bash|bat|cmd)$")
_SETUP_PY_RISK = re.compile(
    r"\b(subprocess|os\.system|os\.popen|urllib\.request|urlopen|requests\.(get|post)|"
    r"socket\.|exec\(|eval\()"
)


def _a03(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        name = file_name(entry).lower()
        if entry.kind not in ("text", "script"):
            continue
        hit: str | None = None
        if name == "setup.py":
            m = _SETUP_PY_RISK.search(read_text(ctx, entry))
            hit = m.group(0) if m else None
        elif _INSTALL_NAMES.match(name) or name == "makefile":
            m = _DANGEROUS_COMMAND.search(read_text(ctx, entry))
            hit = m.group(0) if m else None
        if hit:
            yield finding(
                rule_id="LB-A03-installationsskript",
                ebene=Ebene.A,
                schwere=Schwere.H,
                titel="Installationsskript lädt nach oder startet Prozesse",
                erklaerung=(
                    "Das Skript läuft bei der Installation und lädt Code aus dem Netz oder startet "
                    "Prozesse. Was es nachlädt, ist nicht Teil der Prüfung."
                ),
                datei=entry.path,
                zeile=None,
                beleg=visible(hit),
                fix="Abhängigkeiten über den Paketmanager mit Lockfile beziehen, nichts nachladen.",
                fix_prompt=(
                    f"Ersetze in {entry.path} das Herunterladen und Ausführen durch "
                    "festgelegte Abhängigkeiten im Paketmanager."
                ),
                normbezug=("OWASP-ASI05", "OWASP-LLM03"),
            )
