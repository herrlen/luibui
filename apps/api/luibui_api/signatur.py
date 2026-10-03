"""Signatures of published versions (S4-2): luibui signs a canonical JSON statement (package,
version, archive hash, report hash, lights, grade) with its own Ed25519 key. ``luibui install``
checks it against the public key, which the API and luibui.com publish."""

import base64
import binascii
import json
from functools import lru_cache
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from luibui_api.settings import get_settings


class SignaturError(Exception):
    """REGISTER_SIGNING_KEY is not set or not valid."""


def kanonisch(daten: dict[str, Any]) -> bytes:
    """The exact bytes that are signed: sorted keys, no spaces, UTF-8."""
    return json.dumps(daten, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


@lru_cache
def _schluessel(wert: str) -> Ed25519PrivateKey:
    try:
        seed = base64.b64decode(wert, validate=True)
    except binascii.Error:
        raise SignaturError("kein gültiges Base64") from None
    if len(seed) != 32:
        raise SignaturError("muss 32 Byte lang sein")
    return Ed25519PrivateKey.from_private_bytes(seed)


def privater_schluessel() -> Ed25519PrivateKey:
    secret = get_settings().register_signing_key
    if secret is None or not secret.get_secret_value():
        raise SignaturError("nicht gesetzt")
    return _schluessel(secret.get_secret_value())


def oeffentlicher_schluessel() -> str:
    """Raw 32-byte public key, base64."""
    raw = privater_schluessel().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(raw).decode()


def signieren(daten: dict[str, Any]) -> bytes:
    return privater_schluessel().sign(kanonisch(daten))
