"""Scoring: traffic lights, block list, grade and release level (Konzept §5).

This module is the only place where findings turn into a verdict. Implemented in S1-10;
until then every function raises NotImplementedError so nothing can silently return green.
"""

from collections.abc import Sequence
from enum import StrEnum

from luibui_scan.models import Finding, Pruefumfang, Schwere


class AmpelSicherheit(StrEnum):
    GRUEN = "gruen"
    GELB = "gelb"
    ROT = "rot"
    GESPERRT = "gesperrt"


class AmpelDsgvo(StrEnum):
    GRUEN = "gruen"
    GELB = "gelb"
    ROT = "rot"
    NICHT_BEWERTET = "nicht_bewertet"


class Freigabe(StrEnum):
    FREIGEGEBEN = "freigegeben"
    PRUEFUNG_NOETIG = "pruefung_noetig"
    BLOCKIERT = "blockiert"


ABZUG: dict[Schwere, int] = {Schwere.K: 40, Schwere.H: 15, Schwere.M: 5, Schwere.N: 1, Schwere.I: 0}
"""Grade deductions per finding (Konzept §5)."""


def is_blocklisted(finding: Finding) -> bool:
    """True if the finding is on the block list and locks the package."""
    raise NotImplementedError("S1-10")


def ampel_sicherheit(findings: Sequence[Finding], *, complete: bool) -> AmpelSicherheit:
    raise NotImplementedError("S1-10")


def ampel_dsgvo(
    findings: Sequence[Finding], *, pruefumfang: Pruefumfang, has_manifest: bool
) -> AmpelDsgvo:
    raise NotImplementedError("S1-10")


def ampel_gesamt(sicherheit: AmpelSicherheit, dsgvo: AmpelDsgvo) -> AmpelSicherheit:
    """The worse of both axes; 'nicht bewertet' follows the security axis."""
    raise NotImplementedError("S1-10")


def note(findings: Sequence[Finding]) -> int:
    """100 minus deductions, at least 0."""
    raise NotImplementedError("S1-10")


def freigabe(gesamt: AmpelSicherheit) -> Freigabe:
    raise NotImplementedError("S1-10")
