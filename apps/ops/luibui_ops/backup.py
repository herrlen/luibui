"""Nightly database backup with a restore test (S3-10).

1. A read-only transaction exports its snapshot and counts the rows of every table in it.
2. ``pg_dump --snapshot`` dumps exactly that state (custom format) into a private temp directory.
3. The dump is restored into a scratch database on the same server and the row counts must match.
4. Only then it is encrypted with ``age`` to the public key; the private key is with Len, never on
   the server. The plain dump is deleted in ``finally``, also when a step fails.
5. The last ``behalten`` encrypted files stay in the backup volume, which mittwald's nightly project
   backup copies off the containers (30 days).
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import sql

from luibui_ops.settings import Datenbank, Settings

log = logging.getLogger(__name__)

TESTDB = "luibui_restore_test"
"""Scratch database for the restore test; dropped before and after."""
PREFIX = "luibui-"
ENDUNG = ".dump.age"
STATUS = "status.json"
TIMEOUT = 1800

Runner = Callable[[Sequence[str], dict[str, str]], None]


class BackupError(RuntimeError):
    """A step failed; the message names the step, never a secret."""


def _run(cmd: Sequence[str], env: dict[str, str]) -> None:
    try:
        subprocess.run(  # noqa: S603 - fixed argument lists, no shell
            list(cmd), env=env, check=True, capture_output=True, timeout=TIMEOUT
        )
    except subprocess.CalledProcessError as exc:
        fehler = exc.stderr.decode(errors="replace").strip().splitlines()[-1:] or ["?"]
        raise BackupError(f"{cmd[0]} beendet mit {exc.returncode}: {fehler[0][:300]}") from None
    except subprocess.TimeoutExpired:
        raise BackupError(f"{cmd[0]}: Zeitlimit {TIMEOUT} s") from None


@dataclass(frozen=True)
class Ergebnis:
    zeit: str
    datei: str
    bytes: int
    tabellen: int
    zeilen: int
    sekunden: float


_TABELLEN = """
SELECT schemaname, tablename FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema') ORDER BY 1, 2
"""


def zeilen_je_tabelle(conn: psycopg.Connection[tuple[str, str]]) -> dict[str, int]:
    zahlen: dict[str, int] = {}
    for schema, tabelle in conn.execute(_TABELLEN).fetchall():
        q = sql.SQL("SELECT count(*) FROM {}.{}").format(
            sql.Identifier(schema), sql.Identifier(tabelle)
        )
        row = conn.execute(q).fetchone()
        zahlen[f"{schema}.{tabelle}"] = int(row[0]) if row else 0
    return zahlen


def _testdb_entfernen(db: Datenbank) -> None:
    with psycopg.connect(db.conninfo(), autocommit=True) as conn:
        conn.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(TESTDB))
        )


def _wiederherstellen_und_zaehlen(db: Datenbank, dump: Path, run: Runner) -> dict[str, int]:
    _testdb_entfernen(db)
    with psycopg.connect(db.conninfo(), autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TESTDB)))
    try:
        run(
            [
                "pg_restore",
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                TESTDB,
                str(dump),
            ],
            db.env(),
        )
        with psycopg.connect(db.conninfo(TESTDB)) as conn:
            return zeilen_je_tabelle(conn)
    finally:
        _testdb_entfernen(db)


def aufraeumen(ordner: Path, behalten: int) -> list[Path]:
    """Delete all but the newest ``behalten`` backups; names sort by time."""
    dateien = sorted(p for p in ordner.glob(f"{PREFIX}*{ENDUNG}") if p.is_file())
    weg = dateien[:-behalten] if len(dateien) > behalten else []
    for p in weg:
        p.unlink()
    for rest in ordner.glob(f"{PREFIX}*{ENDUNG}.part"):  # an aborted encryption
        rest.unlink()
    return weg


def sichern(
    s: Settings, run: Runner = _run, jetzt: Callable[[], datetime] | None = None
) -> Ergebnis:
    if s.age_recipient is None:
        raise BackupError("BACKUP_AGE_RECIPIENT fehlt: ohne öffentlichen Schlüssel kein Backup")
    beginn = time.monotonic()
    zeit = (jetzt or (lambda: datetime.now(UTC)))()
    stempel = zeit.strftime("%Y%m%dT%H%M%SZ")
    s.backup_dir.mkdir(parents=True, exist_ok=True)
    ziel = s.backup_dir / f"{PREFIX}{stempel}{ENDUNG}"
    teil = ziel.with_name(ziel.name + ".part")
    alte_maske = os.umask(0o077)  # dump and backup files readable by this user only
    tmp = Path(tempfile.mkdtemp(prefix="luibui-backup-"))
    try:
        dump = tmp / "luibui.dump"
        with psycopg.connect(s.db.conninfo()) as conn:
            conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            row = conn.execute("SELECT pg_export_snapshot()").fetchone()
            snapshot = str(row[0]) if row else ""
            vorher = zeilen_je_tabelle(conn)
            run(
                [
                    "pg_dump",
                    "--format=custom",
                    "--snapshot",
                    snapshot,
                    "--file",
                    str(dump),
                    s.db.name,
                ],
                s.db.env(),
            )
            conn.rollback()
        nachher = _wiederherstellen_und_zaehlen(s.db, dump, run)
        if nachher != vorher:
            abweichend = sorted(
                k for k in vorher.keys() | nachher.keys() if vorher.get(k) != nachher.get(k)
            )
            raise BackupError(f"Restore-Test: Zeilenzahl weicht ab in {', '.join(abweichend[:5])}")
        run(
            ["age", "--encrypt", "--recipient", s.age_recipient, "--output", str(teil), str(dump)],
            {"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        )
        teil.replace(ziel)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        teil.unlink(missing_ok=True)
        os.umask(alte_maske)
    aufraeumen(s.backup_dir, s.behalten)
    ergebnis = Ergebnis(
        zeit=zeit.isoformat(timespec="seconds"),
        datei=ziel.name,
        bytes=ziel.stat().st_size,
        tabellen=len(vorher),
        zeilen=sum(vorher.values()),
        sekunden=round(time.monotonic() - beginn, 1),
    )
    status = s.backup_dir / STATUS
    status.with_suffix(".tmp").write_text(json.dumps(asdict(ergebnis), indent=2))
    status.with_suffix(".tmp").replace(status)
    return ergebnis


def letzter_erfolg(ordner: Path) -> datetime | None:
    try:
        daten = json.loads((ordner / STATUS).read_text())
        return datetime.fromisoformat(str(daten["zeit"]))
    except (OSError, ValueError, KeyError, TypeError):
        return None
