"""S1-10: every report the engine builds validates against spec/report.schema.json."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from luibui_scan.analyzers import AnalyzerInfo, AnalyzerRegistry
from luibui_scan.context import ScanContext
from luibui_scan.models import Achse, Ebene, Finding, Nachweisgrad, ScanArt, Schwere
from luibui_scan.report import OHNE_GEWAEHR, build_report
from luibui_scan.scan import Eingabe, scan_prepared

SPEC = Path(__file__).resolve().parents[3] / "spec"


def _validator() -> Draft202012Validator:
    resources = []
    for name in ("finding.schema.json", "report.schema.json"):
        schema = json.loads((SPEC / name).read_text("utf-8"))
        resource = Resource.from_contents(schema)
        resources += [(schema["$id"], resource), (name, resource)]
    report = json.loads((SPEC / "report.schema.json").read_text("utf-8"))
    registry = Registry().with_resources(resources)
    return Draft202012Validator(report, registry=registry, format_checker=FormatChecker())


VALIDATOR = _validator()


def finding(
    schwere: Schwere, rule_id: str = "LB-B01-test", achse: Achse = Achse.SICHERHEIT
) -> Finding:
    return Finding(
        rule_id=rule_id,
        ebene=Ebene.B,
        schwere=schwere,
        achse=achse,
        titel="Test",
        erklaerung="Test",
        datei="SKILL.md",
        zeile=1,
        beleg="x",
        nachweisgrad=Nachweisgrad.STATISCH_ERKANNT,
        normbezug=(),
        fix="x",
        fix_prompt="",
    )


class Reports:
    def __init__(self, name: str, findings: list[Finding]) -> None:
        self.info = AnalyzerInfo(name=name, titel=name, ebenen=frozenset({Ebene.B}))
        self._findings = findings

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        return self._findings


class Crashes:
    info = AnalyzerInfo(name="kaputt", titel="Kaputt", ebenen=frozenset({Ebene.B}))

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        raise RuntimeError("boom")


def registry(*analyzers: object) -> AnalyzerRegistry:
    reg = AnalyzerRegistry()
    for a in analyzers:
        reg.add(a)  # type: ignore[arg-type]
    return reg


def report_for(
    tmp_path: Path, files: dict[str, str], eingabe: Eingabe, art: ScanArt, reg: AnalyzerRegistry
) -> dict[str, Any]:
    for rel, text in files.items():
        (tmp_path / rel).write_text(text)
    result = scan_prepared(tmp_path, eingabe, art, reg)
    report = build_report(
        result,
        name="paket",
        scan_id=uuid.UUID("0b6f3d2e-8c1a-4e57-9b0d-2f4a6c8e1b3d"),
        geprueft_am=datetime(2026, 9, 26, 18, 0, tzinfo=UTC),
    )
    VALIDATOR.validate(report)
    return report


def test_no_analyzers_is_yellow_with_note(tmp_path: Path) -> None:
    r = report_for(tmp_path, {"SKILL.md": "x"}, Eingabe.DATEI, ScanArt.LOKAL, registry())
    assert r["ampeln"] == {"sicherheit": "gelb", "dsgvo": "nicht_bewertet", "gesamt": "gelb"}
    assert r["freigabe"] == "pruefung_noetig"
    assert r["note"] == 100
    assert r["hinweise"][0] == "Einzeldatei-Prüfung"
    assert "keine Prüfung eingebaut" in r["hinweise"][1]
    assert r["geprueft_am"] == "2026-09-26T18:00:00Z"


def test_clean_package_is_green(tmp_path: Path) -> None:
    files = {"SKILL.md": "x", "luibui.json": "{}"}
    r = report_for(tmp_path, files, Eingabe.ZIP, ScanArt.INTENSIV, registry(Reports("a", [])))
    assert r["pruefumfang"] == "paket"
    assert r["ampeln"] == {"sicherheit": "gruen", "dsgvo": "gruen", "gesamt": "gruen"}
    assert r["freigabe"] == "freigegeben"
    assert r["hinweise"] == []


def test_failed_analyzer_blocks_green(tmp_path: Path) -> None:
    files = {"SKILL.md": "x", "luibui.json": "{}"}
    reg = registry(Reports("a", []), Crashes())
    r = report_for(tmp_path, files, Eingabe.ZIP, ScanArt.INTENSIV, reg)
    assert r["ampeln"]["gesamt"] == "gelb"
    assert {"pruefung": "Kaputt", "grund": "fehlgeschlagen"} in r["nicht_geprueft"]
    assert any("unvollständig" in h for h in r["hinweise"])


def test_findings_sorted_and_locked(tmp_path: Path) -> None:
    findings = [finding(Schwere.N), finding(Schwere.K, "gitleaks:aws-access-token")]
    reg = registry(Reports("a", findings))
    r = report_for(tmp_path, {"a.md": "x"}, Eingabe.AUSWAHL, ScanArt.INTENSIV, reg)
    assert [b["schwere"] for b in r["befunde"]] == ["K", "N"]
    assert r["befunde"][0]["analyzer"] == "a"
    assert r["ampeln"]["gesamt"] == "gesperrt"
    assert r["freigabe"] == "blockiert"
    assert r["note"] == 59


def test_quickscan_always_says_ohne_gewaehr(tmp_path: Path) -> None:
    reg = registry(Reports("a", []))
    r = report_for(tmp_path, {"a.md": "x"}, Eingabe.GIT, ScanArt.SCHNELL, reg)
    assert r["hinweise"][0] == OHNE_GEWAEHR


@pytest.mark.parametrize("schwere", list(Schwere))
def test_dsgvo_finding_in_package(tmp_path: Path, schwere: Schwere) -> None:
    files = {"a.md": "x", "luibui.json": "{}"}
    reg = registry(Reports("a", [finding(schwere, "LB-G1-test", Achse.DSGVO)]))
    report_for(tmp_path, files, Eingabe.ZIP, ScanArt.INTENSIV, reg)
