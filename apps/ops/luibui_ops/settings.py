"""Settings from the environment. Secrets only from ENV (CLAUDE.md), never logged."""

import os
import re
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

_AGE_RECIPIENT = re.compile(r"^age1[02-9ac-hj-np-z]{58}$")
"""An age X25519 public key (bech32). Anything else is refused, so it can never become an option."""


@dataclass(frozen=True)
class Datenbank:
    host: str
    port: int
    user: str
    password: str = field(repr=False)
    name: str

    @classmethod
    def aus_url(cls, url: str) -> "Datenbank":
        """``postgresql+psycopg://user:pw@host:5432/db`` as the API and worker use it."""
        teile = urlsplit(url)
        if not teile.scheme.startswith("postgresql") or not teile.hostname or not teile.username:
            raise ValueError("DATABASE_URL ist keine PostgreSQL-Adresse")
        return cls(
            host=teile.hostname,
            port=teile.port or 5432,
            user=unquote(teile.username),
            password=unquote(teile.password or ""),
            name=teile.path.lstrip("/") or "postgres",
        )

    def env(self) -> dict[str, str]:
        """libpq environment for pg_dump/pg_restore; the password is never in a command line."""
        return {
            "PGHOST": self.host,
            "PGPORT": str(self.port),
            "PGUSER": self.user,
            "PGPASSWORD": self.password,
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        }

    def conninfo(self, name: str | None = None) -> str:
        from psycopg.conninfo import make_conninfo

        return make_conninfo(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname=name or self.name,
            connect_timeout=10,
        )


@dataclass(frozen=True)
class Settings:
    db: Datenbank
    backup_dir: Path
    age_recipient: str | None
    backup_zeit: time
    behalten: int
    alarm_an: str | None
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str | None = field(repr=False)
    health_urls: tuple[str, ...]
    health_sekunden: int
    backup_max_stunden: int

    @classmethod
    def aus_env(cls, env: dict[str, str] | None = None) -> "Settings":
        e = dict(os.environ if env is None else env)
        empfaenger = e.get("BACKUP_AGE_RECIPIENT", "").strip() or None
        if empfaenger is not None and not _AGE_RECIPIENT.fullmatch(empfaenger):
            raise ValueError("BACKUP_AGE_RECIPIENT ist kein öffentlicher age-Schlüssel (age1…)")
        stunde, minute = (int(x) for x in e.get("BACKUP_ZEIT", "01:05").split(":"))
        urls = tuple(
            u.strip()
            for u in e.get(
                "HEALTH_URLS",
                "http://api:8000/health,http://web:3000/healthz,https://luibui.com/healthz",
            ).split(",")
            if u.strip()
        )
        for u in urls:
            if urlsplit(u).scheme not in ("http", "https"):
                raise ValueError("HEALTH_URLS: nur http und https")
        return cls(
            db=Datenbank.aus_url(e["DATABASE_URL"]),
            backup_dir=Path(e.get("BACKUP_DIR", "/backup")),
            age_recipient=empfaenger,
            backup_zeit=time(stunde, minute),
            behalten=max(1, int(e.get("BACKUP_BEHALTEN", "14"))),
            alarm_an=e.get("ALARM_AN", "").strip() or None,
            smtp_host=e.get("SMTP_HOST", "mail.agenturserver.de"),
            smtp_port=int(e.get("SMTP_PORT", "587")),
            smtp_user=e.get("SMTP_USER", "noreply@luibui.com"),
            smtp_password=e.get("SMTP_PASSWORD") or None,
            health_urls=urls,
            health_sekunden=max(30, int(e.get("HEALTH_SEKUNDEN", "300"))),
            backup_max_stunden=int(e.get("BACKUP_MAX_STUNDEN", "26")),
        )
