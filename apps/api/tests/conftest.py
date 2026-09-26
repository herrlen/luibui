"""API test fixtures. ``database_url`` comes from the repository's root conftest.py."""

from collections.abc import Iterator

import pytest

from luibui_api import db
from luibui_api.settings import get_settings


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


@pytest.fixture
def use_database(database_url: str, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("DATABASE_URL", database_url)
    _clear_caches()
    return database_url
