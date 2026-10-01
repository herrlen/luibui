"""Finding status (S3-7): open, fixed, accepted, disputed, and the moderation of disputes.

A status belongs to a finding's fingerprint within one project, so it carries over to the next
check of that project. "Behoben" is never set by hand: a finding of the previous check that is
gone in this one counts as fixed. The report itself never changes; the status is an overlay.
"""

import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from luibui_api.audit import audit
from luibui_api.auth import CurrentCaller, DbSession, get_owned
from luibui_api.errors import fehler
from luibui_api.models import FindingStatus, Project, Scan

router = APIRouter(prefix="/api/v1", tags=["befunde"])

_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


class BefundStatusOut(BaseModel):
    fingerprint: str
    status: str
    begruendung: str | None
    moderation: str | None
    updated_at: datetime


class StatusNeu(BaseModel):
    status: Literal["offen", "akzeptiert", "bestritten"]
    begruendung: str | None = Field(default=None, max_length=2000)


class BehobenerBefund(BaseModel):
    """A finding of the previous check of this project that is gone now."""

    fingerprint: str
    rule_id: str
    schwere: str
    titel: str
    datei: str | None
    zeile: int | None


def _ohne_angaben() -> HTTPException:
    return fehler(status.HTTP_422_UNPROCESSABLE_CONTENT, "angaben_fehlen", "Angaben fehlen")


def _out(f: FindingStatus) -> BefundStatusOut:
    return BefundStatusOut(
        fingerprint=f.fingerprint,
        status=f.status,
        begruendung=f.begruendung,
        moderation=f.moderation,
        updated_at=f.updated_at,
    )


def _befunde(scan: Scan | None) -> list[dict[str, Any]]:
    befunde = ((scan.report or {}) if scan else {}).get("befunde") or []
    return [b for b in befunde if isinstance(b, dict) and b.get("fingerprint")]


def _letzter(db: DbSession, project_id: uuid.UUID, vor: datetime | None = None) -> Scan | None:
    q = select(Scan).where(
        Scan.project_id == project_id, Scan.status == "fertig", Scan.report.is_not(None)
    )
    if vor is not None:
        q = q.where(Scan.created_at < vor)
    return db.scalars(q.order_by(Scan.created_at.desc()).limit(1)).first()


def status_je_befund(db: DbSession, project_id: uuid.UUID) -> dict[str, BefundStatusOut]:
    rows = db.scalars(select(FindingStatus).where(FindingStatus.project_id == project_id))
    return {f.fingerprint: _out(f) for f in rows}


def behoben(db: DbSession, scan: Scan) -> list[BehobenerBefund]:
    """Findings of the previous finished check of the same project that this check no longer has."""
    if scan.project_id is None or scan.report is None:
        return []
    vorher = _letzter(db, scan.project_id, vor=scan.created_at)
    jetzt = {b["fingerprint"] for b in _befunde(scan)}
    weg = [b for b in _befunde(vorher) if b["fingerprint"] not in jetzt]
    return [
        BehobenerBefund(
            fingerprint=str(b["fingerprint"]),
            rule_id=str(b.get("rule_id") or ""),
            schwere=str(b.get("schwere") or ""),
            titel=str(b.get("titel") or ""),
            datei=b.get("datei") if isinstance(b.get("datei"), str) else None,
            zeile=b.get("zeile") if isinstance(b.get("zeile"), int) else None,
        )
        for b in weg
    ]


@router.post("/projects/{project_id}/befunde/{fingerprint}/status")
def status_setzen(
    project_id: uuid.UUID,
    fingerprint: str,
    caller: CurrentCaller,
    db: DbSession,
    body: StatusNeu | None = None,
) -> BefundStatusOut:
    """Accept a finding (with a reason), dispute it (with a reason, goes to moderation) or set it
    back to open. Only findings of the project's latest finished check can be changed."""
    project = get_owned(db, Project, project_id, caller)  # before the body: foreign is 404
    if body is None:
        raise _ohne_angaben()
    nicht_da = fehler(status.HTTP_404_NOT_FOUND, "nicht_gefunden", "Befund nicht gefunden")
    if not _FINGERPRINT.fullmatch(fingerprint):
        raise nicht_da
    befund = next(
        (b for b in _befunde(_letzter(db, project.id)) if b["fingerprint"] == fingerprint), None
    )
    if befund is None:
        raise nicht_da
    begruendung = (body.begruendung or "").strip() or None
    if body.status != "offen" and (begruendung is None or len(begruendung) < 5):
        raise fehler(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "begruendung_fehlt",
            "Bitte kurz begründen (mindestens 5 Zeichen).",
        )
    row = db.scalars(
        select(FindingStatus).where(
            FindingStatus.project_id == project.id, FindingStatus.fingerprint == fingerprint
        )
    ).first()
    if row is None:
        row = FindingStatus(owner_id=caller.user.id, project_id=project.id, fingerprint=fingerprint)
        db.add(row)
    row.status = body.status
    row.begruendung = begruendung if body.status != "offen" else None
    row.updated_by = caller.user.id
    row.rule_id = str(befund.get("rule_id") or "")[:200]
    row.titel = str(befund.get("titel") or "")
    row.datei = befund.get("datei") if isinstance(befund.get("datei"), str) else None
    row.zeile = befund.get("zeile") if isinstance(befund.get("zeile"), int) else None
    # A new dispute, an acceptance or reopening starts without a moderation outcome.
    row.moderation = None
    row.moderiert_am = None
    row.moderiert_von = None
    audit(db, caller.user.id, "befund.status", "project", project.id, status=body.status)
    db.commit()
    db.refresh(row)
    return _out(row)


# --- Moderation of disputes (admins only; everybody else gets the same 404) --------------------


class Einspruch(BaseModel):
    id: uuid.UUID
    rule_id: str | None
    titel: str | None
    datei: str | None
    zeile: int | None
    begruendung: str | None
    updated_at: datetime
    moderation: str | None
    moderiert_am: datetime | None


class Entscheidung(BaseModel):
    entscheidung: Literal["fehlalarm", "bestritten"]
    """fehlalarm: the rule was wrong and gets adjusted; bestritten: stays disputed by the author."""


def _nur_admin(caller: CurrentCaller) -> None:
    if not caller.user.is_admin:
        raise fehler(status.HTTP_404_NOT_FOUND, "nicht_gefunden", "Nicht gefunden")


def _einspruch(f: FindingStatus) -> Einspruch:
    return Einspruch(
        id=f.id,
        rule_id=f.rule_id,
        titel=f.titel,
        datei=f.datei,
        zeile=f.zeile,
        begruendung=f.begruendung,
        updated_at=f.updated_at,
        moderation=f.moderation,
        moderiert_am=f.moderiert_am,
    )


@router.get("/admin/einsprueche")
def einsprueche(caller: CurrentCaller, db: DbSession) -> list[Einspruch]:
    """Disputed findings, waiting ones first. Shows the rule, title, place and the author's
    reason, never the report or the files; every view is logged."""
    _nur_admin(caller)
    rows = db.scalars(
        select(FindingStatus)
        .where(FindingStatus.status == "bestritten")
        .order_by(FindingStatus.moderation.is_not(None), FindingStatus.updated_at)
        .limit(200)
    ).all()
    audit(db, caller.user.id, "admin.einsprueche_gelesen", anzahl=len(rows))
    db.commit()
    return [_einspruch(f) for f in rows]


@router.post("/admin/einsprueche/{einspruch_id}/entscheidung")
def entscheiden(
    einspruch_id: uuid.UUID, caller: CurrentCaller, db: DbSession, body: Entscheidung | None = None
) -> Einspruch:
    _nur_admin(caller)
    if body is None:
        raise _ohne_angaben()
    row = db.get(FindingStatus, einspruch_id)
    if row is None or row.status != "bestritten":
        raise fehler(status.HTTP_404_NOT_FOUND, "nicht_gefunden", "Nicht gefunden")
    row.moderation = body.entscheidung
    row.moderiert_am = datetime.now(UTC)
    row.moderiert_von = caller.user.id
    audit(
        db,
        caller.user.id,
        "admin.einspruch_entschieden",
        "finding_status",
        row.id,
        entscheidung=body.entscheidung,
    )
    db.commit()
    db.refresh(row)
    return _einspruch(row)
