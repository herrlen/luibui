"""Registration, login, logout, the current user and two-factor login (S2-6)."""

import re
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from luibui_api.audit import audit
from luibui_api.auth import CurrentCaller, DbSession, SessionCaller, end_session, start_session
from luibui_api.models import User
from luibui_api.ratelimit import RateLimiter
from luibui_api.security import (
    PASSWORD_MAX,
    PASSWORD_MIN,
    decrypt_totp_secret,
    encrypt_totp_secret,
    hash_password,
    new_totp_secret,
    totp_uri,
    verify_password,
    verify_totp,
)
from luibui_api.settings import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

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


def _ich(user: User) -> Ich:
    return Ich(id=user.id, email=user.email, totp_aktiv=user.totp_confirmed_at is not None)


@router.post("/registrieren", status_code=status.HTTP_201_CREATED)
def registrieren(body: Registrierung, response: Response, db: DbSession) -> Ich:
    user = User(email=body.email, password_hash=hash_password(body.passwort))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Diese E-Mail ist bereits registriert"
        ) from None
    audit(db, user.id, "konto.registriert", "user", user.id)
    start_session(db, response, user)
    db.commit()
    return _ich(user)


@router.post("/anmelden")
def anmelden(body: Anmeldung, request: Request, response: Response, db: DbSession) -> Ich:
    email = body.email.strip().lower()
    client = request.client.host if request.client else "unbekannt"
    keys = (f"email:{email}", f"ip:{client}")
    limiter = login_limiter()
    if limiter.blocked(*keys):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Zu viele Versuche, bitte später erneut"
        )
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if not verify_password(user.password_hash if user else None, body.passwort) or user is None:
        limiter.hit(*keys)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-Mail oder Passwort falsch")
    if user.totp_confirmed_at is not None:
        secret = decrypt_totp_secret(user.id, user.totp_secret_enc or b"")
        if not body.totp:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "totp_erforderlich")
        if secret is None or not verify_totp(secret, body.totp):
            limiter.hit(*keys)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Code falsch")
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
