"""Run one job in an isolated child process with a hard timeout.

- empty environment: no DATABASE_URL, no secrets
- own session / process group: on timeout the whole group is killed, scanner subprocesses included
- working directory is the job's scratch directory
"""

import contextlib
import json
import logging
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CHILD_ENV_KEEP = ("LANG", "LC_ALL", "TZ", "LUIBUI_RULES_DIR", "LUIBUI_GITLEAKS")
"""Only non-secret settings reach the child: locale and where rules and scanners are."""


class Outcome(StrEnum):
    OK = "ok"
    FAILED = "failed"
    CRASHED = "crashed"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class RunResult:
    outcome: Outcome
    result: dict[str, Any] | None = None
    error: str | None = None
    """Short, content-free description suitable for the jobs table."""


def child_env(scratch: Path) -> dict[str, str]:
    env = {k: os.environ[k] for k in CHILD_ENV_KEEP if k in os.environ}
    env["PATH"] = os.pathsep.join(
        [str(Path(sys.executable).parent), "/usr/local/bin", "/usr/bin", "/bin"]
    )
    env["HOME"] = str(scratch)
    env["TMPDIR"] = str(scratch)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _kill_group(proc: subprocess.Popen[bytes], grace: float) -> None:
    for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, grace)):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=wait)
            # The group leader is gone; make sure no grandchild survives it.
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except subprocess.TimeoutExpired:
            continue


def run_in_child(
    *,
    handler: str,
    job_id: str,
    kind: str,
    payload: dict[str, Any],
    scratch: Path,
    timeout: float,
    kill_grace: float = 5.0,
    max_result_bytes: int = 20 * 1024 * 1024,
) -> RunResult:
    request = json.dumps(
        {
            "handler": handler,
            "job_id": job_id,
            "kind": kind,
            "payload": payload,
            "scratch": str(scratch),
        }
    ).encode()
    proc = subprocess.Popen(
        [sys.executable, "-I", "-m", "luibui_worker.child"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
        cwd=scratch,
        env=child_env(scratch),
        start_new_session=True,
        close_fds=True,
    )
    try:
        stdout, _ = proc.communicate(request, timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_group(proc, kill_grace)
        proc.communicate()
        return RunResult(Outcome.TIMEOUT, error=f"Zeitlimit von {int(timeout)} s überschritten")
    finally:
        if proc.poll() is None:
            _kill_group(proc, kill_grace)
        else:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)

    if len(stdout) > max_result_bytes:
        return RunResult(Outcome.FAILED, error="Ergebnis zu groß")
    try:
        message = json.loads(stdout) if stdout else None
    except json.JSONDecodeError:
        message = None

    if proc.returncode == 0 and isinstance(message, dict) and message.get("ok") is True:
        result = message.get("result")
        return RunResult(Outcome.OK, result=result if isinstance(result, dict) else {})
    if isinstance(message, dict) and message.get("ok") is False:
        return RunResult(Outcome.FAILED, error=f"Fehler im Job: {str(message.get('error'))[:100]}")
    return RunResult(Outcome.CRASHED, error=f"Job-Prozess abgestürzt (Exit-Code {proc.returncode})")
