"""The ops loop: health checks every few minutes, the backup once a night, alarms by mail."""

import logging
import signal
import time
from datetime import UTC, datetime, timedelta
from types import FrameType
from zoneinfo import ZoneInfo

from luibui_ops import alarm, backup
from luibui_ops.health import Pruefer, Waechter, pruefen
from luibui_ops.settings import Settings

log = logging.getLogger("luibui_ops")
BERLIN = ZoneInfo("Europe/Berlin")
ERINNERUNG = timedelta(hours=24)


def naechster_lauf(nach: datetime, s: Settings) -> datetime:
    """Next backup after ``nach`` at BACKUP_ZEIT Berlin time (before mittwald's 01:39 copy)."""
    lokal = nach.astimezone(BERLIN)
    lauf = lokal.replace(
        hour=s.backup_zeit.hour, minute=s.backup_zeit.minute, second=0, microsecond=0
    )
    if lauf <= lokal:
        lauf = (lauf + timedelta(days=1)).replace(
            hour=s.backup_zeit.hour, minute=s.backup_zeit.minute
        )
    return lauf.astimezone(UTC)


class Ops:
    def __init__(self, s: Settings, pruefer: Pruefer = pruefen) -> None:
        self.s = s
        self.pruefer = pruefer
        self.waechter = Waechter(s.health_urls)
        self.start = datetime.now(UTC)
        self.naechstes_backup = naechster_lauf(self.start, s)
        self.naechste_pruefung = self.start
        self.veraltet_gemeldet: datetime | None = None

    def schritt(self, jetzt: datetime) -> None:
        if jetzt >= self.naechste_pruefung:
            self.naechste_pruefung = jetzt + timedelta(seconds=self.s.health_sekunden)
            for betreff, text in self.waechter.runde(self.pruefer):
                alarm.senden(self.s, betreff, text)
            self._backup_alter(jetzt)
        if jetzt >= self.naechstes_backup:
            self.naechstes_backup = naechster_lauf(jetzt, self.s)
            self._backup()

    def _backup(self) -> None:
        try:
            e = backup.sichern(self.s)
        except Exception as exc:  # any failure must reach a human
            log.error("Backup fehlgeschlagen: %s", exc)
            alarm.senden(
                self.s,
                "Backup fehlgeschlagen",
                f"Das nächtliche Datenbank-Backup ist fehlgeschlagen:\n\n{exc}\n\n"
                "Das letzte erfolgreiche Backup bleibt erhalten. Logs des ops-Containers ansehen.",
            )
            return
        log.info(
            "Backup %s: %d Bytes, %d Tabellen, %d Zeilen, Restore-Test ok, %.1f s",
            e.datei,
            e.bytes,
            e.tabellen,
            e.zeilen,
            e.sekunden,
        )

    def _backup_alter(self, jetzt: datetime) -> None:
        """Alarm when the newest good backup is too old (or there never was one after a day)."""
        grenze = timedelta(hours=self.s.backup_max_stunden)
        letzter = backup.letzter_erfolg(self.s.backup_dir)
        alt = (jetzt - letzter > grenze) if letzter else (jetzt - self.start > grenze)
        if not alt:
            self.veraltet_gemeldet = None
            return
        if self.veraltet_gemeldet and jetzt - self.veraltet_gemeldet < ERINNERUNG:
            return
        self.veraltet_gemeldet = jetzt
        seit = letzter.isoformat(timespec="minutes") if letzter else "nie"
        alarm.senden(
            self.s,
            "Kein aktuelles Backup",
            f"Das letzte erfolgreiche Datenbank-Backup ist von: {seit}.\n"
            "Erwartet wird eines pro Nacht. Logs des ops-Containers ansehen.",
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    s = Settings.aus_env()
    stop = False

    def _handle(_sig: int, _frame: FrameType | None) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)
    ops = Ops(s)
    if s.age_recipient is None:
        log.warning("BACKUP_AGE_RECIPIENT fehlt: Backups sind aus")
    log.info(
        "ops bereit: %d Health-Ziele alle %d s, nächstes Backup %s",
        len(s.health_urls),
        s.health_sekunden,
        ops.naechstes_backup.isoformat(timespec="minutes"),
    )
    while not stop:
        ops.schritt(datetime.now(UTC))
        time.sleep(5)


if __name__ == "__main__":
    main()
