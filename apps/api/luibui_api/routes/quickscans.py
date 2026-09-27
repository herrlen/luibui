"""Quick scan without an account: a public Git URL, nothing stored, report for 7 days, "ohne
Gewähr" (Konzept §2, threat model T20). The random scan ID is the only key to the report."""

import uuid
from datetime import UTC, datetime
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool

from luibui_api.auth import AnnahmeOffen, DbSession
from luibui_api.models import Job, Scan
from luibui_api.ratelimit import RateLimiter
from luibui_api.routes.scans import ScanStatus, scan_status_of
from luibui_api.settings import get_settings
from luibui_api.uploads import Upload, create_scan
from luibui_scan.intake.safe_git import canonical_url
from luibui_scan.models import ScanArt
from luibui_scan.scan import Eingabe

router = APIRouter(prefix="/api/quickscans", tags=["quickscans"])


@lru_cache
def quickscan_limiter() -> RateLimiter:
    return RateLimiter(get_settings().quickscans_per_ip_and_day, 86400)


class SchnellscanNeu(BaseModel):
    git_url: str = Field(max_length=500)


def _unprocessable(grund: str, text: str) -> HTTPException:
    return HTTPException(
        status.HTTP_422_UNPROCESSABLE_CONTENT, {"grund": grund, "text": text, "pfad": None}
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED, dependencies=[AnnahmeOffen])
async def starten(body: SchnellscanNeu, request: Request, db: DbSession) -> ScanStatus:
    try:
        url = canonical_url(body.git_url)
    except ValueError as exc:
        raise _unprocessable("ungueltige_url", str(exc)) from None
    client = request.client.host if request.client else "unbekannt"
    limiter = quickscan_limiter()
    if limiter.blocked(f"ip:{client}"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Höchstens 3 Schnellscans pro Tag. Mit einem Konto geht mehr.",
        )
    waiting = db.scalar(
        select(func.count())
        .select_from(Job)
        .join(Scan, Job.scan_id == Scan.id)
        .where(Job.status.in_(("queued", "running")), Scan.scan_art == "schnell")
    )
    if int(waiting or 0) >= get_settings().quickscan_queue_max:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Gerade sind zu viele Schnellscans in Arbeit."
        )
    limiter.hit(f"ip:{client}")
    name = url.removeprefix("https://").removesuffix(".git")
    upload = Upload(art=Eingabe.GIT, git_url=url)
    scan = await run_in_threadpool(
        lambda: create_scan(db, upload, project=None, scan_art=ScanArt.SCHNELL, name=name)
    )
    return scan_status_of(scan)


@router.get("/{scan_id}")
def status_(scan_id: uuid.UUID, db: DbSession) -> ScanStatus:
    scan = db.get(Scan, scan_id)
    now = datetime.now(UTC)
    if (
        scan is None
        or scan.scan_art != "schnell"
        or scan.owner_id is not None
        or scan.expires_at is None
        or scan.expires_at <= now
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    return scan_status_of(scan)
