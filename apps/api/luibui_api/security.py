"""Password hashing, random secrets and TOTP.

Passwords: Argon2id. Session and API tokens: 256-bit random, stored as SHA-256 (decided with Len
on 2026-09-26 — Argon2 on every request would let a few bad requests exhaust the API's memory).
"""

import hashlib
import secrets
import uuid

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from luibui_api.storage import master_key
from luibui_api.storage.crypto import DecryptionError, unwrap_key, wrap_key

PASSWORD_MIN = 12
PASSWORD_MAX = 256
TOKEN_PREFIX = "lb_"  # noqa: S105 - public marker in front of every API token, not a secret

_hasher = PasswordHasher()
# Verified against when the e-mail is unknown, so both cases take the same time.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def new_secret() -> str:
    """256 random bits, URL-safe."""
    return secrets.token_urlsafe(32)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_api_token() -> str:
    return TOKEN_PREFIX + new_secret()


# --- TOTP ------------------------------------------------------------------------------------


def new_totp_secret() -> str:
    return pyotp.random_base32()


def _totp_context(user_id: uuid.UUID) -> str:
    return f"totp:{user_id}"


def encrypt_totp_secret(user_id: uuid.UUID, secret: str) -> bytes:
    return wrap_key(master_key(), secret.encode(), _totp_context(user_id))


def decrypt_totp_secret(user_id: uuid.UUID, encrypted: bytes) -> str | None:
    try:
        return unwrap_key(master_key(), encrypted, _totp_context(user_id)).decode()
    except DecryptionError:
        return None


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="luibui")


def verify_totp(secret: str, code: str) -> bool:
    code = code.strip().replace(" ", "")
    return len(code) == 6 and code.isdigit() and pyotp.TOTP(secret).verify(code, valid_window=1)
