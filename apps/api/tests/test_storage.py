"""S2-7: project files are encrypted at rest and every kind of tampering is detected."""

import base64
import io
import os
import uuid
from pathlib import Path

import pytest

from luibui_api import storage
from luibui_api.storage import BlobStore, DecryptionError, parse_master_key, project_data_key
from luibui_api.storage.crypto import CHUNK, new_data_key, unwrap_key, wrap_key

PLAINTEXT = b"LUIBUI-TESTFIXTURE geheimer Inhalt " * 1000


@pytest.fixture
def store(tmp_path: Path) -> BlobStore:
    return BlobStore(tmp_path / "projects")


def read(store: BlobStore, key: str, data_key: bytes) -> bytes:
    return b"".join(store.open(key, data_key))


def blob_path(store: BlobStore, key: str) -> Path:
    return store.root / key[:2] / key[2:4] / key


@pytest.mark.parametrize("size", [0, 1, CHUNK - 1, CHUNK, CHUNK + 1, 3 * CHUNK + 17])
def test_roundtrip(store: BlobStore, size: int) -> None:
    data = os.urandom(size)
    key, dk = storage.new_storage_key(), new_data_key()
    store.put(key, io.BytesIO(data), dk)
    assert read(store, key, dk) == data


def test_no_plaintext_on_disk(store: BlobStore) -> None:
    key, dk = storage.new_storage_key(), new_data_key()
    store.put(key, io.BytesIO(PLAINTEXT), dk)
    raw = blob_path(store, key).read_bytes()
    assert b"geheimer" not in raw
    assert b"LUIBUI-TESTFIXTURE" not in raw
    assert oct(blob_path(store, key).stat().st_mode & 0o777) == "0o600"


def test_wrong_key(store: BlobStore) -> None:
    key = storage.new_storage_key()
    store.put(key, io.BytesIO(PLAINTEXT), new_data_key())
    with pytest.raises(DecryptionError):
        read(store, key, new_data_key())


def test_blob_bound_to_its_storage_key(store: BlobStore) -> None:
    """A blob copied under another record's key does not decrypt (no swapping of files)."""
    dk = new_data_key()
    a, b = storage.new_storage_key(), storage.new_storage_key()
    store.put(a, io.BytesIO(PLAINTEXT), dk)
    blob_path(store, b).parent.mkdir(parents=True, exist_ok=True)
    blob_path(store, b).write_bytes(blob_path(store, a).read_bytes())
    with pytest.raises(DecryptionError):
        read(store, b, dk)


def test_flipped_bit(store: BlobStore) -> None:
    key, dk = storage.new_storage_key(), new_data_key()
    store.put(key, io.BytesIO(PLAINTEXT), dk)
    raw = bytearray(blob_path(store, key).read_bytes())
    raw[len(raw) // 2] ^= 1
    blob_path(store, key).write_bytes(bytes(raw))
    with pytest.raises(DecryptionError):
        read(store, key, dk)


def test_truncated_after_full_chunk(store: BlobStore) -> None:
    """Dropping the final chunk must fail, even though the rest decrypts fine."""
    key, dk = storage.new_storage_key(), new_data_key()
    store.put(key, io.BytesIO(os.urandom(2 * CHUNK + 5)), dk)
    raw = blob_path(store, key).read_bytes()
    first_chunk_end = 4 + 7 + CHUNK + 16
    blob_path(store, key).write_bytes(raw[: first_chunk_end + CHUNK + 16])
    with pytest.raises(DecryptionError):
        read(store, key, dk)


def test_reordered_chunks(store: BlobStore) -> None:
    key, dk = storage.new_storage_key(), new_data_key()
    store.put(key, io.BytesIO(os.urandom(3 * CHUNK)), dk)
    raw = blob_path(store, key).read_bytes()
    head, size = 11, CHUNK + 16
    c = [raw[head + i * size : head + (i + 1) * size] for i in range(3)]
    blob_path(store, key).write_bytes(raw[:head] + c[1] + c[0] + c[2])
    with pytest.raises(DecryptionError):
        read(store, key, dk)


def test_existing_blob_is_never_overwritten(store: BlobStore) -> None:
    key, dk = storage.new_storage_key(), new_data_key()
    store.put(key, io.BytesIO(b"a"), dk)
    with pytest.raises(FileExistsError):
        store.put(key, io.BytesIO(b"b"), dk)


@pytest.mark.parametrize("key", ["../../etc/passwd", "ab", "Z" * 64, "a" * 63])
def test_storage_key_is_validated(store: BlobStore, key: str) -> None:
    with pytest.raises(ValueError):
        store.put(key, io.BytesIO(b"x"), new_data_key())


def test_data_key_is_bound_to_project() -> None:
    master = os.urandom(32)
    dk = new_data_key()
    wrapped = wrap_key(master, dk, "project-a")
    assert unwrap_key(master, wrapped, "project-a") == dk
    with pytest.raises(DecryptionError):
        unwrap_key(master, wrapped, "project-b")
    with pytest.raises(DecryptionError):
        unwrap_key(os.urandom(32), wrapped, "project-a")


def test_project_data_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MASTER_KEY", base64.b64encode(os.urandom(32)).decode())
    storage.get_settings.cache_clear()
    pid = uuid.uuid4()
    dk, enc = project_data_key(pid, None)
    assert dk not in enc
    assert project_data_key(pid, enc) == (dk, enc)


@pytest.mark.parametrize("value", ["", "kein base64!", base64.b64encode(b"x" * 16).decode()])
def test_master_key_is_validated(value: str) -> None:
    with pytest.raises(ValueError):
        parse_master_key(value)


def test_missing_master_key() -> None:
    with pytest.raises(RuntimeError, match="MASTER_KEY"):
        storage.master_key()
