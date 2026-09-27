# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
"""Harmless target for pickle fixtures. The tests mark this module as dangerous, so the fixtures
never need to name os, subprocess or any other real module (CLAUDE.md rule 8)."""


def harmlos() -> str:
    return "echo harmlos"
