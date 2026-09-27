"""E-mail confirmation, credits, PayPal purchase (faked) and isolation between users."""

import re
from email.message import EmailMessage
from typing import Any, ClassVar

import pytest
from sqlalchemy import create_engine, text

from luibui_api import mail, paypal

from .conftest import Api

pytestmark = pytest.mark.db


class FakeSMTP:
    sent: ClassVar[list[EmailMessage]] = []

    def __init__(self, *a: Any, **k: Any) -> None:
        pass

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *a: Any) -> None:
        pass

    def starttls(self, context: Any) -> None:
        pass

    def login(self, user: str, pw: str) -> None:
        pass

    def send_message(self, m: EmailMessage) -> None:
        FakeSMTP.sent.append(m)


class FakePayPal:
    """Orders and captures in memory. ``bezahlt_cent`` lets a test pay a different amount."""

    def __init__(self) -> None:
        self.orders: dict[str, int] = {}
        self.bezahlt_cent: int | None = None
        self.captures = 0

    def bestellung_anlegen(
        self, betrag_cent: int, beschreibung: str, referenz: str, rueckkehr: str, abbruch: str
    ) -> tuple[str, str]:
        order_id = f"ORDER{len(self.orders) + 1}"
        self.orders[order_id] = betrag_cent
        assert rueckkehr.startswith("https://app.luibui.com/guthaben/zurueck?weiter=")
        return order_id, f"https://www.sandbox.paypal.com/checkoutnow?token={order_id}"

    def erfassen(self, order_id: str) -> dict[str, Any]:
        self.captures += 1
        cent = self.bezahlt_cent if self.bezahlt_cent is not None else self.orders[order_id]
        value = f"{cent // 100}.{cent % 100:02d}"
        return {
            "status": "COMPLETED",
            "purchase_units": [
                {
                    "payments": {
                        "captures": [
                            {
                                "id": f"CAP-{order_id}",
                                "status": "COMPLETED",
                                "amount": {"currency_code": "EUR", "value": value},
                            }
                        ]
                    }
                }
            ],
        }


@pytest.fixture
def pp(monkeypatch: pytest.MonkeyPatch) -> FakePayPal:
    fake = FakePayPal()
    monkeypatch.setattr(paypal, "bestellung_anlegen", fake.bestellung_anlegen)
    monkeypatch.setattr(paypal, "erfassen", fake.erfassen)
    return fake


@pytest.fixture
def api_bezahlt(api: Api, monkeypatch: pytest.MonkeyPatch) -> Api:
    """Confirmation required, PayPal configured, mails caught."""
    from luibui_api.routes.auth import bestaetigung_limiter
    from luibui_api.settings import get_settings

    monkeypatch.setenv("EMAIL_BESTAETIGUNG_PFLICHT", "true")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "test-id")
    monkeypatch.setenv("PAYPAL_SECRET", "test-secret")
    monkeypatch.setenv("SMTP_PASSWORD", "test")
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)
    FakeSMTP.sent = []
    bestaetigung_limiter.cache_clear()
    get_settings.cache_clear()
    return api


def link_token() -> str:
    body = FakeSMTP.sent[-1].get_content()
    match = re.search(r"/bestaetigen\?token=([A-Za-z0-9_-]+)", body)
    assert match, body
    return match.group(1)


def bestaetigt(api: Api, email: str):  # type: ignore[no-untyped-def]
    c = api.user(email)
    assert c.post("/api/v1/auth/bestaetigen", json={"token": link_token()}).status_code == 200
    return c


def einzel(c):  # type: ignore[no-untyped-def]
    return c.post(
        "/api/v1/scans", data={"art": "datei"}, files={"dateien": ("SKILL.md", b"# Hallo\n")}
    )


def done(url: str) -> None:
    with create_engine(url).begin() as conn:
        conn.execute(text("UPDATE scans SET status = 'fertig'"))


# --- confirmation ----------------------------------------------------------------------------


def test_registration_sends_a_link_and_checks_need_it(api_bezahlt: Api) -> None:
    c = api_bezahlt.user("a@luibui.example")
    (m,) = FakeSMTP.sent
    assert m["To"] == "a@luibui.example"
    assert c.get("/api/v1/auth/ich").json()["email_bestaetigt"] is False
    r = einzel(c)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "email_unbestaetigt"
    assert c.post("/api/v1/auth/bestaetigen", json={"token": link_token()}).status_code == 200
    assert c.get("/api/v1/auth/ich").json()["email_bestaetigt"] is True
    assert c.get("/api/v1/guthaben").json()["stand"] == 3


def test_link_works_once_and_start_credit_only_once(api_bezahlt: Api) -> None:
    c = api_bezahlt.user("a@luibui.example")
    token = link_token()
    assert c.post("/api/v1/auth/bestaetigen", json={"token": token}).status_code == 200
    r = c.post("/api/v1/auth/bestaetigen", json={"token": token})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "link_ungueltig"
    assert c.get("/api/v1/guthaben").json()["stand"] == 3


def test_expired_and_wrong_links(api_bezahlt: Api, _migrated: str) -> None:
    c = api_bezahlt.user("a@luibui.example")
    token = link_token()
    with create_engine(_migrated).begin() as conn:
        conn.execute(text("UPDATE email_tokens SET expires_at = now() - interval '1 minute'"))
    assert c.post("/api/v1/auth/bestaetigen", json={"token": token}).status_code == 400
    assert c.post("/api/v1/auth/bestaetigen", json={"token": "x" * 43}).status_code == 400


def test_resend_is_limited(api_bezahlt: Api) -> None:
    c = api_bezahlt.user("a@luibui.example")
    codes = [c.post("/api/v1/auth/bestaetigung-senden").status_code for _ in range(4)]
    assert codes == [202, 202, 202, 429]


# --- credits ---------------------------------------------------------------------------------


def test_three_free_checks_then_402(api_bezahlt: Api) -> None:
    c = bestaetigt(api_bezahlt, "a@luibui.example")
    assert [einzel(c).status_code for _ in range(3)] == [202, 202, 202]
    r = einzel(c)
    assert r.status_code == 402
    detail = r.json()["detail"]
    assert detail["code"] == "guthaben_leer"
    assert [p["id"] for p in detail["pakete"]] == ["p10", "p25"]
    assert c.get("/api/v1/guthaben").json()["stand"] == 0


def test_second_project_needs_a_purchase(api_bezahlt: Api, pp: FakePayPal) -> None:
    c = bestaetigt(api_bezahlt, "a@luibui.example")
    assert c.post("/api/v1/projects", json={"name": "eins", "typ": "skill"}).status_code == 201
    r = c.post("/api/v1/projects", json={"name": "zwei", "typ": "skill"})
    assert r.status_code == 402 and r.json()["detail"]["code"] == "projekt_limit"
    kaufen(c, pp)
    assert c.post("/api/v1/projects", json={"name": "zwei", "typ": "skill"}).status_code == 201


def test_failed_check_is_booked_back(api_bezahlt: Api, _migrated: str) -> None:
    from luibui_worker.results import mark_failed

    c = bestaetigt(api_bezahlt, "a@luibui.example")
    sid = einzel(c).json()["id"]
    assert c.get("/api/v1/guthaben").json()["stand"] == 2
    engine = create_engine(_migrated)
    for _ in range(2):  # twice: the refund happens once
        with engine.begin() as conn:
            mark_failed(conn, __import__("uuid").UUID(sid), "Testfehler")
    assert c.get("/api/v1/guthaben").json()["stand"] == 3


def test_rejected_upload_costs_nothing(api_bezahlt: Api) -> None:
    c = bestaetigt(api_bezahlt, "a@luibui.example")
    r = c.post("/api/v1/scans", data={"art": "zip"}, files={"dateien": ("x.zip", b"kein zip")})
    assert r.status_code == 422
    assert c.get("/api/v1/guthaben").json()["stand"] == 3


def test_without_paypal_there_are_no_limits(api: Api) -> None:
    c = api.user("a@luibui.example")
    assert [einzel(c).status_code for _ in range(4)] == [202] * 4
    assert c.post("/api/v1/projects", json={"name": "eins", "typ": "skill"}).status_code == 201
    assert c.post("/api/v1/projects", json={"name": "zwei", "typ": "skill"}).status_code == 201
    assert c.get("/api/v1/guthaben").json()["aktiv"] is False


# --- purchase --------------------------------------------------------------------------------


def kaufen(c, pp: FakePayPal, paket: str = "p10") -> dict[str, Any]:  # type: ignore[no-untyped-def]
    r = c.post(
        "/api/v1/guthaben/kaufen",
        json={"paket": paket, "zustimmung": True, "kenntnis": True, "weiter": "/projekte"},
    )
    assert r.status_code == 200, r.text
    order_id = r.json()["url"].rsplit("=", 1)[1]
    r = c.post("/api/v1/guthaben/bestaetigen", json={"order_id": order_id})
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def test_purchase_credits_once_and_makes_a_receipt(api_bezahlt: Api, pp: FakePayPal) -> None:
    c = bestaetigt(api_bezahlt, "a@luibui.example")
    assert kaufen(c, pp) == {"bezahlt": True, "stand": 13}
    order_id = next(iter(pp.orders))
    again = c.post("/api/v1/guthaben/bestaetigen", json={"order_id": order_id}).json()
    assert again == {"bezahlt": True, "stand": 13}
    assert pp.captures == 1
    (k,) = c.get("/api/v1/guthaben").json()["kaeufe"]
    beleg = c.get(f"/api/v1/guthaben/belege/{k['id']}").json()
    assert (beleg["betrag_cent"], beleg["belegnummer"] > 0) == (490, True)
    assert beleg["paypal_transaktion"] == f"CAP-{order_id}"


def test_wrong_amount_credits_nothing(api_bezahlt: Api, pp: FakePayPal) -> None:
    c = bestaetigt(api_bezahlt, "a@luibui.example")
    pp.bezahlt_cent = 1
    assert kaufen(c, pp) == {"bezahlt": False, "stand": 3}


def test_purchase_needs_both_declarations(api_bezahlt: Api, pp: FakePayPal) -> None:
    c = bestaetigt(api_bezahlt, "a@luibui.example")
    r = c.post(
        "/api/v1/guthaben/kaufen", json={"paket": "p10", "zustimmung": True, "kenntnis": False}
    )
    assert r.status_code == 422 and r.json()["detail"]["code"] == "zustimmung_fehlt"
    assert pp.orders == {}


def test_return_path_cannot_leave_the_app(
    api_bezahlt: Api, pp: FakePayPal, monkeypatch: pytest.MonkeyPatch
) -> None:
    c = bestaetigt(api_bezahlt, "a@luibui.example")
    seen: list[str] = []
    orig = pp.bestellung_anlegen

    def spy(*a: Any) -> tuple[str, str]:
        seen.append(a[3])
        return orig(*a)

    monkeypatch.setattr(paypal, "bestellung_anlegen", spy)
    for weiter in ("//boese.example", "https://boese.example", "/\\boese.example"):
        c.post(
            "/api/v1/guthaben/kaufen",
            json={"paket": "p10", "zustimmung": True, "kenntnis": True, "weiter": weiter},
        )
    assert all(u.endswith("weiter=/") for u in seen), seen


def test_b_cannot_confirm_or_read_a_purchase_of_a(api_bezahlt: Api, pp: FakePayPal) -> None:
    a = bestaetigt(api_bezahlt, "a@luibui.example")
    b = bestaetigt(api_bezahlt, "b@luibui.example")
    r = a.post(
        "/api/v1/guthaben/kaufen", json={"paket": "p25", "zustimmung": True, "kenntnis": True}
    )
    order_id = r.json()["url"].rsplit("=", 1)[1]
    assert b.post("/api/v1/guthaben/bestaetigen", json={"order_id": order_id}).status_code == 404
    assert b.get("/api/v1/guthaben").json()["stand"] == 3
    assert a.post("/api/v1/guthaben/bestaetigen", json={"order_id": order_id}).json()["stand"] == 28
    (k,) = a.get("/api/v1/guthaben").json()["kaeufe"]
    assert b.get(f"/api/v1/guthaben/belege/{k['id']}").status_code == 404


def test_webhook_without_valid_signature_credits_nothing(api_bezahlt: Api, pp: FakePayPal) -> None:
    a = bestaetigt(api_bezahlt, "a@luibui.example")
    r = a.post(
        "/api/v1/guthaben/kaufen", json={"paket": "p10", "zustimmung": True, "kenntnis": True}
    )
    order_id = r.json()["url"].rsplit("=", 1)[1]
    anon = api_bezahlt.client()
    event = {"event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": order_id}}
    assert anon.post("/api/v1/paypal/webhook", json=event).json() == {"verarbeitet": False}
    assert a.get("/api/v1/guthaben").json()["stand"] == 3
