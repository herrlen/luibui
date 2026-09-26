from alembic import context
from sqlalchemy import create_engine, pool

from luibui_api.models import Base
from luibui_api.settings import get_settings

target_metadata = Base.metadata


def _url() -> str:
    return get_settings().database_url.get_secret_value()


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
