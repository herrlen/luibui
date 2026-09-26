"""Database engine and session. One engine per process, created lazily from settings."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from luibui_api.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_size=settings.db_pool_size,
        pool_pre_ping=True,
        connect_args={"connect_timeout": int(settings.health_db_timeout_seconds) or 1},
    )


@lru_cache
def _sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with _sessionmaker()() as session:
        yield session
