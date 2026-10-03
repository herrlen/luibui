"""S4-1: name rules and look-alikes (H04), without a database."""

import pytest

from luibui_api.register import name_fehler, skelett, verwechslung, zu_nah


@pytest.mark.parametrize("name", ["len", "acme-tools", "a1", "x" * 39, "mcp-wetter"])
def test_valid_names(name: str) -> None:
    assert name_fehler(name) is None


@pytest.mark.parametrize(
    "name", ["a", "x" * 40, "-acme", "acme-", "ac--me", "Acme", "ac_me", "ac me", "äcme", "ac.me"]
)
def test_invalid_names(name: str) -> None:
    assert name_fehler(name) is not None


@pytest.mark.parametrize(
    "name",
    ["anthropic", "anthrop1c", "anthr0pic", "anthropics", "antrhopic", "open-ai", "0penai",
     "claude", "c1aude", "modelcontextprotocoll", "luibui", "lu1bui", "api", "ap1", "rnistral"],
)  # fmt: skip
def test_reserved_names_and_their_look_alikes_are_refused(name: str) -> None:
    assert verwechslung(name, []) is not None


@pytest.mark.parametrize("name", ["len", "acme", "wetter-tools", "metal", "pythonic-x", "lex"])
def test_ordinary_names_pass(name: str) -> None:
    assert verwechslung(name, []) is None


def test_existing_names_are_compared_like_reserved_ones() -> None:
    bestehend = ["acme-tools", "len"]
    assert verwechslung("acmetools", bestehend) == "acme-tools"
    assert verwechslung("acme-to0ls", bestehend) == "acme-tools"
    assert verwechslung("acme-tool", bestehend) == "acme-tools"
    assert verwechslung("1en", bestehend) == "len"
    assert verwechslung("lex", bestehend) is None  # short names: only identical skeletons
    assert verwechslung("acme-tools-pro", bestehend) is None


def test_skeleton_and_distance() -> None:
    assert skelett("rn-0-1") == "mol"
    assert zu_nah("abcdef", "abdcef")  # swapped neighbours
    assert not zu_nah("abcdef", "abcxyz")
