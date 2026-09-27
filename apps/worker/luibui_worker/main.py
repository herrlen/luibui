"""Worker loop: claim a job, run it in a child process, record the outcome, delete the scratch.

One job at a time (Konzept §8). On start, jobs whose lock expired are released and orphaned
scratch directories from a crashed worker are removed.
"""

import logging
import signal
import threading
import uuid
from collections.abc import Mapping
from pathlib import Path
from types import FrameType

from sqlalchemy import Engine, create_engine

from luibui_worker import maintenance, malwaredb, osvdb, queue, results
from luibui_worker.handlers import DEFAULT_HANDLERS
from luibui_worker.runner import Outcome, run_in_child
from luibui_worker.scratch import create_scratch, remove_scratch, scratch_path, sweep_orphans
from luibui_worker.settings import MAX_JOB_TIMEOUT_SECONDS, WorkerSettings, get_settings

log = logging.getLogger("luibui_worker")

SWEEP_MIN_AGE_SECONDS = 600


def _uuid_entries(root: Path) -> list[uuid.UUID]:
    if not root.is_dir():
        return []
    ids = []
    for entry in root.iterdir():
        try:
            ids.append(uuid.UUID(entry.name))
        except ValueError:
            continue
    return ids


class Worker:
    def __init__(
        self,
        settings: WorkerSettings,
        engine: Engine | None = None,
        handlers: Mapping[str, str] | None = None,
    ) -> None:
        self.settings = settings
        self.engine = engine or create_engine(
            settings.database_url.get_secret_value(), pool_size=2, pool_pre_ping=True
        )
        self.handlers = dict(DEFAULT_HANDLERS if handlers is None else handlers)
        self._stop = threading.Event()
        self._housekeeping = maintenance.Every(3600)

    def stop(self, *_: object) -> None:
        self._stop.set()

    def recover(self) -> None:
        """Release expired locks, then remove scratch entries of jobs that no longer run."""
        with self.engine.begin() as conn:
            released = queue.release_stale(
                conn, MAX_JOB_TIMEOUT_SECONDS, self.settings.stale_grace_seconds
            )
            keep = queue.scratch_to_keep(conn)
            known = queue.known_job_ids(conn, _uuid_entries(self.settings.scratch_root))
        if released:
            log.warning("released %d stale job(s)", len(released))
        self.settings.scratch_root.mkdir(parents=True, exist_ok=True)
        removed = sweep_orphans(
            self.settings.scratch_root,
            keep=keep,
            known=known,
            min_age_seconds=SWEEP_MIN_AGE_SECONDS,
        )
        if removed:
            log.warning("removed %d orphaned scratch entr(y/ies)", len(removed))

    def run_once(self) -> bool:
        """Process at most one job. Returns False if the queue was empty."""
        with self.engine.begin() as conn:
            job = queue.claim(conn, self.settings.worker_id)
        if job is None:
            return False

        timeout = min(job.timeout_seconds, MAX_JOB_TIMEOUT_SECONDS)
        scan_id = results.scan_id_of(job.kind, job.payload)
        if scan_id is not None:
            with self.engine.begin() as conn:
                results.mark_running(conn, scan_id)
        handler = self.handlers.get(job.kind)
        scratch = None
        error: str | None
        try:
            if handler is None:
                outcome, error = Outcome.FAILED, f"Unbekannte Job-Art: {job.kind[:50]}"
            else:
                if job.attempts > 1:
                    # A retry never sees what an earlier attempt left behind.
                    remove_scratch(scratch_path(self.settings.scratch_root, job.id))
                scratch = create_scratch(self.settings.scratch_root, job.id)
                result = run_in_child(
                    handler=handler,
                    job_id=str(job.id),
                    kind=job.kind,
                    payload=job.payload,
                    scratch=scratch,
                    timeout=timeout,
                    kill_grace=self.settings.kill_grace_seconds,
                    max_result_bytes=self.settings.max_result_bytes,
                )
                outcome, error = result.outcome, result.error
                if scan_id is not None and outcome is Outcome.OK:
                    with self.engine.begin() as conn:
                        results.record_report(conn, scan_id, (result.result or {}).get("report"))
        except results.InvalidReportError:
            log.exception("job %s: invalid report", job.id)
            outcome, error = Outcome.FAILED, "Ungültiger Bericht"
        except Exception as exc:
            log.exception("job %s: worker error", job.id)
            outcome, error = Outcome.FAILED, f"Worker-Fehler: {type(exc).__name__}"
        finally:
            if scratch is not None:
                try:
                    remove_scratch(scratch)
                except OSError:
                    log.exception("job %s: scratch could not be removed", job.id)

        with self.engine.begin() as conn:
            if outcome is Outcome.OK:
                queue.mark_done(conn, job.id, self.settings.worker_id)
            else:
                queue.mark_failed(conn, job.id, self.settings.worker_id, error or outcome)
                if scan_id is not None:
                    results.mark_failed(conn, scan_id, error or outcome)
        log.info("job %s (%s): %s", job.id, job.kind, outcome)
        return True

    def refresh_databases(self) -> None:
        """Between jobs only: the parent has network, the scanning child never does."""
        if self.settings.osv_refresh:
            osvdb.refresh(self.settings.osv_db, self.settings.osv_max_age_hours * 3600)
        if self.settings.malware_refresh:
            malwaredb.refresh(self.settings.malware_db, self.settings.malware_max_age_hours * 3600)

    def housekeeping(self) -> None:
        if not self._housekeeping.due():
            return
        with self.engine.begin() as conn:
            purged = maintenance.purge_expired_quickscans(conn)
        if purged:
            log.info("deleted %d expired quick scan(s)", purged)

    def run_forever(self) -> None:
        self.recover()
        self.refresh_databases()
        log.info("worker %s ready", self.settings.worker_id)
        while not self._stop.is_set():
            self.refresh_databases()
            try:
                self.housekeeping()
            except Exception:
                log.exception("housekeeping failed")
            try:
                worked = self.run_once()
            except Exception:
                log.exception("queue error, retrying")
                worked = False
            if not worked:
                self._stop.wait(self.settings.poll_interval_seconds)
        log.info("worker %s stopped", self.settings.worker_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    worker = Worker(get_settings())

    def _handle(signum: int, frame: FrameType | None) -> None:
        worker.stop()

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)
    worker.run_forever()


if __name__ == "__main__":
    main()
