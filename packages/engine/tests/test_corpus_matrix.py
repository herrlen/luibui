"""Scanner-Matrix: one defused malicious fixture and one benign counterpart per row
(corpus/generate.py). Scanned with the full pipeline like ``luibui scan``."""

import importlib.util
import shutil
from pathlib import Path
from types import ModuleType

import pytest

from luibui_scan.analyzers import _a_modelle
from luibui_scan.models import ScanArt, Schwere
from luibui_scan.scan import Eingabe, scan_prepared

REPO = Path(__file__).resolve().parents[3]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "corpus_generate", REPO / "corpus" / "generate.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GEN = _load()
MALICIOUS, BENIGN = GEN.fixtures()


@pytest.fixture(autouse=True)
def dummy_is_dangerous(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _a_modelle, "_DANGEROUS_MODULES", _a_modelle._DANGEROUS_MODULES | {"_dummy"}
    )


def _scan(tmp_path: Path, files: dict[str, bytes]) -> list[tuple[str, Schwere]]:
    root = tmp_path / "paket"
    for rel, data in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    result = scan_prepared(root, Eingabe.ZIP, ScanArt.INTENSIV)
    shutil.rmtree(root)
    return [(f.rule_id, f.schwere) for f in result.pipeline.findings]


@pytest.mark.parametrize("matrix_id", sorted(MALICIOUS))
def test_malicious_fixture_is_found(tmp_path: Path, matrix_id: str) -> None:
    files, expected = MALICIOUS[matrix_id]
    found = _scan(tmp_path, files)
    assert any(rule.startswith(expected) for rule, _ in found), found


@pytest.mark.parametrize("matrix_id", sorted(BENIGN))
def test_benign_counterpart_has_no_finding_from_that_row(tmp_path: Path, matrix_id: str) -> None:
    found = _scan(tmp_path, BENIGN[matrix_id])
    expected = MALICIOUS[matrix_id][1] if matrix_id in MALICIOUS else None
    serious = [(r, s) for r, s in found if s in (Schwere.K, Schwere.H)]
    assert serious == []
    if expected is not None:
        assert not [r for r, s in found if r.startswith(expected) and s is not Schwere.I]


def test_every_text_fixture_carries_the_marker() -> None:
    for files, _ in MALICIOUS.values():
        for rel, data in files.items():
            if data[:1] in (b"#", b"<", b"{") or rel.endswith((".md", ".sh", ".py", ".yml")):
                assert GEN.MARK.encode() in data or b"LUIBUI-TESTFIXTURE" in data, rel
