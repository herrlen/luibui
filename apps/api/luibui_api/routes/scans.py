"""Start a scan for a project and read its status and report (S1-1)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import FormData, UploadFile

from luibui_api import guthaben
from luibui_api.audit import audit
from luibui_api.auth import AnnahmeOffen, CurrentCaller, DbSession, get_owned
from luibui_api.models import CreditEntry, Project, Scan
from luibui_api.pdf import bericht_als_pdf, dateiname
from luibui_api.routes.befunde import BefundStatus, status_for_scan
from luibui_api.settings import get_settings
from luibui_api.uploads import Upload, ablesen, create_scan
from luibui_scan.intake import DEFAULT_LIMITS
from luibui_scan.scan import Eingabe

router = APIRouter(tags=["scans"])

_ARTEN = {
    e.value: e for e in (Eingabe.DATEI, Eingabe.AUSWAHL, Eingabe.TEXT, Eingabe.ZIP, Eingabe.GIT)
}


class ScanStatus(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID | None
    status: str
    scan_art: str
    pruefumfang: str
    ampeln: dict[str, str] | None
    note: int | None
    freigabe: str | None
    fehler: str | None
    created_at: datetime
    finished_at: datetime | None
    bericht: dict[str, Any] | None
    """The full report (spec/report.schema.json) once the scan is finished."""
    geteilt: bool = False
    """Whether a share link is active (S2-12)."""
    befund_status: dict[str, BefundStatus] | None = None
    """Status per finding fingerprint, only for the owner's checks in a project (S3-7)."""


def scan_status_of(scan: Scan) -> ScanStatus:
    ampeln = None
    if scan.ampel_gesamt is not None:
        ampeln = {
            "sicherheit": scan.ampel_sicherheit or "",
            "dsgvo": scan.ampel_dsgvo or "",
            "gesamt": scan.ampel_gesamt,
        }
    return ScanStatus(
        id=scan.id,
        project_id=scan.project_id,
        status=scan.status,
        scan_art=scan.scan_art,
        pruefumfang=scan.pruefumfang,
        ampeln=ampeln,
        note=scan.note,
        freigabe=scan.freigabe,
        fehler=scan.error,
        created_at=scan.created_at,
        finished_at=scan.finished_at,
        bericht=scan.report,
        geteilt=scan.share_token_hash is not None,
    )


async def _check_size(request: Request) -> None:
    length = request.headers.get("content-length")
    if length is None or not length.isdigit():
        raise HTTPException(status.HTTP_411_LENGTH_REQUIRED, "Content-Length fehlt")
    if int(length) > get_settings().upload_max_bytes:
        await ablesen(request)
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Upload zu groß")


def _verknuepfen(db: DbSession, buchung: CreditEntry | None, scan: Scan) -> None:
    """The debit was committed together with the scan; link it so a failure can refund it."""
    if buchung is not None:
        buchung.scan_id = scan.id
        db.commit()


def _upload_from(
    form: FormData, arten: dict[str, Eingabe], git_default: str | None
) -> tuple[Upload, str]:
    """The upload described by a multipart form, and a display name for it."""
    art = arten.get(str(form.get("art")))
    if art is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unbekannte Art")
    uploads = [f for f in form.getlist("dateien") if isinstance(f, UploadFile)]
    pfade = [p for p in form.getlist("pfade") if isinstance(p, str)]
    if art is Eingabe.AUSWAHL and len(pfade) != len(uploads):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Zu jeder Datei gehört ein Pfad")
    names = pfade if art is Eingabe.AUSWAHL else [u.filename or "" for u in uploads]
    text = form.get("text")
    git_url = form.get("git_url")
    upload = Upload(
        art=art,
        files=[(n, u.file) for n, u in zip(names, uploads, strict=True)],
        text=text if isinstance(text, str) else None,
        git_url=git_url if isinstance(git_url, str) and git_url else git_default,
    )
    if art is Eingabe.TEXT:
        name = "Eingefügter Text"
    elif art is Eingabe.AUSWAHL and names:
        name = names[0].split("/")[0] if "/" in names[0] else f"{len(names)} Dateien"
    else:
        name = names[0] if names else "Einzelprüfung"
    return upload, name[:200]


@router.post(
    "/api/v1/projects/{project_id}/scans",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[AnnahmeOffen],
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["art"],
                        "properties": {
                            "art": {"type": "string", "enum": list(_ARTEN)},
                            "dateien": {
                                "type": "array",
                                "items": {"type": "string", "format": "binary"},
                            },
                            "pfade": {"type": "array", "items": {"type": "string"}},
                            "text": {"type": "string"},
                            "git_url": {"type": "string"},
                        },
                    }
                }
            }
        }
    },
)
async def scan_starten(
    project_id: uuid.UUID, request: Request, caller: CurrentCaller, db: DbSession
) -> ScanStatus:
    """``art``: datei, auswahl, zip, text or git. For ``auswahl`` the relative path of each file
    comes in ``pfade`` (same order as ``dateien``), because browsers drop folders from file names.
    For ``git`` the URL comes in ``git_url`` or from the project."""
    project = get_owned(db, Project, project_id, caller)
    await _check_size(request)
    guthaben.email_pruefen(caller.user)
    limit = DEFAULT_LIMITS.auswahl_dateien
    form = await request.form(max_files=limit + 1, max_fields=limit + 10)
    try:
        upload, _ = _upload_from(form, _ARTEN, project.git_url)
        buchung = guthaben.pruefung_abbuchen(db, caller.user)
        scan = await run_in_threadpool(
            lambda: create_scan(db, upload, project=project, name=project.name)
        )
        _verknuepfen(db, buchung, scan)
    finally:
        await form.close()
    art = upload.art
    audit(db, caller.user.id, "scan.gestartet", "scan", scan.id, art=art.value)
    db.commit()
    return scan_status_of(scan)


@router.get("/api/v1/scans/{scan_id}")
def scan_status(scan_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> ScanStatus:
    scan = get_owned(db, Scan, scan_id, caller)
    out = scan_status_of(scan)
    out.befund_status = status_for_scan(db, scan)
    return out


@router.get(
    "/api/v1/scans/{scan_id}/bericht.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def bericht_pdf(
    scan_id: uuid.UUID,
    caller: CurrentCaller,
    db: DbSession,
    umfang: Literal["standard", "detail"] = "standard",
) -> Response:
    """The finished report as PDF (S3-11). ``detail`` opens every finding up: explanation,
    evidence, fix and fix prompt. Built in a worker thread: a few hundred findings take seconds."""
    scan = get_owned(db, Scan, scan_id, caller)
    if scan.report is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"code": "nicht_fertig", "text": "Die Prüfung ist noch nicht fertig."},
        )
    status_ = {fp: st.model_dump() for fp, st in (status_for_scan(db, scan) or {}).items()}
    return await pdf_antwort(scan.report, umfang, status_)


async def pdf_antwort(
    report: dict[str, Any],
    umfang: Literal["standard", "detail"],
    status_: dict[str, dict[str, Any]] | None = None,
) -> Response:
    """The PDF download of a finished report, shared with the public quick scan route (which
    never passes a status)."""
    pdf = await run_in_threadpool(lambda: bericht_als_pdf(report, umfang, status=status_))
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{dateiname(report, umfang)}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


# --- Single checks from the overview (no project, nothing stored) -----------------------------

_EINZEL_ARTEN = {e.value: e for e in (Eingabe.DATEI, Eingabe.AUSWAHL, Eingabe.TEXT, Eingabe.ZIP)}


class Einzelpruefung(BaseModel):
    """A single check in the overview list."""

    id: uuid.UUID
    name: str
    status: str
    pruefumfang: str
    ampel_gesamt: str | None
    note: int | None
    created_at: datetime


@router.post("/api/v1/scans", status_code=status.HTTP_202_ACCEPTED, dependencies=[AnnahmeOffen])
async def einzelpruefung_starten(
    request: Request, caller: CurrentCaller, db: DbSession
) -> ScanStatus:
    """Drag and drop on the overview: a full check without a project. The files are not kept,
    the report stays until the owner deletes it. Same form fields as a project upload, no Git."""
    await _check_size(request)
    guthaben.email_pruefen(caller.user)
    limit = DEFAULT_LIMITS.auswahl_dateien
    form = await request.form(max_files=limit + 1, max_fields=limit + 10)
    try:
        upload, name = _upload_from(form, _EINZEL_ARTEN, None)
        buchung = guthaben.pruefung_abbuchen(db, caller.user)
        scan = await run_in_threadpool(
            lambda: create_scan(db, upload, project=None, name=name, owner_id=caller.user.id)
        )
        _verknuepfen(db, buchung, scan)
    finally:
        await form.close()
    audit(db, caller.user.id, "scan.gestartet", "scan", scan.id, art=upload.art.value)
    db.commit()
    return scan_status_of(scan)


@router.get("/api/v1/scans")
def einzelpruefungen(caller: CurrentCaller, db: DbSession) -> list[Einzelpruefung]:
    rows = db.scalars(
        select(Scan)
        .where(Scan.owner_id == caller.user.id, Scan.project_id.is_(None))
        .order_by(Scan.created_at.desc())
        .limit(100)
    )
    return [
        Einzelpruefung(
            id=s.id,
            name=str(((s.report or {}).get("paket") or {}).get("name") or "Einzelprüfung"),
            status=s.status,
            pruefumfang=s.pruefumfang,
            ampel_gesamt=s.ampel_gesamt,
            note=s.note,
            created_at=s.created_at,
        )
        for s in rows
    ]


@router.delete("/api/v1/scans/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def einzelpruefung_loeschen(scan_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> None:
    """Only single checks; a project's scans go with the project."""
    scan = get_owned(db, Scan, scan_id, caller)
    if scan.project_id is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"code": "gehoert_zu_projekt", "text": "Diese Prüfung gehört zu einem Projekt."},
        )
    if scan.status in ("wartend", "laeuft"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"code": "laeuft_noch", "text": "Die Prüfung läuft noch. Bitte danach löschen."},
        )
    db.delete(scan)
    audit(db, caller.user.id, "scan.geloescht", "scan", scan_id)
    db.commit()
