"""Validate the example files in spec/examples against the schemas.

Every file in spec/examples/ must be valid, every file in spec/examples/invalid/ must be rejected.
The file name prefix (finding-, report-, luibui-) selects the schema.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SPEC = Path(__file__).resolve().parent.parent
EXAMPLES = SPEC / "examples"
SCHEMAS = {
    "finding": "finding.schema.json",
    "report": "report.schema.json",
    "luibui": "luibui.schema.json",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry() -> Registry:
    resources = []
    for filename in SCHEMAS.values():
        schema = _load(SPEC / filename)
        resource = Resource.from_contents(schema)
        resources.append((schema["$id"], resource))
        resources.append((filename, resource))
    return Registry().with_resources(resources)


REGISTRY = _registry()


def validator_for(example: Path) -> Draft202012Validator:
    kind = example.name.split("-", 1)[0]
    schema = _load(SPEC / SCHEMAS[kind])
    return Draft202012Validator(schema, registry=REGISTRY, format_checker=FormatChecker())


VALID = sorted(EXAMPLES.glob("*.json"))
INVALID = sorted((EXAMPLES / "invalid").glob("*.json"))


@pytest.mark.parametrize("schema_file", SCHEMAS.values())
def test_schema_is_valid_draft_2020_12(schema_file: str) -> None:
    Draft202012Validator.check_schema(_load(SPEC / schema_file))


def test_there_are_examples_for_every_schema() -> None:
    for kind in SCHEMAS:
        assert any(p.name.startswith(f"{kind}-") for p in VALID), kind
        assert any(p.name.startswith(f"{kind}-") for p in INVALID), kind


@pytest.mark.parametrize("example", VALID, ids=lambda p: p.name)
def test_valid_example_is_accepted(example: Path) -> None:
    errors = [e.message for e in validator_for(example).iter_errors(_load(example))]
    assert errors == []


@pytest.mark.parametrize("example", INVALID, ids=lambda p: p.name)
def test_invalid_example_is_rejected(example: Path) -> None:
    assert not validator_for(example).is_valid(_load(example))
