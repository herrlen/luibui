"""S3-2: benchmark counting rules and the reference list (the full run is scripts/benchmark.sh)."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from luibui_scan import benchmark
from luibui_scan.analyzers._common import finding
from luibui_scan.intake.safe_git import ALLOWED_HOSTS, canonical_url
from luibui_scan.models import Ebene, Finding, Schwere
from luibui_scan.scan import ScanResult
from luibui_scan.scoring import AmpelSicherheit

REPO = Path(__file__).resolve().parents[3]


def _f(rule_id: str, schwere: Schwere) -> Finding:
    return finding(
        rule_id=rule_id,
        ebene=Ebene.C,
        schwere=schwere,
        titel="t",
        erklaerung="e",
        datei="x.py",
        zeile=1,
        beleg=None,
        fix="f",
        fix_prompt="",
        normbezug=(),
    )


def _result(findings: list[Finding], ampel: AmpelSicherheit) -> ScanResult:
    return cast(
        ScanResult,
        SimpleNamespace(
            pipeline=SimpleNamespace(findings=findings), bewertung=SimpleNamespace(gesamt=ampel)
        ),
    )


def test_benign_counts_k_and_h_but_not_known_vulnerabilities() -> None:
    result = _result(
        [
            _f("LB-C01-shell", Schwere.H),
            _f("osv:GHSA-xxxx", Schwere.H),
            _f("LB-C11-tls", Schwere.M),
        ],
        AmpelSicherheit.ROT,
    )
    t = benchmark.bewerte_gutartig("p", "g", result)
    assert t.fehlalarm
    assert t.ernst == ["H LB-C01-shell x.py"]
    assert t.luecken == ["H osv:GHSA-xxxx x.py"]


def test_benign_accepted_rule_leaves_the_count_but_stays_listed() -> None:
    result = _result([_f("LB-C01-shell", Schwere.K)], AmpelSicherheit.GESPERRT)
    t = benchmark.bewerte_gutartig("p", "g", result, ["LB-C01"])
    assert not t.fehlalarm
    assert t.berechtigt == ["K LB-C01-shell x.py"]


def test_benign_with_only_medium_findings_is_no_false_alarm() -> None:
    t = benchmark.bewerte_gutartig(
        "p", "g", _result([_f("LB-D04-lockfile", Schwere.M)], AmpelSicherheit.GELB)
    )
    assert not t.fehlalarm


def test_malicious_needs_expected_rule_and_a_light_that_is_not_green() -> None:
    hit = _result([_f("LB-C04-zugangsdaten-lesen", Schwere.K)], AmpelSicherheit.GESPERRT)
    assert benchmark.bewerte_boesartig("COD-01", "LB-C04", hit).erkannt
    other_rule = _result([_f("LB-C05-abfluss", Schwere.K)], AmpelSicherheit.GESPERRT)
    assert not benchmark.bewerte_boesartig("COD-01", "LB-C04", other_rule).erkannt
    green = _result([_f("LB-C04-zugangsdaten-lesen", Schwere.I)], AmpelSicherheit.GRUEN)
    assert not benchmark.bewerte_boesartig("COD-01", "LB-C04", green).erkannt


def test_ebene_and_group_come_from_rule_and_matrix_id() -> None:
    assert benchmark.ebene_von("LB-C04-zugangsdaten-lesen") == "C"
    assert benchmark.ebene_von("LB-B08") == "B"
    t = benchmark.bewerte_boesartig("COD-01", "LB-C04", _result([], AmpelSicherheit.GRUEN))
    assert t.gruppe == "Code"


def test_render_reports_targets_and_missed_fixtures() -> None:
    lauf = benchmark.Lauf(
        boesartig=[
            benchmark.Treffer("COD-01", "Code", "rot", erkannt=True, erwartet="LB-C04"),
            benchmark.Treffer("AGT-01", "Agenten", "gruen", erkannt=False, erwartet="LB-B08"),
        ],
        uebersprungen={"A08 – Bekannte Schadsoftware": "keine Datenbank"},
    )
    text = benchmark.render(lauf, stand="abc", datum="2026-09-30")
    assert "| Erkennung, Nachbildungen | 1/2 (50 %) | ≥ 90 % | **nicht erreicht** |" in text
    assert "| AGT-01 | Agenten | `LB-B08` | gruen | **nein** |" in text
    assert "nicht gemessen (ohne `--vergleich`)" in text
    assert "A08 – Bekannte Schadsoftware: übersprungen, keine Datenbank" in text


def test_reference_list_has_60_unique_packages_on_allowed_hosts() -> None:
    data = json.loads((REPO / "corpus" / "vergleich.json").read_text("utf-8"))
    pakete = data["pakete"]
    assert len(pakete) == 60
    assert len({(p["repo"], p["pfad"]) for p in pakete}) == 60
    for p in pakete:
        assert canonical_url(p["repo"]).split("/")[2] in ALLOWED_HOSTS
        assert ".." not in p["pfad"].split("/")
        assert p["lizenz"]
        for b in p.get("berechtigt", []):
            assert b["regel"] and b["grund"]
