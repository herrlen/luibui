"""Expired quick scans are deleted with their findings; everything else stays."""

import uuid

import pytest
from sqlalchemy import Engine, text

from luibui_worker import maintenance

pytestmark = pytest.mark.db


def insert_scan(
    engine: Engine, art: str, expires: str | None, owner: uuid.UUID | None
) -> uuid.UUID:
    with engine.begin() as conn:
        scan_id = conn.execute(
            text(
                "INSERT INTO scans (owner_id, scan_art, pruefumfang, expires_at) VALUES "
                "(:owner, CAST(:art AS scan_art), 'paket', "
                "now() + CAST(:expires AS interval)) "
                "RETURNING id"
            ),
            {"owner": owner, "art": art, "expires": expires},
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO findings (scan_id, rule_id, ebene, schwere, achse, titel, erklaerung, "
                "nachweisgrad, fix, fix_prompt) VALUES (:s, 'LB-B01-x', 'B', 'K', 'sicherheit', "
                "'t', 'e', 'statisch_erkannt', 'f', '')"
            ),
            {"s": scan_id},
        )
    return scan_id


def test_purge(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM scans"))
        owner = conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, 'x') RETURNING id"),
            {"e": f"{uuid.uuid4().hex}@example.invalid"},
        ).scalar_one()
    old = insert_scan(engine, "schnell", "-1 hour", None)
    fresh = insert_scan(engine, "schnell", "6 days", None)
    account = insert_scan(engine, "intensiv", None, owner)
    with engine.begin() as conn:
        assert maintenance.purge_expired_quickscans(conn) == 1
        left = {r[0] for r in conn.execute(text("SELECT id FROM scans"))}
        orphans = conn.execute(
            text("SELECT count(*) FROM findings WHERE scan_id = :s"), {"s": old}
        ).scalar_one()
    assert left == {fresh, account}
    assert orphans == 0


def test_every() -> None:
    every = maintenance.Every(3600)
    assert every.due() and not every.due()
