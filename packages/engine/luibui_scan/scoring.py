"""Scoring: traffic lights, block list, grade and release level (Konzept §5).

This module is the only place where findings turn into a verdict. An incomplete scan (an analyzer
failed, or none ran at all) never gets green on either axis.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from luibui_scan.models import Achse, Finding, Pruefumfang, Schwere


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

SPERRLISTE_KATALOG: frozenset[str] = frozenset(
    {
        "A02", "A08",
        "B01", "B07", "B08", "B09", "B10", "B11", "B12", "B13", "B16", "B20",
        "C03", "C04", "C05", "C07", "C08", "C09", "C10",
        "E01", "E02",
        "F02", "F04", "F05",
    }
)  # fmt: skip
"""Prüfkatalog IDs whose critical findings lock the package (docs/luibui_Pruefkatalog.md §10).

Own rules are matched by the catalog ID inside ``LB-<ID>-<name>``, so every rule of a listed check
counts. B18 (LLM) is deliberately absent: a language model alone never locks a package.
"""

SPERRLISTE_EXTERN: tuple[str, ...] = (
    "gitleaks:",  # echte Secrets (B20)
    "osv:MAL-",  # bekannte Schadpakete (D01, OSV malicious-packages database)
)
"""Rule-ID prefixes of external tools whose critical findings lock the package."""

_RANK_SICHERHEIT = list(AmpelSicherheit)
_RANK_DSGVO = [AmpelDsgvo.GRUEN, AmpelDsgvo.GELB, AmpelDsgvo.ROT]


def _catalog_id(rule_id: str) -> str | None:
    if not rule_id.startswith("LB-"):
        return None
    return rule_id.split("-", 2)[1]


def is_blocklisted(finding: Finding) -> bool:
    """True if the finding is critical and on the block list, which locks the package."""
    if finding.schwere is not Schwere.K:
        return False
    if _catalog_id(finding.rule_id) in SPERRLISTE_KATALOG:
        return True
    return finding.rule_id.startswith(SPERRLISTE_EXTERN)


def _worst(findings: Sequence[Finding], achse: Achse) -> Schwere | None:
    order = [Schwere.K, Schwere.H, Schwere.M, Schwere.N, Schwere.I]
    present = {f.schwere for f in findings if f.achse is achse}
    return next((s for s in order if s in present), None)


def ampel_sicherheit(findings: Sequence[Finding], *, complete: bool) -> AmpelSicherheit:
    """Green: at most N/I. Yellow: an M. Red: an H or a K off the block list. Locked: listed K."""
    if any(f.achse is Achse.SICHERHEIT and is_blocklisted(f) for f in findings):
        return AmpelSicherheit.GESPERRT
    worst = _worst(findings, Achse.SICHERHEIT)
    if worst in (Schwere.K, Schwere.H):
        return AmpelSicherheit.ROT
    if worst is Schwere.M or not complete:
        return AmpelSicherheit.GELB
    return AmpelSicherheit.GRUEN


def ampel_dsgvo(
    findings: Sequence[Finding], *, pruefumfang: Pruefumfang, has_manifest: bool, complete: bool
) -> AmpelDsgvo:
    """Only a package with manifest is rated. Otherwise only findings (third-country endpoints)
    can turn the axis yellow or red; without them it stays 'nicht bewertet'."""
    if pruefumfang is Pruefumfang.PAKET and not has_manifest:
        raise ValueError("Ein Paket hat immer ein Manifest")
    worst = _worst(findings, Achse.DSGVO)
    if worst in (Schwere.K, Schwere.H):
        return AmpelDsgvo.ROT
    if worst is Schwere.M:
        return AmpelDsgvo.GELB
    if pruefumfang is not Pruefumfang.PAKET:
        return AmpelDsgvo.NICHT_BEWERTET
    return AmpelDsgvo.GRUEN if complete else AmpelDsgvo.GELB


def ampel_gesamt(sicherheit: AmpelSicherheit, dsgvo: AmpelDsgvo) -> AmpelSicherheit:
    """The worse of both axes; 'nicht bewertet' follows the security axis."""
    if dsgvo is AmpelDsgvo.NICHT_BEWERTET:
        return sicherheit
    as_security = AmpelSicherheit(dsgvo.value)
    return max(sicherheit, as_security, key=_RANK_SICHERHEIT.index)


def note(findings: Sequence[Finding]) -> int:
    """100 minus deductions, at least 0."""
    return max(0, 100 - sum(ABZUG[f.schwere] for f in findings))


def freigabe(gesamt: AmpelSicherheit) -> Freigabe:
    if gesamt is AmpelSicherheit.GRUEN:
        return Freigabe.FREIGEGEBEN
    if gesamt is AmpelSicherheit.GESPERRT:
        return Freigabe.BLOCKIERT
    return Freigabe.PRUEFUNG_NOETIG


@dataclass(frozen=True, slots=True)
class Bewertung:
    sicherheit: AmpelSicherheit
    dsgvo: AmpelDsgvo
    gesamt: AmpelSicherheit
    note: int
    freigabe: Freigabe
    vollstaendig: bool


def bewerte(
    findings: Sequence[Finding], *, pruefumfang: Pruefumfang, has_manifest: bool, complete: bool
) -> Bewertung:
    """All of the above in one step. ``complete`` is False if any analyzer failed or none ran."""
    sicherheit = ampel_sicherheit(findings, complete=complete)
    dsgvo = ampel_dsgvo(
        findings, pruefumfang=pruefumfang, has_manifest=has_manifest, complete=complete
    )
    gesamt = ampel_gesamt(sicherheit, dsgvo)
    return Bewertung(sicherheit, dsgvo, gesamt, note(findings), freigabe(gesamt), complete)
