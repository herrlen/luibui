"""Sprint 1 DoD: `luibui scan corpus/benign/*` yields no K/H findings; manifests are valid."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from luibui_scan.models import ScanArt, Schwere
from luibui_scan.scan import Eingabe, scan_prepared
from luibui_scan.textrules import load_atr

REPO = Path(__file__).resolve().parents[3]
BENIGN = sorted(p for p in (REPO / "corpus" / "benign").iterdir() if p.is_dir())
SCHEMA = json.loads((REPO / "spec" / "luibui.schema.json").read_text("utf-8"))


def test_corpus_is_not_empty() -> None:
    assert len(BENIGN) >= 5


@pytest.mark.parametrize("package", BENIGN, ids=lambda p: p.name)
def test_benign_package_has_no_critical_or_high_findings(package: Path) -> None:
    result = scan_prepared(package, Eingabe.LOKAL, ScanArt.LOKAL)
    serious = [
        f"{f.schwere.value} {f.rule_id} {f.datei}"
        for f in result.pipeline.findings
        if f.schwere in (Schwere.K, Schwere.H)
    ]
    assert serious == []


@pytest.mark.parametrize(
    "manifest",
    sorted((REPO / "corpus" / "benign").glob("*/luibui.json")),
    ids=lambda p: p.parent.name,
)
def test_benign_manifests_are_valid(manifest: Path) -> None:
    errors = [
        e.message
        for e in Draft202012Validator(SCHEMA).iter_errors(json.loads(manifest.read_text()))
    ]
    assert errors == []


def test_benign_corpus_triggers_no_vendored_atr_rule() -> None:
    """Same calibration as scripts/vendor_atr.py: an ATR rule that fires here is not taken."""
    rules = load_atr(REPO / "rules" / "external" / "atr" / "rules")
    texts = [
        p
        for p in sorted((REPO / "corpus" / "benign").rglob("*"))
        if p.is_file() and p.suffix in {".md", ".txt", ".yaml", ".yml", ".json", ".toml"}
    ]
    hits = [
        f"{rule.id} {path.relative_to(REPO)}"
        for path in texts
        for rule in rules
        if rule.search(path.read_text("utf-8")) is not None
    ]
    assert hits == []
