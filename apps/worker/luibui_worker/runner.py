"""Run one job in an isolated child process with a hard timeout.

- empty environment: no DATABASE_URL, no secrets
- own session / process group: on timeout the whole group is killed, scanner subprocesses included
- working directory is the job's scratch directory
- progress: the child writes JSON lines to a pipe of its own; the parent checks every message
  (known keys, bounded numbers, short printable title) before passing it on, since the child
  handles hostile packages
"""

import contextlib
import json
import logging
import os
import signal
import subprocess
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CHILD_ENV_KEEP = (
    "LANG",
    "LC_ALL",
    "TZ",
    "LUIBUI_RULES_DIR",
    "LUIBUI_GITLEAKS",
    "LUIBUI_OSV_SCANNER",
    "LUIBUI_OSV_DB",
    "LUIBUI_MALWARE_DB",
    "LUIBUI_OPENGREP",
    "LUIBUI_OPENGREP_CACHE",
    "LUIBUI_PRESIDIO_PYTHON",
    "LUIBUI_YARA",
    "LUIBUI_NETZ_ISOLIEREN",
)
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


MAX_MELDUNGEN = 200


def fortschritt_pruefen(zeile: bytes) -> dict[str, Any] | None:
    """A progress message as the parent accepts it, or None."""
    try:
        m = json.loads(zeile)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(m, dict) or set(m) != {"schritt", "von", "titel"}:
        return None
    schritt, von, titel = m["schritt"], m["von"], m["titel"]
    if not (isinstance(schritt, int) and isinstance(von, int) and 1 <= schritt <= von <= 100):
        return None
    if not isinstance(titel, str):
        return None
    titel = "".join(c for c in titel if c.isprintable())[:80]
    return {"schritt": schritt, "von": von, "titel": titel}


def _lesen(fd: int, melden: Callable[[dict[str, Any]], None] | None) -> None:
    with os.fdopen(fd, "rb") as kanal:
        for n, zeile in enumerate(kanal):
            if n >= MAX_MELDUNGEN or len(zeile) > 1000:
                continue  # keep draining so the child never blocks on a full pipe
            m = fortschritt_pruefen(zeile)
            if m is not None and melden is not None:
                try:
                    melden(m)
                except Exception:
                    log.exception("progress callback failed")


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
    fortschritt: Callable[[dict[str, Any]], None] | None = None,
) -> RunResult:
    lesen, schreiben = os.pipe()
    request = json.dumps(
        {
            "handler": handler,
            "job_id": job_id,
            "kind": kind,
            "payload": payload,
            "scratch": str(scratch),
            "fortschritt_fd": schreiben,
        }
    ).encode()
    try:
        proc = subprocess.Popen(
            [sys.executable, "-I", "-m", "luibui_worker.child"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            cwd=scratch,
            env=child_env(scratch),
            start_new_session=True,
            close_fds=True,
            pass_fds=(schreiben,),
        )
    except BaseException:
        os.close(lesen)
        raise
    finally:
        os.close(schreiben)  # only the child keeps the write end; EOF when it exits
    leser = threading.Thread(target=_lesen, args=(lesen, fortschritt), daemon=True)
    leser.start()
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
        leser.join(timeout=kill_grace)

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
