"""Opengrep adapter (Prüfkatalog C01–C12, S2-1). Only our own rules from ``rules/opengrep/``.

Hardening against the scanned package: ``--disable-nosem`` (``# nosem`` comments in the package
do not hide findings), no ``.gitignore``/``.semgrepignore`` from the package (so ``tests/``,
``node_modules/`` and hidden folders are scanned), fixed config directory (never
``--config auto`` or registry rules), no version check, empty environment, timeout. Opengrep
never goes online.

The binary unpacks itself into ``$XDG_CACHE_HOME/opengrep`` (240 MB). The worker image does that
once at build time and points ``LUIBUI_OPENGREP_CACHE`` at the read-only copy.
"""

import json
import os
import shutil
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from luibui_scan.tools import ToolError

TIMEOUT_SECONDS = 150
"""The whole intensive job has 300 s (uploads.py); gitleaks and Bandit need their share."""
RULE_TIMEOUT_SECONDS = 10
MAX_FILE_BYTES = 2_000_000
MAX_MEMORY_MB = 900
"""The worker has 1536 MB; measured peak for 779 code files: 262 MB."""
JOBS = 1
"""Opengrep would start one process per host core, not per container core."""


@dataclass(frozen=True, slots=True)
class Treffer:
    rule_id: str
    datei: str
    zeile: int | None
    code: str
    """The matched lines as Opengrep reports them (package content, never interpreted)."""


def binary() -> str:
    path = os.environ.get("LUIBUI_OPENGREP") or shutil.which("opengrep")
    if not path:
        raise ToolError("opengrep nicht installiert")
    return path


def _env(home: Path) -> dict[str, str]:
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONUTF8": "1",
        "OPENGREP_ENABLE_VERSION_CHECK": "0",
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
        "SEMGREP_SEND_METRICS": "off",
    }
    cache = os.environ.get("LUIBUI_OPENGREP_CACHE")
    if cache:
        env["XDG_CACHE_HOME"] = cache
    elif "HOME" in os.environ:  # local runs: reuse the user's unpacked copy
        env["XDG_CACHE_HOME"] = str(Path(os.environ["HOME"]) / ".cache")
    return env


def scan(root: Path, rules: Path, timeout: float = TIMEOUT_SECONDS) -> list[Treffer]:
    argv = [
        binary(),
        "scan",
        "--config", str((rules / "opengrep").resolve()),
        "--json",
        "--quiet",
        "--disable-nosem",
        "--disable-version-check",
        "--no-git-ignore",
        "--x-ignore-semgrepignore-files",
        "--no-rewrite-rule-ids",
        "--timeout", str(RULE_TIMEOUT_SECONDS),
        "--max-target-bytes", str(MAX_FILE_BYTES),
        "--max-memory", str(MAX_MEMORY_MB),
        "--jobs", str(JOBS),
        str(root.resolve()),
    ]  # fmt: skip
    # Own HOME for the log Opengrep writes, removed afterwards (the CLI leaves nothing behind).
    # Own process group: Opengrep starts opengrep-core, and a timeout must stop both.
    with tempfile.TemporaryDirectory(dir=root.parent, prefix=".opengrep-") as home:
        proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            argv,
            env=_env(Path(home)),
            cwd=home,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            raise ToolError("opengrep: Zeitlimit überschritten") from None
    # 0: no findings, 1: findings. Everything else is an error of the tool itself.
    if proc.returncode not in (0, 1):
        raise ToolError(f"opengrep: Exit-Code {proc.returncode}")
    try:
        raw = json.loads(stdout or b"{}")
    except ValueError:
        raise ToolError("opengrep: Ausgabe nicht lesbar") from None
    if not isinstance(raw, dict) or not isinstance(raw.get("results", []), list):
        raise ToolError("opengrep: Ausgabe nicht lesbar")
    root_str = str(root.resolve()) + os.sep
    treffer = []
    for item in raw.get("results", []):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", ""))
        resolved = str((root.parent / path).resolve()) if path else ""
        if not resolved.startswith(root_str):
            continue  # never report paths outside the package
        start = item.get("start")
        line = start.get("line") if isinstance(start, dict) else None
        extra = item.get("extra")
        code = extra.get("lines", "") if isinstance(extra, dict) else ""
        treffer.append(
            Treffer(
                rule_id=str(item.get("check_id", "unbekannt")).rsplit(".", 1)[-1][:100],
                datei=resolved[len(root_str) :].replace(os.sep, "/"),
                zeile=line if isinstance(line, int) and line >= 1 else None,
                code=str(code)[:2000],
            )
        )
    return treffer
