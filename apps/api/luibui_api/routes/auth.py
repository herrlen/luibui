"""Registration, login, logout, password reset, the current user and two-factor login (S2-6)."""

import contextlib
import re
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from luibui_api import guthaben, mail
from luibui_api.audit import audit
from luibui_api.auth import (
    AnnahmeOffen,
    CurrentCaller,
    DbSession,
    SessionCaller,
    end_session,
    start_session,
)
from luibui_api.errors import fehler
from luibui_api.models import EmailToken, User, UserSession
from luibui_api.ratelimit import RateLimiter
from luibui_api.security import (
    PASSWORD_MAX,
    PASSWORD_MIN,
    decrypt_totp_secret,
    encrypt_totp_secret,
    hash_password,
    new_secret,
    new_totp_secret,
    sha256_hex,
    totp_uri,
    verify_password,
    verify_totp,
)
from luibui_api.settings import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s.]{2,63}$")
Passwort = Annotated[str, Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)]


@lru_cache
def login_limiter() -> RateLimiter:
    s = get_settings()
    return RateLimiter(s.login_max_attempts, s.login_window_seconds)


def _email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 320 or not _EMAIL.match(value):
        raise ValueError("Keine gültige E-Mail-Adresse")
    return value


class Registrierung(BaseModel):
    email: str = Field(max_length=320)
    passwort: Passwort

    _norm = field_validator("email")(_email)


class Anmeldung(BaseModel):
    email: str = Field(max_length=320)
    passwort: str = Field(max_length=PASSWORD_MAX)
    totp: str | None = Field(default=None, max_length=10)


class Ich(BaseModel):
    id: uuid.UUID
    email: str
    totp_aktiv: bool
    email_bestaetigt: bool
    admin: bool = False
    """Shows the moderation view in the menu; the API checks it again on every admin route."""


def _ich(user: User) -> Ich:
    return Ich(
        id=user.id,
        email=user.email,
        totp_aktiv=user.totp_confirmed_at is not None,
        email_bestaetigt=user.email_verified_at is not None,
        admin=user.is_admin,
    )


# --- e-mail confirmation ---------------------------------------------------------------------

BESTAETIGUNG_STUNDEN = 24


@lru_cache
def bestaetigung_limiter() -> RateLimiter:
    return RateLimiter(3, 3600)


def _bestaetigung_senden(db: DbSession, user: User) -> bool:
    """Create a one-time link and mail it. False if the mail could not be sent."""
    secret = new_secret()
    db.add(
        EmailToken(
            owner_id=user.id,
            secret_hash=sha256_hex(secret),
            zweck="bestaetigung",
            expires_at=datetime.now(UTC) + timedelta(hours=BESTAETIGUNG_STUNDEN),
        )
    )
    db.flush()
    link = f"{get_settings().app_origin}/bestaetigen?token={secret}"
    try:
        mail.senden(
            user.email,
            "luibui: Bitte bestätige deine E-Mail-Adresse",
            "Hallo,\n\nbitte bestätige deine E-Mail-Adresse für luibui mit diesem Link:\n\n"
            f"{link}\n\nDer Link gilt {BESTAETIGUNG_STUNDEN} Stunden und nur einmal. Danach stehen "
            "dir ein Projekt und drei Prüfungen gratis zur Verfügung.\n\n"
            "Hast du dich nicht bei luibui registriert, kannst du diese Mail ignorieren.\n\n"
            "-- \nluibui · luibui.com · Diese Mail wurde automatisch verschickt.\n",
        )
    except mail.MailError:
        return False
    return True


class Bestaetigung(BaseModel):
    token: str = Field(min_length=20, max_length=200)


@router.post("/bestaetigen")
def bestaetigen(body: Bestaetigung, db: DbSession) -> dict[str, bool]:
    """Works without a session: the link may be opened on another device."""
    now = datetime.now(UTC)
    token = db.scalar(
        select(EmailToken)
        .where(EmailToken.secret_hash == sha256_hex(body.token), EmailToken.zweck == "bestaetigung")
        .with_for_update()
    )
    if token is None or token.used_at is not None or token.expires_at < now:
        raise fehler(
            status.HTTP_400_BAD_REQUEST,
            "link_ungueltig",
            "Der Link ist abgelaufen oder wurde schon benutzt. "
            "Fordere in der Übersicht einen neuen an.",
        )
    token.used_at = now
    user = db.get(User, token.owner_id)
    if user is not None and user.email_verified_at is None:
        user.email_verified_at = now
        guthaben.startguthaben(db, user)
        audit(db, user.id, "konto.email_bestaetigt", "user", user.id)
    db.commit()
    return {"bestaetigt": True}


@router.post("/bestaetigung-senden", status_code=status.HTTP_202_ACCEPTED)
def bestaetigung_senden(caller: CurrentCaller, db: DbSession) -> dict[str, bool]:
    user = caller.user
    if user.email_verified_at is not None:
        return {"gesendet": False}
    limiter = bestaetigung_limiter()
    if limiter.blocked(f"user:{user.id}"):
        raise fehler(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "zu_viele_mails",
            "Höchstens drei Mails pro Stunde. Bitte schau auch im Spam-Ordner nach.",
        )
    limiter.hit(f"user:{user.id}")
    gesendet = _bestaetigung_senden(db, user)
    db.commit()
    if not gesendet:
        raise fehler(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "mail_fehlgeschlagen",
            "Die Mail konnte gerade nicht verschickt werden. Bitte später erneut.",
        )
    return {"gesendet": True}


# --- password reset ----------------------------------------------------------------------------

RESET_MINUTEN = 60


@lru_cache
def reset_limiter() -> RateLimiter:
    return RateLimiter(3, 3600)


class PasswortVergessen(BaseModel):
    email: str = Field(max_length=320)


class PasswortNeu(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    passwort: Passwort


@router.post("/passwort-vergessen", status_code=status.HTTP_202_ACCEPTED)
def passwort_vergessen(body: PasswortVergessen, request: Request, db: DbSession) -> dict[str, str]:
    """Always the same answer, whether the account exists or not (no address probing)."""
    antwort = {"hinweis": "Falls es ein Konto mit dieser Adresse gibt, ist eine Mail unterwegs."}
    email = body.email.strip().lower()
    client = request.client.host if request.client else "unbekannt"
    limiter = reset_limiter()
    keys = (f"email:{email}", f"ip:{client}")
    if limiter.blocked(*keys):
        return antwort
    limiter.hit(*keys)
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        return antwort
    secret = new_secret()
    db.add(
        EmailToken(
            owner_id=user.id,
            secret_hash=sha256_hex(secret),
            zweck="passwort",
            expires_at=datetime.now(UTC) + timedelta(minutes=RESET_MINUTEN),
        )
    )
    audit(db, user.id, "konto.passwort_link_angefordert", "user", user.id)
    db.commit()
    link = f"{get_settings().app_origin}/passwort-neu?token={secret}"
    # Same answer when the mail fails; the user can ask again.
    with contextlib.suppress(mail.MailError):
        mail.senden(
            user.email,
            "luibui: Neues Passwort festlegen",
            "Hallo,\n\nfür dein luibui-Konto wurde ein neues Passwort angefordert. Mit diesem Link "
            f"legst du es fest:\n\n{link}\n\nDer Link gilt {RESET_MINUTEN} Minuten und nur "
            "einmal. Danach bist du auf allen Geräten abgemeldet.\n\nHast du das nicht "
            "angefordert, ignoriere diese Mail; dein Passwort bleibt unverändert.\n\n"
            "-- \nluibui · luibui.com · Diese Mail wurde automatisch verschickt.\n",
        )
    return antwort


@router.post("/passwort-neu")
def passwort_neu(body: PasswortNeu, db: DbSession) -> dict[str, bool]:
    """Sets the new password and ends every session. Two-factor login stays on."""
    now = datetime.now(UTC)
    token = db.scalar(
        select(EmailToken)
        .where(EmailToken.secret_hash == sha256_hex(body.token), EmailToken.zweck == "passwort")
        .with_for_update()
    )
    if token is None or token.used_at is not None or token.expires_at < now:
        raise fehler(
            status.HTTP_400_BAD_REQUEST,
            "link_ungueltig",
            "Der Link ist abgelaufen oder wurde schon benutzt. Fordere einen neuen an.",
        )
    token.used_at = now
    user = db.get(User, token.owner_id)
    if user is None:
        raise fehler(status.HTTP_400_BAD_REQUEST, "link_ungueltig", "Der Link ist ungültig.")
    user.password_hash = hash_password(body.passwort)
    db.execute(delete(UserSession).where(UserSession.owner_id == user.id))
    audit(db, user.id, "konto.passwort_geaendert", "user", user.id)
    db.commit()
    return {"geaendert": True}


@router.post("/registrieren", status_code=status.HTTP_201_CREATED, dependencies=[AnnahmeOffen])
def registrieren(body: Registrierung, response: Response, db: DbSession) -> Ich:
    user = User(email=body.email, password_hash=hash_password(body.passwort))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise fehler(
            status.HTTP_409_CONFLICT, "email_vergeben", "Diese E-Mail ist bereits registriert"
        ) from None
    audit(db, user.id, "konto.registriert", "user", user.id)
    start_session(db, response, user)
    _bestaetigung_senden(db, user)  # a failed mail can be requested again from the overview
    db.commit()
    return _ich(user)


@router.post("/anmelden")
def anmelden(body: Anmeldung, request: Request, response: Response, db: DbSession) -> Ich:
    email = body.email.strip().lower()
    client = request.client.host if request.client else "unbekannt"
    keys = (f"email:{email}", f"ip:{client}")
    limiter = login_limiter()
    if limiter.blocked(*keys):
        raise fehler(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "zu_viele_versuche",
            "Zu viele Versuche, bitte später erneut",
        )
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if not verify_password(user.password_hash if user else None, body.passwort) or user is None:
        limiter.hit(*keys)
        raise fehler(
            status.HTTP_401_UNAUTHORIZED, "anmeldung_falsch", "E-Mail oder Passwort falsch"
        )
    if user.totp_confirmed_at is not None:
        secret = decrypt_totp_secret(user.id, user.totp_secret_enc or b"")
        if not body.totp:
            raise fehler(
                status.HTTP_401_UNAUTHORIZED,
                "totp_erforderlich",
                "Bitte den Code aus der App angeben",
            )
        if secret is None or not verify_totp(secret, body.totp):
            limiter.hit(*keys)
            raise fehler(status.HTTP_401_UNAUTHORIZED, "totp_falsch", "Code falsch")
    limiter.reset(f"email:{email}")
    user.last_login_at = datetime.now(UTC)
    audit(db, user.id, "konto.angemeldet", "user", user.id)
    start_session(db, response, user)
    db.commit()
    return _ich(user)


@router.post("/abmelden", status_code=status.HTTP_204_NO_CONTENT)
def abmelden(caller: CurrentCaller, response: Response, db: DbSession) -> None:
    end_session(db, response, caller)
    db.commit()


@router.get("/ich")
def ich(caller: CurrentCaller) -> Ich:
    return _ich(caller.user)


# --- two-factor ------------------------------------------------------------------------------


class TotpEinrichtung(BaseModel):
    secret: str
    uri: str


class TotpCode(BaseModel):
    code: str = Field(max_length=10)


class TotpAus(BaseModel):
    passwort: str = Field(max_length=PASSWORD_MAX)
    code: str = Field(max_length=10)


@router.post("/totp/einrichten")
def totp_einrichten(caller: SessionCaller, db: DbSession) -> TotpEinrichtung:
    """Start (or restart) setup. Takes effect only after ``/totp/bestaetigen``."""
    user = db.merge(caller.user)
    if user.totp_confirmed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Zwei-Faktor-Anmeldung ist bereits aktiv")
    secret = new_totp_secret()
    user.totp_secret_enc = encrypt_totp_secret(user.id, secret)
    db.commit()
    return TotpEinrichtung(secret=secret, uri=totp_uri(secret, user.email))


@router.post("/totp/bestaetigen")
def totp_bestaetigen(body: TotpCode, caller: SessionCaller, db: DbSession) -> Ich:
    user = db.merge(caller.user)
    secret = decrypt_totp_secret(user.id, user.totp_secret_enc) if user.totp_secret_enc else None
    if user.totp_confirmed_at is not None or secret is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Keine Einrichtung offen")
    if not verify_totp(secret, body.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Code falsch")
    user.totp_confirmed_at = datetime.now(UTC)
    audit(db, user.id, "konto.totp_aktiviert", "user", user.id)
    db.commit()
    return _ich(user)


@router.post("/totp/deaktivieren")
def totp_deaktivieren(body: TotpAus, caller: SessionCaller, db: DbSession) -> Ich:
    user = db.merge(caller.user)
    secret = decrypt_totp_secret(user.id, user.totp_secret_enc) if user.totp_secret_enc else None
    if user.totp_confirmed_at is None or secret is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Zwei-Faktor-Anmeldung ist nicht aktiv")
    if not verify_password(user.password_hash, body.passwort) or not verify_totp(secret, body.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passwort oder Code falsch")
    user.totp_secret_enc = None
    user.totp_confirmed_at = None
    audit(db, user.id, "konto.totp_deaktiviert", "user", user.id)
    db.commit()
    return _ich(user)
