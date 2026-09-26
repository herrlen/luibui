"""AES-256-GCM for project files (CLAUDE.md rule 10).

Key hierarchy: ``MASTER_KEY`` (ENV) encrypts one data key per project; the data key encrypts the
project's files. Files are encrypted in 1 MiB chunks so large files never sit in memory at once.
Each chunk has its own nonce (random prefix + counter + last-chunk flag), which makes reordering,
dropping or truncating chunks fail authentication.
"""

import os
from collections.abc import Iterator
from typing import IO

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_BYTES = 32
CHUNK = 1024 * 1024
_TAG = 16
_KEY_MAGIC = b"LBK1"
_FILE_MAGIC = b"LBF1"
_PREFIX = 7


class DecryptionError(Exception):
    """Wrong key, tampered or truncated data. The message never contains plaintext."""


def new_data_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def _aad(kind: bytes, context: str) -> bytes:
    return kind + b":" + context.encode()


def wrap_key(master_key: bytes, data_key: bytes, context: str) -> bytes:
    """Encrypt a data key with the master key, bound to ``context`` (the project ID)."""
    nonce = os.urandom(12)
    return _KEY_MAGIC + nonce + AESGCM(master_key).encrypt(nonce, data_key, _aad(b"dk", context))


def unwrap_key(master_key: bytes, wrapped: bytes, context: str) -> bytes:
    if not wrapped.startswith(_KEY_MAGIC):
        raise DecryptionError("unbekanntes Schlüsselformat")
    nonce, ciphertext = wrapped[4:16], wrapped[16:]
    try:
        return AESGCM(master_key).decrypt(nonce, ciphertext, _aad(b"dk", context))
    except InvalidTag:
        raise DecryptionError("Schlüssel passt nicht") from None


def _nonce(prefix: bytes, counter: int, last: bool) -> bytes:
    return prefix + counter.to_bytes(4, "big") + (b"\x01" if last else b"\x00")


def encrypt_stream(data_key: bytes, src: IO[bytes], context: str) -> Iterator[bytes]:
    """Yield the encrypted form of ``src``. ``context`` (the storage key) binds blob to record."""
    aead = AESGCM(data_key)
    prefix = os.urandom(_PREFIX)
    aad = _aad(b"file", context)
    yield _FILE_MAGIC + prefix
    counter = 0
    current = src.read(CHUNK)
    while True:
        following = src.read(CHUNK) if current else b""
        last = not following
        yield aead.encrypt(_nonce(prefix, counter, last), current, aad)
        if last:
            return
        counter += 1
        current = following


def decrypt_stream(data_key: bytes, src: IO[bytes], context: str) -> Iterator[bytes]:
    """Yield plaintext chunks. Raises ``DecryptionError`` on any tampering, even at the end."""
    header = src.read(len(_FILE_MAGIC) + _PREFIX)
    if len(header) != len(_FILE_MAGIC) + _PREFIX or not header.startswith(_FILE_MAGIC):
        raise DecryptionError("unbekanntes Dateiformat")
    prefix = header[len(_FILE_MAGIC) :]
    aead = AESGCM(data_key)
    aad = _aad(b"file", context)
    counter = 0
    current = src.read(CHUNK + _TAG)
    if not current:
        raise DecryptionError("Datei abgeschnitten")
    while True:
        following = src.read(CHUNK + _TAG)
        last = not following
        try:
            yield aead.decrypt(_nonce(prefix, counter, last), current, aad)
        except InvalidTag:
            raise DecryptionError("Daten verändert oder abgeschnitten") from None
        if last:
            return
        counter += 1
        current = following
