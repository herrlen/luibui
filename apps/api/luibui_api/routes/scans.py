"""Start a scan for a project and read its status and report (S1-1)."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from luibui_api.audit import audit
from luibui_api.auth import AnnahmeOffen, CurrentCaller, DbSession, get_owned
from luibui_api.models import Project, Scan
from luibui_api.settings import get_settings
from luibui_api.uploads import Upload, create_scan
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
    )


def _check_size(request: Request) -> None:
    length = request.headers.get("content-length")
    if length is None or not length.isdigit():
        raise HTTPException(status.HTTP_411_LENGTH_REQUIRED, "Content-Length fehlt")
    if int(length) > get_settings().upload_max_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Upload zu groß")


@router.post(
    "/api/projects/{project_id}/scans",
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
    _check_size(request)
    limit = DEFAULT_LIMITS.auswahl_dateien
    form = await request.form(max_files=limit + 1, max_fields=limit + 10)
    try:
        art = _ARTEN.get(str(form.get("art")))
        if art is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unbekannte Art")
        uploads = [f for f in form.getlist("dateien") if isinstance(f, UploadFile)]
        pfade = [p for p in form.getlist("pfade") if isinstance(p, str)]
        if art is Eingabe.AUSWAHL and len(pfade) != len(uploads):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Zu jeder Datei gehört ein Pfad"
            )
        names = pfade if art is Eingabe.AUSWAHL else [u.filename or "" for u in uploads]
        text = form.get("text")
        git_url = form.get("git_url")
        upload = Upload(
            art=art,
            files=[(n, u.file) for n, u in zip(names, uploads, strict=True)],
            text=text if isinstance(text, str) else None,
            git_url=git_url if isinstance(git_url, str) and git_url else project.git_url,
        )
        scan = await run_in_threadpool(
            lambda: create_scan(db, upload, project=project, name=project.name)
        )
    finally:
        await form.close()
    audit(db, caller.user.id, "scan.gestartet", "scan", scan.id, art=art.value)
    db.commit()
    return scan_status_of(scan)


@router.get("/api/scans/{scan_id}")
def scan_status(scan_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> ScanStatus:
    return scan_status_of(get_owned(db, Scan, scan_id, caller))
