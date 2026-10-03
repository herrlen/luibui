"""S4-7 part 1 / H02: nightly re-check of published versions. The API queues ordinary scan jobs
for the versions and mails the author about new critical or high findings."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text

from luibui_api import mail
from luibui_api.nachpruefung import auswerten, faellig, lauf, letzter_start, starten

from .conftest import Api
from .test_guthaben import FakeSMTP
from .test_pakete import pruefung

NACHT = datetime(2026, 10, 4, 1, 30, tzinfo=UTC)  # 03:30 in Berlin (summer time)
JETZT = datetime.now(UTC)
"""The database stamps rows with the real time, so the queue tests use it too."""


def befund_mails(post: list[Any]) -> list[Any]:
    return [m for m in post if "Neue Befunde" in m["Subject"]]


@pytest.fixture
def post(api: Api, monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    monkeypatch.setenv("SMTP_PASSWORD", "test")
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)
    FakeSMTP.sent = []
    from luibui_api.settings import get_settings

    get_settings.cache_clear()
    return FakeSMTP.sent


@pytest.fixture
def db(api: Api) -> Any:
    from luibui_api.db import _sessionmaker

    with _sessionmaker()() as session:
        yield session


def sql(url: str, query: str, **params: Any) -> list[Any]:
    engine = create_engine(url)
    with engine.begin() as conn:
        result = conn.execute(text(query), params)
        rows = list(result.all()) if result.returns_rows else []
    engine.dispose()
    return rows


def veroeffentlicht(api: Api, url: str) -> tuple[Any, str]:
    a = api.user("anna@example.org")
    assert a.post("/api/v1/namespaces", json={"name": "anna-tools"}).status_code == 201
    sid = pruefung(a, url)
    befunde = [{"fingerprint": "alt", "schwere": "K", "titel": "Alter Befund", "datei": "x"}]
    sql(url, "UPDATE scans SET report = CAST(:r AS jsonb) WHERE id = :id",
        r=json.dumps({"befunde": befunde, "note": 60}), id=sid)  # fmt: skip
    v = a.post("/api/v1/register/veroeffentlichen", json={"scan_id": sid}).json()
    return a, v["id"]


def test_last_start_is_03_00_berlin() -> None:
    assert letzter_start(NACHT) == datetime(2026, 10, 4, 1, 0, tzinfo=UTC)
    vorher = datetime(2026, 10, 4, 0, 59, tzinfo=UTC)  # 02:59 Berlin
    assert letzter_start(vorher) == datetime(2026, 10, 3, 1, 0, tzinfo=UTC)
    winter = datetime(2026, 12, 1, 2, 30, tzinfo=UTC)  # 03:30 Berlin, winter time
    assert letzter_start(winter) == datetime(2026, 12, 1, 2, 0, tzinfo=UTC)


def test_queues_one_recheck_per_version_and_night(
    api: Api, db: Any, _migrated: str, tmp_path: Path
) -> None:
    a, vid = veroeffentlicht(api, _migrated)
    assert faellig(db, JETZT)
    assert starten(db, JETZT) == 1
    assert not faellig(db, JETZT) and starten(db, JETZT) == 0
    ((sid, project, kind),) = sql(
        _migrated,
        "SELECT s.id, s.project_id, j.kind FROM scans s JOIN jobs j ON j.scan_id = s.id "
        "WHERE s.paketversion_id = :v",
        v=vid,
    )
    assert project is None and kind == "scan"
    assert (tmp_path / "scratch").exists() and any((tmp_path / "scratch").rglob("SKILL.md"))
    assert sid not in {s["id"] for s in a.get("/api/v1/scans").json()}  # not a single check
    assert a.get(f"/api/v1/scans/{sid}").status_code == 200  # the author may open the report


def test_new_critical_findings_are_mailed_once(
    api: Api, db: Any, post: list[Any], _migrated: str
) -> None:
    _, vid = veroeffentlicht(api, _migrated)
    starten(db, JETZT)
    befunde = [
        {"fingerprint": "alt", "schwere": "K", "titel": "Alter Befund", "datei": "x"},
        {
            "fingerprint": "neu",
            "schwere": "H",
            "titel": "Neue Lücke in requests",
            "datei": "requirements.txt",
        },
        {"fingerprint": "klein", "schwere": "N", "titel": "Unwichtig", "datei": "y"},
    ]
    sql(_migrated, "UPDATE scans SET status = 'fertig', report = CAST(:r AS jsonb) "
        "WHERE paketversion_id = :v", r=json.dumps({"befunde": befunde}), v=vid)  # fmt: skip
    assert auswerten(db, JETZT) == 1
    (m,) = befund_mails(post)
    assert m["To"] == "anna@example.org" and "anna-tools/wetter 1.0.0" in m["Subject"]
    inhalt = m.get_content()
    assert "Neue Lücke in requests" in inhalt and "Alter Befund" not in inhalt
    assert "/pruefungen/" in inhalt
    assert auswerten(db, JETZT) == 0 and len(befund_mails(post)) == 1
    assert sql(
        _migrated, "SELECT nachpruefung_neu FROM scans WHERE paketversion_id = :v", v=vid
    ) == [(1,)]


def test_failed_rechecks_and_no_news_send_nothing(
    api: Api, db: Any, post: list[Any], _migrated: str
) -> None:
    _, vid = veroeffentlicht(api, _migrated)
    starten(db, JETZT)
    sql(_migrated, "UPDATE scans SET status = 'fehlgeschlagen' WHERE paketversion_id = :v", v=vid)
    assert auswerten(db, JETZT) == 0 and befund_mails(post) == []
    assert sql(_migrated, "SELECT nachpruefung_ausgewertet_at IS NOT NULL FROM scans "
               "WHERE paketversion_id = :v", v=vid) == [(True,)]  # fmt: skip


def test_withdrawn_versions_are_not_rechecked(api: Api, db: Any, _migrated: str) -> None:
    a, vid = veroeffentlicht(api, _migrated)
    a.post(f"/api/v1/register/versionen/{vid}/zurueckziehen")
    assert not faellig(db, JETZT) and starten(db, JETZT) == 0


def test_a_second_instance_waits_for_the_lock(api: Api, db: Any, _migrated: str) -> None:
    veroeffentlicht(api, _migrated)
    engine = create_engine(_migrated)
    with engine.connect() as andere:
        andere.execute(text("SELECT pg_advisory_lock(7340201)"))
        lauf(db, JETZT)
        assert sql(_migrated, "SELECT count(*) FROM scans WHERE paketversion_id IS NOT NULL") == [
            (0,)
        ]
        andere.execute(text("SELECT pg_advisory_unlock(7340201)"))
    engine.dispose()
    lauf(db, JETZT)
    assert sql(_migrated, "SELECT count(*) FROM scans WHERE paketversion_id IS NOT NULL") == [(1,)]
