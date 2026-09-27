"""Analyzer A, part 1: things that run by themselves (Prüfkatalog A02, A03)."""

import re
from collections.abc import Iterator
from typing import Any

from luibui_scan.analyzers._common import (
    file_name,
    finding,
    read_bytes,
    read_json,
    read_text,
    visible,
)
from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.models import Ebene, Finding, Schwere

_DANGEROUS_COMMAND = re.compile(
    r"(curl|wget|invoke-webrequest|iwr|irm)\b[^\n]*\|\s*(sudo\s+)?(ba|z|da)?sh\b"
    r"|\b(curl|wget)\b[^\n]*(-o|--output|>)\s*\S+[^\n]*(&&|;)\s*(sh|bash|chmod|\./)"
    r"|base64\s+(-d|--decode)|\beval\b|\bnc\s+-e\b|/dev/tcp/|python[0-9.]*\s+-c\b"
    r"|node\s+-e\b|powershell[^\n]*-enc"
    # Deleting the home or root folder, reading credentials, sending files away, persistence.
    r"|\brm\s+-[a-z]*r[a-z]*f?[a-z]*\s+(~|\$home|/)(\s|/?$|/\*)"
    r"|(~|\$home|%userprofile%)[/\\]\.(ssh|aws|gnupg|kube|docker/config)"
    r"|\.config/gcloud|library/application support/(google/chrome|firefox)|\.mozilla/firefox"
    r"|\bcurl\b[^\n]*\s(-d|--data[a-z-]*|-F|--form|-T|--upload-file)\s+\S*@"
    r"|\b(crontab\s+-|launchctl\s+load|systemctl\s+(--user\s+)?enable)\b"
    r"|>>\s*~/\.(bashrc|zshrc|profile|bash_profile)"
    r"|iex\s*\(|invoke-expression|new-object\s+net\.webclient",
    re.IGNORECASE,
)
_INSTALL_HOOKS = ("preinstall", "install", "postinstall")
_DEV_HOOKS = ("prepare",)
"""``prepare`` runs on ``npm install`` from Git and in a local checkout, not for registry installs.
It is reported only when the command itself is dangerous (husky and builds are the common case)."""

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


def _flatten(value: Any) -> list[str]:
    """devcontainer commands: a string, a list of arguments or an object of named commands."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [" ".join(str(v) for v in value)]
    if isinstance(value, dict):
        return [c for v in value.values() for c in _flatten(v)]
    return []


_DEVCONTAINER_KEYS = (
    "initializeCommand",
    "onCreateCommand",
    "updateContentCommand",
    "postCreateCommand",
    "postStartCommand",
    "postAttachCommand",
)
_PYTHON_RISK = re.compile(
    r"\b(subprocess|os\.system|os\.popen|os\.exec|urllib|urlopen|requests\.|socket\.|"
    r"exec\s*\(|eval\s*\(|compile\s*\(|base64|marshal|__import__|ctypes)"
)


def _autostart(
    entry: InventoryEntry,
    art: str,
    commands: list[str],
    erklaerung: str,
    risk: re.Pattern[str] = _DANGEROUS_COMMAND,
) -> Finding | None:
    if not commands:
        return None
    dangerous = [c for c in commands if risk.search(c) or _DANGEROUS_COMMAND.search(c)]
    shown = dangerous[0] if dangerous else commands[0]
    m = risk.search(shown) or _DANGEROUS_COMMAND.search(shown)
    if m and len(shown) > 300:
        line_start = shown.rfind("\n", 0, m.start()) + 1
        shown = shown[line_start : line_start + 300]
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
                cmds += [
                    str(scripts[h])
                    for h in _DEV_HOOKS
                    if isinstance(scripts.get(h), str) and _DANGEROUS_COMMAND.search(scripts[h])
                ]
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
        elif name in ("devcontainer.json", ".devcontainer.json"):
            data = read_json(ctx, entry)
            cmds = []
            if isinstance(data, dict):
                for key in _DEVCONTAINER_KEYS:
                    cmds.extend(_flatten(data.get(key)))
            f = _autostart(
                entry,
                "devcontainer",
                cmds,
                "Dev Container führen diese Befehle beim Öffnen aus, `initializeCommand` sogar "
                "direkt auf dem Rechner des Nutzers.",
            )
        elif path.endswith(".vscode/settings.json"):
            data = read_json(ctx, entry)
            if isinstance(data, dict) and data.get("task.allowAutomaticTasks") == "on":
                f = _autostart(
                    entry,
                    "vscode-automatische-aufgaben",
                    ['"task.allowAutomaticTasks": "on"'],
                    "Die Einstellung erlaubt VS Code, Aufgaben beim Öffnen ohne Rückfrage zu "
                    "starten.",
                )
        elif name.endswith(".pth") and entry.kind == "text":
            lines = [
                line
                for line in read_text(ctx, entry, 64 * 1024).splitlines()
                if line.startswith(("import ", "import\t"))
            ]
            f = _autostart(
                entry,
                "python-pth",
                lines,
                "Python führt `import`-Zeilen in `.pth`-Dateien bei jedem Start des Interpreters "
                "aus, sobald das Paket installiert ist.",
                risk=_PYTHON_RISK,
            )
        elif name in ("sitecustomize.py", "usercustomize.py"):
            f = _autostart(
                entry,
                "python-sitecustomize",
                [read_text(ctx, entry, 64 * 1024)],
                f"`{name}` läuft bei jedem Start von Python automatisch, wenn es im Suchpfad "
                "liegt.",
                risk=_PYTHON_RISK,
            )
        elif name == "setup.py":
            text = read_text(ctx, entry)
            m = _DANGEROUS_COMMAND.search(text)
            if m:
                f = _autostart(
                    entry,
                    "setup-py",
                    [m.group(0)],
                    "`setup.py` läuft bei `pip install` aus dem Quellcode automatisch.",
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


_SCRIPT_EXT = (".sh", ".bash", ".zsh", ".ps1", ".psm1", ".bat", ".cmd")
_SHELL_SHEBANG = re.compile(rb"^#![^\n]*\b(sh|bash|zsh|dash|ksh|pwsh|powershell)\b")
_SCRIPT_RISK = re.compile(
    r"(curl|wget|invoke-webrequest|iwr|irm)\b[^\n]*\|\s*(sudo\s+)?(ba|z|da)?sh\b"
    r"|\b(curl|wget)\b[^\n]*(-o|--output|>)\s*\S+[^\n]*(&&|;)\s*(sh|bash|chmod|\./)"
    r"|base64\s+(-d|--decode)[^\n]*\|\s*(ba|z)?sh\b|\bnc\s+-e\b"
    r"|/dev/tcp/[^\n]*(0>&1|<&)|\bsh\s+-i\s*>&"
    r"|iex\s*\(|invoke-expression|new-object\s+net\.webclient|powershell[^\n]*-enc",
    re.IGNORECASE,
)
_NETWORK = re.compile(r"\b(urllib\.request|urlopen|requests\.(get|post)|httpx\.|socket\.)")
_LOCAL_BACKEND = re.compile(r"^\s*backend-path\s*=\s*\[[^\]]*\]", re.MULTILINE)


def _is_script(ctx: ScanContext, entry: InventoryEntry) -> bool:
    """Shell and PowerShell scripts; code in Python, JavaScript & Co. belongs to Ebene C."""
    if entry.path.lower().endswith(_SCRIPT_EXT):
        return True
    return entry.kind == "script" and bool(_SHELL_SHEBANG.match(read_bytes(ctx, entry, 128)))


def _a03(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        name = file_name(entry).lower()
        if entry.kind not in ("text", "script"):
            continue
        hit: str | None = None
        if name == "setup.py":
            m = _SETUP_PY_RISK.search(read_text(ctx, entry))
            hit = m.group(0) if m else None
        elif _INSTALL_NAMES.match(name) or name in ("makefile", "justfile"):
            m = _DANGEROUS_COMMAND.search(read_text(ctx, entry))
            hit = m.group(0) if m else None
        elif name == "conftest.py":
            m = _NETWORK.search(read_text(ctx, entry))
            hit = m.group(0) if m else None
        elif name == "pyproject.toml":
            m = _LOCAL_BACKEND.search(read_text(ctx, entry))
            hit = m.group(0) if m else None
        elif _is_script(ctx, entry):
            m = _SCRIPT_RISK.search(read_text(ctx, entry))
            hit = m.group(0) if m else None
        if hit:
            yield finding(
                rule_id="LB-A03-installationsskript",
                ebene=Ebene.A,
                schwere=Schwere.H,
                titel="Skript lädt nach, startet Prozesse oder greift auf Zugangsdaten zu",
                erklaerung=(
                    "Das Skript läuft bei Installation, Tests, Build oder auf Aufruf und lädt Code "
                    "aus dem Netz, startet Prozesse oder liest Zugangsdaten. Was es nachlädt, ist "
                    "nicht Teil der Prüfung."
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
