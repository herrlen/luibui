"""S3-7: the worker carries the finding status to the newest check of a project."""

import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from luibui_worker import results

pytestmark = pytest.mark.db

SPEC = Path(__file__).resolve().parents[3] / "spec" / "examples"
BEFUND: dict[str, Any] = json.loads((SPEC / "finding-secret.json").read_text())


def _befund(fp: str) -> dict[str, Any]:
    return {**BEFUND, "fingerprint": fp * 64}


@pytest.fixture
def projekt(engine: Engine) -> tuple[uuid.UUID, uuid.UUID]:
    with engine.begin() as conn:
        owner = conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, 'x') RETURNING id"),
            {"e": f"{uuid.uuid4().hex}@example.org"},
        ).scalar_one()
        pid = conn.execute(
            text(
                "INSERT INTO projects (owner_id, name, typ, quelle) "
                "VALUES (:o, 'p', 'skill', 'zip') RETURNING id"
            ),
            {"o": owner},
        ).scalar_one()
    return owner, pid


def _pruefung(
    engine: Engine,
    projekt: tuple[uuid.UUID, uuid.UUID],
    fps: list[str],
    umfang: str = "paket",
    minuten: int = 0,
) -> uuid.UUID:
    owner, pid = projekt
    with engine.begin() as conn:
        sid: uuid.UUID = conn.execute(
            text(
                "INSERT INTO scans "
                "(owner_id, project_id, scan_art, pruefumfang, status, created_at) "
                "VALUES (:o, :p, 'intensiv', CAST(:u AS pruefumfang), 'laeuft', "
                "now() + make_interval(mins => :m)) RETURNING id"
            ),
            {"o": owner, "p": pid, "u": umfang, "m": minuten},
        ).scalar_one()
        report = {
            "scan_id": str(sid),
            "engine_version": "test",
            "ampeln": {"sicherheit": "rot", "dsgvo": "gruen", "gesamt": "rot"},
            "note": 40,
            "freigabe": "blockiert",
            "befunde": [_befund(fp) for fp in fps],
        }
        results.record_report(conn, sid, report)
    return sid


def _status(engine: Engine, pid: uuid.UUID) -> dict[str, str]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT fingerprint, status FROM finding_status WHERE project_id = :p"),
            {"p": pid},
        )
        return {r.fingerprint[0]: r.status for r in rows}


def _setzen(engine: Engine, projekt: tuple[uuid.UUID, uuid.UUID], fp: str, status: str) -> None:
    owner, pid = projekt
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO finding_status "
                "(owner_id, project_id, fingerprint, status, begruendung) "
                "VALUES (:o, :p, :f, CAST(:s AS befund_status), 'Grund')"
            ),
            {"o": owner, "p": pid, "f": fp * 64, "s": status},
        )


def test_gone_findings_are_fixed_and_returning_ones_open_again(
    engine: Engine, projekt: tuple[uuid.UUID, uuid.UUID]
) -> None:
    _, pid = projekt
    _pruefung(engine, projekt, ["a", "b", "c"])
    _setzen(engine, projekt, "b", "akzeptiert")
    assert _status(engine, pid) == {"b": "akzeptiert"}

    _pruefung(engine, projekt, ["c"], minuten=1)
    assert _status(engine, pid) == {"a": "behoben", "b": "behoben"}

    _pruefung(engine, projekt, ["a", "c"], minuten=2)
    assert _status(engine, pid) == {"a": "offen", "b": "behoben"}


def test_narrower_scope_fixes_nothing(engine: Engine, projekt: tuple[uuid.UUID, uuid.UUID]) -> None:
    _, pid = projekt
    _pruefung(engine, projekt, ["a", "b"])
    _pruefung(engine, projekt, ["a"], umfang="auswahl", minuten=1)
    assert _status(engine, pid) == {}


def test_late_older_check_changes_nothing(
    engine: Engine, projekt: tuple[uuid.UUID, uuid.UUID]
) -> None:
    _, pid = projekt
    _pruefung(engine, projekt, ["a"], minuten=5)
    _pruefung(engine, projekt, [], minuten=1)
    assert _status(engine, pid) == {}


def test_checks_outside_projects_have_no_status(engine: Engine) -> None:
    with engine.begin() as conn:
        owner = conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, 'x') RETURNING id"),
            {"e": f"{uuid.uuid4().hex}@example.org"},
        ).scalar_one()
        sid = conn.execute(
            text(
                "INSERT INTO scans (owner_id, scan_art, pruefumfang, status) "
                "VALUES (:o, 'intensiv', 'paket', 'laeuft') RETURNING id"
            ),
            {"o": owner},
        ).scalar_one()
        results.update_finding_status(conn, sid)
        rows = conn.execute(
            text("SELECT count(*) FROM finding_status WHERE owner_id = :o"), {"o": owner}
        )
        assert rows.scalar_one() == 0
