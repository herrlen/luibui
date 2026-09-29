"""Projects of the signed-in developer (minimal backend for S1-1; the UI follows with S2-8)."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.exc import IntegrityError

from luibui_api import guthaben
from luibui_api.audit import audit
from luibui_api.auth import CurrentCaller, DbSession, get_owned
from luibui_api.models import FindingStatus, Project, ProjectVersion, Scan, StoredFile
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
        return None if not value else canonical_url(value)

    @model_validator(mode="after")
    def _git_braucht_url(self) -> "ProjektNeu":
        if self.quelle == "git" and not self.git_url:
            raise ValueError("Für die Quelle Git bitte die Adresse des Repositorys angeben")
        return self


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
    offen_k: int = 0
    """Open critical findings of the last finished check (not marked as fixed, accepted or
    disputed)."""
    offen_h: int = 0


class OffenerBefund(BaseModel):
    """A critical or high finding of a project's last finished check, for the overview."""

    project_id: uuid.UUID
    projekt: str
    scan_id: uuid.UUID
    rule_id: str
    schwere: Literal["K", "H"]
    titel: str
    datei: str | None
    zeile: int | None


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


def _out(p: Project, letzte: Scan | None = None, offen: Sequence[dict[str, Any]] = ()) -> Projekt:
    return Projekt(
        id=p.id,
        name=p.name,
        typ=p.typ,
        quelle=p.quelle,
        git_url=p.git_url,
        nach_pruefung_loeschen=p.delete_files_after_scan,
        created_at=p.created_at,
        letzte_pruefung=kurz(letzte) if letzte else None,
        offen_k=sum(1 for f in offen if f.get("schwere") == "K"),
        offen_h=sum(1 for f in offen if f.get("schwere") == "H"),
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


def _latest(db: DbSession, owner_id: uuid.UUID, *, fertig: bool) -> dict[uuid.UUID, Scan]:
    query = select(Scan).where(Scan.owner_id == owner_id, Scan.project_id.is_not(None))
    if fertig:
        query = query.where(Scan.status == "fertig", Scan.report.is_not(None))
    rows = db.scalars(
        query.ext(distinct_on(Scan.project_id)).order_by(Scan.project_id, Scan.created_at.desc())
    )
    return {s.project_id: s for s in rows if s.project_id is not None}


def _offen(
    db: DbSession, owner_id: uuid.UUID
) -> dict[uuid.UUID, tuple[Scan, list[dict[str, Any]]]]:
    """Per project: the last finished check and its critical and high findings that nobody
    marked as fixed, accepted or disputed."""
    erledigt = {
        (f.project_id, f.fingerprint)
        for f in db.scalars(
            select(FindingStatus).where(
                FindingStatus.owner_id == owner_id, FindingStatus.status != "offen"
            )
        )
    }
    ergebnis = {}
    for pid, scan in _latest(db, owner_id, fertig=True).items():
        befunde = (scan.report or {}).get("befunde") or []
        ergebnis[pid] = (
            scan,
            [
                f
                for f in befunde
                if isinstance(f, dict)
                and f.get("schwere") in ("K", "H")
                and (pid, f.get("fingerprint")) not in erledigt
            ],
        )
    return ergebnis


@router.get("")
def liste(caller: CurrentCaller, db: DbSession) -> list[Projekt]:
    """Projects with open critical findings first, then open high ones, then by age."""
    uid = caller.user.id
    rows = db.scalars(select(Project).where(Project.owner_id == uid).order_by(Project.created_at))
    latest = _latest(db, uid, fertig=False)
    offen = _offen(db, uid)
    projekte = [_out(p, latest.get(p.id), offen.get(p.id, (None, []))[1]) for p in rows]
    return sorted(projekte, key=lambda p: (-p.offen_k, -p.offen_h))


@router.get("/offene-befunde")
def offene_befunde(caller: CurrentCaller, db: DbSession) -> list[OffenerBefund]:
    """For the overview: open critical and high findings across all projects, critical first,
    at most 50."""
    projekte = {
        p.id: p.name for p in db.scalars(select(Project).where(Project.owner_id == caller.user.id))
    }
    liste_ = [
        OffenerBefund(
            project_id=pid,
            projekt=projekte.get(pid, ""),
            scan_id=scan.id,
            rule_id=str(f.get("rule_id") or ""),
            schwere=f["schwere"],
            titel=str(f.get("titel") or ""),
            datei=f.get("datei") if isinstance(f.get("datei"), str) else None,
            zeile=f.get("zeile") if isinstance(f.get("zeile"), int) else None,
        )
        for pid, (scan, befunde) in _offen(db, caller.user.id).items()
        for f in befunde
    ]
    liste_.sort(key=lambda b: (b.schwere != "K", b.projekt.lower(), b.datei or "", b.zeile or 0))
    return liste_[:50]


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


class Version(BaseModel):
    """A stored version of a project (S2-7, S2-8)."""

    id: uuid.UUID
    nummer: int
    angelegt: datetime
    dateien: int
    bytes: int
    commit_sha: str | None
    dateien_geloescht: bool
    """The files were removed after the check (project option); only the report is left."""
    pruefung: Pruefungskurz | None


@router.get("/{project_id}/versions")
def versionen(project_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> list[Version]:
    """Newest first, each with its latest check."""
    project = get_owned(db, Project, project_id, caller)
    rows = db.scalars(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project.id)
        .order_by(ProjectVersion.number.desc())
    )
    pruefungen_ = {
        s.version_id: s
        for s in db.scalars(
            select(Scan)
            .where(Scan.project_id == project.id, Scan.version_id.is_not(None))
            .ext(distinct_on(Scan.version_id))
            .order_by(Scan.version_id, Scan.created_at.desc())
        )
    }
    return [
        Version(
            id=v.id,
            nummer=v.number,
            angelegt=v.created_at,
            dateien=v.file_count,
            bytes=v.bytes,
            commit_sha=v.commit_sha,
            dateien_geloescht=v.files_deleted_at is not None,
            pruefung=kurz(pruefungen_[v.id]) if v.id in pruefungen_ else None,
        )
        for v in rows
    ]


@router.delete("/{project_id}/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
def version_loeschen(
    project_id: uuid.UUID, version_id: uuid.UUID, caller: CurrentCaller, db: DbSession
) -> None:
    """Removes the version and its encrypted files; the reports of its checks stay."""
    project = get_owned(db, Project, project_id, caller)
    version = get_owned(db, ProjectVersion, version_id, caller)
    if version.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    keys = list(
        db.scalars(select(StoredFile.storage_key).where(StoredFile.version_id == version.id))
    )
    db.delete(version)
    audit(
        db,
        caller.user.id,
        "version.geloescht",
        "project_version",
        version_id,
        nummer=version.number,
    )
    db.commit()
    # Only after the commit: a failed commit must not leave records without their files.
    for key in keys:
        blob_store().delete(key)


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
