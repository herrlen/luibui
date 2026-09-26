"""API test fixtures.

Tests marked ``db`` need a PostgreSQL server in TEST_DATABASE_URL (admin connection). Each test
session creates a fresh database and drops it afterwards, so a developer database is never touched.
"""

import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, make_url, text

from luibui_api import db
from luibui_api.settings import get_settings

ADMIN_URL = os.environ.get("TEST_DATABASE_URL")


def _clear_caches() -> None:
    get_settings.cache_clear()
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


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    if not ADMIN_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    name = f"luibui_test_{uuid.uuid4().hex[:12]}"
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield make_url(ADMIN_URL).set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def use_database(database_url: str, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("DATABASE_URL", database_url)
    _clear_caches()
    return database_url
