"""Contact form on luibui.com (imprint: second contact channel). Nothing is stored: the message
goes by mail to ``KONTAKT_AN`` and is gone from luibui afterwards. Public like the quick scan,
without cookies; limited per IP (in memory only) and with a honeypot field against bots."""

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from luibui_api.ratelimit import RateLimiter
from luibui_api.routes.auth import _email
from luibui_api.settings import get_settings

router = APIRouter(prefix="/api/v1/kontakt", tags=["kontakt"])
SMTP_TIMEOUT = 15


@lru_cache
def kontakt_limiter() -> RateLimiter:
    return RateLimiter(get_settings().kontakt_pro_ip_und_stunde, 3600)


def _einzeilig(value: str) -> str:
    return " ".join(value.split())


class Nachricht(BaseModel):
    name: str = Field(default="", max_length=100)
    email: str = Field(max_length=320)
    nachricht: str = Field(min_length=10, max_length=5000)
    website: str = Field(default="", max_length=200)
    """Honeypot: hidden in the form, people leave it empty."""

    _mail = field_validator("email")(_email)
    _name = field_validator("name")(_einzeilig)


def senden(n: Nachricht) -> None:
    s = get_settings()
    if s.smtp_password is None or not s.smtp_password.get_secret_value():
        raise OSError("SMTP nicht eingerichtet")
    m = EmailMessage()
    m["From"] = formataddr(("luibui Kontaktformular", s.smtp_user))
    m["To"] = s.kontakt_an
    m["Reply-To"] = formataddr((n.name, n.email)) if n.name else n.email
    m["Subject"] = "luibui: Nachricht über das Kontaktformular"
    m.set_content(
        f"Name: {n.name or '(keine Angabe)'}\nE-Mail: {n.email}\n\n{n.nachricht}\n\n"
        "-- \nGesendet über luibui.com/kontakt. luibui speichert die Nachricht nicht.\n"
    )
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=SMTP_TIMEOUT) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(s.smtp_user, s.smtp_password.get_secret_value())
        smtp.send_message(m)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def absenden(body: Nachricht, request: Request) -> dict[str, str]:
    """A sync route: FastAPI runs it in the thread pool, so the SMTP call never blocks others."""
    ok = {"status": "angenommen"}
    if body.website:
        return ok  # bot: pretend success, send nothing
    client = request.client.host if request.client else "unbekannt"
    limiter = kontakt_limiter()
    if limiter.blocked(f"ip:{client}"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            {"code": "zu_viele_nachrichten", "text": "Zu viele Nachrichten. Bitte später erneut."},
        )
    limiter.hit(f"ip:{client}")
    try:
        senden(body)
    except (OSError, smtplib.SMTPException):
        an = get_settings().kontakt_an
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            {
                "code": "versand_fehlgeschlagen",
                "text": f"Die Nachricht konnte nicht gesendet werden. Bitte schreib an {an}.",
            },
        ) from None
    return ok
