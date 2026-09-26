"""Accept an upload for a project scan (S1-1).

The upload goes through the engine's intake straight into ``<scratch_root>/<job-id>``, the
directory the worker scans. Unless the project says "nach Prüfung löschen", the files are also
stored encrypted as a new project version (S2-7). The scratch directory is removed here on any
error and by the worker after the scan.
"""

import shutil
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from luibui_api.models import Job, Project, ProjectVersion, Scan, StoredFile
from luibui_api.settings import get_settings
from luibui_api.storage import blob_store, new_storage_key, project_data_key
from luibui_scan.intake import (
    IntakeRejectedError,
    accept_file,
    accept_selection,
    accept_text,
    extract_zip,
)
from luibui_scan.inventory import Inventory, build_inventory
from luibui_scan.models import ScanArt
from luibui_scan.scan import Eingabe, pruefumfang_for


@dataclass(frozen=True, slots=True)
class Upload:
    art: Eingabe
    files: Sequence[tuple[str, IO[bytes]]] = ()
    text: str | None = None


def rejected(exc: IntakeRejectedError) -> HTTPException:
    detail = {"grund": exc.grund.value, "text": exc.text, "pfad": exc.pfad}
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


def _intake(upload: Upload, root: Path, scratch_root: Path) -> None:
    if upload.art is Eingabe.TEXT:
        if upload.text is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Text fehlt")
        accept_text(upload.text, root)
        return
    if not upload.files:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Keine Datei übergeben")
    if upload.art is Eingabe.AUSWAHL:
        accept_selection(upload.files, root)
        return
    if len(upload.files) != 1:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Genau eine Datei erwartet")
    name, src = upload.files[0]
    if upload.art is Eingabe.DATEI:
        accept_file(name, src, root)
        return
    # ZIP: zipfile needs a seekable file with a known size, so it is copied next to the scratch.
    archive = scratch_root / f".upload-{root.name}.zip"
    try:
        with archive.open("xb") as out:
            shutil.copyfileobj(src, out, 1024 * 1024)
        extract_zip(archive, root)
    finally:
        archive.unlink(missing_ok=True)


def _store_version(
    db: Session, project: Project, inventory: Inventory, root: Path, written: list[str]
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
            "Speicherplatz voll (500 MB pro Konto). Alte Versionen oder Projekte löschen.",
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


def create_scan(db: Session, project: Project, upload: Upload) -> Scan:
    """Intake, store and enqueue. Commits; on error nothing stays behind."""
    settings = get_settings()
    job_id = uuid.uuid4()
    root = settings.scratch_root / str(job_id)
    root.mkdir(mode=0o700)
    written: list[str] = []
    try:
        try:
            _intake(upload, root, settings.scratch_root)
        except IntakeRejectedError as exc:
            raise rejected(exc) from None
        inventory = build_inventory(root)
        version_id = None
        if not project.delete_files_after_scan:
            version_id = _store_version(db, project, inventory, root, written)
        scan = Scan(
            owner_id=project.owner_id,
            project_id=project.id,
            version_id=version_id,
            scan_art=ScanArt.INTENSIV.value,
            pruefumfang=pruefumfang_for(upload.art, inventory).value,
        )
        db.add(scan)
        db.flush()
        db.add(
            Job(
                id=job_id,
                owner_id=project.owner_id,
                kind="scan",
                scan_id=scan.id,
                max_attempts=1,
                payload={
                    "scan_id": str(scan.id),
                    "eingabe": upload.art.value,
                    "scan_art": ScanArt.INTENSIV.value,
                    "name": project.name,
                },
            )
        )
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
