"""Sharing a report by link (S2-12).

The owner makes a link for a finished check; only the SHA-256 of its 256-bit token is stored in
``scans.share_token_hash``. A new link replaces the old one, and ending the share or deleting the
check ends it too. Anyone with the link sees the report, never account data: the link itself is
the permission, so the public route has no owner check.
"""

import re
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import select

from luibui_api.audit import audit
from luibui_api.auth import CurrentCaller, DbSession, get_owned
from luibui_api.errors import fehler
from luibui_api.models import Scan
from luibui_api.security import new_secret, sha256_hex

router = APIRouter(prefix="/api/v1", tags=["teilen"])

_TOKEN = re.compile(r"^[A-Za-z0-9_-]{20,100}$")


class Link(BaseModel):
    token: str
    """Shown once; luibui keeps only its hash."""


class Geteilt(BaseModel):
    bericht: dict[str, Any]
    geprueft_am: datetime | None


@router.post("/scans/{scan_id}/teilen", status_code=status.HTTP_201_CREATED)
def teilen(scan_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> Link:
    scan = get_owned(db, Scan, scan_id, caller)
    if scan.status != "fertig" or scan.report is None:
        raise fehler(
            status.HTTP_409_CONFLICT,
            "nicht_fertig",
            "Teilen geht erst, wenn die Prüfung fertig ist",
        )
    token = new_secret()
    scan.share_token_hash = sha256_hex(token)
    audit(db, caller.user.id, "bericht.geteilt", "scan", scan.id)
    db.commit()
    return Link(token=token)


@router.delete("/scans/{scan_id}/teilen", status_code=status.HTTP_204_NO_CONTENT)
def nicht_mehr_teilen(scan_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> None:
    scan = get_owned(db, Scan, scan_id, caller)
    scan.share_token_hash = None
    audit(db, caller.user.id, "bericht.teilen_beendet", "scan", scan.id)
    db.commit()


@router.get("/geteilt/{token}")
def geteilt(token: str, db: DbSession) -> Geteilt:
    nicht_da = fehler(status.HTTP_404_NOT_FOUND, "nicht_gefunden", "Dieser Link gilt nicht (mehr)")
    if not _TOKEN.fullmatch(token):
        raise nicht_da
    scan = db.scalar(select(Scan).where(Scan.share_token_hash == sha256_hex(token)))
    if scan is None or scan.owner_id is None or scan.report is None:
        raise nicht_da
    return Geteilt(bericht=scan.report, geprueft_am=scan.finished_at)
