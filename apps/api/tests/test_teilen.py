"""S2-12: sharing a report by link. The link is the permission; only its hash is stored."""

import json

from sqlalchemy import create_engine, text

from .conftest import Api
from .test_scans import db_rows, project, upload_zip

BERICHT = {"paket": {"name": "wetter-skill"}, "befunde": [], "hinweise": []}


def fertig(url: str, scan_id: str) -> None:
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE scans SET status = 'fertig', report = :r, finished_at = now() WHERE id = :i"
            ),
            {"r": json.dumps(BERICHT), "i": scan_id},
        )
    engine.dispose()


def test_share_link_shows_the_report_without_login(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    scan = upload_zip(a, project(a)).json()["id"]
    assert a.post(f"/api/v1/scans/{scan}/teilen").status_code == 409  # not finished yet
    fertig(_migrated, scan)
    token = a.post(f"/api/v1/scans/{scan}/teilen").json()["token"]
    assert len(token) >= 40
    anonym = api.client()
    r = anonym.get(f"/api/v1/geteilt/{token}")
    assert r.status_code == 200
    assert r.json()["bericht"]["paket"]["name"] == "wetter-skill"
    assert "anna" not in r.text and "owner" not in r.text
    assert a.get(f"/api/v1/scans/{scan}").json()["geteilt"] is True
    (gespeichert,) = db_rows(
        _migrated, "SELECT share_token_hash FROM scans WHERE share_token_hash IS NOT NULL"
    )[0]
    assert gespeichert != token and len(gespeichert) == 64


def test_new_link_replaces_the_old_one_and_ending_stops_it(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    scan = upload_zip(a, project(a)).json()["id"]
    fertig(_migrated, scan)
    alt = a.post(f"/api/v1/scans/{scan}/teilen").json()["token"]
    neu = a.post(f"/api/v1/scans/{scan}/teilen").json()["token"]
    c = api.client()
    assert c.get(f"/api/v1/geteilt/{alt}").status_code == 404
    assert c.get(f"/api/v1/geteilt/{neu}").status_code == 200
    assert a.delete(f"/api/v1/scans/{scan}/teilen").status_code == 204
    assert c.get(f"/api/v1/geteilt/{neu}").status_code == 404
    assert a.get(f"/api/v1/scans/{scan}").json()["geteilt"] is False


def test_link_dies_with_the_project(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    pid = project(a)
    scan = upload_zip(a, pid).json()["id"]
    fertig(_migrated, scan)
    token = a.post(f"/api/v1/scans/{scan}/teilen").json()["token"]
    assert a.delete(f"/api/v1/projects/{pid}").status_code == 204
    assert api.client().get(f"/api/v1/geteilt/{token}").status_code == 404


def test_malformed_and_unknown_tokens(api: Api) -> None:
    c = api.client()
    for token in ["x", "a" * 43, "../../etc", "%00" * 20]:
        assert c.get(f"/api/v1/geteilt/{token}").status_code == 404
