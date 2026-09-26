"""Finding model and spec/finding.schema.json must describe the same thing."""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from luibui_scan.models import Finding, is_valid_rule_id

SPEC = Path(__file__).resolve().parents[3] / "spec"
SCHEMA = json.loads((SPEC / "finding.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)
VALID = sorted((SPEC / "examples").glob("finding-*.json"))
INVALID = sorted((SPEC / "examples" / "invalid").glob("finding-*.json"))


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_model_fields_match_schema_properties() -> None:
    assert set(Finding.model_fields) == set(SCHEMA["properties"])


def test_required_fields_match_schema() -> None:
    required = {name for name, f in Finding.model_fields.items() if f.is_required()}
    assert required == set(SCHEMA["required"])


@pytest.mark.parametrize("example", VALID, ids=lambda p: p.name)
def test_valid_examples_round_trip(example: Path) -> None:
    data = _load(example)
    finding = Finding.model_validate(data)
    out = finding.to_json_dict()
    assert VALIDATOR.is_valid(out)
    assert out == data


@pytest.mark.parametrize("example", INVALID, ids=lambda p: p.name)
def test_invalid_examples_are_rejected_by_model(example: Path) -> None:
    with pytest.raises(ValidationError):
        Finding.model_validate(_load(example))


def test_beleg_with_five_lines_is_allowed() -> None:
    data = _load(VALID[0]) | {"beleg": "1\n2\n3\n4\n5"}
    assert Finding.model_validate(data).beleg == "1\n2\n3\n4\n5"


@pytest.mark.parametrize(
    "rule_id",
    [
        "LB-B01-unicode-tags",
        "LB-A2-zip-slip",
        "ATR-2026-00258",
        "gitleaks:aws-key",
        "osv:GHSA-xxxx",
    ],
)
def test_rule_id_accepts_conventions(rule_id: str) -> None:
    assert is_valid_rule_id(rule_id)


@pytest.mark.parametrize("rule_id", ["", "LB-B01", "lb-b01-x", "unicode tags", "LB-Z01-x"])
def test_rule_id_rejects_others(rule_id: str) -> None:
    assert not is_valid_rule_id(rule_id)


def test_finding_is_immutable() -> None:
    finding = Finding.model_validate(_load(VALID[0]))
    with pytest.raises(ValidationError):
        finding.schwere = "N"  # type: ignore[misc, assignment]
