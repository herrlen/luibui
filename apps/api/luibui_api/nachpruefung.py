"""Nightly re-check of published versions (S4-7 part 1, Prüfkatalog H02).

Every night after 03:00 (Berlin), when the worker has fresh OSV data and current rules, the API
creates one check per version that is not withdrawn: it decrypts the archive (only the API holds
MASTER_KEY), stages it through the same intake as an upload and queues an ordinary scan job, so
the worker needs nothing new. Afterwards it compares the critical and high findings with the check
the version was published from; new ones go to the author by mail, with a link to the report.

Nothing public happens yet: showing "Befund offen" on the package page waits for the disclosure
policy (S3-8). Re-checks cost no credit and are not listed as single checks.

The API runs as one instance; a PostgreSQL advisory lock keeps a second one from doubling the run.
"""

import io
import logging
import threading
import uuid
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import exists, select, text
from sqlalchemy.orm import Session

from luibui_api import benachrichtigung
from luibui_api.audit import audit
from luibui_api.db import _sessionmaker
from luibui_api.models import Namespace, Package, PackageVersion, Scan, User
from luibui_api.settings import get_settings
from luibui_api.storage import blob_store, project_data_key
from luibui_api.uploads import Upload, create_scan
from luibui_scan.models import ScanArt
from luibui_scan.scan import Eingabe

log = logging.getLogger(__name__)

BERLIN = ZoneInfo("Europe/Berlin")
UHRZEIT = time(3, 0)
TAKT_SEKUNDEN = 300
SPERRE = 7_340_201
"""pg_advisory_lock key for the re-check."""
MAX_MAIL_BEFUNDE = 10


def _schwer(report: dict[str, object] | None) -> dict[str, dict[str, object]]:
    befunde = (report or {}).get("befunde")
    out: dict[str, dict[str, object]] = {}
    for b in befunde if isinstance(befunde, list) else []:
        if isinstance(b, dict) and b.get("schwere") in ("K", "H") and b.get("fingerprint"):
            out[str(b["fingerprint"])] = b
    return out


def letzter_start(jetzt: datetime) -> datetime:
    """The most recent 03:00 Berlin at or before ``jetzt``, in UTC."""
    lokal = jetzt.astimezone(BERLIN)
    heute = datetime.combine(lokal.date(), UHRZEIT, tzinfo=BERLIN)
    return (heute if lokal >= heute else heute - timedelta(days=1)).astimezone(UTC)


def faellig(db: Session, jetzt: datetime) -> bool:
    """True if versions exist that have no re-check since the last 03:00."""
    seit = letzter_start(jetzt)
    offen = (
        select(PackageVersion.id)
        .where(PackageVersion.yanked_at.is_(None))
        .where(~exists().where(Scan.paketversion_id == PackageVersion.id, Scan.created_at >= seit))
        .limit(1)
    )
    return db.scalar(offen) is not None


def starten(db: Session, jetzt: datetime) -> int:
    """Queue a re-check for every version that is not withdrawn and has none since 03:00."""
    seit = letzter_start(jetzt)
    rows = db.execute(
        select(PackageVersion, Package, Namespace)
        .join(Package, Package.id == PackageVersion.package_id)
        .join(Namespace, Namespace.id == Package.namespace_id)
        .where(PackageVersion.yanked_at.is_(None))
        .where(~exists().where(Scan.paketversion_id == PackageVersion.id, Scan.created_at >= seit))
    ).all()
    angelegt = 0
    for v, p, ns in rows:
        if p.data_key_enc is None:
            continue
        try:
            data_key, _ = project_data_key(p.id, p.data_key_enc)
            archiv = b"".join(blob_store().open(v.storage_key, data_key))
            create_scan(
                db,
                Upload(art=Eingabe.ZIP, files=[("archiv.zip", io.BytesIO(archiv))]),
                project=None,
                scan_art=ScanArt.INTENSIV,
                name=f"{ns.name}/{p.name} {v.version} (Nachprüfung)",
                owner_id=v.owner_id,
                paketversion_id=v.id,
            )
            angelegt += 1
        except Exception:
            db.rollback()
            log.exception("re-check of version %s could not be queued", v.id)
    return angelegt


def _mail(db: Session, scan: Scan, v: PackageVersion, neu: list[dict[str, object]]) -> None:
    user = db.get(User, v.owner_id)
    paket = db.get(Package, v.package_id)
    ns = db.get(Namespace, paket.namespace_id) if paket else None
    if user is None or paket is None or ns is None:
        return
    zeilen = [
        f"- [{b.get('schwere')}] {str(b.get('titel', ''))[:120]} "
        f"({str(b.get('datei') or 'Paket')[:120]})"
        for b in neu[:MAX_MAIL_BEFUNDE]
    ]
    if len(neu) > MAX_MAIL_BEFUNDE:
        zeilen.append(f"- … und {len(neu) - MAX_MAIL_BEFUNDE} weitere")
    link = f"{get_settings().app_origin}/pruefungen/{scan.id}"
    benachrichtigung.senden(
        user,
        "nachpruefung",
        f"luibui: Neue Befunde in {ns.name}/{paket.name} {v.version}",
        "Hallo,\n\nluibui prüft veröffentlichte Pakete jede Nacht mit den aktuellen Regeln und "
        f"Schwachstellen-Daten. In {ns.name}/{paket.name} {v.version} gibt es jetzt "
        f"{len(neu)} kritische oder hohe Befunde, die es bei der Veröffentlichung noch nicht "
        "gab:\n\n" + "\n".join(zeilen) + f"\n\nZum Bericht: {link}\n\nBitte prüfe sie und "
        "veröffentliche bei Bedarf eine neue Version oder ziehe diese zurück. Bis auf Weiteres "
        "zeigen wir das nicht öffentlich an.",
    )


def auswerten(db: Session, jetzt: datetime) -> int:
    """Compare finished re-checks with the publishing check; mail new critical/high findings."""
    scans = db.scalars(
        select(Scan).where(
            Scan.paketversion_id.is_not(None),
            Scan.nachpruefung_ausgewertet_at.is_(None),
            Scan.status.in_(("fertig", "fehlgeschlagen")),
        )
    ).all()
    gemeldet = 0
    for scan in scans:
        v = db.get(PackageVersion, scan.paketversion_id)
        original = db.get(Scan, v.scan_id) if v else None
        scan.nachpruefung_ausgewertet_at = jetzt
        if v is None or original is None or scan.status != "fertig":
            db.commit()
            continue
        alt = _schwer(original.report)
        neu = [b for fp, b in _schwer(scan.report).items() if fp not in alt]
        scan.nachpruefung_neu = len(neu)
        if neu:
            audit(db, None, "paket.nachpruefung_befund", "version", v.id)
        db.commit()
        if neu:
            _mail(db, scan, v, neu)
            gemeldet += 1
    return gemeldet


def push_auswerten(db: Session, jetzt: datetime) -> int:
    """Checks started by a push (S5-9): new critical/high findings against the project's previous
    finished check go to the owner by mail."""
    scans = db.scalars(
        select(Scan).where(
            Scan.ausloeser == "webhook",
            Scan.nachpruefung_ausgewertet_at.is_(None),
            Scan.status.in_(("fertig", "fehlgeschlagen")),
        )
    ).all()
    gemeldet = 0
    for scan in scans:
        scan.nachpruefung_ausgewertet_at = jetzt
        if scan.status != "fertig" or scan.project_id is None:
            db.commit()
            continue
        vorher = db.scalar(
            select(Scan)
            .where(
                Scan.project_id == scan.project_id,
                Scan.status == "fertig",
                Scan.created_at < scan.created_at,
                Scan.id != scan.id,
            )
            .order_by(Scan.created_at.desc())
            .limit(1)
        )
        alt = _schwer(vorher.report) if vorher else {}
        neu = [b for fp, b in _schwer(scan.report).items() if fp not in alt]
        scan.nachpruefung_neu = len(neu)
        db.commit()
        user = db.get(User, scan.owner_id) if scan.owner_id else None
        if neu and user is not None:
            _push_mail(scan, user, neu)
            gemeldet += 1
    return gemeldet


def _push_mail(scan: Scan, user: User, neu: list[dict[str, object]]) -> None:
    zeilen = [
        f"- [{b.get('schwere')}] {str(b.get('titel', ''))[:120]} "
        f"({str(b.get('datei') or 'Paket')[:120]})"
        for b in neu[:MAX_MAIL_BEFUNDE]
    ]
    if len(neu) > MAX_MAIL_BEFUNDE:
        zeilen.append(f"- … und {len(neu) - MAX_MAIL_BEFUNDE} weitere")
    link = f"{get_settings().app_origin}/pruefungen/{scan.id}"
    benachrichtigung.senden(
        user,
        "push",
        "luibui: Neue Befunde nach einem Push",
        "Hallo,\n\ndie Prüfung, die dein letzter Push ausgelöst hat, hat "
        f"{len(neu)} kritische oder hohe Befunde, die es in der Prüfung davor nicht gab:\n\n"
        + "\n".join(zeilen)
        + f"\n\nZum Bericht: {link}",
    )


def lauf(db: Session, jetzt: datetime) -> None:
    """One tick: only the holder of the advisory lock works; others return at once."""
    if not db.scalar(text("SELECT pg_try_advisory_lock(:k)"), {"k": SPERRE}):
        return
    try:
        if faellig(db, jetzt):
            n = starten(db, jetzt)
            log.info("re-check: %s versions queued", n)
        auswerten(db, jetzt)
        push_auswerten(db, jetzt)
    finally:
        db.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": SPERRE})
        db.commit()


class Nachpruefer(threading.Thread):
    """Background thread of the API process; one tick every five minutes."""

    def __init__(self) -> None:
        super().__init__(name="nachpruefung", daemon=True)
        self.stopp = threading.Event()

    def run(self) -> None:
        while not self.stopp.wait(TAKT_SEKUNDEN):
            try:
                with _sessionmaker()() as db:
                    lauf(db, datetime.now(UTC))
            except Exception:
                log.exception("re-check tick failed")


def scan_ids_fuer(db: Session, version_id: uuid.UUID) -> list[uuid.UUID]:
    """Re-checks of one version, newest first (tests, later the package page)."""
    return list(
        db.scalars(
            select(Scan.id)
            .where(Scan.paketversion_id == version_id)
            .order_by(Scan.created_at.desc())
        )
    )
