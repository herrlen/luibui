"""S2-10 and S2-6: data export, account deletion (DSGVO Art. 15, 17, 20) and password reset."""

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any

import pyotp
import pytest

from luibui_api import mail
from luibui_api.routes.auth import reset_limiter

from .conftest import Api
from .test_auth import PW, enable_totp, login
from .test_guthaben import FakePayPal, FakeSMTP, api_bezahlt, bestaetigt, kaufen, pp  # noqa: F401
from .test_scans import blobs, db_rows, project, upload_zip


@pytest.fixture
def post(api: Api, monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    monkeypatch.setenv("SMTP_PASSWORD", "test")
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)
    FakeSMTP.sent = []
    reset_limiter.cache_clear()
    from luibui_api.settings import get_settings

    get_settings.cache_clear()
    return FakeSMTP.sent


def _resets(sent: list[Any]) -> list[Any]:
    return [m for m in sent if "Neues Passwort" in m["Subject"]]


def _link(sent: list[Any]) -> str:
    match = re.search(r"/passwort-neu\?token=([A-Za-z0-9_-]+)", sent[-1].get_content())
    assert match, sent[-1].get_content()
    return match.group(1)


# --- export ------------------------------------------------------------------------------------


def test_export_contains_everything_and_no_secrets(api: Api) -> None:
    a = api.user("anna@example.org")
    pid = project(a)
    assert upload_zip(a, pid).status_code == 202
    token = a.post("/api/v1/tokens", json={"name": "ci"}).json()["token"]
    assert a.post("/api/v1/konto/export", json={"passwort": "falsch"}).status_code == 400
    r = a.post("/api/v1/konto/export", json={"passwort": PW})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert "attachment" in r.headers["content-disposition"]
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    namen = zf.namelist()
    konto = json.loads(zf.read("konto.json"))
    assert konto["konto"]["email"] == "anna@example.org"
    assert [t["name"] for t in konto["api_tokens"]] == ["ci"]
    datei = next(n for n in namen if n.endswith("/dateien/v1/SKILL.md"))
    assert b"geheimer Inhalt" in zf.read(datei)  # stored files come back decrypted
    assert any(n.endswith("/projekt.json") for n in namen)
    alles = b"".join(zf.read(n) for n in namen)
    assert token.encode() not in alles and b"argon2" not in alles and b"secret_hash" not in alles


def test_export_needs_a_session_and_the_second_factor(api: Api) -> None:
    a = api.user("anna@example.org")
    secret = enable_totp(a)
    assert a.post("/api/v1/konto/export", json={"passwort": PW}).status_code == 400
    code = pyotp.TOTP(secret).now()
    assert a.post("/api/v1/konto/export", json={"passwort": PW, "code": code}).status_code == 200
    token = a.post("/api/v1/tokens", json={"name": "ci"}).json()["token"]
    api_host = api.client(base_url="https://api.luibui.com")
    r = api_host.post(
        "/api/v1/konto/export",
        json={"passwort": PW, "code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code in (401, 403)


# --- delete ------------------------------------------------------------------------------------


def test_delete_removes_account_projects_and_files(
    api: Api, tmp_path: Path, _migrated: str
) -> None:
    a, b = api.user("anna@example.org"), api.user("bert@example.org")
    upload_zip(a, project(a))
    upload_zip(b, project(b))
    assert len(blobs(tmp_path)) == 4
    falsch = {"passwort": PW, "bestaetigung": "ja"}
    assert a.post("/api/v1/konto/loeschen", json=falsch).status_code == 400
    r = a.post("/api/v1/konto/loeschen", json={"passwort": PW, "bestaetigung": "LÖSCHEN"})
    assert r.status_code == 204
    assert len(blobs(tmp_path)) == 2  # only B's files are left
    assert db_rows(_migrated, "SELECT count(*) FROM users")[0][0] == 1
    assert db_rows(_migrated, "SELECT count(*) FROM projects")[0][0] == 1
    assert a.get("/api/v1/auth/ich").status_code == 401
    _, r = login(api, "anna@example.org")
    assert r.status_code == 401
    assert b.get("/api/v1/projects").json()[0]["name"] == "wetter"
    aktion = db_rows(
        _migrated, "SELECT action, actor_id FROM audit_log WHERE action = 'konto.geloescht'"
    )
    assert aktion == [("konto.geloescht", None)]


def test_delete_keeps_receipts_without_the_account(
    api_bezahlt: Api,  # noqa: F811
    pp: FakePayPal,  # noqa: F811
    _migrated: str,
) -> None:
    a = bestaetigt(api_bezahlt, "a@luibui.example")
    kaufen(a, pp)
    r = a.post("/api/v1/konto/loeschen", json={"passwort": PW, "bestaetigung": "LÖSCHEN"})
    assert r.status_code == 204
    assert db_rows(_migrated, "SELECT owner_id, belegnummer IS NOT NULL FROM payments") == [
        (None, True)
    ]


# --- password reset ------------------------------------------------------------------------------


def test_reset_answers_the_same_for_unknown_addresses(api: Api, post: list[Any]) -> None:
    api.user("anna@example.org")
    c = api.client()
    bekannt = c.post("/api/v1/auth/passwort-vergessen", json={"email": "anna@example.org"})
    unbekannt = c.post("/api/v1/auth/passwort-vergessen", json={"email": "nie@example.org"})
    assert bekannt.status_code == unbekannt.status_code == 202
    assert bekannt.json() == unbekannt.json()
    assert len(_resets(post)) == 1


def test_reset_sets_the_password_once_and_ends_sessions(api: Api, post: list[Any]) -> None:
    alt = api.user("anna@example.org")
    api.client().post("/api/v1/auth/passwort-vergessen", json={"email": "Anna@Example.org"})
    token = _link(post)
    neu = "ein-ganz-neues-passwort"
    c = api.client()
    assert (
        c.post("/api/v1/auth/passwort-neu", json={"token": token, "passwort": neu}).status_code
        == 200
    )
    assert alt.get("/api/v1/auth/ich").status_code == 401  # every session ended
    _, r = login(api, "anna@example.org")
    assert r.status_code == 401
    _, r = login(api, "anna@example.org", passwort=neu)
    assert r.status_code == 200
    wieder = c.post(
        "/api/v1/auth/passwort-neu", json={"token": token, "passwort": "noch-ein-anderes"}
    )
    assert wieder.status_code == 400


def test_reset_link_and_confirmation_link_are_not_interchangeable(
    api_bezahlt: Api,  # noqa: F811
    post: list[Any],
) -> None:
    api_bezahlt.user("anna@example.org")
    bestaetigung = re.search(r"token=([A-Za-z0-9_-]+)", FakeSMTP.sent[-1].get_content())
    assert bestaetigung
    c = api_bezahlt.client()
    r = c.post(
        "/api/v1/auth/passwort-neu",
        json={"token": bestaetigung.group(1), "passwort": "ein-ganz-neues-passwort"},
    )
    assert r.status_code == 400
    c.post("/api/v1/auth/passwort-vergessen", json={"email": "anna@example.org"})
    assert c.post("/api/v1/auth/bestaetigen", json={"token": _link(post)}).status_code == 400


def test_reset_keeps_the_second_factor(api: Api, post: list[Any]) -> None:
    enable_totp(api.user("anna@example.org"))
    api.client().post("/api/v1/auth/passwort-vergessen", json={"email": "anna@example.org"})
    neu = "ein-ganz-neues-passwort"
    api.client().post("/api/v1/auth/passwort-neu", json={"token": _link(post), "passwort": neu})
    _, r = login(api, "anna@example.org", passwort=neu)
    assert r.status_code == 401 and r.json()["detail"]["code"] == "totp_erforderlich"


def test_reset_requests_are_limited(api: Api, post: list[Any]) -> None:
    api.user("anna@example.org")
    c = api.client()
    for _ in range(5):
        assert (
            c.post(
                "/api/v1/auth/passwort-vergessen", json={"email": "anna@example.org"}
            ).status_code
            == 202
        )
    assert len(_resets(post)) == 3
