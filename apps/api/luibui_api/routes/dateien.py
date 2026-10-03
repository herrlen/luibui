"""Files of a checked version (S4-8): file tree, view as text with the findings at their line,
download as attachment.

Only through the owner's scan (get_owned): scan → its version → the stored files of that version.
Files are decrypted in memory only, never written in plain text anywhere (CLAUDE.md rule 10).
The view returns text that the web UI renders as text; nothing here is ever served as HTML or
Markdown. Binary files, and text that is not UTF-8, are only offered as a download, which always
goes out as ``application/octet-stream`` with ``Content-Disposition: attachment``.
"""

import uuid
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select

from luibui_api.audit import audit
from luibui_api.auth import CurrentCaller, DbSession, get_owned
from luibui_api.models import Project, ProjectVersion, Scan, StoredFile
from luibui_api.storage import blob_store, project_data_key
from luibui_api.storage.crypto import DecryptionError

router = APIRouter(tags=["dateien"])

MAX_ENTSCHLUESSELN = 50 * 1024 * 1024
"""Files are decrypted completely in memory before anything is sent (the API has 768 MB)."""
MAX_ANSICHT = 1024 * 1024
"""The view shows at most this much text; the download has the whole file."""


class Datei(BaseModel):
    id: uuid.UUID
    path: str
    size: int
    befunde: int


class Dateiliste(BaseModel):
    verfuegbar: bool
    grund: str | None = None
    """Why there are no files to show, in plain German."""
    dateien: list[Datei] = []


class BefundAnZeile(BaseModel):
    zeile: int | None
    schwere: str
    titel: str
    rule_id: str
    fingerprint: str | None


class DateiAnsicht(BaseModel):
    id: uuid.UUID
    path: str
    size: int
    sha256: str
    text: str | None
    """None for binary files and text that is not UTF-8."""
    gekuerzt: bool
    befunde: list[BefundAnZeile]


def _befunde(scan: Scan) -> list[dict[str, Any]]:
    befunde = (scan.report or {}).get("befunde")
    return [b for b in befunde if isinstance(b, dict)] if isinstance(befunde, list) else []


def _version(db: DbSession, scan: Scan) -> tuple[ProjectVersion | None, str | None]:
    """The scan's version and, if there are no files to show, the reason."""
    if scan.version_id is None:
        return None, "Zu dieser Prüfung gehören keine gespeicherten Dateien."
    version = db.get(ProjectVersion, scan.version_id)
    project = db.get(Project, scan.project_id) if scan.project_id else None
    if version is None or project is None:
        return None, "Zu dieser Prüfung gehören keine gespeicherten Dateien."
    if project.quelle == "git":
        return None, (
            "Bei Git-Projekten speichert luibui nur den Commit, keine Dateien. Die Ansicht für "
            "Git-Projekte folgt."
        )
    if version.files_deleted_at is not None:
        return None, "Die Dateien dieser Version wurden gelöscht."
    return version, None


@router.get("/api/v1/scans/{scan_id}/dateien")
def dateien(scan_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> Dateiliste:
    scan = get_owned(db, Scan, scan_id, caller)
    version, grund = _version(db, scan)
    if version is None:
        return Dateiliste(verfuegbar=False, grund=grund)
    je_datei: dict[str, int] = {}
    for b in _befunde(scan):
        if isinstance(b.get("datei"), str):
            je_datei[b["datei"]] = je_datei.get(b["datei"], 0) + 1
    rows = db.scalars(
        select(StoredFile)
        .where(StoredFile.version_id == version.id, StoredFile.owner_id == scan.owner_id)
        .order_by(StoredFile.path)
    )
    return Dateiliste(
        verfuegbar=True,
        dateien=[
            Datei(id=f.id, path=f.path, size=f.size, befunde=je_datei.get(f.path, 0)) for f in rows
        ],
    )


def _datei(db: DbSession, scan: Scan, datei_id: uuid.UUID) -> tuple[StoredFile, bytes]:
    """The stored file of this scan's version, decrypted. 404 for anything else."""
    version, _ = _version(db, scan)
    datei = db.get(StoredFile, datei_id)
    if version is None or datei is None or datei.version_id != version.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    if datei.owner_id != scan.owner_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    if datei.size > MAX_ENTSCHLUESSELN:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            {"code": "zu_gross", "text": "Dateien über 50 MB lassen sich hier nicht öffnen."},
        )
    project = db.get(Project, scan.project_id)
    if project is None or project.data_key_enc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    data_key, _ = project_data_key(project.id, project.data_key_enc)
    try:
        inhalt = b"".join(blob_store().open(datei.storage_key, data_key))
    except (DecryptionError, FileNotFoundError):
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"code": "datei_defekt", "text": "Die Datei lässt sich nicht lesen."},
        ) from None
    return datei, inhalt


def _als_text(inhalt: bytes) -> tuple[str | None, bool]:
    if b"\x00" in inhalt[:8192]:
        return None, False
    gekuerzt = len(inhalt) > MAX_ANSICHT
    teil = inhalt[:MAX_ANSICHT]
    try:
        text = teil.decode("utf-8")
    except UnicodeDecodeError as exc:
        # Cut in the middle of a character at the limit: fine. Anywhere else: not UTF-8.
        if not gekuerzt or exc.start < len(teil) - 4:
            return None, False
        text = teil[: exc.start].decode("utf-8")
    if gekuerzt and "\n" in text:
        text = text[: text.rfind("\n") + 1]
    return text, gekuerzt


@router.get("/api/v1/scans/{scan_id}/dateien/{datei_id}")
def datei_ansicht(
    scan_id: uuid.UUID, datei_id: uuid.UUID, caller: CurrentCaller, db: DbSession
) -> DateiAnsicht:
    scan = get_owned(db, Scan, scan_id, caller)
    datei, inhalt = _datei(db, scan, datei_id)
    text, gekuerzt = _als_text(inhalt)
    befunde = [
        BefundAnZeile(
            zeile=b["zeile"] if isinstance(b.get("zeile"), int) else None,
            schwere=str(b.get("schwere", "")),
            titel=str(b.get("titel", "")),
            rule_id=str(b.get("rule_id", "")),
            fingerprint=b.get("fingerprint") if isinstance(b.get("fingerprint"), str) else None,
        )
        for b in _befunde(scan)
        if b.get("datei") == datei.path
    ]
    return DateiAnsicht(
        id=datei.id,
        path=datei.path,
        size=datei.size,
        sha256=datei.sha256,
        text=text,
        gekuerzt=gekuerzt,
        befunde=befunde,
    )


@router.get(
    "/api/v1/scans/{scan_id}/dateien/{datei_id}/download",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
def datei_download(
    scan_id: uuid.UUID, datei_id: uuid.UUID, caller: CurrentCaller, db: DbSession
) -> Response:
    scan = get_owned(db, Scan, scan_id, caller)
    datei, inhalt = _datei(db, scan, datei_id)
    audit(db, caller.user.id, "datei.heruntergeladen", "stored_file", datei.id)
    db.commit()
    name = datei.path.rsplit("/", 1)[-1] or "datei"
    ascii_name = "".join(c if (c.isascii() and c.isalnum()) or c in "._-" else "_" for c in name)
    return Response(
        content=inhalt,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{ascii_name[:100]}\"; filename*=UTF-8''{quote(name)}"
            ),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
