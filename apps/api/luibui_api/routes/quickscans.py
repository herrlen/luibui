"""Quick scan without an account: a public Git URL or one file up to 2 MB, nothing stored,
report for 7 days, "ohne Gewähr" (Konzept §2, threat model T20). The random scan ID is the only
key to the report."""

import uuid
from datetime import UTC, datetime
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from luibui_api.auth import AnnahmeOffen, DbSession
from luibui_api.models import Job, Scan
from luibui_api.ratelimit import RateLimiter
from luibui_api.routes.scans import ScanStatus, scan_status_of
from luibui_api.settings import get_settings
from luibui_api.uploads import Upload, create_scan
from luibui_scan.intake.safe_git import canonical_url
from luibui_scan.models import ScanArt
from luibui_scan.scan import Eingabe

router = APIRouter(prefix="/api/v1/quickscans", tags=["quickscans"])


@lru_cache
def quickscan_limiter() -> RateLimiter:
    return RateLimiter(get_settings().quickscans_per_ip_and_day, 86400)


class SchnellscanNeu(BaseModel):
    git_url: str = Field(max_length=500)


def _unprocessable(grund: str, text: str) -> HTTPException:
    return HTTPException(
        status.HTTP_422_UNPROCESSABLE_CONTENT, {"code": grund, "text": text, "pfad": None}
    )


MAX_DATEI = 2 * 1024 * 1024
"""A quick scan takes one file up to 2 MB (Sprintplanung S2-13); the intensive scan takes more."""
_ARCHIVE = (".zip", ".tar", ".tgz", ".tar.gz")


def _zulassen(request: Request, db: DbSession) -> None:
    """Same limits for Git and file: 3 per IP and day, a cap on waiting quick scans."""
    client = request.client.host if request.client else "unbekannt"
    limiter = quickscan_limiter()
    if limiter.blocked(f"ip:{client}"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            {
                "code": "zu_viele_schnellscans",
                "text": "Höchstens 3 Schnellscans pro Tag. Mit einem Konto geht mehr.",
            },
        )
    waiting = db.scalar(
        select(func.count())
        .select_from(Job)
        .join(Scan, Job.scan_id == Scan.id)
        .where(Job.status.in_(("queued", "running")), Scan.scan_art == "schnell")
    )
    if int(waiting or 0) >= get_settings().quickscan_queue_max:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            {"code": "warteschlange_voll", "text": "Gerade sind zu viele Schnellscans in Arbeit."},
        )
    limiter.hit(f"ip:{client}")


def _zu_gross() -> HTTPException:
    return HTTPException(
        status.HTTP_413_CONTENT_TOO_LARGE,
        {"code": "zu_gross", "text": "Der Schnellscan nimmt eine Datei bis 2 MB.", "pfad": None},
    )


_ABLESEN = 16 * 1024 * 1024
"""Up to this size an oversized body is read and thrown away before the 413: the web proxy of
Next.js is still sending, and an early answer breaks its pipe and turns into a 500."""


async def _verwerfen(request: Request) -> None:
    gelesen = 0
    async for teil in request.stream():
        gelesen += len(teil)
        if gelesen > _ABLESEN:
            break


async def _datei_upload(request: Request) -> tuple[Upload, str, list[UploadFile]]:
    laenge = request.headers.get("content-length")
    if laenge is not None and laenge.isdigit() and int(laenge) > MAX_DATEI + 64 * 1024:
        if int(laenge) <= _ABLESEN:
            await _verwerfen(request)
        raise _zu_gross()
    form = await request.form(max_files=1, max_fields=5)
    datei = form.get("datei")
    if not isinstance(datei, UploadFile) or not datei.filename:
        await form.close()
        raise _unprocessable("datei_fehlt", "Bitte eine Datei auswählen.")
    if datei.size is not None and datei.size > MAX_DATEI:
        await form.close()
        raise _zu_gross()
    name = datei.filename.rsplit("/", 1)[-1][:200]
    art = Eingabe.ZIP if name.lower().endswith(_ARCHIVE) else Eingabe.DATEI
    return Upload(art=art, files=[(name, datei.file)]), name, [datei]


@router.post("", status_code=status.HTTP_202_ACCEPTED, dependencies=[AnnahmeOffen])
async def starten(request: Request, db: DbSession) -> ScanStatus:
    """A public Git URL as JSON (``{"git_url": …}``) or one file up to 2 MB as form field
    ``datei``; an archive is unpacked like a package."""
    offen: list[UploadFile] = []
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        upload, name, offen = await _datei_upload(request)
    else:
        try:
            body = SchnellscanNeu.model_validate(await request.json())
            url = canonical_url(body.git_url)
        except (ValueError, ValidationError) as exc:
            raise _unprocessable("ungueltige_url", str(exc)[:300]) from None
        upload = Upload(art=Eingabe.GIT, git_url=url)
        name = url.removeprefix("https://").removesuffix(".git")
    try:
        _zulassen(request, db)
        scan = await run_in_threadpool(
            lambda: create_scan(db, upload, project=None, scan_art=ScanArt.SCHNELL, name=name)
        )
    finally:
        for datei in offen:
            await datei.close()
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
