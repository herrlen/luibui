"""Worker loop: claim a job, run it in a child process, record the outcome, delete the scratch.

One job at a time (Konzept §8). On start, jobs whose lock expired are released and orphaned
scratch directories from a crashed worker are removed.
"""

import logging
import signal
import threading
from collections.abc import Mapping
from types import FrameType

from sqlalchemy import Engine, create_engine

from luibui_worker import queue
from luibui_worker.handlers import DEFAULT_HANDLERS
from luibui_worker.runner import Outcome, run_in_child
from luibui_worker.scratch import create_scratch, remove_scratch, sweep_orphans
from luibui_worker.settings import MAX_JOB_TIMEOUT_SECONDS, WorkerSettings, get_settings

log = logging.getLogger("luibui_worker")


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

    def stop(self, *_: object) -> None:
        self._stop.set()

    def recover(self) -> None:
        """Release expired locks, then remove scratch entries of jobs that no longer run."""
        with self.engine.begin() as conn:
            released = queue.release_stale(
                conn, MAX_JOB_TIMEOUT_SECONDS, self.settings.stale_grace_seconds
            )
            running = queue.running_job_ids(conn)
        if released:
            log.warning("released %d stale job(s)", len(released))
        self.settings.scratch_root.mkdir(parents=True, exist_ok=True)
        removed = sweep_orphans(self.settings.scratch_root, keep=running)
        if removed:
            log.warning("removed %d orphaned scratch entr(y/ies)", len(removed))

    def run_once(self) -> bool:
        """Process at most one job. Returns False if the queue was empty."""
        with self.engine.begin() as conn:
            job = queue.claim(conn, self.settings.worker_id)
        if job is None:
            return False

        timeout = min(job.timeout_seconds, MAX_JOB_TIMEOUT_SECONDS)
        handler = self.handlers.get(job.kind)
        scratch = None
        error: str | None
        try:
            if handler is None:
                outcome, error = Outcome.FAILED, f"Unbekannte Job-Art: {job.kind[:50]}"
            else:
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
        log.info("job %s (%s): %s", job.id, job.kind, outcome)
        return True

    def run_forever(self) -> None:
        self.recover()
        log.info("worker %s ready", self.settings.worker_id)
        while not self._stop.is_set():
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
