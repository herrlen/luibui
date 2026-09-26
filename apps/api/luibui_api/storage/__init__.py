"""The only way project files are written or read (CLAUDE.md rule 10).

AES-256-GCM with one data key per project, encrypted with ``MASTER_KEY``. Never plaintext on the
volume, never file contents in logs.
"""

import base64
import binascii
import uuid
from functools import lru_cache

from luibui_api.settings import get_settings
from luibui_api.storage.blobs import BlobStore, new_storage_key
from luibui_api.storage.crypto import (
    KEY_BYTES,
    DecryptionError,
    new_data_key,
    unwrap_key,
    wrap_key,
)

__all__ = [
    "BlobStore",
    "DecryptionError",
    "blob_store",
    "master_key",
    "new_storage_key",
    "project_data_key",
]


def parse_master_key(value: str) -> bytes:
    """``MASTER_KEY`` is 32 random bytes, base64-encoded (``openssl rand -base64 32``)."""
    try:
        key = base64.b64decode(value, validate=True)
    except binascii.Error:
        raise ValueError("MASTER_KEY ist kein gültiges Base64") from None
    if len(key) != KEY_BYTES:
        raise ValueError(f"MASTER_KEY muss {KEY_BYTES} Byte lang sein")
    return key


def master_key() -> bytes:
    secret = get_settings().master_key
    if secret is None:
        raise RuntimeError("MASTER_KEY ist nicht gesetzt")
    return parse_master_key(secret.get_secret_value())


@lru_cache
def blob_store() -> BlobStore:
    return BlobStore(get_settings().storage_root)


def project_data_key(project_id: uuid.UUID, data_key_enc: bytes | None) -> tuple[bytes, bytes]:
    """Return ``(data_key, data_key_enc)``, creating the key if the project has none yet.

    The caller stores ``data_key_enc`` on the project when it was newly created.
    """
    if data_key_enc is not None:
        return unwrap_key(master_key(), data_key_enc, str(project_id)), data_key_enc
    data_key = new_data_key()
    return data_key, wrap_key(master_key(), data_key, str(project_id))
