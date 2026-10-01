"""S3-10: settings, health alarm, schedule and the stale-backup alarm (no database needed)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from luibui_ops import alarm, backup, main
from luibui_ops.health import Waechter
from luibui_ops.settings import Settings

SCHLUESSEL = "age1" + "q" * 58


def settings(tmp_path: Path, **env: str) -> Settings:
    basis = {
        "DATABASE_URL": "postgresql+psycopg://luibui:geheim%40pw@postgres:5432/luibui",
        "BACKUP_DIR": str(tmp_path),
        "BACKUP_AGE_RECIPIENT": SCHLUESSEL,
        "HEALTH_URLS": "http://api:8000/health,https://luibui.com/healthz",
    }
    return Settings.aus_env(basis | env)


def test_settings_from_env(tmp_path: Path) -> None:
    s = settings(tmp_path)
    assert (s.db.host, s.db.port, s.db.user, s.db.name) == ("postgres", 5432, "luibui", "luibui")
    assert s.db.password == "geheim@pw"  # noqa: S105
    assert s.db.env()["PGPASSWORD"] == "geheim@pw"
    assert "geheim" not in repr(s)  # secrets never end up in a log line
    assert s.backup_zeit.hour == 1 and s.backup_zeit.minute == 5
    assert s.behalten == 14 and s.alarm_an is None


@pytest.mark.parametrize(
    "falsch",
    ["age1kurz", "--recipient=x", "ssh-ed25519 AAAA", "age1" + "b" * 58, " age1" + "q" * 57 + "-"],
)
def test_only_an_age_public_key_is_accepted(tmp_path: Path, falsch: str) -> None:
    with pytest.raises(ValueError, match="age"):
        settings(tmp_path, BACKUP_AGE_RECIPIENT=falsch)


def test_health_urls_must_be_http(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="http"):
        settings(tmp_path, HEALTH_URLS="file:///etc/passwd")


def test_one_alarm_after_two_failures_and_one_all_clear() -> None:
    w = Waechter(("http://api/health",))
    antworten = iter(
        [None, "HTTP 502", None, "HTTP 502", "ConnectionRefusedError", "HTTP 502", None]
    )
    runden = [w.runde(lambda _url: next(antworten)) for _ in range(7)]
    betreffe = [[a[0] for a in r] for r in runden]
    assert betreffe == [
        [],
        [],  # one failure (a rollout) is no alarm
        [],
        [],
        ["Nicht erreichbar: http://api/health"],
        [],  # no repeat while it stays down
        ["Wieder erreichbar: http://api/health"],
    ]
    assert "ConnectionRefusedError" in runden[4][0][1]


def test_backup_runs_before_mittwalds_copy_berlin_time(tmp_path: Path) -> None:
    s = settings(tmp_path)
    # 23:00 UTC on 30.09. is 01:00 in Berlin (summer time) -> today 01:05 Berlin = 23:05 UTC
    assert main.naechster_lauf(datetime(2026, 9, 30, 23, 0, tzinfo=UTC), s) == datetime(
        2026, 9, 30, 23, 5, tzinfo=UTC
    )
    # just after: the next night
    assert main.naechster_lauf(datetime(2026, 9, 30, 23, 6, tzinfo=UTC), s) == datetime(
        2026, 10, 1, 23, 5, tzinfo=UTC
    )
    # winter time (CET, UTC+1): 01:05 Berlin = 00:05 UTC
    assert main.naechster_lauf(datetime(2026, 12, 1, 12, 0, tzinfo=UTC), s) == datetime(
        2026, 12, 2, 0, 5, tzinfo=UTC
    )


def test_stale_backup_alarm_once_a_day(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gesendet: list[str] = []
    monkeypatch.setattr(alarm, "senden", lambda _s, betreff, _t: gesendet.append(betreff) or True)
    ops = main.Ops(settings(tmp_path), pruefer=lambda _url: None)
    ops.naechstes_backup = datetime.max.replace(tzinfo=UTC)  # only the age check here
    t0 = ops.start
    ops.schritt(t0)
    assert gesendet == []  # a fresh container waits a day before missing its first backup
    ops.schritt(t0 + timedelta(hours=27))
    assert gesendet == ["Kein aktuelles Backup"]
    ops.schritt(t0 + timedelta(hours=28))
    assert gesendet == ["Kein aktuelles Backup"]  # no repeat within a day
    (tmp_path / backup.STATUS).write_text(
        '{"zeit": "' + (t0 + timedelta(hours=28, minutes=10)).isoformat() + '"}'
    )
    ops.schritt(t0 + timedelta(hours=29))
    assert gesendet == ["Kein aktuelles Backup"]  # fresh again: quiet


def test_failed_backup_sends_an_alarm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gesendet: list[tuple[str, str]] = []
    monkeypatch.setattr(alarm, "senden", lambda _s, b, t: gesendet.append((b, t)) or True)
    ops = main.Ops(settings(tmp_path, BACKUP_AGE_RECIPIENT=""), pruefer=lambda _url: None)
    ops.naechstes_backup = ops.start
    ops.schritt(ops.start)
    assert gesendet[0][0] == "Backup fehlgeschlagen"
    assert "BACKUP_AGE_RECIPIENT fehlt" in gesendet[0][1]


def test_retention_keeps_the_newest(tmp_path: Path) -> None:
    for tag in range(1, 6):
        (tmp_path / f"luibui-202610{tag:02d}T010500Z.dump.age").write_bytes(b"x")
    (tmp_path / "luibui-20261006T010500Z.dump.age.part").write_bytes(b"x")
    (tmp_path / "fremd.txt").write_bytes(b"x")
    backup.aufraeumen(tmp_path, 3)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "fremd.txt",
        "luibui-20261003T010500Z.dump.age",
        "luibui-20261004T010500Z.dump.age",
        "luibui-20261005T010500Z.dump.age",
    ]


def test_mail_without_setup_is_only_logged(tmp_path: Path) -> None:
    assert alarm.senden(settings(tmp_path), "Test", "Text") is False
