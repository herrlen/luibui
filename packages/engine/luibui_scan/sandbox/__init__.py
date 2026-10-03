"""Dynamic check in the sandbox (Sprint 6, ADR-001), the parts that run in the worker.

The sandbox server runs the package (nsjail, no network, decoys) and returns a protocol; here the
decoys are made (``koeder``), the protocol is checked (``protokoll``) and turned into findings
F01–F05 with Nachweisgrad ``in_sandbox_beobachtet`` (``befunde``). Nothing here executes package
code (CLAUDE.md rule 1); the sandbox server never decides a light.
"""
