"""Authentication and the central access check (CLAUDE.md rules 9 and 11).

- ``api.luibui.com`` accepts only ``Authorization: Bearer lb_…`` (CLI, CI).
- ``app.luibui.com/api/*`` also accepts the host-only session cookie. State-changing requests with
  the cookie must come from ``APP_ORIGIN`` (CSRF).
- Every resource is loaded through ``get_owned``, which answers 404 for anything the caller does
  not own — never 403, so foreign IDs cannot be probed.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from luibui_api.db import get_session
from luibui_api.errors import fehler
from luibui_api.models import Base, Token, User, UserSession
from luibui_api.security import TOKEN_PREFIX, new_secret, sha256_hex
from luibui_api.settings import get_settings

COOKIE = "__Host-luibui_session"
"""The __Host- prefix makes browsers refuse a Domain attribute: the cookie stays host-only."""
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_TOUCH_AFTER = timedelta(minutes=5)

DbSession = Annotated[Session, Depends(get_session)]


def _now() -> datetime:
    return datetime.now(UTC)


def _unauthorized() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Nicht angemeldet")


@dataclass(frozen=True, slots=True)
class Caller:
    user: User
    via: Literal["session", "token"]
    session_id: uuid.UUID | None = None


# --- sessions --------------------------------------------------------------------------------


def start_session(db: Session, response: Response, user: User) -> None:
    secret = new_secret()
    settings = get_settings()
    expires = _now() + timedelta(days=settings.session_days)
    db.add(UserSession(owner_id=user.id, secret_hash=sha256_hex(secret), expires_at=expires))
    response.set_cookie(
        COOKIE,
        secret,
        max_age=settings.session_days * 86400,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


def end_session(db: Session, response: Response, caller: Caller) -> None:
    if caller.session_id is not None:
        db.execute(delete(UserSession).where(UserSession.id == caller.session_id))
    response.delete_cookie(COOKIE, path="/", secure=get_settings().session_cookie_secure)


def _host(request: Request) -> str:
    return (request.headers.get("host") or "").split(":")[0].lower()


def _check_origin(request: Request) -> None:
    if request.method in _SAFE_METHODS:
        return
    origin = request.headers.get("origin")
    if origin is not None:
        if origin != get_settings().app_origin:
            raise fehler(
                status.HTTP_403_FORBIDDEN, "herkunft_ungueltig", "Ungültige Herkunft der Anfrage"
            )
        return
    if request.headers.get("sec-fetch-site") != "same-origin":
        raise fehler(
            status.HTTP_403_FORBIDDEN, "herkunft_ungueltig", "Ungültige Herkunft der Anfrage"
        )


def _from_token(db: Session, raw: str) -> Caller | None:
    if not raw.startswith(TOKEN_PREFIX):
        return None
    now = _now()
    token = db.scalar(select(Token).where(Token.token_hash == sha256_hex(raw)))
    if token is None or token.revoked_at is not None or token.expires_at <= now:
        return None
    user = db.get(User, token.owner_id)
    if user is None:
        return None
    if token.last_used_at is None or now - token.last_used_at > _TOUCH_AFTER:
        db.execute(update(Token).where(Token.id == token.id).values(last_used_at=now))
        db.commit()
    return Caller(user, "token")


def _from_cookie(db: Session, secret: str) -> Caller | None:
    now = _now()
    sess = db.scalar(select(UserSession).where(UserSession.secret_hash == sha256_hex(secret)))
    if sess is None or sess.expires_at <= now:
        return None
    user = db.get(User, sess.owner_id)
    if user is None:
        return None
    if now - sess.last_seen_at > _TOUCH_AFTER:
        db.execute(update(UserSession).where(UserSession.id == sess.id).values(last_seen_at=now))
        db.commit()
    return Caller(user, "session", sess.id)


def get_caller(request: Request, db: DbSession) -> Caller:
    authorization = request.headers.get("authorization")
    if authorization is not None:
        scheme, _, raw = authorization.partition(" ")
        caller = _from_token(db, raw.strip()) if scheme.lower() == "bearer" else None
        if caller is None:
            raise _unauthorized()
        return caller
    if _host(request) in get_settings().bearer_only_hosts:
        raise _unauthorized()
    secret = request.cookies.get(COOKIE)
    caller = _from_cookie(db, secret) if secret else None
    if caller is None:
        raise _unauthorized()
    _check_origin(request)
    return caller


def get_session_caller(caller: Annotated[Caller, Depends(get_caller)]) -> Caller:
    """For account actions (tokens, 2FA): an API token must not be able to mint more tokens."""
    if caller.via != "session":
        raise fehler(
            status.HTTP_403_FORBIDDEN,
            "browser_anmeldung_noetig",
            "Nur mit Anmeldung im Browser möglich",
        )
    return caller


def require_annahme_offen() -> None:
    """Gate for everything that brings new accounts or package content into the system."""
    if not get_settings().annahme_offen:
        raise fehler(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "nicht_freigeschaltet",
            "luibui ist noch nicht freigeschaltet. Bitte später erneut versuchen.",
        )


AnnahmeOffen = Depends(require_annahme_offen)
CurrentCaller = Annotated[Caller, Depends(get_caller)]
SessionCaller = Annotated[Caller, Depends(get_session_caller)]


def get_owned[M: Base](db: Session, model: type[M], resource_id: uuid.UUID, caller: Caller) -> M:
    """Load a resource of the caller. Missing and foreign resources both answer 404."""
    obj = db.get(model, resource_id)
    if obj is None or getattr(obj, "owner_id", None) != caller.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    return obj
