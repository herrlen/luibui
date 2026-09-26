from pathlib import Path

import pytest

from luibui_scan.context import ScanContext
from luibui_scan.models import Pruefumfang, ScanArt

REPO = Path(__file__).resolve().parents[3]
SPEC = REPO / "spec"


@pytest.fixture
def ctx(tmp_path: Path) -> ScanContext:
    return ScanContext(root=tmp_path, scan_art=ScanArt.INTENSIV, pruefumfang=Pruefumfang.PAKET)
