"""S2-8: the overview shows open critical and high findings first."""

import json
import uuid
from typing import Any

from sqlalchemy import create_engine, text

from .conftest import Api
from .test_scans import project, upload_zip


def _befund(schwere: str, titel: str, fp: str, zeile: int = 1) -> dict[str, Any]:
    return {
        "rule_id": f"LB-A01-{titel}",
        "schwere": schwere,
        "titel": titel,
        "datei": "SKILL.md",
        "zeile": zeile,
        "fingerprint": fp * 64,
    }


def _fertig(url: str, scan_id: str, befunde: list[dict[str, Any]]) -> None:
    bericht = {"paket": {"name": "p"}, "befunde": befunde, "hinweise": []}
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE scans SET status = 'fertig', report = :r, finished_at = now() WHERE id = :i"
            ),
            {"r": json.dumps(bericht), "i": scan_id},
        )
    engine.dispose()


def _status(url: str, owner: str, pid: str, fp: str, status: str) -> None:
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO finding_status "
                "(id, owner_id, project_id, fingerprint, status, begruendung) "
                "VALUES (:id, :o, :p, :f, :s, 'Testbegründung')"
            ),
            {"id": str(uuid.uuid4()), "o": owner, "p": pid, "f": fp * 64, "s": status},
        )
    engine.dispose()


def test_open_critical_and_high_findings_come_first(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    ruhig = project(a, "ruhig")
    hoch = project(a, "hoch")
    kritisch = project(a, "kritisch")
    _fertig(_migrated, upload_zip(a, ruhig).json()["id"], [_befund("M", "mittel", "a")])
    _fertig(_migrated, upload_zip(a, hoch).json()["id"], [_befund("H", "hoch", "b")])
    _fertig(
        _migrated,
        upload_zip(a, kritisch).json()["id"],
        [_befund("K", "krit", "c"), _befund("H", "auch-hoch", "d", 2), _befund("N", "n", "e")],
    )
    projekte = a.get("/api/v1/projects").json()
    assert [p["name"] for p in projekte] == ["kritisch", "hoch", "ruhig"]
    assert (projekte[0]["offen_k"], projekte[0]["offen_h"]) == (1, 1)
    assert (projekte[2]["offen_k"], projekte[2]["offen_h"]) == (0, 0)

    offen = a.get("/api/v1/projects/offene-befunde").json()
    assert [(b["projekt"], b["schwere"], b["titel"]) for b in offen] == [
        ("kritisch", "K", "krit"),
        ("hoch", "H", "hoch"),
        ("kritisch", "H", "auch-hoch"),
    ]
    assert offen[0]["datei"] == "SKILL.md" and offen[0]["project_id"] == kritisch


def test_marked_findings_and_running_checks_do_not_count(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    pid = project(a)
    _fertig(
        _migrated,
        upload_zip(a, pid).json()["id"],
        [_befund("K", "akzeptiert", "a"), _befund("H", "offen", "b")],
    )
    owner = a.get("/api/v1/auth/ich").json()["id"]
    _status(_migrated, owner, pid, "a", "akzeptiert")
    upload_zip(a, pid)  # a newer check still waiting: the last finished one counts
    (p,) = a.get("/api/v1/projects").json()
    assert (p["offen_k"], p["offen_h"]) == (0, 1)
    assert p["letzte_pruefung"]["status"] == "wartend"
    assert [b["titel"] for b in a.get("/api/v1/projects/offene-befunde").json()] == ["offen"]


def test_open_findings_stay_with_their_owner(api: Api, _migrated: str) -> None:
    a, b = api.user("anna@example.org"), api.user("bert@example.org")
    _fertig(_migrated, upload_zip(a, project(a)).json()["id"], [_befund("K", "geheim", "a")])
    assert b.get("/api/v1/projects/offene-befunde").json() == []
    assert b.get("/api/v1/projects").json() == []
