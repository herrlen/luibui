"""S1-10: traffic lights, block list, grade and release level (Konzept §5)."""

import pytest

from luibui_scan import scoring
from luibui_scan.models import Achse, Ebene, Finding, Nachweisgrad, Pruefumfang, Schwere
from luibui_scan.scoring import AmpelDsgvo, AmpelSicherheit, Freigabe, bewerte


def f(schwere: str, achse: Achse = Achse.SICHERHEIT, rule_id: str = "LB-A5-test") -> Finding:
    return Finding(
        rule_id=rule_id,
        ebene=Ebene.A,
        schwere=Schwere(schwere),
        achse=achse,
        titel="t",
        erklaerung="e",
        datei=None,
        zeile=None,
        beleg=None,
        nachweisgrad=Nachweisgrad.STATISCH_ERKANNT,
        normbezug=(),
        fix="x",
        fix_prompt="",
    )


def test_deductions_follow_concept() -> None:
    assert scoring.ABZUG == {Schwere.K: 40, Schwere.H: 15, Schwere.M: 5, Schwere.N: 1, Schwere.I: 0}


@pytest.mark.parametrize(
    ("severities", "expected"),
    [
        ([], AmpelSicherheit.GRUEN),
        (["I", "N", "N"], AmpelSicherheit.GRUEN),
        (["N", "M"], AmpelSicherheit.GELB),
        (["M", "H"], AmpelSicherheit.ROT),
        (["K"], AmpelSicherheit.ROT),  # critical, but not on the block list
    ],
)
def test_ampel_sicherheit(severities: list[str], expected: AmpelSicherheit) -> None:
    assert scoring.ampel_sicherheit([f(s) for s in severities], complete=True) is expected


def test_dsgvo_findings_do_not_move_the_security_axis() -> None:
    assert scoring.ampel_sicherheit([f("H", Achse.DSGVO)], complete=True) is AmpelSicherheit.GRUEN


def test_incomplete_scan_is_never_green() -> None:
    assert scoring.ampel_sicherheit([], complete=False) is AmpelSicherheit.GELB
    assert scoring.ampel_sicherheit([f("H")], complete=False) is AmpelSicherheit.ROT
    dsgvo = scoring.ampel_dsgvo(
        [], pruefumfang=Pruefumfang.PAKET, has_manifest=True, complete=False
    )
    assert dsgvo is AmpelDsgvo.GELB


@pytest.mark.parametrize(
    ("rule_id", "schwere", "locked"),
    [
        ("gitleaks:aws-access-token", "K", True),
        ("osv:MAL-2026-1234", "K", True),
        ("osv:GHSA-xxxx-yyyy-zzzz", "K", False),
        ("gitleaks:aws-access-token", "H", False),
        ("LB-B01-unicode-tags", "K", False),  # catalog IDs follow with luibui_Pruefkatalog.md
    ],
)
def test_block_list(rule_id: str, schwere: str, locked: bool) -> None:
    assert scoring.is_blocklisted(f(schwere, rule_id=rule_id)) is locked


def test_block_list_by_catalog_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scoring, "SPERRLISTE_KATALOG", frozenset({"B01"}))
    assert scoring.is_blocklisted(f("K", rule_id="LB-B01-unicode-tags"))
    assert scoring.is_blocklisted(f("K", rule_id="LB-B01-anything-else"))
    assert not scoring.is_blocklisted(f("K", rule_id="LB-B10-other"))
    assert not scoring.is_blocklisted(f("M", rule_id="LB-B01-unicode-tags"))


def test_locked_beats_everything() -> None:
    findings = [f("K", rule_id="gitleaks:generic-api-key"), f("H")]
    assert scoring.ampel_sicherheit(findings, complete=False) is AmpelSicherheit.GESPERRT


@pytest.mark.parametrize(
    ("umfang", "severities", "expected"),
    [
        (Pruefumfang.PAKET, [], AmpelDsgvo.GRUEN),
        (Pruefumfang.PAKET, ["N"], AmpelDsgvo.GRUEN),
        (Pruefumfang.PAKET, ["M"], AmpelDsgvo.GELB),
        (Pruefumfang.PAKET, ["H"], AmpelDsgvo.ROT),
        (Pruefumfang.AUSWAHL, [], AmpelDsgvo.NICHT_BEWERTET),
        (Pruefumfang.EINZELDATEI, ["N"], AmpelDsgvo.NICHT_BEWERTET),
        (Pruefumfang.EINZELDATEI, ["M"], AmpelDsgvo.GELB),
        (Pruefumfang.AUSWAHL, ["K"], AmpelDsgvo.ROT),
    ],
)
def test_ampel_dsgvo(umfang: Pruefumfang, severities: list[str], expected: AmpelDsgvo) -> None:
    findings = [f(s, Achse.DSGVO) for s in severities] + [f("H")]  # security finding ignored
    has_manifest = umfang is Pruefumfang.PAKET
    got = scoring.ampel_dsgvo(
        findings, pruefumfang=umfang, has_manifest=has_manifest, complete=True
    )
    assert got is expected


def test_package_without_manifest_is_a_programming_error() -> None:
    with pytest.raises(ValueError, match="Manifest"):
        scoring.ampel_dsgvo([], pruefumfang=Pruefumfang.PAKET, has_manifest=False, complete=True)


@pytest.mark.parametrize(
    ("sicherheit", "dsgvo", "gesamt"),
    [
        (AmpelSicherheit.GRUEN, AmpelDsgvo.GRUEN, AmpelSicherheit.GRUEN),
        (AmpelSicherheit.GRUEN, AmpelDsgvo.ROT, AmpelSicherheit.ROT),
        (AmpelSicherheit.GELB, AmpelDsgvo.GRUEN, AmpelSicherheit.GELB),
        (AmpelSicherheit.GESPERRT, AmpelDsgvo.ROT, AmpelSicherheit.GESPERRT),
        (AmpelSicherheit.ROT, AmpelDsgvo.GELB, AmpelSicherheit.ROT),
        (AmpelSicherheit.GRUEN, AmpelDsgvo.NICHT_BEWERTET, AmpelSicherheit.GRUEN),
        (AmpelSicherheit.GESPERRT, AmpelDsgvo.NICHT_BEWERTET, AmpelSicherheit.GESPERRT),
    ],
)
def test_ampel_gesamt(
    sicherheit: AmpelSicherheit, dsgvo: AmpelDsgvo, gesamt: AmpelSicherheit
) -> None:
    assert scoring.ampel_gesamt(sicherheit, dsgvo) is gesamt


@pytest.mark.parametrize(
    ("severities", "expected"),
    [([], 100), (["I"] * 5, 100), (["N", "M"], 94), (["H", "H"], 70), (["K", "K", "K"], 0)],
)
def test_note(severities: list[str], expected: int) -> None:
    assert scoring.note([f(s) for s in severities]) == expected


def test_note_counts_both_axes() -> None:
    assert scoring.note([f("M"), f("M", Achse.DSGVO)]) == 90


@pytest.mark.parametrize(
    ("gesamt", "expected"),
    [
        (AmpelSicherheit.GRUEN, Freigabe.FREIGEGEBEN),
        (AmpelSicherheit.GELB, Freigabe.PRUEFUNG_NOETIG),
        (AmpelSicherheit.ROT, Freigabe.PRUEFUNG_NOETIG),
        (AmpelSicherheit.GESPERRT, Freigabe.BLOCKIERT),
    ],
)
def test_freigabe(gesamt: AmpelSicherheit, expected: Freigabe) -> None:
    assert scoring.freigabe(gesamt) is expected


def test_bewerte_single_file_with_locked_finding() -> None:
    """Mirrors spec/examples/report-einzeldatei-lokal.json."""
    b = bewerte(
        [f("K", rule_id="gitleaks:aws-access-token")],
        pruefumfang=Pruefumfang.EINZELDATEI,
        has_manifest=False,
        complete=True,
    )
    assert (b.sicherheit, b.dsgvo, b.gesamt) == (
        AmpelSicherheit.GESPERRT,
        AmpelDsgvo.NICHT_BEWERTET,
        AmpelSicherheit.GESPERRT,
    )
    assert (b.note, b.freigabe, b.vollstaendig) == (60, Freigabe.BLOCKIERT, True)
