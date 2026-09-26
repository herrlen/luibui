"""Job queue on PostgreSQL with SELECT … FOR UPDATE SKIP LOCKED.

Only the worker's parent process talks to the database; the child that handles package content
never gets credentials.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, text

_CLAIM = text("""
UPDATE jobs
SET status = 'running', locked_at = now(), locked_by = :worker, attempts = attempts + 1
WHERE id = (
    SELECT id FROM jobs
    WHERE status = 'queued' AND run_after <= now()
    ORDER BY run_after, created_at
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
RETURNING id, kind, payload, timeout_seconds, attempts, max_attempts
""")

_DONE = text("""
UPDATE jobs SET status = 'done', finished_at = now(), locked_at = NULL, error = NULL
WHERE id = :id AND locked_by = :worker AND status = 'running'
""")

_FAIL = text("""
UPDATE jobs
SET status = CASE WHEN attempts < max_attempts THEN 'queued'::job_status
                  ELSE 'failed'::job_status END,
    run_after = CASE WHEN attempts < max_attempts
                     THEN now() + make_interval(secs => 30 * attempts)
                     ELSE run_after END,
    finished_at = CASE WHEN attempts < max_attempts THEN NULL ELSE now() END,
    locked_at = NULL,
    error = :error
WHERE id = :id AND locked_by = :worker AND status = 'running'
""")

_RELEASE_STALE = text("""
UPDATE jobs
SET status = CASE WHEN attempts < max_attempts THEN 'queued'::job_status
                  ELSE 'failed'::job_status END,
    finished_at = CASE WHEN attempts < max_attempts THEN NULL ELSE now() END,
    locked_at = NULL,
    error = 'Worker nicht mehr erreichbar (Sperre abgelaufen)'
WHERE status = 'running'
  AND locked_at < now() - make_interval(secs => LEAST(timeout_seconds, :max_timeout) + :grace)
RETURNING id
""")

_RUNNING_IDS = text("SELECT id FROM jobs WHERE status = 'running'")
_KEEP_IDS = text(
    "SELECT id FROM jobs WHERE status = 'running' OR (status = 'queued' AND attempts = 0)"
)
_KNOWN_IDS = text("SELECT id FROM jobs WHERE id = ANY(:ids)")


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    id: uuid.UUID
    kind: str
    payload: dict[str, Any]
    timeout_seconds: int
    attempts: int
    max_attempts: int


def claim(conn: Connection, worker_id: str) -> ClaimedJob | None:
    row = conn.execute(_CLAIM, {"worker": worker_id}).mappings().first()
    if row is None:
        return None
    return ClaimedJob(**row)


def mark_done(conn: Connection, job_id: uuid.UUID, worker_id: str) -> None:
    conn.execute(_DONE, {"id": job_id, "worker": worker_id})


def mark_failed(conn: Connection, job_id: uuid.UUID, worker_id: str, error: str) -> None:
    conn.execute(_FAIL, {"id": job_id, "worker": worker_id, "error": error[:500]})


def release_stale(conn: Connection, max_timeout: int, grace: int) -> list[uuid.UUID]:
    rows = conn.execute(_RELEASE_STALE, {"max_timeout": max_timeout, "grace": grace})
    return [r[0] for r in rows]


def running_job_ids(conn: Connection) -> set[uuid.UUID]:
    return {r[0] for r in conn.execute(_RUNNING_IDS)}


def scratch_to_keep(conn: Connection) -> set[uuid.UUID]:
    """Running jobs, and queued jobs that never started: the API may have prepared their input.
    A job queued again after a failed attempt starts with an empty directory instead."""
    return {r[0] for r in conn.execute(_KEEP_IDS)}


def known_job_ids(conn: Connection, ids: list[uuid.UUID]) -> set[uuid.UUID]:
    return {r[0] for r in conn.execute(_KNOWN_IDS, {"ids": ids})} if ids else set()
