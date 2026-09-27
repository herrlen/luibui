"""Analyzer A – Dateien (Prüfkatalog A02–A12, S1-5).

Looks at what lies in the package: files that run by themselves, install scripts, binaries,
disguised file types, archives, known malware, hidden files, symlinks and submodules from Git, and
settings that redirect package sources. Content is only read and matched, never interpreted.
"""

import re
from collections.abc import Iterator
from pathlib import PurePosixPath

from luibui_scan.analyzers._a_ausfuehrung import _a02, _a03
from luibui_scan.analyzers._a_formate import _a13, _a14, _a15, _installer
from luibui_scan.analyzers._a_herkunft import _a10, _a11, _a12
from luibui_scan.analyzers._a_modelle import _a16_pickle, _a18_safetensors, _a19_config
from luibui_scan.analyzers._common import finding, read_bytes, rules_dir, visible
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.inventory import EXECUTABLE_KINDS
from luibui_scan.models import Ebene, Finding, Schwere

__all__ = ["MAX_PER_RULE", "DateienAnalyzer", "known_malware", "rules_dir"]

MAX_PER_RULE = 20
"""At most this many findings per rule; the rest is summed up in the last one."""


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
_OFFICE_EXT = frozenset(
    {".docx", ".xlsx", ".pptx", ".docm", ".xlsm", ".pptm", ".dotx", ".dotm", ".xltm", ".potm",
     ".odt", ".ods", ".odp", ".epub",
     # PyTorch checkpoints are ZIP files; A16/A18 read their pickle data.
     ".pt", ".pth", ".ckpt", ".bin"}
)  # fmt: skip
_KIND_LABEL = {
    "elf": "Linux",
    "macho": "macOS",
    "pe": "Windows",
    "java-class": "Java",
    "wasm": "WebAssembly",
    "deb": "Debian-Paket",
    "rpm": "RPM-Paket",
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
    entpackt = set(ctx.entpackt)
    nicht_entpackt = dict(ctx.nicht_entpackt)
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
        if (ext == ".pyc" or kind == "pyc") and entry.path[: -len(ext) or None].split(
            "__pycache__/"
        )[-1].split(".")[0] not in {p[:-3].rsplit("/", 1)[-1] for p in paths if p.endswith(".py")}:
            compiled.append(_a06(entry, "Python-Bytecode ohne passende .py-Datei"))
        elif ext == ".js" and entry.kind == "text" and entry.size > 50_000:
            head = read_bytes(ctx, entry, 200_000)
            if head.count(b"\n") < 5 and not any(p == entry.path + ".map" for p in paths):
                compiled.append(_a06(entry, "Minifizierter JavaScript-Code ohne Quelle"))
        if kind in _ARCHIVE_KINDS and ext not in _OFFICE_EXT and entry.path not in entpackt:
            grund = nicht_entpackt.get(entry.path)
            archives.append(
                finding(
                    rule_id="LB-A07-archiv-im-paket",
                    ebene=Ebene.A,
                    schwere=Schwere.M,
                    titel="Archiv im Paket bleibt ungeprüft",
                    erklaerung=(
                        "Verschachtelte Archive werden nicht entpackt. Ihr Inhalt ist nicht "
                        "Teil dieser Prüfung."
                        if grund is None
                        else "Das Paket im Paket ließ sich nicht sicher entpacken. Sein Inhalt "
                        "ist nicht Teil dieser Prüfung."
                    ),
                    datei=entry.path,
                    zeile=None,
                    beleg=f"Typ: {kind}, {entry.size} Byte"
                    + ("" if grund is None else f", Grund: {grund}"),
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
        ".git-blame-ignore-revs",
        ".overrides",
        ".readthedocs.yaml",
        ".readthedocs.yml",
        ".mailmap",
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


@register
class DateienAnalyzer:
    info = AnalyzerInfo(name="a_dateien", titel="A – Dateien", ebenen=frozenset({Ebene.A}))

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        findings: list[Finding] = []
        for check in (
            _a02,
            _a03,
            _a04_to_a07,
            _installer,
            _a08,
            _a09,
            _a10,
            _a11,
            _a12,
            _a13,
            _a14,
            _a15,
            _a16_pickle,
            _a18_safetensors,
            _a19_config,
        ):
            findings.extend(check(ctx))
        return findings
