"""Projects of the signed-in developer (minimal backend for S1-1; the UI follows with S2-8)."""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.exc import IntegrityError

from luibui_api import guthaben
from luibui_api.audit import audit
from luibui_api.auth import CurrentCaller, DbSession, get_owned
from luibui_api.models import Project, ProjectVersion, Scan, StoredFile
from luibui_api.storage import blob_store
from luibui_scan.intake.safe_git import canonical_url

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

Typ = Literal["skill", "mcp-server", "plugin", "tool", "einzeldatei"]
Quelle = Literal["datei", "auswahl", "text", "zip", "git"]


class ProjektNeu(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    typ: Typ
    quelle: Quelle = "zip"
    git_url: str | None = Field(default=None, max_length=500)
    nach_pruefung_loeschen: bool = False

    @field_validator("git_url")
    @classmethod
    def _git_url(cls, value: str | None) -> str | None:
        return None if value is None else canonical_url(value)


class Pruefungskurz(BaseModel):
    """A scan in lists: status and verdict, without the report."""

    id: uuid.UUID
    status: str
    pruefumfang: str
    ampel_gesamt: str | None
    note: int | None
    freigabe: str | None
    created_at: datetime
    finished_at: datetime | None


class Projekt(BaseModel):
    id: uuid.UUID
    name: str
    typ: str
    quelle: str
    git_url: str | None
    nach_pruefung_loeschen: bool
    created_at: datetime
    letzte_pruefung: Pruefungskurz | None = None


def kurz(s: Scan) -> Pruefungskurz:
    return Pruefungskurz(
        id=s.id,
        status=s.status,
        pruefumfang=s.pruefumfang,
        ampel_gesamt=s.ampel_gesamt,
        note=s.note,
        freigabe=s.freigabe,
        created_at=s.created_at,
        finished_at=s.finished_at,
    )


def _out(p: Project, letzte: Scan | None = None) -> Projekt:
    return Projekt(
        id=p.id,
        name=p.name,
        typ=p.typ,
        quelle=p.quelle,
        git_url=p.git_url,
        nach_pruefung_loeschen=p.delete_files_after_scan,
        created_at=p.created_at,
        letzte_pruefung=kurz(letzte) if letzte else None,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def anlegen(body: ProjektNeu, caller: CurrentCaller, db: DbSession) -> Projekt:
    guthaben.projekt_erlaubt(db, caller.user)
    project = Project(
        owner_id=caller.user.id,
        name=body.name.strip(),
        typ=body.typ,
        quelle=body.quelle,
        git_url=body.git_url,
        delete_files_after_scan=body.nach_pruefung_loeschen,
    )
    db.add(project)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"code": "name_vergeben", "text": "Es gibt schon ein Projekt mit diesem Namen"},
        ) from None
    db.refresh(project)
    audit(db, caller.user.id, "projekt.angelegt", "project", project.id)
    db.commit()
    return _out(project)


@router.get("")
def liste(caller: CurrentCaller, db: DbSession) -> list[Projekt]:
    rows = list(
        db.scalars(
            select(Project).where(Project.owner_id == caller.user.id).order_by(Project.created_at)
        )
    )
    latest = {
        s.project_id: s
        for s in db.scalars(
            select(Scan)
            .where(Scan.owner_id == caller.user.id, Scan.project_id.is_not(None))
            .ext(distinct_on(Scan.project_id))
            .order_by(Scan.project_id, Scan.created_at.desc())
        )
    }
    return [_out(p, latest.get(p.id)) for p in rows]


@router.get("/{project_id}/scans")
def pruefungen(project_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> list[Pruefungskurz]:
    project = get_owned(db, Project, project_id, caller)
    rows = db.scalars(
        select(Scan)
        .where(Scan.project_id == project.id, Scan.owner_id == caller.user.id)
        .order_by(Scan.created_at.desc())
        .limit(100)
    )
    return [kurz(s) for s in rows]


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
