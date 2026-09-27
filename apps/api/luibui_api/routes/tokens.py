"""API tokens for CLI and CI (S2-6). The token is shown exactly once, only its hash is stored."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from luibui_api.audit import audit
from luibui_api.auth import DbSession, SessionCaller, get_owned
from luibui_api.models import Token
from luibui_api.security import new_api_token, sha256_hex

router = APIRouter(prefix="/api/v1/tokens", tags=["tokens"])

_PREFIX_LEN = 11  # "lb_" + 8 characters, enough for the owner to recognise a token


class TokenNeu(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    gueltig_tage: int = Field(default=90, ge=1, le=365)


class TokenInfo(BaseModel):
    id: uuid.UUID
    name: str
    prefix: str
    expires_at: datetime
    last_used_at: datetime | None
    created_at: datetime


class TokenErstellt(TokenInfo):
    token: str
    """Shown only in this response."""


def _info(t: Token) -> dict[str, object]:
    return {
        "id": t.id,
        "name": t.name,
        "prefix": t.prefix,
        "expires_at": t.expires_at,
        "last_used_at": t.last_used_at,
        "created_at": t.created_at,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def erstellen(body: TokenNeu, caller: SessionCaller, db: DbSession) -> TokenErstellt:
    raw = new_api_token()
    token = Token(
        owner_id=caller.user.id,
        name=body.name,
        prefix=raw[:_PREFIX_LEN],
        token_hash=sha256_hex(raw),
        expires_at=datetime.now(UTC) + timedelta(days=body.gueltig_tage),
    )
    db.add(token)
    db.flush()
    db.refresh(token)
    audit(db, caller.user.id, "token.erstellt", "token", token.id)
    db.commit()
    return TokenErstellt(**_info(token), token=raw)


@router.get("")
def liste(caller: SessionCaller, db: DbSession) -> list[TokenInfo]:
    rows = db.scalars(
        select(Token)
        .where(Token.owner_id == caller.user.id, Token.revoked_at.is_(None))
        .order_by(Token.created_at.desc())
    )
    return [TokenInfo(**_info(t)) for t in rows]


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def widerrufen(token_id: uuid.UUID, caller: SessionCaller, db: DbSession) -> None:
    token = get_owned(db, Token, token_id, caller)
    if token.revoked_at is None:
        token.revoked_at = datetime.now(UTC)
        audit(db, caller.user.id, "token.widerrufen", "token", token.id)
        db.commit()
