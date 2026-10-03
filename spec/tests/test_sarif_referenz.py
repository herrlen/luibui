"""SARIF from the engine equals the reference that apps/web/lib/sarif.test.ts also checks."""

import json
from pathlib import Path

from luibui_scan.sarif import bericht_als_sarif

HIER = Path(__file__).parent


def test_python_sarif_matches_the_reference() -> None:
    eingabe = json.loads((HIER / "sarif-eingabe.json").read_text(encoding="utf-8"))
    referenz = json.loads((HIER / "sarif-referenz.json").read_text(encoding="utf-8"))
    for fall in eingabe["faelle"]:
        erzeugt = bericht_als_sarif(fall["bericht"], fall["status"])
        assert erzeugt == referenz[fall["name"]], fall["name"]
