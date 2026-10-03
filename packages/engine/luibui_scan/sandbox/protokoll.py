"""Checking the protocol from the sandbox server before anything reads it (ADR-001, SB5)."""

import json
from functools import lru_cache
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator

MAX_BYTES = 5 * 1024 * 1024


class ProtokollError(Exception):
    """The protocol is missing, too large or does not match the schema."""


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    """A copy of spec/sandbox-protokoll.schema.json ships with the package; a test keeps both
    equal."""
    text = resources.files("luibui_scan").joinpath("data/sandbox-protokoll.schema.json")
    return Draft202012Validator(json.loads(text.read_text("utf-8")))


def laden(roh: bytes) -> dict[str, Any]:
    if len(roh) > MAX_BYTES:
        raise ProtokollError("Protokoll zu groß")
    try:
        daten = json.loads(roh)
    except (ValueError, RecursionError):
        raise ProtokollError("Protokoll nicht lesbar") from None
    fehler = next(iter(_validator().iter_errors(daten)), None)
    if fehler is not None:
        raise ProtokollError(f"Protokoll entspricht nicht dem Schema: {fehler.message[:200]}")
    if not isinstance(daten, dict):
        raise ProtokollError("Protokoll nicht lesbar")
    return daten
