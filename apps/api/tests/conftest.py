"""API test fixtures. ``database_url`` comes from the repository's root conftest.py."""

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from luibui_api import db
from luibui_api.settings import get_settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _clear_caches() -> None:
    from luibui_api import storage

    if db.get_engine.cache_info().currsize:
        db.get_engine().dispose()  # close pooled connections before the engine is forgotten
    get_settings.cache_clear()
    storage.blob_store.cache_clear()
    db.get_engine.cache_clear()
    db._sessionmaker.cache_clear()


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("LUIBUI_ENV", "test")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://nobody:not-the-password@127.0.0.1:1/none"
    )
    _clear_caches()
    yield
    _clear_caches()


@pytest.fixture
def use_database(database_url: str, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("DATABASE_URL", database_url)
    _clear_caches()
    return database_url


MASTER_KEY_B64 = "bHVpYnVpLXRlc3QtbWFzdGVyLWtleS0zMi1ieXRlcyE="  # 32 bytes, test only
APP = "https://app.luibui.com"


@pytest.fixture(scope="session")
def _migrated(database_url: str) -> str:
    import os

    from alembic import command
    from alembic.config import Config

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        get_settings.cache_clear()
        command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()
    return database_url


@pytest.fixture
def api(_migrated: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator["Api"]:
    """A migrated, emptied database and a client that talks to the app host over HTTPS."""
    from sqlalchemy import create_engine, text

    from luibui_api.main import create_app
    from luibui_api.routes.auth import login_limiter
    from luibui_api.routes.quickscans import quickscan_limiter

    monkeypatch.setenv("DATABASE_URL", _migrated)
    monkeypatch.setenv("MASTER_KEY", MASTER_KEY_B64)
    monkeypatch.setenv("ANNAHME_OFFEN", "true")
    # Most tests are about uploads, not about the confirmation mail; test_guthaben turns it on.
    monkeypatch.setenv("EMAIL_BESTAETIGUNG_PFLICHT", "false")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "projects"))
    monkeypatch.setenv("SCRATCH_ROOT", str(tmp_path / "scratch"))
    (tmp_path / "scratch").mkdir()
    _clear_caches()
    login_limiter.cache_clear()
    quickscan_limiter.cache_clear()
    engine = create_engine(_migrated)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, jobs, audit_log CASCADE"))
    engine.dispose()
    yield Api(create_app())
    login_limiter.cache_clear()


class Api:
    """Creates independent browser-like clients, one per user."""

    def __init__(self, app: object) -> None:
        self.app = app

    def client(self, base_url: str = APP) -> "TestClient":
        from fastapi.testclient import TestClient

        return TestClient(self.app, base_url=base_url, headers={"Origin": APP})  # type: ignore[arg-type]

    def user(self, email: str, passwort: str = "ein-langes-passwort") -> "TestClient":
        c = self.client()
        r = c.post("/api/v1/auth/registrieren", json={"email": email, "passwort": passwort})
        assert r.status_code == 201, r.text
        return c
