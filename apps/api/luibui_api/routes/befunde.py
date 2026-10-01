"""Finding status in the developer area and moderation of disputes (S3-7).

A status belongs to a finding of a project, keyed by its fingerprint, so it carries over to the
next check. ``behoben`` is only set by the worker, when a finding is gone from a new check of the
same scope. The status never changes lights or grade (Len, 2026-10-01): the report stays the
check's verdict; a false alarm leaves the report once the rule is adjusted.

Moderation is the one place where someone reads a finding of another account. Only users with
``is_admin``, only with a browser session, only disputed findings, and every opened dispute and
every decision lands in the audit log (metadata only). Everybody else gets 404.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from luibui_api.audit import audit
from luibui_api.auth import Caller, CurrentCaller, DbSession, get_caller, get_owned
from luibui_api.models import FindingStatus, Project, Scan

router = APIRouter(tags=["befunde"])

BEGRUENDUNG_MAX = 2000


def _text(value: str | None) -> str | None:
    return (value or "").strip() or None


class BefundStatus(BaseModel):
    """What the owner sees at a finding."""

    status: Literal["offen", "behoben", "akzeptiert", "bestritten"]
    begruendung: str | None
    geaendert_am: datetime
    moderation: Literal["bestritten", "fehlalarm"] | None
    moderation_notiz: str | None
    moderiert_am: datetime | None


def befund_status_of(f: FindingStatus) -> BefundStatus:
    return BefundStatus(
        status=f.status,
        begruendung=f.begruendung,
        geaendert_am=f.updated_at,
        moderation=f.moderation,
        moderation_notiz=f.moderation_notiz,
        moderiert_am=f.moderiert_at,
    )


def status_for_scan(db: Session, scan: Scan) -> dict[str, BefundStatus] | None:
    """The status of every finding of a project check that has one; ``None`` outside projects."""
    if scan.project_id is None:
        return None
    fps = {
        f.get("fingerprint")
        for f in (scan.report or {}).get("befunde") or []
        if isinstance(f, dict) and isinstance(f.get("fingerprint"), str)
    }
    if not fps:
        return {}
    rows = db.scalars(
        select(FindingStatus).where(
            FindingStatus.project_id == scan.project_id, FindingStatus.fingerprint.in_(fps)
        )
    )
    return {r.fingerprint: befund_status_of(r) for r in rows}


class StatusSetzen(BaseModel):
    fingerprint: str = Field(min_length=1, max_length=64)
    status: Literal["offen", "akzeptiert", "bestritten"]
    begruendung: str | None = Field(default=None, max_length=BEGRUENDUNG_MAX)

    _strip = field_validator("begruendung")(_text)

    @model_validator(mode="after")
    def _begruendung_noetig(self) -> "StatusSetzen":
        if self.status != "offen" and not self.begruendung:
            raise ValueError("Bitte eine Begründung angeben")
        return self


def _befund(report: dict[str, Any] | None, fingerprint: str) -> dict[str, Any] | None:
    for f in (report or {}).get("befunde") or []:
        if isinstance(f, dict) and f.get("fingerprint") == fingerprint:
            return f
    return None


def _owned_scan(scan_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> Scan:
    """As a dependency, so a foreign scan answers 404 before the body is even looked at."""
    return get_owned(db, Scan, scan_id, caller)


@router.post("/api/v1/scans/{scan_id}/befund-status")
def status_setzen(
    scan: Annotated[Scan, Depends(_owned_scan)],
    body: StatusSetzen,
    caller: CurrentCaller,
    db: DbSession,
) -> BefundStatus:
    """Accept a finding (with a reason), dispute it as a false alarm, or open it again."""
    if scan.project_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "code": "kein_projekt",
                "text": "Einen Status gibt es nur für Prüfungen in Projekten.",
            },
        )
    if _befund(scan.report, body.fingerprint) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    row = db.scalar(
        select(FindingStatus).where(
            FindingStatus.project_id == scan.project_id,
            FindingStatus.fingerprint == body.fingerprint,
        )
    )
    if row is not None and row.status == "behoben":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "code": "schon_behoben",
                "text": "Dieser Befund ist in einer neueren Prüfung nicht mehr enthalten.",
            },
        )
    if row is None:
        row = FindingStatus(
            owner_id=caller.user.id, project_id=scan.project_id, fingerprint=body.fingerprint
        )
        db.add(row)
    row.status = body.status
    row.begruendung = body.begruendung if body.status != "offen" else None
    row.updated_by = caller.user.id
    row.updated_at = datetime.now(UTC)
    row.moderation = row.moderation_notiz = row.moderiert_von = row.moderiert_at = None
    db.flush()
    audit(db, caller.user.id, "befund.status", "scan", scan.id, status=body.status)
    db.commit()
    db.refresh(row)
    return befund_status_of(row)


# --- Moderation ------------------------------------------------------------------------------


def get_moderator(caller: Annotated[Caller, Depends(get_caller)]) -> Caller:
    """Admins with a browser session; for everybody else the moderation does not exist."""
    if caller.via != "session" or not caller.user.is_admin:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    return caller


Moderator = Annotated[Caller, Depends(get_moderator)]


class Einspruch(BaseModel):
    id: uuid.UUID
    projekt: str
    rule_id: str
    schwere: str | None
    titel: str
    datei: str | None
    zeile: int | None
    begruendung: str | None
    eingereicht_am: datetime
    moderation: Literal["bestritten", "fehlalarm"] | None
    moderation_notiz: str | None
    moderiert_am: datetime | None


class EinspruchDetail(Einspruch):
    erklaerung: str | None
    beleg: str | None
    """At most five lines, secrets masked by the engine; the UI renders it as plain text."""


def _letzter_befund(db: Session, f: FindingStatus) -> dict[str, Any]:
    """The finding as the newest finished check of the project shows it."""
    reports: list[dict[str, Any] | None] = list(
        db.scalars(
            select(Scan.report)
            .where(Scan.project_id == f.project_id, Scan.status == "fertig")
            .order_by(Scan.created_at.desc())
            .limit(20)
        )
    )
    for report in reports:
        befund = _befund(report, f.fingerprint)
        if befund is not None:
            return befund
    return {}


def _str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _einspruch(db: Session, f: FindingStatus) -> tuple[Einspruch, dict[str, Any]]:
    b = _letzter_befund(db, f)
    projekt = db.get(Project, f.project_id)
    e = Einspruch(
        id=f.id,
        projekt=projekt.name if projekt else "",
        rule_id=_str(b.get("rule_id")) or "",
        schwere=_str(b.get("schwere")),
        titel=_str(b.get("titel")) or "Befund nicht mehr im Bericht",
        datei=_str(b.get("datei")),
        zeile=b.get("zeile") if isinstance(b.get("zeile"), int) else None,
        begruendung=f.begruendung,
        eingereicht_am=f.updated_at,
        moderation=f.moderation,
        moderation_notiz=f.moderation_notiz,
        moderiert_am=f.moderiert_at,
    )
    return e, b


def _bestritten(db: Session, einspruch_id: uuid.UUID) -> FindingStatus:
    f = db.get(FindingStatus, einspruch_id)
    if f is None or f.status != "bestritten":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    return f


@router.get("/api/v1/moderation/einsprueche")
def einsprueche(caller: Moderator, db: DbSession, entschieden: bool = False) -> list[Einspruch]:
    """Disputed findings, oldest first; ``entschieden`` lists the decided ones, newest first.
    Without evidence: that is only in the detail, which is logged."""
    query = select(FindingStatus).where(FindingStatus.status == "bestritten")
    if entschieden:
        query = query.where(FindingStatus.moderation.is_not(None)).order_by(
            FindingStatus.moderiert_at.desc()
        )
    else:
        query = query.where(FindingStatus.moderation.is_(None)).order_by(FindingStatus.updated_at)
    return [_einspruch(db, f)[0] for f in db.scalars(query.limit(200))]


@router.get("/api/v1/moderation/einsprueche/{einspruch_id}")
def einspruch(einspruch_id: uuid.UUID, caller: Moderator, db: DbSession) -> EinspruchDetail:
    f = _bestritten(db, einspruch_id)
    e, b = _einspruch(db, f)
    audit(db, caller.user.id, "moderation.angesehen", "finding_status", f.id, owner=str(f.owner_id))
    db.commit()
    return EinspruchDetail(
        **e.model_dump(), erklaerung=_str(b.get("erklaerung")), beleg=_str(b.get("beleg"))
    )


class Entscheidung(BaseModel):
    ergebnis: Literal["bestritten", "fehlalarm"]
    notiz: str | None = Field(default=None, max_length=BEGRUENDUNG_MAX)

    _strip = field_validator("notiz")(_text)


@router.post("/api/v1/moderation/einsprueche/{einspruch_id}/entscheidung")
def entscheiden(
    einspruch_id: uuid.UUID, body: Entscheidung, caller: Moderator, db: DbSession
) -> Einspruch:
    """``bestritten``: the finding stays, marked "disputed by the author". ``fehlalarm``: false
    alarm, the rule gets adjusted; the next check of the project then marks it fixed."""
    f = _bestritten(db, einspruch_id)
    # Core update: the ORM's onupdate would move updated_at, which is when the dispute came in.
    db.execute(
        update(FindingStatus)
        .where(FindingStatus.id == f.id)
        .values(
            moderation=body.ergebnis,
            moderation_notiz=body.notiz,
            moderiert_von=caller.user.id,
            moderiert_at=datetime.now(UTC),
            updated_at=FindingStatus.updated_at,
        )
    )
    audit(
        db,
        caller.user.id,
        "moderation.entschieden",
        "finding_status",
        f.id,
        owner=str(f.owner_id),
        ergebnis=body.ergebnis,
    )
    db.commit()
    db.refresh(f)
    return _einspruch(db, f)[0]
