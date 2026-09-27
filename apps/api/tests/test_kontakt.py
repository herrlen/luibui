"""Contact form: sends one mail, stores nothing, refuses header injection, bots and floods."""

from email.message import EmailMessage
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from luibui_api.main import create_app
from luibui_api.routes import kontakt

GUT = {
    "name": "Erika Muster",
    "email": "erika@firma.example",
    "nachricht": "Hallo, eine Frage zu luibui.",
}


class FakeSMTP:
    sent: ClassVar[list[EmailMessage]] = []
    fail = False

    def __init__(self, host: str, port: int, timeout: float) -> None:
        if FakeSMTP.fail:
            raise OSError("keine Verbindung")

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *a: Any) -> None:
        pass

    def starttls(self, context: Any) -> None:
        pass

    def login(self, user: str, pw: str) -> None:
        assert pw == "test-passwort"

    def send_message(self, m: EmailMessage) -> None:
        FakeSMTP.sent.append(m)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SMTP_PASSWORD", "test-passwort")
    monkeypatch.setattr(kontakt.smtplib, "SMTP", FakeSMTP)
    FakeSMTP.sent, FakeSMTP.fail = [], False
    kontakt.kontakt_limiter.cache_clear()
    return TestClient(create_app())


def test_message_is_sent_with_reply_to(client: TestClient) -> None:
    r = client.post("/api/v1/kontakt", json=GUT)
    assert r.status_code == 202
    (m,) = FakeSMTP.sent
    assert m["To"] == "hallo@luibui.com"
    assert m["From"] == "luibui Kontaktformular <noreply@luibui.com>"
    assert m["Reply-To"] == "Erika Muster <erika@firma.example>"
    assert "eine Frage zu luibui" in m.get_content()


def test_header_injection_is_impossible(client: TestClient) -> None:
    evil = {**GUT, "name": "X\r\nBcc: opfer@x.example", "email": "a@b.example\r\nBcc: c@d.example"}
    assert client.post("/api/v1/kontakt", json=evil).status_code == 422
    r = client.post("/api/v1/kontakt", json={**GUT, "name": "X\r\nBcc: opfer@x.example"})
    assert r.status_code == 202
    (m,) = FakeSMTP.sent
    assert m["Bcc"] is None
    assert "\n" not in m["Reply-To"]


def test_honeypot_sends_nothing(client: TestClient) -> None:
    r = client.post("/api/v1/kontakt", json={**GUT, "website": "https://spam.example"})
    assert r.status_code == 202
    assert FakeSMTP.sent == []


def test_rate_limit(client: TestClient) -> None:
    codes = [client.post("/api/v1/kontakt", json=GUT).status_code for _ in range(6)]
    assert codes == [202] * 5 + [429]


def test_invalid_input(client: TestClient) -> None:
    assert client.post("/api/v1/kontakt", json={**GUT, "nachricht": "kurz"}).status_code == 422
    assert client.post("/api/v1/kontakt", json={**GUT, "email": "keine"}).status_code == 422


def test_smtp_failure_names_the_address(client: TestClient) -> None:
    FakeSMTP.fail = True
    r = client.post("/api/v1/kontakt", json=GUT)
    assert r.status_code == 503
    assert "hallo@luibui.com" in r.json()["detail"]["text"]


def test_without_smtp_password(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from luibui_api.settings import get_settings

    monkeypatch.delenv("SMTP_PASSWORD")
    get_settings.cache_clear()
    assert client.post("/api/v1/kontakt", json=GUT).status_code == 503
