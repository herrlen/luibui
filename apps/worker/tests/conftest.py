"""Worker test fixtures: a migrated database and a scratch root per test."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

from luibui_worker.main import Worker
from luibui_worker.selftest import SELFTEST_HANDLERS
from luibui_worker.settings import WorkerSettings

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "api" / "alembic.ini"


@pytest.fixture(scope="session")
def migrated(database_url: str) -> str:
    import os

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        from luibui_api.settings import get_settings

        get_settings.cache_clear()
        command.upgrade(Config(str(ALEMBIC_INI)), "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
    return database_url


@pytest.fixture
def engine(migrated: str) -> Iterator[Engine]:
    eng = create_engine(migrated)
    with eng.begin() as conn:
        conn.execute(text("DELETE FROM jobs"))
    yield eng
    eng.dispose()


@pytest.fixture
def scratch_root(tmp_path: Path) -> Path:
    root = tmp_path / "scratch"
    root.mkdir()
    return root


@pytest.fixture
def worker(engine: Engine, scratch_root: Path, migrated: str) -> Worker:
    settings = WorkerSettings(
        database_url=migrated,  # type: ignore[arg-type]
        scratch_root=scratch_root,
        worker_id="test-worker",
        kill_grace_seconds=1.0,
        stale_grace_seconds=0,
    )
    return Worker(settings, engine=engine, handlers=SELFTEST_HANDLERS)
