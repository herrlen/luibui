"""S2-10 and S2-6: storage, password change and reset, data export, account deletion."""

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


def test_export_is_streamed_and_intact(api: Api, tmp_path: Path) -> None:
    import os

    a = api.user("anna@example.org")
    gross = os.urandom(3 * 1024 * 1024)  # does not compress: the ZIP really carries 3 MB
    files = {"SKILL.md": b"# LUIBUI-TESTFIXTURE Skill\n", "daten/gross.bin": gross}
    assert upload_zip(a, project(a), files).status_code == 202
    with a.stream("POST", "/api/v1/konto/export", json={"passwort": PW}) as r:
        assert r.status_code == 200
        assert "content-length" not in r.headers  # streamed while it is built
        teile = list(r.iter_bytes())
    zf = zipfile.ZipFile(io.BytesIO(b"".join(teile)))
    assert zf.testzip() is None
    datei = next(n for n in zf.namelist() if n.endswith("/dateien/v1/daten/gross.bin"))
    assert zf.read(datei) == gross
    # The export never touches the disk (the scratch only holds the upload for the queued check).
    assert not list((tmp_path / "scratch").rglob("*.zip"))


# --- storage and password change -------------------------------------------------------------


def test_storage_counts_only_own_files(api: Api) -> None:
    a = api.user("anna@example.org")
    b = api.user("bert@example.org")
    leer = a.get("/api/v1/konto/speicher").json()
    assert leer == {"belegt": 0, "grenze": 500 * 1024 * 1024}
    assert upload_zip(a, project(a), {"SKILL.md": b"# Wetter\n" * 100}).status_code == 202
    assert a.get("/api/v1/konto/speicher").json()["belegt"] == 900
    assert b.get("/api/v1/konto/speicher").json()["belegt"] == 0
    assert api.client().get("/api/v1/konto/speicher").status_code == 401


def test_password_change_keeps_this_session_and_ends_the_others(api: Api) -> None:
    a = api.user("anna@example.org")
    zweit, r = login(api, "anna@example.org")  # a second session in another browser
    assert r.status_code == 200
    neu = "ein-ganz-neues-passwort"
    falsch = a.post("/api/v1/konto/passwort", json={"passwort": "falsch-falsch", "neu": neu})
    assert falsch.status_code == 400
    kurz = a.post("/api/v1/konto/passwort", json={"passwort": PW, "neu": "kurz"})
    assert kurz.status_code == 422
    assert a.post("/api/v1/konto/passwort", json={"passwort": PW, "neu": neu}).status_code == 200
    assert a.get("/api/v1/auth/ich").status_code == 200
    assert zweit.get("/api/v1/auth/ich").status_code == 401
    assert login(api, "anna@example.org")[1].status_code == 401
    assert login(api, "anna@example.org", passwort=neu)[1].status_code == 200


def test_password_change_needs_the_second_factor_and_a_session(api: Api) -> None:
    a = api.user("anna@example.org")
    secret = enable_totp(a)
    neu = "ein-ganz-neues-passwort"
    assert a.post("/api/v1/konto/passwort", json={"passwort": PW, "neu": neu}).status_code == 400
    token = a.post("/api/v1/tokens", json={"name": "ci"}).json()["token"]
    r = api.client(base_url="https://api.luibui.com").post(
        "/api/v1/konto/passwort",
        json={"passwort": PW, "neu": neu, "code": pyotp.TOTP(secret).now()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code in (401, 403)
    code = pyotp.TOTP(secret).now()
    ok = a.post("/api/v1/konto/passwort", json={"passwort": PW, "neu": neu, "code": code})
    assert ok.status_code == 200


def test_totp_setup_returns_a_square_qr_code(api: Api) -> None:
    setup = api.user("anna@example.org").post("/api/v1/auth/totp/einrichten").json()
    n = len(setup["qr"])
    assert n >= 21 and all(len(z) == n and set(z) <= {"0", "1"} for z in setup["qr"])
    assert setup["qr"][0].startswith("1111111")  # finder pattern
