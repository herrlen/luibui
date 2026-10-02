"""History of a project (S3-5): grade and findings over time, and two checks compared.

Only finished checks count. Findings are matched by fingerprint (S2-5), so a finding that moved a
few lines is still the same finding. A comparison of checks with different scope (a selection of
files against the whole package) says so: missing findings may just be outside the selection.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import select, text

from luibui_api.auth import CurrentCaller, DbSession, get_owned
from luibui_api.errors import fehler
from luibui_api.models import Project, Scan

router = APIRouter(prefix="/api/v1/projects", tags=["verlauf"])

SCHWEREN = ("K", "H", "M", "N", "I")
MAX_PUNKTE = 100


class Punkt(BaseModel):
    """One finished check in the history."""

    scan_id: uuid.UUID
    created_at: datetime
    note: int | None
    ampel_gesamt: str | None
    pruefumfang: str
    befunde: dict[str, int]
    """Number of findings per severity (K, H, M, N, I)."""


_VERLAUF = text("""
SELECT s.id, s.created_at, s.note, s.ampel_gesamt, s.pruefumfang,
       count(*) FILTER (WHERE b->>'schwere' = 'K') AS k,
       count(*) FILTER (WHERE b->>'schwere' = 'H') AS h,
       count(*) FILTER (WHERE b->>'schwere' = 'M') AS m,
       count(*) FILTER (WHERE b->>'schwere' = 'N') AS n,
       count(*) FILTER (WHERE b->>'schwere' = 'I') AS i
FROM scans s
LEFT JOIN LATERAL jsonb_array_elements(
    CASE WHEN jsonb_typeof(s.report->'befunde') = 'array' THEN s.report->'befunde'
         ELSE '[]'::jsonb END
) AS b ON true
WHERE s.project_id = :p AND s.owner_id = :o AND s.status = 'fertig' AND s.report IS NOT NULL
GROUP BY s.id
ORDER BY s.created_at DESC
LIMIT :n
""")


@router.get("/{project_id}/verlauf")
def verlauf(project_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> list[Punkt]:
    """The last 100 finished checks, oldest first."""
    project = get_owned(db, Project, project_id, caller)
    rows = db.execute(_VERLAUF, {"p": project.id, "o": caller.user.id, "n": MAX_PUNKTE}).all()
    return [
        Punkt(
            scan_id=r.id,
            created_at=r.created_at,
            note=r.note,
            ampel_gesamt=r.ampel_gesamt,
            pruefumfang=r.pruefumfang,
            befunde={"K": r.k, "H": r.h, "M": r.m, "N": r.n, "I": r.i},
        )
        for r in reversed(rows)
    ]


class Eintrag(BaseModel):
    """A finding in a comparison: what it is and where, nothing more."""

    fingerprint: str
    rule_id: str
    schwere: str
    titel: str
    datei: str | None
    zeile: int | None


class Seite(BaseModel):
    scan_id: uuid.UUID
    created_at: datetime
    note: int | None
    ampel_gesamt: str | None
    pruefumfang: str


class Vergleich(BaseModel):
    von: Seite
    bis: Seite
    neu: list[Eintrag]
    behoben: list[Eintrag]
    unveraendert: list[Eintrag]
    gleicher_umfang: bool


def _seite(s: Scan) -> Seite:
    return Seite(
        scan_id=s.id,
        created_at=s.created_at,
        note=s.note,
        ampel_gesamt=s.ampel_gesamt,
        pruefumfang=s.pruefumfang,
    )


def _befunde(s: Scan) -> dict[str, Eintrag]:
    """Findings by fingerprint; those without one cannot be matched and are left out."""
    liste = (s.report or {}).get("befunde")
    out: dict[str, Eintrag] = {}
    for b in liste if isinstance(liste, list) else []:
        if not isinstance(b, dict) or not isinstance(b.get("fingerprint"), str):
            continue
        out.setdefault(
            b["fingerprint"],
            Eintrag(
                fingerprint=b["fingerprint"],
                rule_id=str(b.get("rule_id") or ""),
                schwere=str(b.get("schwere") or ""),
                titel=str(b.get("titel") or ""),
                datei=b.get("datei") if isinstance(b.get("datei"), str) else None,
                zeile=b.get("zeile") if isinstance(b.get("zeile"), int) else None,
            ),
        )
    return out


def _sortiert(eintraege: list[Eintrag]) -> list[Eintrag]:
    rang = {s: i for i, s in enumerate(SCHWEREN)}
    return sorted(eintraege, key=lambda e: (rang.get(e.schwere, 9), e.datei or "", e.zeile or 0))


def _fertige(db: DbSession, project: Project, owner_id: uuid.UUID) -> list[Scan]:
    return list(
        db.scalars(
            select(Scan)
            .where(
                Scan.project_id == project.id,
                Scan.owner_id == owner_id,
                Scan.status == "fertig",
                Scan.report.is_not(None),
            )
            .order_by(Scan.created_at.desc())
            .limit(2)
        )
    )


@router.get("/{project_id}/vergleich")
def vergleich(
    project_id: uuid.UUID,
    caller: CurrentCaller,
    db: DbSession,
    von: uuid.UUID | None = None,
    bis: uuid.UUID | None = None,
) -> Vergleich:
    """Two finished checks of the project: new, fixed and unchanged findings. Without ``von`` and
    ``bis``: the last check against the one before."""
    project = get_owned(db, Project, project_id, caller)
    nicht_da = fehler(status.HTTP_404_NOT_FOUND, "nicht_gefunden", "Prüfung nicht gefunden")
    if von is None and bis is None:
        letzte = _fertige(db, project, caller.user.id)
        if len(letzte) < 2:
            raise fehler(
                status.HTTP_409_CONFLICT,
                "zu_wenig_pruefungen",
                "Für einen Vergleich braucht es zwei fertige Prüfungen.",
            )
        bis_scan, von_scan = letzte
    elif von is None or bis is None:
        raise fehler(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "von_und_bis", "Bitte beide Prüfungen angeben."
        )
    else:
        scans: list[Scan] = []
        for scan_id in (von, bis):
            s = db.get(Scan, scan_id)
            if (
                s is None
                or s.project_id != project.id
                or s.owner_id != caller.user.id
                or s.status != "fertig"
                or s.report is None
            ):
                raise nicht_da
            scans.append(s)
        von_scan, bis_scan = scans
        if von_scan.created_at > bis_scan.created_at:  # always older -> newer
            von_scan, bis_scan = bis_scan, von_scan
    alt, neu = _befunde(von_scan), _befunde(bis_scan)
    return Vergleich(
        von=_seite(von_scan),
        bis=_seite(bis_scan),
        neu=_sortiert([e for fp, e in neu.items() if fp not in alt]),
        behoben=_sortiert([e for fp, e in alt.items() if fp not in neu]),
        unveraendert=_sortiert([e for fp, e in neu.items() if fp in alt]),
        gleicher_umfang=von_scan.pruefumfang == bis_scan.pruefumfang,
    )
