"""Analyzer A – Dateien (Prüfkatalog A02–A12, S1-5).

Looks at what lies in the package: files that run by themselves, install scripts, binaries,
disguised file types, archives, known malware, hidden files, symlinks and submodules from Git, and
settings that redirect package sources. Content is only read and matched, never interpreted.
"""

import json
import os
import re
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import Any

from luibui_scan.analyzers._common import finding, read_bytes, visible
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.inventory import EXECUTABLE_KINDS
from luibui_scan.models import Ebene, Finding, Schwere

MAX_PER_RULE = 20
"""At most this many findings per rule; the rest is summed up in the last one."""

_DANGEROUS_COMMAND = re.compile(
    r"(curl|wget|invoke-webrequest|iwr|irm)\b[^\n]*\|\s*(sudo\s+)?(ba|z|da)?sh\b"
    r"|\b(curl|wget)\b[^\n]*(-o|--output|>)\s*\S+[^\n]*(&&|;)\s*(sh|bash|chmod|\./)"
    r"|base64\s+(-d|--decode)|\beval\b|\bnc\s+-e\b|/dev/tcp/|python[0-9.]*\s+-c\b"
    r"|node\s+-e\b|powershell[^\n]*-enc",
    re.IGNORECASE,
)
_INSTALL_HOOKS = ("preinstall", "install", "postinstall")


def _text(ctx: ScanContext, entry: InventoryEntry, limit: int = 1024 * 1024) -> str:
    return read_bytes(ctx, entry, limit).decode("utf-8", errors="replace")


def _json(ctx: ScanContext, entry: InventoryEntry) -> Any:
    try:
        return json.loads(_text(ctx, entry))
    except (ValueError, RecursionError):
        return None


def _name(entry: InventoryEntry) -> str:
    return PurePosixPath(entry.path).name


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
        name = _name(entry).lower()
        f: Finding | None = None
        if path.endswith((".claude/settings.json", ".claude/settings.local.json")) or (
            name == "hooks.json"
        ):
            data = _json(ctx, entry)
            hooks = data.get("hooks") if isinstance(data, dict) else None
            f = _autostart(
                entry,
                "claude-hooks",
                list(_commands(hooks)),
                "Hooks von Claude Code führen Befehle bei Ereignissen automatisch aus, etwa bei "
                "jedem Tool-Aufruf oder Sitzungsstart.",
            )
        elif path.endswith(".vscode/tasks.json"):
            data = _json(ctx, entry)
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
            data = _json(ctx, entry)
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
                    [_text(ctx, entry, 4096)],
                    "Git-Hooks laufen bei Git-Befehlen automatisch.",
                )
        elif name == ".envrc":
            f = _autostart(
                entry,
                "envrc",
                [_text(ctx, entry, 4096)],
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
        name = _name(entry).lower()
        if entry.kind not in ("text", "script"):
            continue
        hit: str | None = None
        if name == "setup.py":
            m = _SETUP_PY_RISK.search(_text(ctx, entry))
            hit = m.group(0) if m else None
        elif _INSTALL_NAMES.match(name) or name == "makefile":
            m = _DANGEROUS_COMMAND.search(_text(ctx, entry))
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


# --- A04 binaries, A05 disguised types, A06 compiled code, A07 archives ----------------------

_TEXT_EXT = frozenset(
    [
        ".md",
        ".txt",
        ".py",
        ".js",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".jsx",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".sh",
        ".ps1",
        ".html",
        ".css",
        ".csv",
        ".ini",
        ".cfg",
        ".xml",
        ".svg",
        ".rst",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".java",
        ".kt",
        ".cs",
        ".c",
        ".h",
        ".cpp",
        ".lua",
        ".sql",
        ".env",
    ]
)
_BINARY_EXT: dict[str, frozenset[str]] = {
    ".png": frozenset({"png"}),
    ".jpg": frozenset({"jpeg"}),
    ".jpeg": frozenset({"jpeg"}),
    ".gif": frozenset({"gif"}),
    ".webp": frozenset({"webp"}),
    ".pdf": frozenset({"pdf"}),
    ".zip": frozenset({"zip"}),
    ".gz": frozenset({"gzip"}),
    ".tgz": frozenset({"gzip"}),
    ".docx": frozenset({"zip"}),
    ".xlsx": frozenset({"zip"}),
    ".pptx": frozenset({"zip"}),
    ".sqlite": frozenset({"sqlite"}),
    ".db": frozenset({"sqlite"}),
}
_ARCHIVE_KINDS = frozenset({"zip", "gzip", "bzip2", "xz", "7z", "rar", "tar"})
_OFFICE_EXT = frozenset({".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp", ".epub"})
_KIND_LABEL = {
    "elf": "Linux",
    "macho": "macOS",
    "pe": "Windows",
    "java-class": "Java",
    "wasm": "WebAssembly",
}


def _capped(findings: list[Finding]) -> list[Finding]:
    if len(findings) <= MAX_PER_RULE:
        return findings
    rest = len(findings) - MAX_PER_RULE + 1
    last = findings[MAX_PER_RULE - 1]
    summary = last.model_copy(
        update={"erklaerung": last.erklaerung + f" Dazu {rest - 1} weitere Dateien derselben Art."}
    )
    return [*findings[: MAX_PER_RULE - 1], summary]


def _a04_to_a07(ctx: ScanContext) -> Iterator[Finding]:
    binaries, disguised, compiled, archives = [], [], [], []
    paths = {e.path for e in ctx.inventory}
    for entry in ctx.inventory:
        ext = PurePosixPath(entry.path).suffix.lower()
        kind = entry.kind or "binary"
        if kind in EXECUTABLE_KINDS:
            binaries.append(
                finding(
                    rule_id="LB-A04-programmdatei",
                    ebene=Ebene.A,
                    schwere=Schwere.H,
                    titel=f"Ausführbare Programmdatei ({_KIND_LABEL.get(kind, kind)})",
                    erklaerung=(
                        "Das Paket enthält ein fertiges Programm. Was es tut, lässt sich statisch "
                        "nicht prüfen. Skills und MCP-Server brauchen selten Binärdateien."
                    ),
                    datei=entry.path,
                    zeile=None,
                    beleg=f"Typ: {kind}, {entry.size} Byte, SHA-256 {entry.sha256[:16]}…",
                    fix="Die Programmdatei entfernen oder aus Quellcode im Paket bauen lassen.",
                    fix_prompt=f"Entferne {entry.path} oder ersetze es durch Quellcode.",
                    normbezug=("OWASP-ASI04", "OWASP-LLM03"),
                )
            )
        mismatch = (ext in _TEXT_EXT and kind not in ("text", "script", "leer")) or (
            ext in _BINARY_EXT and kind not in _BINARY_EXT[ext] and kind != "leer"
        )
        if mismatch:
            disguised.append(
                finding(
                    rule_id="LB-A05-falsche-endung",
                    ebene=Ebene.A,
                    schwere=Schwere.H,
                    titel="Dateiendung passt nicht zum Inhalt",
                    erklaerung=(
                        f"Die Datei heißt `{ext}`, ist aber vom Typ `{kind}`. So werden Programme "
                        "oder Archive als harmlose Dateien getarnt."
                    ),
                    datei=entry.path,
                    zeile=None,
                    beleg=f"Endung {ext}, erkannter Typ {kind}",
                    fix="Die Datei entfernen oder mit der richtigen Endung ablegen.",
                    fix_prompt=f"Prüfe {entry.path}: Endung {ext}, tatsächlicher Typ {kind}.",
                    normbezug=("OWASP-ASI04",),
                )
            )
        if ext == ".pyc" and entry.path[: -len(ext)].split("__pycache__/")[-1].split(".")[
            0
        ] not in {p[:-3].rsplit("/", 1)[-1] for p in paths if p.endswith(".py")}:
            compiled.append(_a06(entry, "Python-Bytecode ohne passende .py-Datei"))
        elif ext == ".js" and entry.kind == "text" and entry.size > 50_000:
            head = read_bytes(ctx, entry, 200_000)
            if head.count(b"\n") < 5 and not any(p == entry.path + ".map" for p in paths):
                compiled.append(_a06(entry, "Minifizierter JavaScript-Code ohne Quelle"))
        if kind in _ARCHIVE_KINDS and ext not in _OFFICE_EXT:
            archives.append(
                finding(
                    rule_id="LB-A07-archiv-im-paket",
                    ebene=Ebene.A,
                    schwere=Schwere.M,
                    titel="Archiv im Paket bleibt ungeprüft",
                    erklaerung=(
                        "Verschachtelte Archive werden nicht entpackt. Ihr Inhalt ist nicht "
                        "Teil dieser Prüfung."
                    ),
                    datei=entry.path,
                    zeile=None,
                    beleg=f"Typ: {kind}, {entry.size} Byte",
                    fix="Den Inhalt entpackt ins Paket legen oder das Archiv entfernen.",
                    fix_prompt=f"Entpacke {entry.path} ins Paket oder entferne es.",
                    normbezug=("OWASP-ASI04",),
                )
            )
    for group in (binaries, disguised, compiled, archives):
        yield from _capped(group)


def _a06(entry: InventoryEntry, titel: str) -> Finding:
    return finding(
        rule_id="LB-A06-kompiliert-ohne-quelle",
        ebene=Ebene.A,
        schwere=Schwere.M,
        titel=titel,
        erklaerung="Kompilierter oder minifizierter Code lässt sich kaum prüfen.",
        datei=entry.path,
        zeile=None,
        beleg=f"{entry.size} Byte",
        fix="Den lesbaren Quellcode beilegen oder die Datei entfernen.",
        fix_prompt=f"Ersetze {entry.path} durch den lesbaren Quellcode.",
        normbezug=("OWASP-ASI04",),
    )


# --- A08 known malware ---------------------------------------------------------------------

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def rules_dir() -> Path:
    """``LUIBUI_RULES_DIR``, else the repository's ``rules/`` (development), else ``/rules``."""
    env = os.environ.get("LUIBUI_RULES_DIR")
    if env:
        return Path(env)
    repo = Path(__file__).resolve().parents[4] / "rules"
    return repo if repo.is_dir() else Path("/rules")


def known_malware() -> frozenset[str]:
    path = rules_dir() / "data" / "schadsoftware-sha256.txt"
    try:
        lines = path.read_text("utf-8").splitlines()
    except FileNotFoundError:
        return frozenset()
    return frozenset(
        h for line in lines if _HEX64.match(h := line.split("#", 1)[0].strip().lower())
    )


def _a08(ctx: ScanContext) -> Iterator[Finding]:
    bad = known_malware()
    for entry in ctx.inventory:
        if entry.sha256 in bad:
            yield finding(
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


# --- A09 hidden files ----------------------------------------------------------------------

_USUAL_DOT = frozenset(
    [
        ".github",
        ".gitignore",
        ".gitattributes",
        ".editorconfig",
        ".npmignore",
        ".dockerignore",
        ".gitmodules",
        ".nvmrc",
        ".node-version",
        ".python-version",
        ".tool-versions",
        ".well-known",
        ".claude-plugin",
        ".claude",
        ".vscode",
        ".devcontainer",
        ".cursor",
        ".husky",
        ".changeset",
        ".mcp.json",
        ".env.example",
        ".env.sample",
        ".pre-commit-config.yaml",
        ".prettierrc",
        ".prettierignore",
        ".eslintrc",
        ".eslintignore",
        ".markdownlint",
        ".yarnrc",
        ".yarnrc.yml",
        ".npmrc",
        ".ruff.toml",
        ".flake8",
        ".coveragerc",
        ".pylintrc",
        ".stylelintrc",
        ".browserslistrc",
        ".gitkeep",
        ".keep",
        ".envrc",
        ".babelrc",
        ".swcrc",
        ".vscodeignore",
    ]
)


def _a09(ctx: ScanContext) -> Iterator[Finding]:
    unusual: list[str] = []
    env_files: list[str] = []
    for entry in ctx.inventory:
        parts = entry.path.split("/")
        dot = next((p for p in parts if p.startswith(".")), None)
        if dot is None:
            continue
        base = dot.split(".json")[0] if dot.startswith(".eslintrc") else dot
        if parts[-1] == ".env" or re.fullmatch(r"\.env\.(local|prod|production|dev)", parts[-1]):
            env_files.append(entry.path)
        elif not any(base == u or base.startswith(u + ".") for u in _USUAL_DOT):
            unusual.append(entry.path)
    if env_files:
        yield finding(
            rule_id="LB-A09-env-datei",
            ebene=Ebene.A,
            schwere=Schwere.M,
            titel="Umgebungsdatei im Paket",
            erklaerung=(
                "Eine `.env`-Datei enthält meist Zugangsdaten und gehört nicht in ein "
                "veröffentlichtes Paket."
            ),
            datei=env_files[0],
            zeile=None,
            beleg=visible(", ".join(env_files[:10])),
            fix="Die `.env`-Datei entfernen und nur eine `.env.example` ohne Werte beilegen.",
            fix_prompt="Entferne .env-Dateien und lege eine .env.example ohne Werte an.",
            normbezug=("OWASP-LLM02",),
        )
    if unusual:
        yield finding(
            rule_id="LB-A09-versteckte-dateien",
            ebene=Ebene.A,
            schwere=Schwere.N,
            titel="Ungewöhnliche versteckte Dateien",
            erklaerung=(
                f"{len(unusual)} Dateien liegen in versteckten Ordnern oder beginnen mit einem "
                "Punkt und gehören zu keinem bekannten Werkzeug. Sie fallen beim Durchsehen "
                "leicht nicht auf."
            ),
            datei=unusual[0],
            zeile=None,
            beleg=visible(", ".join(unusual[:10])),
            fix="Prüfen, ob diese Dateien ins Paket gehören.",
            fix_prompt="Prüfe die versteckten Dateien und entferne, was nicht gebraucht wird.",
            normbezug=(),
        )


# --- A10 Git symlinks, A11 submodules ------------------------------------------------------


def _a10(ctx: ScanContext) -> Iterator[Finding]:
    by_path = {e.path: e for e in ctx.inventory}
    for path in ctx.options.get("git_symlinks", []):
        entry = by_path.get(path)
        if entry is None:
            continue
        target = _text(ctx, entry, 1024).strip()
        resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
        if target.startswith("/") or resolved == ".." or resolved.startswith("../"):
            yield finding(
                rule_id="LB-A10-symlink-nach-aussen",
                ebene=Ebene.A,
                schwere=Schwere.M,
                titel="Verknüpfung zeigt aus dem Paket heraus",
                erklaerung=(
                    "Im Repository ist diese Datei eine Verknüpfung auf ein Ziel außerhalb des "
                    "Pakets. Beim Installieren kann sie auf Dateien des Nutzers zeigen. luibui hat "
                    "sie nur als Text mit dem Ziel übernommen."
                ),
                datei=path,
                zeile=None,
                beleg="Ziel: " + visible(target, 200),
                fix="Die Verknüpfung durch eine echte Datei im Paket ersetzen.",
                fix_prompt=f"Ersetze die Verknüpfung {path} durch eine echte Datei im Paket.",
                normbezug=("OWASP-ASI04",),
            )


_SUBMODULE_URL = re.compile(r"^\s*url\s*=\s*(\S+)", re.MULTILINE)


def _a11(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        if _name(entry) == ".gitmodules":
            urls = _SUBMODULE_URL.findall(_text(ctx, entry, 64 * 1024))
            yield finding(
                rule_id="LB-A11-submodule",
                ebene=Ebene.A,
                schwere=Schwere.M,
                titel="Submodule werden nicht mitgeprüft",
                erklaerung=(
                    "Das Paket bindet weitere Repositories als Submodule ein. Sie werden bei der "
                    "Installation nachgeladen, sind aber nicht Teil dieser Prüfung."
                ),
                datei=entry.path,
                zeile=None,
                beleg=visible(", ".join(urls[:5]) or "(keine URL)"),
                fix="Den benötigten Code direkt ins Paket übernehmen.",
                fix_prompt="Übernimm den Code der Submodule ins Paket und entferne .gitmodules.",
                normbezug=("OWASP-ASI04", "OWASP-LLM03"),
            )


# --- A12 foreign package sources -----------------------------------------------------------

_PIP_INDEX = re.compile(r"^\s*(--index-url|--extra-index-url|-i|--find-links|-f)[\s=]+(\S+)", re.M)
_PIP_CONF = re.compile(r"^\s*(index-url|extra-index-url|find-links)\s*=\s*(\S+)", re.M)
_NPM_REGISTRY = re.compile(r"^\s*(@[\w.-]+:)?registry\s*=\s*(\S+)", re.M)
_TOML_INDEX = re.compile(
    r"\[\[?tool\.(uv\.index|poetry\.source|pdm\.source)\]?\][^\[]*?url\s*=\s*\"([^\"]+)\"", re.S
)
_OFFICIAL = re.compile(
    r"^https://(pypi\.org|files\.pythonhosted\.org|registry\.npmjs\.org|registry\.yarnpkg\.com)(/|$)"
)


def _a12(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        name = _name(entry).lower()
        if entry.kind not in ("text", "script"):
            continue
        patterns: list[re.Pattern[str]] = []
        if name.startswith("requirements") and name.endswith((".txt", ".in")):
            patterns = [_PIP_INDEX]
        elif name in ("pip.conf", "pip.ini"):
            patterns = [_PIP_CONF]
        elif name in (".npmrc", ".yarnrc", ".yarnrc.yml"):
            patterns = [_NPM_REGISTRY]
        elif name == "pyproject.toml":
            patterns = [_TOML_INDEX]
        if not patterns:
            continue
        text = _text(ctx, entry)
        for pattern in patterns:
            for m in pattern.finditer(text):
                url = m.group(2).strip("\"'")
                if _OFFICIAL.match(url):
                    continue
                yield finding(
                    rule_id="LB-A12-fremde-paketquelle",
                    ebene=Ebene.A,
                    schwere=Schwere.H,
                    titel="Pakete kommen aus einer fremden Quelle",
                    erklaerung=(
                        "Die Installation lädt Pakete nicht nur vom offiziellen Verzeichnis. Unter "
                        "gleichem Namen kann dort etwas anderes liegen (Dependency Confusion)."
                    ),
                    datei=entry.path,
                    zeile=text.count("\n", 0, m.start()) + 1,
                    beleg=visible(m.group(0).strip()),
                    fix="Nur das offizielle Paketverzeichnis verwenden oder die Quelle begründen.",
                    fix_prompt=f"Entferne in {entry.path} die Paketquelle {visible(url, 100)}.",
                    normbezug=("OWASP-ASI04", "OWASP-LLM03"),
                )
                break


@register
class DateienAnalyzer:
    info = AnalyzerInfo(name="a_dateien", titel="A – Dateien", ebenen=frozenset({Ebene.A}))

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        findings: list[Finding] = []
        for check in (_a02, _a03, _a04_to_a07, _a08, _a09, _a10, _a11, _a12):
            findings.extend(check(ctx))
        return findings
