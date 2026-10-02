"""Presidio adapter (Prüfkatalog G07, Scanner-Matrix DAT-01, S3-13).

Presidio and its German spaCy model live in their own venv in the worker image
(``LUIBUI_PRESIDIO_PYTHON``), never in the engine's dependencies: loaded they take about 280 MB,
so they run in a short-lived subprocess that frees the memory again (docs/log.md, 02.10.2026).
The subprocess gets one text per table column on stdin and returns only counts (values, values
that are names), never the values.
Isolated mode (``-I``: no environment, no user site, no current directory on the path), empty
environment, timeout. Network is cut by the worker for the whole job anyway.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from luibui_scan.tools import ToolError

TIMEOUT_SECONDS = 120
RUNNER = Path(__file__).with_name("_presidio_runner.py")


def python() -> str:
    path = os.environ.get("LUIBUI_PRESIDIO_PYTHON")
    if not path:
        raise ToolError("Presidio nicht installiert (LUIBUI_PRESIDIO_PYTHON)")
    return path


def zaehlen(
    texte: dict[str, str], arbeitsordner: Path, timeout: float = TIMEOUT_SECONDS
) -> dict[str, dict[str, int]]:
    """Counts for each text, keyed like ``texte`` (see ``_presidio_runner.zaehlen``)."""
    if not texte:
        return {}
    eingabe = json.dumps({"texte": [{"id": k, "text": v} for k, v in texte.items()]})
    try:
        with tempfile.TemporaryDirectory(dir=arbeitsordner, prefix=".presidio-") as home:
            proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
                [python(), "-I", str(RUNNER)],
                input=eingabe.encode(),
                env={"PATH": "/usr/bin:/bin", "HOME": home, "LANG": "C.UTF-8"},
                cwd=home,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
    except subprocess.TimeoutExpired:
        raise ToolError("presidio: Zeitlimit überschritten") from None
    if proc.returncode != 0:
        raise ToolError(f"presidio: Exit-Code {proc.returncode}")
    try:
        raw = json.loads(proc.stdout or b"{}")
    except ValueError:
        raise ToolError("presidio: Ausgabe nicht lesbar") from None
    ergebnisse = raw.get("ergebnisse") if isinstance(raw, dict) else None
    if not isinstance(ergebnisse, dict):
        raise ToolError("presidio: Ausgabe nicht lesbar")
    sauber: dict[str, dict[str, int]] = {}
    for key in texte:
        werte = ergebnisse.get(key, {})
        if not isinstance(werte, dict):
            raise ToolError("presidio: Ausgabe nicht lesbar")
        sauber[key] = {
            str(art)[:20]: n for art, n in werte.items() if isinstance(n, int) and n >= 0
        }
    return sauber
