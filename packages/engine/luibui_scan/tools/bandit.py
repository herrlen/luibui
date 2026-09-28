"""Bandit adapter (Prüfkatalog C01, C02, C11, C13 for Python, S2-1).

Bandit parses Python to a syntax tree and never imports or runs it. Hardening against the
scanned package: our own empty ``--ini`` (otherwise Bandit reads a ``.bandit`` file from the
package), ``--ignore-nosec`` (``# nosec`` comments do not hide findings), ``-x`` replaces the
default exclusions (``.git``, ``.tox``, ``*.egg`` …) so code cannot hide there, empty
environment, timeout.
"""

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from luibui_scan.tools import ToolError

TIMEOUT_SECONDS = 90
NIE_VORHANDEN = "/luibui-keine-ausnahme"
"""``-x`` needs a value; this path never exists, so nothing is excluded."""


@dataclass(frozen=True, slots=True)
class Treffer:
    test_id: str
    schwere: str
    """HIGH, MEDIUM or LOW."""
    sicherheit: str
    """Bandit's confidence: HIGH, MEDIUM or LOW."""
    text: str
    datei: str
    zeile: int | None
    code: str


def scan(root: Path, rules: Path, timeout: float = TIMEOUT_SECONDS) -> list[Treffer]:
    argv = [
        sys.executable, "-m", "bandit",
        "-r", str(root.resolve()),
        "-f", "json",
        "--exit-zero",
        "--quiet",
        "--ignore-nosec",
        "--ini", str((rules / "bandit" / "leer.bandit").resolve()),
        "-x", NIE_VORHANDEN,
    ]  # fmt: skip
    try:
        with tempfile.TemporaryDirectory(dir=root.parent, prefix=".bandit-") as home:
            proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
                argv,
                env={"PATH": "/usr/bin:/bin", "HOME": home, "LANG": "C.UTF-8"},
                cwd=home,
                capture_output=True,
                timeout=timeout,
                check=False,
                stdin=subprocess.DEVNULL,
            )
    except subprocess.TimeoutExpired:
        raise ToolError("bandit: Zeitlimit überschritten") from None
    if proc.returncode != 0:
        raise ToolError(f"bandit: Exit-Code {proc.returncode}")
    try:
        raw = json.loads(proc.stdout or b"{}")
    except ValueError:
        raise ToolError("bandit: Ausgabe nicht lesbar") from None
    if not isinstance(raw, dict) or not isinstance(raw.get("results", []), list):
        raise ToolError("bandit: Ausgabe nicht lesbar")
    root_str = str(root.resolve()) + os.sep
    treffer = []
    for item in raw.get("results", []):
        if not isinstance(item, dict):
            continue
        file = str(item.get("filename", ""))
        resolved = str(Path(file).resolve()) if file else ""
        if not resolved.startswith(root_str):
            continue  # never report paths outside the package
        line = item.get("line_number")
        treffer.append(
            Treffer(
                test_id=str(item.get("test_id", ""))[:10],
                schwere=str(item.get("issue_severity", "LOW")).upper(),
                sicherheit=str(item.get("issue_confidence", "LOW")).upper(),
                text=str(item.get("issue_text", ""))[:300],
                datei=resolved[len(root_str) :].replace(os.sep, "/"),
                zeile=line if isinstance(line, int) and line >= 1 else None,
                code=str(item.get("code", ""))[:2000],
            )
        )
    return treffer
