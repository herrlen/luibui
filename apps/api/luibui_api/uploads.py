"""Accept an upload for a project scan (S1-1).

The upload goes through the engine's intake straight into ``<scratch_root>/<job-id>``, the
directory the worker scans. Unless the project says "nach Prüfung löschen", the files are also
stored encrypted as a new project version (S2-7). The scratch directory is removed here on any
error and by the worker after the scan.
"""

import asyncio
import contextlib
import shutil
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import IO

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.requests import ClientDisconnect

from luibui_api.models import Job, Project, ProjectVersion, Scan, StoredFile
from luibui_api.settings import get_settings
from luibui_api.storage import blob_store, new_storage_key, project_data_key
from luibui_scan.intake import (
    IntakeRejectedError,
    accept_file,
    accept_selection,
    accept_text,
    extract_archive,
    rejection_finding,
)
from luibui_scan.intake.safe_git import GitError, clone_into
from luibui_scan.inventory import Inventory, build_inventory
from luibui_scan.malware import known_malware
from luibui_scan.models import ScanArt
from luibui_scan.scan import Eingabe, pruefumfang_for


@dataclass(frozen=True, slots=True)
class Upload:
    art: Eingabe
    files: Sequence[tuple[str, IO[bytes]]] = ()
    text: str | None = None
    git_url: str | None = None


QUICKSCAN_DAYS = 7
QUICKSCAN_TIMEOUT_SECONDS = 60


def rejected(exc: IntakeRejectedError) -> HTTPException:
    detail = {
        "code": exc.grund.value,
        "text": exc.text,
        "pfad": exc.pfad,
        "befund": rejection_finding(exc).to_json_dict(),
    }
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


def _unprocessable(grund: str, text: str) -> HTTPException:
    return HTTPException(
        status.HTTP_422_UNPROCESSABLE_CONTENT, {"code": grund, "text": text, "pfad": None}
    )


@dataclass(frozen=True, slots=True)
class _Intake:
    commit: str | None = None
    git_symlinks: tuple[str, ...] = ()


def _intake(upload: Upload, root: Path, scratch_root: Path) -> _Intake:
    """Unpack the upload into ``root``; for Git input also return commit and symlink paths."""
    if upload.art is Eingabe.GIT:
        try:
            cloned = clone_into(upload.git_url or "", root, scratch_root)
            return _Intake(cloned.commit, tuple(cloned.symlinks))
        except ValueError as exc:
            raise _unprocessable("ungueltige_url", str(exc)) from None
        except GitError:
            raise _unprocessable(
                "git_fehler", "Repository nicht erreichbar, nicht öffentlich oder zu langsam."
            ) from None
    if upload.art is Eingabe.TEXT:
        if upload.text is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Text fehlt")
        accept_text(upload.text, root)
        return _Intake()
    if not upload.files:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Keine Datei übergeben")
    if upload.art is Eingabe.AUSWAHL:
        accept_selection(upload.files, root)
        return _Intake()
    if len(upload.files) != 1:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Genau eine Datei erwartet")
    name, src = upload.files[0]
    if upload.art is Eingabe.DATEI:
        accept_file(name, src, root)
        return _Intake()
    # ZIP or tar: both need a seekable file with a known size, so it is copied next to the scratch.
    archive = scratch_root / f".upload-{root.name}.archiv"
    try:
        with archive.open("xb") as out:
            shutil.copyfileobj(src, out, 1024 * 1024)
        extract_archive(archive, root)
    finally:
        archive.unlink(missing_ok=True)
    return _Intake()


def _store_version(
    db: Session,
    project: Project,
    inventory: Inventory,
    root: Path,
    written: list[str],
    commit: str | None,
) -> uuid.UUID:
    """Store every file encrypted. Each storage key is appended to ``written`` right after its
    blob exists, so the caller can remove them if anything later fails."""
    settings = get_settings()
    used = db.scalar(
        select(func.coalesce(func.sum(StoredFile.size), 0)).where(
            StoredFile.owner_id == project.owner_id
        )
    )
    if int(used or 0) + inventory.bytes > settings.account_quota_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            {
                "code": "speicher_voll",
                "text": "Speicherplatz voll (500 MB pro Konto). Alte Versionen löschen.",
            },
        )
    data_key, data_key_enc = project_data_key(project.id, project.data_key_enc)
    project.data_key_enc = data_key_enc
    number = (
        db.scalar(
            select(func.max(ProjectVersion.number)).where(ProjectVersion.project_id == project.id)
        )
        or 0
    ) + 1
    version = ProjectVersion(
        owner_id=project.owner_id,
        project_id=project.id,
        number=number,
        commit_sha=commit,
        inventory_sha256=inventory.sha256,
        file_count=len(inventory.entries),
        bytes=inventory.bytes,
    )
    db.add(version)
    db.flush()
    store = blob_store()
    for entry in inventory.entries:
        key = new_storage_key()
        with root.joinpath(*entry.path.split("/")).open("rb") as src:
            store.put(key, src, data_key)
        written.append(key)
        db.add(
            StoredFile(
                owner_id=project.owner_id,
                version_id=version.id,
                path=entry.path,
                size=entry.size,
                sha256=entry.sha256,
                storage_key=key,
            )
        )
    return version.id


def prune_versions(db: Session, project: Project) -> list[str]:
    """Drop versions beyond the limit (oldest first); return storage keys to delete after commit."""
    keep = get_settings().versions_per_project
    old = list(
        db.scalars(
            select(ProjectVersion)
            .where(ProjectVersion.project_id == project.id)
            .order_by(ProjectVersion.number.desc())
            .offset(keep)
        )
    )
    keys: list[str] = []
    for version in old:
        keys.extend(
            db.scalars(select(StoredFile.storage_key).where(StoredFile.version_id == version.id))
        )
        db.delete(version)
    return keys


def create_scan(
    db: Session,
    upload: Upload,
    *,
    project: Project | None,
    scan_art: ScanArt = ScanArt.INTENSIV,
    name: str,
    owner_id: uuid.UUID | None = None,
) -> Scan:
    """Intake, store and enqueue. Commits; on error nothing stays behind.

    Without ``project`` nothing is stored. A quick scan has no owner and its report is kept
    7 days; a single check from the overview has ``owner_id`` and stays until its owner deletes it.
    """
    settings = get_settings()
    job_id = uuid.uuid4()
    root = settings.scratch_root / str(job_id)
    root.mkdir(mode=0o700)
    written: list[str] = []
    stale_keys: list[str] = []
    owner_id = project.owner_id if project else owner_id
    try:
        try:
            intake = _intake(upload, root, settings.scratch_root)
        except IntakeRejectedError as exc:
            raise rejected(exc) from None
        inventory = build_inventory(root)
        version_id = None
        malware = known_malware()
        # Rule 10: known malware is never stored. The scan still runs and reports A08.
        if (
            project is not None
            and not project.delete_files_after_scan
            and not any(e.sha256 in malware for e in inventory.entries)
        ):
            version_id = _store_version(db, project, inventory, root, written, intake.commit)
        scan = Scan(
            owner_id=owner_id,
            project_id=project.id if project else None,
            version_id=version_id,
            scan_art=scan_art.value,
            pruefumfang=pruefumfang_for(upload.art, inventory).value,
            expires_at=(
                datetime.now(UTC) + timedelta(days=QUICKSCAN_DAYS)
                if scan_art is ScanArt.SCHNELL
                else None
            ),
        )
        db.add(scan)
        db.flush()
        db.add(
            Job(
                id=job_id,
                owner_id=owner_id,
                kind="scan",
                scan_id=scan.id,
                max_attempts=1,
                timeout_seconds=(QUICKSCAN_TIMEOUT_SECONDS if scan_art is ScanArt.SCHNELL else 300),
                payload={
                    "scan_id": str(scan.id),
                    "eingabe": upload.art.value,
                    "scan_art": scan_art.value,
                    "name": name,
                    "options": {"git_symlinks": list(intake.git_symlinks)},
                },
            )
        )
        if project is not None:
            stale_keys = prune_versions(db, project)
        db.commit()
    except BaseException:
        db.rollback()
        shutil.rmtree(root, ignore_errors=True)
        for key in written:
            blob_store().delete(key)
        raise
    for key in stale_keys:
        blob_store().delete(key)
    db.refresh(scan)
    return scan


ABLESEN_MAX = 80 * 1024 * 1024
"""An oversized body up to this size is read and thrown away before the 413. Behind the web
proxy of Next.js an answer that comes while the proxy is still sending breaks its pipe and
turns into a 500. Next.js itself cuts bodies at 61 MB (next.config.ts), so this covers them."""
ABLESEN_FRIST = 15.0


async def ablesen(request: Request) -> None:
    """Drain the request body, bounded in size and time, so an early refusal reaches the
    client. A bigger announced body is refused at once."""
    laenge = request.headers.get("content-length", "")
    if not laenge.isdigit() or int(laenge) > ABLESEN_MAX:
        return

    async def lesen() -> None:
        gelesen = 0
        async for teil in request.stream():
            gelesen += len(teil)
            if gelesen > ABLESEN_MAX:
                return

    with contextlib.suppress(TimeoutError, ClientDisconnect):
        await asyncio.wait_for(lesen(), ABLESEN_FRIST)
