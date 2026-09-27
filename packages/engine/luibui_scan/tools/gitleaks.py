"""gitleaks adapter (Prüfkatalog B20, S1-8).

Hardening against the scanned package: our own ``--config`` (otherwise gitleaks would read a
``.gitleaks.toml`` from the package), our own empty ignore file (otherwise ``.gitleaksignore``),
``--ignore-gitleaks-allow`` (inline ``gitleaks:allow`` comments are ignored), no symlink following,
secrets redacted, empty environment, timeout. gitleaks never goes online.
"""

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from luibui_scan.tools import ToolError

TIMEOUT_SECONDS = 120
MAX_FILE_MB = 10


@dataclass(frozen=True, slots=True)
class Leak:
    rule_id: str
    beschreibung: str
    datei: str
    zeile: int | None
    match: str
    """Matched text with the secret already replaced by ``REDACTED``."""


def binary() -> str:
    path = os.environ.get("LUIBUI_GITLEAKS") or shutil.which("gitleaks")
    if not path:
        raise ToolError("gitleaks nicht installiert")
    return path


def scan(root: Path, rules: Path, timeout: float = TIMEOUT_SECONDS) -> list[Leak]:
    argv = [
        binary(),
        "dir",
        str(root),
        "--config", str(rules / "gitleaks" / "gitleaks.toml"),
        "--gitleaks-ignore-path", str(rules / "gitleaks" / "leer.gitleaksignore"),
        "--ignore-gitleaks-allow",
        "--redact=100",
        "--report-format", "json",
        "--report-path", "-",
        "--exit-code", "0",
        "--max-target-megabytes", str(MAX_FILE_MB),
        "--max-archive-depth", "0",
        "--no-banner",
        "--no-color",
        "--log-level", "error",
    ]  # fmt: skip
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            argv,
            env={"PATH": "/usr/bin:/bin", "HOME": str(root.parent), "LANG": "C"},
            cwd=root.parent,
            capture_output=True,
            timeout=timeout,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        raise ToolError("gitleaks: Zeitlimit überschritten") from None
    if proc.returncode != 0:
        raise ToolError(f"gitleaks: Exit-Code {proc.returncode}")
    try:
        raw = json.loads(proc.stdout or b"[]")
    except ValueError:
        raise ToolError("gitleaks: Ausgabe nicht lesbar") from None
    if not isinstance(raw, list):
        raise ToolError("gitleaks: Ausgabe nicht lesbar")
    root_str = str(root.resolve()) + os.sep
    leaks = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        file = str(item.get("File", ""))
        resolved = str(Path(file).resolve()) if file else ""
        if not resolved.startswith(root_str):
            continue  # never report paths outside the package
        line = item.get("StartLine")
        leaks.append(
            Leak(
                rule_id=str(item.get("RuleID", "unbekannt"))[:100],
                beschreibung=str(item.get("Description", ""))[:200],
                datei=resolved[len(root_str) :].replace(os.sep, "/"),
                zeile=line if isinstance(line, int) and line >= 1 else None,
                match=str(item.get("Match", ""))[:300],
            )
        )
    return leaks
