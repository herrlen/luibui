"""Housekeeping between jobs (parent process only).

Quick scans keep their report for 7 days (Konzept §2, ENTWICKLERREGELN G2). Afterwards the scan and
its findings are deleted, not just hidden.
"""

import logging
import time

from sqlalchemy import Connection, text

log = logging.getLogger(__name__)

_PURGE = text(
    "DELETE FROM scans WHERE scan_art = 'schnell' AND expires_at IS NOT NULL AND expires_at < now()"
)


def purge_expired_quickscans(conn: Connection) -> int:
    """Delete expired quick scans; findings and jobs go with them (ON DELETE CASCADE)."""
    return conn.execute(_PURGE).rowcount or 0


class Every:
    """True at most once per ``seconds``."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self._last = float("-inf")

    def due(self) -> bool:
        now = time.monotonic()
        if now - self._last < self.seconds:
            return False
        self._last = now
        return True
