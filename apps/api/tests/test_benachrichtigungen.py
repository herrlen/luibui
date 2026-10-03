"""S5-9: notification settings per account; mails for moderation decisions and for the nightly
re-check respect them."""

from datetime import UTC, datetime
from typing import Any

import pytest

from luibui_api import mail

from .conftest import Api
from .test_befund_status import _admin, _befund, _pruefung, _setzen
from .test_guthaben import FakeSMTP


@pytest.fixture
def post(api: Api, monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    monkeypatch.setenv("SMTP_PASSWORD", "test")
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)
    FakeSMTP.sent = []
    from luibui_api.settings import get_settings

    get_settings.cache_clear()
    return FakeSMTP.sent


def entscheidungs_mails(post: list[Any]) -> list[Any]:
    return [m for m in post if "Einspruch" in m["Subject"]]


def test_settings_default_on_and_only_known_kinds(api: Api) -> None:
    a = api.user("anna@example.org")
    d = a.get("/api/v1/konto/benachrichtigungen").json()
    assert d["einstellungen"] == {"nachpruefung": True, "einspruch": True}
    assert set(d["beschreibungen"]) == {"nachpruefung", "einspruch"}
    r = a.post("/api/v1/konto/benachrichtigungen", json={"einspruch": False, "werbung": True})
    assert r.json()["einstellungen"] == {"nachpruefung": True, "einspruch": False}
    b = api.user("bert@example.org")
    assert b.get("/api/v1/konto/benachrichtigungen").json()["einstellungen"]["einspruch"] is True
    token = a.post("/api/v1/tokens", json={"name": "ci"}).json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    api_host = api.client(base_url="https://api.luibui.com")
    assert api_host.post("/api/v1/konto/benachrichtigungen", json={}, headers=h).status_code in (
        401,
        403,
    )


def _entscheiden(api: Api, url: str, a: Any) -> None:
    _, sid = _pruefung(a, url, [_befund("H", "Secret im Code", "a")])
    _setzen(a, sid, "a", "bestritten", "Platzhalter, kein echter Schlüssel.")
    m = _admin(api, url)
    (e,) = m.get("/api/v1/moderation/einsprueche").json()
    r = m.post(
        f"/api/v1/moderation/einsprueche/{e['id']}/entscheidung",
        json={"ergebnis": "fehlalarm", "notiz": "Regel angepasst."},
    )
    assert r.status_code == 200, r.text


def test_the_author_gets_the_moderation_decision(api: Api, post: list[Any], _migrated: str) -> None:
    a = api.user("anna@example.org")
    _entscheiden(api, _migrated, a)
    (m,) = entscheidungs_mails(post)
    inhalt = m.get_content()
    assert m["To"] == "anna@example.org"
    assert "Secret im Code" in inhalt and "Fehlalarm" in inhalt and "Regel angepasst." in inhalt
    assert "Benachrichtigungen ändern" in inhalt


def test_switched_off_means_no_mail(api: Api, post: list[Any], _migrated: str) -> None:
    a = api.user("anna@example.org")
    a.post("/api/v1/konto/benachrichtigungen", json={"einspruch": False})
    _entscheiden(api, _migrated, a)
    assert entscheidungs_mails(post) == []


def test_recheck_mail_respects_the_setting(api: Api, post: list[Any], _migrated: str) -> None:
    from luibui_api.db import _sessionmaker
    from luibui_api.nachpruefung import auswerten, starten

    from .test_nachpruefung import sql, veroeffentlicht

    a, vid = veroeffentlicht(api, _migrated)
    a.post("/api/v1/konto/benachrichtigungen", json={"nachpruefung": False})
    jetzt = datetime.now(UTC)
    with _sessionmaker()() as db:
        starten(db, jetzt)
        befunde = '{"befunde": [{"fingerprint": "neu", "schwere": "K", "titel": "Neu"}]}'
        sql(_migrated, "UPDATE scans SET status = 'fertig', report = CAST(:r AS jsonb) "
            "WHERE paketversion_id = :v", r=befunde, v=vid)  # fmt: skip
        auswerten(db, jetzt)
    assert [m for m in post if "Neue Befunde" in m["Subject"]] == []
