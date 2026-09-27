"""S2-6: registration, login, sessions, TOTP, API tokens and the owner check."""

import pyotp
import pytest
from sqlalchemy import create_engine, text

from luibui_api.auth import COOKIE

from .conftest import Api

pytestmark = pytest.mark.db

PW = "ein-langes-passwort"


def login(api: Api, email: str, passwort: str = PW, **extra: str):  # type: ignore[no-untyped-def]
    c = api.client()
    return c, c.post("/api/v1/auth/anmelden", json={"email": email, "passwort": passwort, **extra})


# --- registration and login ------------------------------------------------------------------


def test_register_sets_host_only_cookie(api: Api) -> None:
    c = api.client()
    r = c.post("/api/v1/auth/registrieren", json={"email": " Anna@Example.org ", "passwort": PW})
    assert r.status_code == 201
    assert r.json()["email"] == "anna@example.org"
    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    assert "Domain" not in cookie and "domain" not in cookie
    for attr in ("HttpOnly", "Secure", "Path=/", "SameSite=lax"):
        assert attr in cookie
    assert c.get("/api/v1/auth/ich").json()["email"] == "anna@example.org"


@pytest.mark.parametrize(
    "body",
    [
        {"email": "anna@example.org", "passwort": "kurz"},
        {"email": "kein-at-zeichen", "passwort": PW},
        {"email": "a@b", "passwort": PW},
        {"email": "anna@example.org", "passwort": "x" * 257},
    ],
)
def test_register_validation(api: Api, body: dict[str, str]) -> None:
    assert api.client().post("/api/v1/auth/registrieren", json=body).status_code == 422


def test_duplicate_email_ignores_case(api: Api) -> None:
    api.user("anna@example.org")
    r = api.client().post(
        "/api/v1/auth/registrieren", json={"email": "ANNA@example.org", "passwort": PW}
    )
    assert r.status_code == 409


def test_password_is_stored_as_argon2(api: Api, _migrated: str) -> None:
    api.user("anna@example.org")
    engine = create_engine(_migrated)
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT password_hash FROM users")).scalar_one()
        session_hash = conn.execute(text("SELECT secret_hash FROM sessions")).scalar_one()
    engine.dispose()
    assert stored.startswith("$argon2id$")
    assert PW not in stored
    assert len(session_hash) == 64


def test_login_logout(api: Api) -> None:
    api.user("anna@example.org")
    c, r = login(api, "ANNA@example.org")
    assert r.status_code == 200
    assert c.get("/api/v1/auth/ich").status_code == 200
    assert c.post("/api/v1/auth/abmelden").status_code == 204
    assert c.get("/api/v1/auth/ich").status_code == 401


def test_logout_invalidates_the_session_server_side(api: Api) -> None:
    c = api.user("anna@example.org")
    secret = c.cookies[COOKIE]
    c.post("/api/v1/auth/abmelden")
    replay = api.client()
    replay.cookies.set(COOKIE, secret)
    assert replay.get("/api/v1/auth/ich").status_code == 401


def test_wrong_password_and_unknown_email_look_the_same(api: Api) -> None:
    api.user("anna@example.org")
    _, wrong = login(api, "anna@example.org", "falsches-passwort")
    _, unknown = login(api, "niemand@example.org")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_login_rate_limit(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    api.user("anna@example.org")
    for _ in range(10):
        assert login(api, "anna@example.org", "falsches-passwort")[1].status_code == 401
    assert login(api, "anna@example.org")[1].status_code == 429


def test_no_session_no_access(api: Api) -> None:
    assert api.client().get("/api/v1/auth/ich").status_code == 401


def test_forged_cookie(api: Api) -> None:
    c = api.client()
    c.cookies.set(COOKIE, "ausgedacht")
    assert c.get("/api/v1/auth/ich").status_code == 401


# --- CSRF and hosts --------------------------------------------------------------------------


def test_cookie_post_from_foreign_origin_is_refused(api: Api) -> None:
    c = api.user("anna@example.org")
    r = c.post("/api/v1/tokens", json={"name": "x"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_cookie_post_without_origin_needs_same_origin_fetch(api: Api) -> None:
    c = api.user("anna@example.org")
    del c.headers["Origin"]
    assert c.post("/api/v1/tokens", json={"name": "x"}).status_code == 403
    r = c.post("/api/v1/tokens", json={"name": "x"}, headers={"Sec-Fetch-Site": "same-origin"})
    assert r.status_code == 201


def test_api_host_ignores_cookies(api: Api) -> None:
    c = api.user("anna@example.org")
    same = api.client()
    same.cookies.set(COOKIE, c.cookies[COOKIE])
    assert same.get("/api/v1/auth/ich").status_code == 200  # the cookie itself is valid
    other = api.client("https://api.luibui.com")
    other.cookies.set(COOKIE, c.cookies[COOKIE])
    assert other.get("/api/v1/auth/ich").status_code == 401


# --- API tokens ------------------------------------------------------------------------------


def new_token(c, name: str = "ci") -> dict[str, str]:  # type: ignore[no-untyped-def]
    r = c.post("/api/v1/tokens", json={"name": name, "gueltig_tage": 30})
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


def test_token_works_on_api_host(api: Api) -> None:
    c = api.user("anna@example.org")
    tok = new_token(c)
    assert tok["token"].startswith("lb_") and tok["prefix"] == tok["token"][:11]
    cli = api.client("https://api.luibui.com")
    r = cli.get("/api/v1/auth/ich", headers={"Authorization": f"Bearer {tok['token']}"})
    assert r.status_code == 200
    assert r.json()["email"] == "anna@example.org"


def test_token_is_shown_once_and_stored_hashed(api: Api, _migrated: str) -> None:
    c = api.user("anna@example.org")
    tok = new_token(c)
    assert "token" not in c.get("/api/v1/tokens").json()[0]
    engine = create_engine(_migrated)
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT token_hash FROM tokens")).scalar_one()
    engine.dispose()
    assert tok["token"] not in stored and len(stored) == 64


def test_revoked_and_expired_tokens(api: Api, _migrated: str) -> None:
    c = api.user("anna@example.org")
    a, b = new_token(c, "a"), new_token(c, "b")
    assert c.delete(f"/api/v1/tokens/{a['id']}").status_code == 204
    engine = create_engine(_migrated)
    with engine.begin() as conn:
        conn.execute(text("UPDATE tokens SET expires_at = now() - interval '1 second'"))
    engine.dispose()
    cli = api.client("https://api.luibui.com")
    for t in (a, b):
        r = cli.get("/api/v1/auth/ich", headers={"Authorization": f"Bearer {t['token']}"})
        assert r.status_code == 401


@pytest.mark.parametrize("header", ["Bearer lb_ausgedacht", "Bearer ", "Basic abc", "lb_x"])
def test_bad_authorization_header(api: Api, header: str) -> None:
    c = api.user("anna@example.org")
    assert c.get("/api/v1/auth/ich", headers={"Authorization": header}).status_code == 401


def test_token_cannot_manage_tokens(api: Api) -> None:
    tok = new_token(api.user("anna@example.org"))
    cli = api.client("https://api.luibui.com")
    headers = {"Authorization": f"Bearer {tok['token']}"}
    assert cli.post("/api/v1/tokens", json={"name": "x"}, headers=headers).status_code == 403
    assert cli.get("/api/v1/tokens", headers=headers).status_code == 403


# --- rule 9: user B never reaches user A's data ----------------------------------------------


def test_b_cannot_see_or_revoke_a_tokens(api: Api) -> None:
    a = api.user("anna@example.org")
    b = api.user("bert@example.org")
    tok = new_token(a)
    assert b.get("/api/v1/tokens").json() == []
    assert b.delete(f"/api/v1/tokens/{tok['id']}").status_code == 404
    assert len(a.get("/api/v1/tokens").json()) == 1
    cli = api.client("https://api.luibui.com")
    r = cli.get("/api/v1/auth/ich", headers={"Authorization": f"Bearer {tok['token']}"})
    assert r.json()["email"] == "anna@example.org"


def test_unknown_id_is_404_too(api: Api) -> None:
    c = api.user("anna@example.org")
    assert c.delete("/api/v1/tokens/00000000-0000-4000-8000-000000000000").status_code == 404
    assert c.delete("/api/v1/tokens/keine-uuid").status_code == 422


# --- TOTP ------------------------------------------------------------------------------------


def enable_totp(c) -> str:  # type: ignore[no-untyped-def]
    setup = c.post("/api/v1/auth/totp/einrichten").json()
    assert setup["uri"].startswith("otpauth://totp/luibui:")
    code = pyotp.TOTP(setup["secret"]).now()
    assert c.post("/api/v1/auth/totp/bestaetigen", json={"code": code}).json()["totp_aktiv"]
    return setup["secret"]  # type: ignore[no-any-return]


def test_totp_login(api: Api) -> None:
    secret = enable_totp(api.user("anna@example.org"))
    _, r = login(api, "anna@example.org")
    assert r.status_code == 401 and r.json()["detail"]["code"] == "totp_erforderlich"
    _, r = login(api, "anna@example.org", totp="000000")
    assert r.status_code == 401
    c, r = login(api, "anna@example.org", totp=pyotp.TOTP(secret).now())
    assert r.status_code == 200
    assert c.get("/api/v1/auth/ich").json()["totp_aktiv"]


def test_totp_needs_confirmation(api: Api) -> None:
    c = api.user("anna@example.org")
    c.post("/api/v1/auth/totp/einrichten")
    assert c.post("/api/v1/auth/totp/bestaetigen", json={"code": "123456"}).status_code == 400
    _, r = login(api, "anna@example.org")
    assert r.status_code == 200  # setup not confirmed, so no second factor yet


def test_totp_secret_is_encrypted(api: Api, _migrated: str) -> None:
    secret = enable_totp(api.user("anna@example.org"))
    engine = create_engine(_migrated)
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT totp_secret_enc FROM users")).scalar_one()
    engine.dispose()
    assert secret.encode() not in bytes(stored)


def test_totp_disable_needs_password_and_code(api: Api) -> None:
    c = api.user("anna@example.org")
    secret = enable_totp(c)
    code = pyotp.TOTP(secret).now()
    bad = c.post("/api/v1/auth/totp/deaktivieren", json={"passwort": "falsch", "code": code})
    assert bad.status_code == 400
    ok = c.post("/api/v1/auth/totp/deaktivieren", json={"passwort": PW, "code": code})
    assert ok.status_code == 200 and not ok.json()["totp_aktiv"]


def test_audit_log_has_no_secrets(api: Api, _migrated: str) -> None:
    c = api.user("anna@example.org")
    tok = new_token(c)
    engine = create_engine(_migrated)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT action, meta::text FROM audit_log")).all()
    engine.dispose()
    actions = {r[0] for r in rows}
    assert {"konto.registriert", "token.erstellt"} <= actions
    dump = repr(rows)
    assert tok["token"] not in dump and PW not in dump


def test_intake_is_closed_by_default(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    """Until the worker is isolated, nothing new may come in — but existing accounts work."""
    c = api.user("anna@example.org")
    pid = c.post("/api/v1/projects", json={"name": "p", "typ": "skill"}).json()["id"]
    monkeypatch.delenv("ANNAHME_OFFEN")
    from luibui_api.settings import get_settings

    get_settings.cache_clear()
    new = api.client().post(
        "/api/v1/auth/registrieren", json={"email": "neu@example.org", "passwort": PW}
    )
    assert new.status_code == 503
    upload = c.post(
        f"/api/v1/projects/{pid}/scans", data={"art": "text", "text": "x"}, files={"x": ("", b"")}
    )
    assert upload.status_code == 503
    quick = api.client().post("/api/v1/quickscans", json={"git_url": "https://github.com/a/b"})
    assert quick.status_code == 503
    assert login(api, "anna@example.org")[1].status_code == 200
    assert c.get("/api/v1/auth/ich").status_code == 200


def test_error_format_is_uniform_and_never_echoes_input(api: Api) -> None:
    c = api.client()
    wrong = c.post(
        "/api/v1/auth/anmelden", json={"email": "x@example.org", "passwort": "geheim-123"}
    )
    assert wrong.json() == {
        "detail": {"code": "anmeldung_falsch", "text": "E-Mail oder Passwort falsch"}
    }
    invalid = c.post("/api/v1/auth/registrieren", json={"email": "x", "passwort": "kurz-geheim"})
    assert invalid.status_code == 422
    body = invalid.json()["detail"]
    assert body["code"] == "ungueltige_eingabe" and set(body["felder"]) == {"email", "passwort"}
    assert "kurz-geheim" not in invalid.text
    assert c.get("/api/v1/auth/ich").json()["detail"]["code"] == "nicht_angemeldet"
    assert c.get("/api/auth/ich").status_code == 404  # only /api/v1 exists
