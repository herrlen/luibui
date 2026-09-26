"""Projects of the signed-in developer (minimal backend for S1-1; the UI follows with S2-8)."""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from luibui_api.audit import audit
from luibui_api.auth import CurrentCaller, DbSession, get_owned
from luibui_api.models import Project, ProjectVersion, StoredFile
from luibui_api.storage import blob_store

router = APIRouter(prefix="/api/projects", tags=["projects"])

Typ = Literal["skill", "mcp-server", "plugin", "tool", "einzeldatei"]
Quelle = Literal["datei", "auswahl", "text", "zip", "git"]


class ProjektNeu(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    typ: Typ
    quelle: Quelle = "zip"
    nach_pruefung_loeschen: bool = False


class Projekt(BaseModel):
    id: uuid.UUID
    name: str
    typ: str
    quelle: str
    nach_pruefung_loeschen: bool
    created_at: datetime


def _out(p: Project) -> Projekt:
    return Projekt(
        id=p.id,
        name=p.name,
        typ=p.typ,
        quelle=p.quelle,
        nach_pruefung_loeschen=p.delete_files_after_scan,
        created_at=p.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def anlegen(body: ProjektNeu, caller: CurrentCaller, db: DbSession) -> Projekt:
    project = Project(
        owner_id=caller.user.id,
        name=body.name.strip(),
        typ=body.typ,
        quelle=body.quelle,
        delete_files_after_scan=body.nach_pruefung_loeschen,
    )
    db.add(project)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Es gibt schon ein Projekt mit diesem Namen"
        ) from None
    db.refresh(project)
    audit(db, caller.user.id, "projekt.angelegt", "project", project.id)
    db.commit()
    return _out(project)


@router.get("")
def liste(caller: CurrentCaller, db: DbSession) -> list[Projekt]:
    rows = db.scalars(
        select(Project).where(Project.owner_id == caller.user.id).order_by(Project.created_at)
    )
    return [_out(p) for p in rows]


@router.get("/{project_id}")
def zeigen(project_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> Projekt:
    return _out(get_owned(db, Project, project_id, caller))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def loeschen(project_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> None:
    """Deletes the project, all versions, scans and the encrypted files on the volume."""
    project = get_owned(db, Project, project_id, caller)
    keys = _storage_keys(db, project)
    db.delete(project)
    audit(db, caller.user.id, "projekt.geloescht", "project", project_id)
    db.commit()
    # Only after the commit: a failed commit must not leave records without their files.
    for key in keys:
        blob_store().delete(key)


def _storage_keys(db: DbSession, project: Project) -> list[str]:
    return list(
        db.scalars(
            select(StoredFile.storage_key)
            .join(ProjectVersion, StoredFile.version_id == ProjectVersion.id)
            .where(ProjectVersion.project_id == project.id)
        )
    )
