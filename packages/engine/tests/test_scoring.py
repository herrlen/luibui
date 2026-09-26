"""Scoring is implemented in S1-10. Until then it must fail loudly instead of returning green."""

import pytest

from luibui_scan import scoring
from luibui_scan.models import Pruefumfang, Schwere


def test_deductions_follow_concept() -> None:
    assert scoring.ABZUG == {Schwere.K: 40, Schwere.H: 15, Schwere.M: 5, Schwere.N: 1, Schwere.I: 0}


def test_unimplemented_scoring_never_returns_a_verdict() -> None:
    with pytest.raises(NotImplementedError):
        scoring.ampel_sicherheit([], complete=True)
    with pytest.raises(NotImplementedError):
        scoring.ampel_dsgvo([], pruefumfang=Pruefumfang.PAKET, has_manifest=True)
    with pytest.raises(NotImplementedError):
        scoring.note([])
