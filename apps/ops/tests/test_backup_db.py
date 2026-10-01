"""S3-10 against a real PostgreSQL: snapshot dump, restore test, nothing left behind.

With ``age`` installed the backup is really encrypted and decrypted again; without it ``age`` is
replaced by a copy (the image always has it, docs/restore.md).
"""

import os
import shutil
import subprocess
import uuid
from collections.abc import Iterator, Sequence
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from luibui_ops import backup
from luibui_ops.settings import Datenbank, Settings

pytestmark = pytest.mark.db

ADMIN = os.environ.get("TEST_DATABASE_URL")
MIT_AGE = shutil.which("age") is not None and shutil.which("age-keygen") is not None


@pytest.fixture
def schluessel(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, Path | None]:
    """(public key, private key file); a dummy key without age."""
    if not MIT_AGE:
        return "age1" + "q" * 58, None
    datei = tmp_path_factory.mktemp("key") / "test.key"
    subprocess.run(["age-keygen", "-o", str(datei)], check=True, capture_output=True)  # noqa: S603,S607
    oeffentlich = next(
        z.split(": ", 1)[1] for z in datei.read_text().splitlines() if "public key" in z
    )
    return oeffentlich, datei


@pytest.fixture
def quelle() -> Iterator[Datenbank]:
    if not ADMIN or not shutil.which("pg_dump") or not shutil.which("pg_restore"):
        pytest.skip("TEST_DATABASE_URL oder pg_dump/pg_restore fehlt")
    admin = Datenbank.aus_url(ADMIN)
    name = f"luibui_ops_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(admin.conninfo(), autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    db = Datenbank(admin.host, admin.port, admin.user, admin.password, name)
    with psycopg.connect(db.conninfo()) as conn:
        conn.execute("CREATE TABLE users (id serial PRIMARY KEY, email text)")
        conn.execute("INSERT INTO users (email) SELECT 'u' || g FROM generate_series(1, 50) g")
        conn.execute('CREATE TABLE "Mit Leerzeichen" (x int)')
        conn.execute('INSERT INTO "Mit Leerzeichen" VALUES (1), (2)')
    try:
        yield db
    finally:
        with psycopg.connect(admin.conninfo(), autocommit=True) as conn:
            for n in (name, backup.TESTDB):
                conn.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(n))
                )


def _settings(db: Datenbank, ordner: Path, schluessel: str = "age1" + "q" * 58) -> Settings:
    url = f"postgresql+psycopg://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}"
    return Settings.aus_env(
        {"DATABASE_URL": url, "BACKUP_DIR": str(ordner), "BACKUP_AGE_RECIPIENT": schluessel}
    )


def _runner(nach_restore: str | None = None):  # type: ignore[no-untyped-def]
    def run(cmd: Sequence[str], env: dict[str, str]) -> None:
        if cmd[0] == "age" and not MIT_AGE:
            Path(cmd[cmd.index("--output") + 1]).write_bytes(Path(cmd[-1]).read_bytes())
            return
        backup._run(cmd, env)
        if cmd[0] == "pg_restore" and nach_restore:
            db = Datenbank(env["PGHOST"], int(env["PGPORT"]), env["PGUSER"], env["PGPASSWORD"], "")
            with psycopg.connect(db.conninfo(backup.TESTDB)) as conn:
                conn.execute(nach_restore)

    return run


def _datenbanken(db: Datenbank) -> set[str]:
    with psycopg.connect(db.conninfo()) as conn:
        return {r[0] for r in conn.execute("SELECT datname FROM pg_database")}


def test_backup_with_restore_test(
    quelle: Datenbank, tmp_path: Path, schluessel: tuple[str, Path | None]
) -> None:
    oeffentlich, privat = schluessel
    e = backup.sichern(_settings(quelle, tmp_path, oeffentlich), run=_runner())
    assert (e.tabellen, e.zeilen) == (2, 52)
    datei = tmp_path / e.datei
    assert datei.is_file() and e.bytes > 0
    assert oct(datei.stat().st_mode & 0o777) == "0o600"
    assert backup.letzter_erfolg(tmp_path) is not None
    assert backup.TESTDB not in _datenbanken(quelle)  # the scratch database is gone
    assert not list(tmp_path.glob("*.part"))
    if privat is not None:  # the private key turns it back into a dump with both tables
        assert b"u50" not in datei.read_bytes()
        klar = subprocess.run(  # noqa: S603
            ["age", "--decrypt", "-i", str(privat), str(datei)],  # noqa: S607
            check=True,
            capture_output=True,
        ).stdout
        liste = subprocess.run(
            ["pg_restore", "--list"],  # noqa: S607
            input=klar,
            check=True,
            capture_output=True,
        ).stdout.decode()
        assert "TABLE public users" in liste and "TABLE public Mit Leerzeichen" in liste


def test_a_restore_that_differs_is_no_backup(quelle: Datenbank, tmp_path: Path) -> None:
    with pytest.raises(backup.BackupError, match=r"Restore-Test.*public\.users"):
        backup.sichern(_settings(quelle, tmp_path), run=_runner("DELETE FROM users WHERE id = 1"))
    assert list(tmp_path.iterdir()) == []  # no file, no status
    assert backup.TESTDB not in _datenbanken(quelle)


def test_failing_dump_names_the_step(quelle: Datenbank, tmp_path: Path) -> None:
    def run(cmd: Sequence[str], env: dict[str, str]) -> None:
        backup._run([*cmd[:-1], "gibt_es_nicht"] if cmd[0] == "pg_dump" else cmd, env)

    with pytest.raises(backup.BackupError, match="pg_dump beendet"):
        backup.sichern(_settings(quelle, tmp_path), run=run)
    assert list(tmp_path.iterdir()) == []
