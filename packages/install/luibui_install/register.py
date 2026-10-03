"""Talking to the register: package info, signature, archive. Every answer is checked before it is
used; the public key is built in, never taken from the server."""

import base64
import hashlib
import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlparse

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

REGISTER = "https://luibui.com"
OEFFENTLICHER_SCHLUESSEL = "YaegLlxn2uvkwY9rLJOR2KBUv7y0oCwQ1HTDgBmQxf0="
"""luibui's Ed25519 key for published versions (luibui.com/api/v1/register/schluessel)."""
TIMEOUT = 30
MAX_ARCHIV = 50 * 1024 * 1024
MAX_JSON = 20 * 1024 * 1024


class InstallError(Exception):
    """Something is wrong; the message is German and safe to print."""


def register_url() -> str:
    url = os.environ.get("LUIBUI_REGISTER_URL", REGISTER).rstrip("/")
    teile = urlparse(url)
    lokal = teile.hostname in ("localhost", "127.0.0.1")
    if teile.scheme != "https" and not (teile.scheme == "http" and lokal):
        raise InstallError("Das Register muss über HTTPS erreichbar sein.")
    return url


def schluessel() -> Ed25519PublicKey:
    wert = os.environ.get("LUIBUI_REGISTER_SCHLUESSEL", OEFFENTLICHER_SCHLUESSEL)
    return Ed25519PublicKey.from_public_bytes(base64.b64decode(wert))


def _holen(pfad: str, grenze: int) -> bytes:
    # https (or http to localhost for tests) is enforced in register_url()
    anfrage = urllib.request.Request(  # noqa: S310
        register_url() + pfad, headers={"User-Agent": "luibui-install/0.1"}
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=TIMEOUT) as antwort:  # noqa: S310
            daten: bytes = antwort.read(grenze + 1)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise InstallError("Paket oder Version nicht gefunden.") from None
        raise InstallError(f"Das Register antwortet mit Fehler {exc.code}.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise InstallError("Das Register ist nicht erreichbar.") from None
    if len(daten) > grenze:
        raise InstallError("Die Antwort des Registers ist zu groß.")
    return daten


@dataclass(frozen=True, slots=True)
class Version:
    paket: str
    version: str
    aussage: dict[str, Any]
    manifest: dict[str, Any]
    archiv: bytes


def name_teilen(angabe: str) -> tuple[str, str, str | None]:
    """``namespace/name`` or ``namespace/name@version``."""
    paket, _, version = angabe.partition("@")
    ns, _, name = paket.lower().partition("/")
    if not ns or not name or "/" in name:
        raise InstallError("Paket bitte als namespace/name angeben, z. B. acme/wetter.")
    return ns, name, version or None


def laden(angabe: str) -> Version:
    ns, name, gewuenscht = name_teilen(angabe)
    try:
        info = json.loads(_holen(f"/api/v1/register/pakete/{quote(ns)}/{quote(name)}", MAX_JSON))
    except ValueError:
        raise InstallError("Antwort des Registers nicht lesbar.") from None
    versionen = [v for v in info.get("versionen", []) if isinstance(v, dict)]
    if gewuenscht:
        v = next((x for x in versionen if x.get("version") == gewuenscht), None)
    else:
        v = next((x for x in versionen if not x.get("zurueckgezogen")), None)
    if v is None and not gewuenscht and versionen:
        raise InstallError("Alle Versionen dieses Pakets wurden vom Autor zurückgezogen.")
    if v is None:
        raise InstallError("Paket oder Version nicht gefunden.")
    if v.get("zurueckgezogen"):
        raise InstallError("Diese Version wurde vom Autor zurückgezogen.")
    aussage_text = str(v.get("aussage", ""))
    try:
        schluessel().verify(base64.b64decode(str(v.get("signatur", ""))), aussage_text.encode())
    except (InvalidSignature, ValueError):
        raise InstallError(
            "Die Signatur stimmt nicht. Das Paket wurde nicht von luibui veröffentlicht oder "
            "unterwegs verändert; nichts installiert."
        ) from None
    aussage = json.loads(aussage_text)
    paket = f"{ns}/{name}"
    if aussage.get("paket") != paket or aussage.get("version") != v.get("version"):
        raise InstallError("Die signierte Aussage passt nicht zu diesem Paket; nichts installiert.")
    groesse = int(aussage.get("archiv_bytes", 0))
    if not 0 < groesse <= MAX_ARCHIV:
        raise InstallError("Das Archiv ist zu groß.")
    archiv = _holen(
        f"/api/v1/register/pakete/{quote(ns)}/{quote(name)}/{quote(aussage['version'])}/archiv.zip",
        groesse,
    )
    if len(archiv) != groesse or hashlib.sha256(archiv).hexdigest() != aussage.get("archiv_sha256"):
        raise InstallError("Das Archiv passt nicht zur signierten Prüfsumme; nichts installiert.")
    manifest = v.get("manifest") if isinstance(v.get("manifest"), dict) else {}
    return Version(paket, str(aussage["version"]), aussage, manifest or {}, archiv)
