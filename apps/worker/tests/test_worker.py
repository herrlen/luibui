"""Job loop against a real database (marked db)."""

import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from luibui_worker import queue
from luibui_worker.main import Worker
from luibui_worker.scratch import create_scratch

pytestmark = pytest.mark.db


def enqueue(engine: Engine, kind: str, **columns: Any) -> uuid.UUID:
    payload = columns.pop("payload", {})
    cols = {"kind": kind, "payload": payload, **columns}
    names = ", ".join(cols)
    values = ", ".join(f"CAST(:{k} AS jsonb)" if k == "payload" else f":{k}" for k in cols)
    params = {**cols, "payload": json.dumps(payload)}
    with engine.begin() as conn:
        return conn.execute(
            text(f"INSERT INTO jobs ({names}) VALUES ({values}) RETURNING id"),  # noqa: S608 - test helper, fixed column names
            params,
        ).scalar_one()


def job_row(engine: Engine, job_id: uuid.UUID) -> dict[str, Any]:
    with engine.connect() as conn:
        row = (
            conn.execute(text("SELECT * FROM jobs WHERE id = :id"), {"id": job_id}).mappings().one()
        )
        return dict(row)


def test_empty_queue(worker: Worker) -> None:
    assert worker.run_once() is False


def test_successful_job_is_done_and_scratch_removed(
    worker: Worker, engine: Engine, scratch_root: Path
) -> None:
    job_id = enqueue(engine, "selftest.ok")
    assert worker.run_once() is True
    row = job_row(engine, job_id)
    assert row["status"] == "done"
    assert row["attempts"] == 1
    assert row["finished_at"] is not None
    assert list(scratch_root.iterdir()) == []


def test_crashing_job_leaves_no_scratch(worker: Worker, engine: Engine, scratch_root: Path) -> None:
    """Definition of Done Sprint 0: the worker cleans up scratch even after a deliberate crash."""
    job_id = enqueue(engine, "selftest.crash", payload={"exit_code": 139})
    assert worker.run_once() is True
    row = job_row(engine, job_id)
    assert row["status"] == "failed"
    assert "139" in row["error"]
    assert list(scratch_root.iterdir()) == []


def test_failing_job_does_not_store_exception_message(
    worker: Worker, engine: Engine, scratch_root: Path
) -> None:
    job_id = enqueue(engine, "selftest.fail")
    worker.run_once()
    row = job_row(engine, job_id)
    assert row["status"] == "failed"
    assert "package content" not in row["error"]
    assert list(scratch_root.iterdir()) == []


def test_timeout_fails_job_and_cleans_up(
    worker: Worker, engine: Engine, scratch_root: Path
) -> None:
    job_id = enqueue(engine, "selftest.hang", timeout_seconds=2)
    worker.run_once()
    row = job_row(engine, job_id)
    assert row["status"] == "failed"
    assert "Zeitlimit" in row["error"]
    assert list(scratch_root.iterdir()) == []


def test_unknown_kind_fails_without_scratch(
    worker: Worker, engine: Engine, scratch_root: Path
) -> None:
    job_id = enqueue(engine, "does.not.exist")
    worker.run_once()
    assert job_row(engine, job_id)["status"] == "failed"
    assert list(scratch_root.iterdir()) == []


def test_retry_until_max_attempts(worker: Worker, engine: Engine) -> None:
    job_id = enqueue(engine, "selftest.fail", max_attempts=2)
    worker.run_once()
    row = job_row(engine, job_id)
    assert row["status"] == "queued"
    assert row["run_after"] > row["created_at"]
    with engine.begin() as conn:
        conn.execute(text("UPDATE jobs SET run_after = now() WHERE id = :id"), {"id": job_id})
    worker.run_once()
    assert job_row(engine, job_id)["status"] == "failed"


def test_skip_locked_lets_two_workers_take_different_jobs(engine: Engine) -> None:
    first, second = enqueue(engine, "selftest.ok"), enqueue(engine, "selftest.ok")
    with engine.connect() as holder, holder.begin():
        locked = holder.execute(
            text("SELECT id FROM jobs WHERE id = :id FOR UPDATE"), {"id": first}
        ).scalar_one()
        with engine.begin() as other:
            claimed = queue.claim(other, "other-worker")
        assert locked == first
        assert claimed is not None
        assert claimed.id == second


def test_future_jobs_are_not_claimed(worker: Worker, engine: Engine) -> None:
    enqueue(engine, "selftest.ok")
    with engine.begin() as conn:
        conn.execute(text("UPDATE jobs SET run_after = now() + interval '1 hour'"))
    assert worker.run_once() is False


def test_recover_releases_stale_jobs_and_sweeps_orphans(
    worker: Worker, engine: Engine, scratch_root: Path
) -> None:
    stale = enqueue(engine, "selftest.ok", max_attempts=2, timeout_seconds=1)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE jobs SET status = 'running', attempts = 1, locked_by = 'dead', "
                "locked_at = now() - interval '10 minutes' WHERE id = :id"
            ),
            {"id": stale},
        )
    create_scratch(scratch_root, stale)
    (scratch_root / str(stale) / "leftover").write_text("x")
    worker.recover()
    assert job_row(engine, stale)["status"] == "queued"
    assert list(scratch_root.iterdir()) == []
