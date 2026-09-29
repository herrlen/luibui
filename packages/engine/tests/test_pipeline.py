from pathlib import Path

import pytest

from luibui_scan.analyzers import AnalyzerInfo, AnalyzerRegistry
from luibui_scan.context import ScanContext
from luibui_scan.models import (
    Achse,
    Ebene,
    Finding,
    Nachweisgrad,
    Pruefumfang,
    ScanArt,
    Schwere,
)
from luibui_scan.pipeline import run_pipeline


def make_finding(**overrides: object) -> Finding:
    data: dict[str, object] = {
        "rule_id": "LB-A2-test",
        "ebene": Ebene.A,
        "schwere": Schwere.N,
        "achse": Achse.SICHERHEIT,
        "titel": "Test",
        "erklaerung": "Test",
        "datei": "a.txt",
        "zeile": 1,
        "beleg": "x",
        "nachweisgrad": Nachweisgrad.STATISCH_ERKANNT,
        "normbezug": (),
        "fix": "nichts",
        "fix_prompt": "",
    }
    return Finding.model_validate(data | overrides)


class Fixed:
    def __init__(self, name: str, findings: list[Finding], **info: object) -> None:
        self.info = AnalyzerInfo(name=name, titel=name, ebenen=frozenset({Ebene.A}), **info)  # type: ignore[arg-type]
        self._findings = findings
        self.calls = 0

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        self.calls += 1
        return self._findings


class Boom:
    info = AnalyzerInfo(name="boom", titel="Boom", ebenen=frozenset({Ebene.B}))

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        raise RuntimeError("secret package content must not leak")


def test_runs_analyzers_in_order_and_tags_findings(ctx: ScanContext) -> None:
    reg = AnalyzerRegistry()
    reg.add(Fixed("one", [make_finding()]))
    reg.add(Fixed("two", [make_finding(rule_id="LB-A3-x", analyzer="explicit")]))
    result = run_pipeline(ctx, reg)
    assert result.ran == ["one", "two"]
    assert [f.analyzer for f in result.findings] == ["one", "explicit"]
    assert result.complete


def test_failing_analyzer_is_reported_not_swallowed(ctx: ScanContext) -> None:
    reg = AnalyzerRegistry()
    reg.add(Boom())
    after = reg.add(Fixed("after", [make_finding()]))
    result = run_pipeline(ctx, reg)
    assert not result.complete
    assert [(f.analyzer, f.fehler) for f in result.failed] == [("boom", "RuntimeError")]
    assert "secret" not in repr(result.failed)
    assert after.calls == 1  # type: ignore[attr-defined]


def test_scope_and_scan_art_filters(tmp_path: Path) -> None:
    reg = AnalyzerRegistry()
    reg.add(Fixed("paket_only", [], scopes=frozenset({Pruefumfang.PAKET})))
    reg.add(Fixed("intensiv_only", [], scan_arts=frozenset({ScanArt.INTENSIV})))
    reg.add(Fixed("manifest", [], needs_manifest=True))
    reg.add(Fixed("always", []))
    ctx = ScanContext(root=tmp_path, scan_art=ScanArt.SCHNELL, pruefumfang=Pruefumfang.EINZELDATEI)
    result = run_pipeline(ctx, reg)
    assert result.ran == ["always"]
    assert {(s.analyzer, s.grund) for s in result.skipped} == {
        ("paket_only", "Einzeldatei-Prüfung"),
        ("intensiv_only", "nur im Intensivscan"),
        ("manifest", "kein luibui.json"),
    }


def test_analyzer_returning_wrong_type_is_a_programming_error(ctx: ScanContext) -> None:
    reg = AnalyzerRegistry()
    reg.add(Fixed("bad", ["not a finding"]))  # type: ignore[list-item]
    with pytest.raises(TypeError):
        run_pipeline(ctx, reg)


def test_registry_rejects_duplicates_and_non_analyzers() -> None:
    reg = AnalyzerRegistry()
    reg.add(Fixed("x", []))
    with pytest.raises(ValueError, match="bereits"):
        reg.add(Fixed("x", []))
    with pytest.raises(TypeError):
        reg.add(object())  # type: ignore[arg-type]


def test_context_resolve_refuses_escape(ctx: ScanContext) -> None:
    (ctx.root / "ok.txt").write_text("x")
    assert ctx.resolve("ok.txt") == (ctx.root / "ok.txt").resolve()
    with pytest.raises(ValueError):
        ctx.resolve("../outside.txt")
    (ctx.root / "link").symlink_to("/etc")
    with pytest.raises(ValueError):
        ctx.resolve("link/passwd")


def test_evidence_of_every_analyzer_is_masked(ctx: ScanContext) -> None:
    token = "sk-" + "A1b2C3d4" * 4
    reg = AnalyzerRegistry()
    reg.add(Fixed("b_x", [make_finding(beleg=f"Nutze den Schlüssel {token} hier.")]))
    (f,) = run_pipeline(ctx, reg).findings
    assert f.beleg is not None and token not in f.beleg and "sk-A…" in f.beleg
