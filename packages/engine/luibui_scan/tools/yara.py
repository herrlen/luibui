"""YARA-X adapter (Prüfkatalog C10 and A04 for binaries, Scanner-Matrix BIN-01, S4-10).

Runs the ``yr`` command line of YARA-X (BSD-3-Clause) with luibui's own rules from
``rules/yara``. Only the files named in a scan list are read; YARA rules cannot execute anything.
Hardening: empty environment, one thread, size limit per file, timeout, JSON output parsed and
paths outside the package dropped.
"""

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from luibui_scan.tools import ToolError

TIMEOUT_SECONDS = 120
MAX_DATEI = 50 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class Treffer:
    regel: str
    schwere: str
    titel: str
    datei: str


def binary() -> str:
    path = os.environ.get("LUIBUI_YARA") or shutil.which("yr")
    if not path:
        raise ToolError("YARA-X (yr) nicht installiert")
    return path


def scan(
    root: Path, dateien: list[str], rules: Path, timeout: float = TIMEOUT_SECONDS
) -> list[Treffer]:
    """Scan ``dateien`` (paths relative to ``root``) with the rules in ``rules/yara``."""
    if not dateien:
        return []
    root_str = str(root.resolve()) + os.sep
    with tempfile.TemporaryDirectory(dir=root.parent, prefix=".yara-") as tmp:
        liste = Path(tmp) / "liste"
        liste.write_text("".join(str((root / d).resolve()) + "\n" for d in dateien), "utf-8")
        argv = [
            binary(), "scan",
            "--output-format", "json",
            "--print-meta",
            "--disable-console-logs",
            "--disable-warnings",
            "--threads", "1",
            "--skip-larger", str(MAX_DATEI),
            "--timeout", str(int(timeout)),
            "--scan-list",
            str((rules / "yara").resolve()),
            str(liste),
        ]  # fmt: skip
        try:
            proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
                argv,
                env={"PATH": "/usr/bin:/bin", "HOME": tmp, "LANG": "C.UTF-8"},
                cwd=tmp,
                capture_output=True,
                timeout=timeout + 10,
                check=False,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            raise ToolError("yr: Zeitlimit überschritten") from None
    if proc.returncode != 0:
        raise ToolError(f"yr: Exit-Code {proc.returncode}")
    try:
        raw = json.loads(proc.stdout or b"{}")
    except ValueError:
        raise ToolError("yr: Ausgabe nicht lesbar") from None
    matches = raw.get("matches") if isinstance(raw, dict) else None
    if not isinstance(matches, list):
        raise ToolError("yr: Ausgabe nicht lesbar")
    treffer = []
    for m in matches:
        if not isinstance(m, dict) or not isinstance(m.get("meta"), dict):
            continue
        datei = str(Path(str(m.get("file", ""))).resolve())
        if not datei.startswith(root_str):
            continue
        meta = m["meta"]
        treffer.append(
            Treffer(
                regel=str(meta.get("regel", m.get("rule", "")))[:100],
                schwere=str(meta.get("schwere", "M"))[:1],
                titel=str(meta.get("titel", ""))[:200],
                datei=datei[len(root_str) :].replace(os.sep, "/"),
            )
        )
    return treffer
