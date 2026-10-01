"""Write scan outcomes to the database. Runs in the parent process only.

The report comes from the child that touched hostile content, so it is validated field by field
before anything is stored; a report that does not fit is refused as a whole.
"""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import Connection, text

from luibui_scan.models import Finding
from luibui_scan.scoring import AmpelDsgvo, AmpelSicherheit, Freigabe


class InvalidReportError(Exception):
    """The child's report does not match the expected shape."""


class _Ampeln(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sicherheit: AmpelSicherheit
    dsgvo: AmpelDsgvo
    gesamt: AmpelSicherheit


class _Report(BaseModel):
    model_config = ConfigDict(extra="allow")
    scan_id: uuid.UUID
    engine_version: str = Field(max_length=50)
    ampeln: _Ampeln
    note: int = Field(ge=0, le=100)
    freigabe: Freigabe
    befunde: list[Finding]


def scan_id_of(kind: str, payload: dict[str, Any]) -> uuid.UUID | None:
    if kind != "scan":
        return None
    try:
        return uuid.UUID(str(payload.get("scan_id")))
    except ValueError:
        return None


def mark_running(conn: Connection, scan_id: uuid.UUID) -> None:
    conn.execute(
        text("UPDATE scans SET status = 'laeuft', started_at = now() WHERE id = :id"),
        {"id": scan_id},
    )


def mark_failed(conn: Connection, scan_id: uuid.UUID, error: str) -> None:
    conn.execute(
        text(
            "UPDATE scans SET status = 'fehlgeschlagen', error = :error, finished_at = now() "
            "WHERE id = :id"
        ),
        {"id": scan_id, "error": error[:500]},
    )
    # A paid check that fails on our side is booked back, once (unique index per scan).
    conn.execute(
        text(
            "INSERT INTO credit_entries (owner_id, delta, grund, scan_id) "
            "SELECT owner_id, 1, 'erstattung', scan_id FROM credit_entries "
            "WHERE scan_id = :id AND grund = 'pruefung' "
            "ON CONFLICT (scan_id) WHERE grund = 'erstattung' DO NOTHING"
        ),
        {"id": scan_id},
    )


_INSERT_FINDING = text("""
INSERT INTO findings (
    owner_id, scan_id, rule_id, ebene, schwere, achse, titel, erklaerung, datei, zeile, beleg,
    nachweisgrad, normbezug, fix, fix_prompt, analyzer, fingerprint, hochgestuft_von
) VALUES (
    :owner_id, :scan_id, :rule_id, CAST(:ebene AS ebene), CAST(:schwere AS schwere),
    CAST(:achse AS achse), :titel, :erklaerung, :datei, :zeile, :beleg,
    CAST(:nachweisgrad AS nachweisgrad), :normbezug, :fix, :fix_prompt, :analyzer, :fingerprint,
    CAST(:hochgestuft_von AS schwere)
)
""")


def record_report(conn: Connection, scan_id: uuid.UUID, raw: object) -> None:
    try:
        report = _Report.model_validate(raw)
    except ValidationError as exc:
        # Only the field locations, never the values: they may carry package content.
        fields = ", ".join(".".join(map(str, e["loc"])) for e in exc.errors()[:5])
        raise InvalidReportError(fields) from None
    if report.scan_id != scan_id:
        raise InvalidReportError("scan_id")
    owner_id: uuid.UUID | None = conn.execute(
        text("SELECT owner_id FROM scans WHERE id = :id"), {"id": scan_id}
    ).scalar_one()
    conn.execute(
        text("""
        UPDATE scans SET
            status = 'fertig',
            ampel_sicherheit = CAST(:sicherheit AS ampel_sicherheit),
            ampel_dsgvo = CAST(:dsgvo AS ampel_dsgvo),
            ampel_gesamt = CAST(:gesamt AS ampel_sicherheit),
            note = :note,
            freigabe = CAST(:freigabe AS freigabe),
            report = CAST(:report AS jsonb),
            engine_version = :engine_version,
            finished_at = now()
        WHERE id = :id
        """),
        {
            "id": scan_id,
            "sicherheit": report.ampeln.sicherheit.value,
            "dsgvo": report.ampeln.dsgvo.value,
            "gesamt": report.ampeln.gesamt.value,
            "note": report.note,
            "freigabe": report.freigabe.value,
            "report": report.model_dump_json(),
            "engine_version": report.engine_version,
        },
    )
    for finding in report.befunde:
        data = finding.model_dump(mode="json")
        data["normbezug"] = list(data["normbezug"])
        data.pop("verweise", None)
        conn.execute(_INSERT_FINDING, {**data, "owner_id": owner_id, "scan_id": scan_id})
    update_finding_status(conn, scan_id)


def update_finding_status(conn: Connection, scan_id: uuid.UUID) -> None:
    """Carry the finding status of a project to its newest check (S3-7).

    A finding that came back is open again. A finding of the previous check that this check of
    the same scope no longer has is marked fixed: a selection of files says nothing about the
    files it left out. An older check that finishes late changes nothing.
    """
    scan = conn.execute(
        text("SELECT project_id, pruefumfang, created_at FROM scans WHERE id = :id"),
        {"id": scan_id},
    ).one()
    if scan.project_id is None:
        return
    ort = {"id": scan_id, "p": scan.project_id, "c": scan.created_at}
    neuer = conn.execute(
        text(
            "SELECT 1 FROM scans WHERE project_id = :p AND status = 'fertig' AND id <> :id "
            "AND created_at > :c LIMIT 1"
        ),
        ort,
    ).first()
    if neuer is not None:
        return
    jetzt: list[str] = list(
        conn.execute(
            text(
                "SELECT DISTINCT fingerprint FROM findings "
                "WHERE scan_id = :id AND fingerprint IS NOT NULL"
            ),
            ort,
        ).scalars()
    )
    conn.execute(
        text("""
        UPDATE finding_status SET status = 'offen', begruendung = NULL, updated_by = NULL,
            updated_at = now(), moderation = NULL, moderation_notiz = NULL,
            moderiert_von = NULL, moderiert_at = NULL
        WHERE project_id = :p AND status = 'behoben' AND fingerprint = ANY(:jetzt)
        """),
        {**ort, "jetzt": jetzt},
    )
    vorher = conn.execute(
        text(
            "SELECT id, pruefumfang FROM scans WHERE project_id = :p AND status = 'fertig' "
            "AND id <> :id AND created_at < :c ORDER BY created_at DESC LIMIT 1"
        ),
        ort,
    ).first()
    if vorher is None or vorher.pruefumfang != scan.pruefumfang:
        return
    conn.execute(
        text("""
        INSERT INTO finding_status (owner_id, project_id, fingerprint, status)
        SELECT DISTINCT s.owner_id, s.project_id, f.fingerprint, 'behoben'::befund_status
        FROM findings f JOIN scans s ON s.id = f.scan_id
        WHERE f.scan_id = :vorher AND f.fingerprint IS NOT NULL
            AND NOT (f.fingerprint = ANY(:jetzt))
        ON CONFLICT (project_id, fingerprint) DO UPDATE
            SET status = 'behoben', updated_by = NULL, updated_at = now()
            WHERE finding_status.status <> 'behoben'
        """),
        {"vorher": vorher.id, "jetzt": jetzt},
    )
