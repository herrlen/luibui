"""Shared fixtures for all Python tests.

Tests marked ``db`` need a PostgreSQL server in TEST_DATABASE_URL (admin connection). Each test
session creates a fresh database and drops it afterwards, so no developer database is touched.
"""

import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, make_url, text

ADMIN_URL = os.environ.get("TEST_DATABASE_URL")


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
