"""The migration creates exactly the model schema; every user-data table has owner_id."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from luibui_api.models import Base

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"

EXPECTED_TABLES = {
    "users",
    "sessions",
    "tokens",
    "projects",
    "project_versions",
    "stored_files",
    "scans",
    "findings",
    "finding_status",
    "jobs",
    "packages",
    "versions",
    "audit_log",
    "email_tokens",
    "payments",
    "credit_entries",
}
# Tables without owner_id and why: users is the owner itself; audit_log records the actor instead.
WITHOUT_OWNER = {"users", "audit_log"}


def test_models_define_expected_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_every_user_data_table_has_owner_id() -> None:
    for name, table in Base.metadata.tables.items():
        if name in WITHOUT_OWNER:
            continue
        assert "owner_id" in table.columns, name


def test_all_primary_keys_are_uuids() -> None:
    for name, table in Base.metadata.tables.items():
        (pk,) = table.primary_key.columns
        assert pk.type.python_type.__name__ == "UUID", name


@pytest.mark.db
def test_upgrade_matches_models_and_downgrade_is_clean(use_database: str) -> None:
    config = Config(str(ALEMBIC_INI))
    command.upgrade(config, "head")
    command.check(config)  # raises if models and migrations differ

    engine = create_engine(use_database)
    tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
    assert tables == EXPECTED_TABLES

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    command.upgrade(config, "head")
    engine.dispose()
