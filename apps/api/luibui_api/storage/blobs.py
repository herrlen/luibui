"""Encrypted blobs on the ``luibui-projects`` volume. Plaintext never touches this directory."""

import os
import secrets
from collections.abc import Iterator
from pathlib import Path
from typing import IO

from luibui_api.storage.crypto import decrypt_stream, encrypt_stream


def new_storage_key() -> str:
    return secrets.token_hex(32)


class BlobStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, storage_key: str) -> Path:
        if len(storage_key) != 64 or not all(c in "0123456789abcdef" for c in storage_key):
            raise ValueError("ungültiger Speicherschlüssel")
        return self.root / storage_key[:2] / storage_key[2:4] / storage_key

    def put(self, storage_key: str, src: IO[bytes], data_key: bytes) -> int:
        """Encrypt ``src`` into a new blob; return the number of bytes written to disk."""
        path = self._path(storage_key)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        written = 0
        try:
            with os.fdopen(fd, "wb") as out:
                for part in encrypt_stream(data_key, src, storage_key):
                    out.write(part)
                    written += len(part)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return written

    def open(self, storage_key: str, data_key: bytes) -> Iterator[bytes]:
        """Plaintext chunks. Only use the data once the iterator finished without an error."""
        fd = os.open(self._path(storage_key), os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as src:
            yield from decrypt_stream(data_key, src, storage_key)

    def delete(self, storage_key: str) -> None:
        self._path(storage_key).unlink(missing_ok=True)
