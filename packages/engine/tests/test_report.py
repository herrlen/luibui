"""S1-10: every report the engine builds validates against spec/report.schema.json."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from luibui_scan.abdeckung import dateiart
from luibui_scan.analyzers import AnalyzerInfo, AnalyzerRegistry
from luibui_scan.context import InventoryEntry, ScanContext
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
    result = scan_prepared(tmp_path, eingabe, art, reg, erwartet={})
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


def test_missing_expected_analyzers_block_green(tmp_path: Path) -> None:
    """A clean package is not green while planned checks are not built yet."""
    (tmp_path / "SKILL.md").write_text("x")
    (tmp_path / "luibui.json").write_text("{}")
    result = scan_prepared(
        tmp_path,
        Eingabe.ZIP,
        ScanArt.INTENSIV,
        registry(Reports("a", [])),
        erwartet={"a": "A", "c_code": "C – Code"},
    )
    report = build_report(result, name="p")
    VALIDATOR.validate(report)
    assert report["ampeln"]["gesamt"] == "gelb"
    assert {"pruefung": "C – Code", "grund": "noch nicht eingebaut"} in report["nicht_geprueft"]
    assert any("noch nicht eingebaut" in h for h in report["hinweise"])


# --- abdeckung: what ran for which kind of file (S2-1) ------------------------------------------


def _abdeckung(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {a["dateiart"]: a for a in report["abdeckung"]}


def test_coverage_lists_what_ran_per_kind_of_file(tmp_path: Path) -> None:
    reg = registry(*(Reports(n, []) for n in ("a_dateien", "b_inhalte", "b_muster", "c_code")))
    files = {"SKILL.md": "# Skill\n", "tool.py": "x = 1\n", "main.go": "package main\n"}
    a = _abdeckung(report_for(tmp_path, files, Eingabe.LOKAL, ScanArt.LOKAL, reg))
    assert a["Python"]["dateien"] == 1
    assert "Was der Code tut" in a["Python"]["geprueft"]
    assert "Anweisungen an die KI (Prompt-Injection)" in a["Anweisungen und Doku"]["geprueft"]
    assert "Was der Code tut: für diese Programmiersprache noch nicht" in a["Anderer Code"]["offen"]
    # Not registered here, so never claimed as checked:
    assert "Zugangsdaten im Klartext" not in a["Python"]["geprueft"]


def test_coverage_never_claims_a_failed_check(tmp_path: Path) -> None:
    class CodeCrashes(Crashes):
        info = AnalyzerInfo(name="c_code", titel="C – Code", ebenen=frozenset({Ebene.C}))

    reg = registry(Reports("a_dateien", []), CodeCrashes())
    a = _abdeckung(report_for(tmp_path, {"t.py": "x = 1\n"}, Eingabe.LOKAL, ScanArt.LOKAL, reg))
    assert "Was der Code tut: fehlgeschlagen" in a["Python"]["offen"]
    assert "Was der Code tut" not in a["Python"]["geprueft"]


def test_coverage_in_quick_scan_names_the_missing_code_check(tmp_path: Path) -> None:
    code = AnalyzerInfo(
        name="c_code",
        titel="C – Code",
        ebenen=frozenset({Ebene.C}),
        scan_arts=frozenset({ScanArt.INTENSIV, ScanArt.LOKAL}),
    )
    only_deep = Reports("c_code", [])
    only_deep.info = code
    reg = registry(Reports("a_dateien", []), only_deep)
    a = _abdeckung(report_for(tmp_path, {"t.js": "x()\n"}, Eingabe.ZIP, ScanArt.SCHNELL, reg))
    assert "Was der Code tut: nur im Intensivscan" in a["JavaScript und TypeScript"]["offen"]


@pytest.mark.parametrize(
    ("path", "kind", "sprache", "art"),
    [
        ("a/b.py", "text", "python", "Python"),
        ("x.tsx", "text", "typescript", "JavaScript und TypeScript"),
        ("run.sh", "script", "shell", "Shell-Skripte"),
        ("run", "script", "shell", "Anderer Code"),
        ("x.ps1", "text", "powershell", "Anderer Code"),
        ("SKILL.md", "text", "markdown", "Anweisungen und Doku"),
        ("mcp.json", "text", "json", "Konfiguration und Daten"),
        ("logo.png", "png", None, "Binärdateien, Bilder und Archive"),
        ("__MACOSX/._a.md", "appledouble", None, "macOS-Begleitdateien"),
    ],
)
def test_kind_of_file_goes_by_extension(
    path: str, kind: str, sprache: str | None, art: str
) -> None:
    entry = InventoryEntry(path, 10, "0" * 64, kind, sprache)
    assert dateiart(entry) == art


def test_coverage_names_mcp_checks_for_mcp_servers(tmp_path: Path) -> None:
    reg = registry(Reports("a_dateien", []), Reports("e_mcp", []))
    files = {
        "server.py": "from mcp.server.fastmcp import FastMCP\n",
        "index.ts": 'import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";\n',
    }
    a = _abdeckung(report_for(tmp_path, files, Eingabe.LOKAL, ScanArt.LOKAL, reg))
    mcp = "MCP-Tools: versteckte Anweisungen, Shadowing, Anmeldung, Token"
    assert mcp in a["Python"]["geprueft"] and mcp in a["JavaScript und TypeScript"]["geprueft"]
    assert "MCP-Tools: Beschreibung passt zum Code" in a["Python"]["geprueft"]
    assert (
        "MCP-Tools: Beschreibung passt zum Code: bisher nur für Python"
        in a["JavaScript und TypeScript"]["offen"]
    )
