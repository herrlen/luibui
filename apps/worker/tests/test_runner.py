"""Child-process runner, without a database."""

import json
import os
import uuid
from pathlib import Path

import pytest

from luibui_worker.runner import Outcome, run_in_child


def _run(tmp_path: Path, kind: str, timeout: float = 20, **payload: object):  # type: ignore[no-untyped-def]
    scratch = tmp_path / str(uuid.uuid4())
    scratch.mkdir()
    return run_in_child(
        handler=f"luibui_worker.selftest:{kind}",
        job_id="j",
        kind=kind,
        payload=dict(payload),
        scratch=scratch,
        timeout=timeout,
        kill_grace=1.0,
    )


def test_ok_returns_result_and_runs_with_empty_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret")
    monkeypatch.setenv("MASTER_KEY", "secret")
    result = _run(tmp_path, "ok")
    assert result.outcome is Outcome.OK
    assert result.result is not None
    env = set(result.result["env"])
    assert "DATABASE_URL" not in env
    assert "MASTER_KEY" not in env
    # LC_CTYPE is set by Python's locale coercion (PEP 538), __CF_* by macOS itself.
    allowed = {"PATH", "HOME", "TMPDIR", "PYTHONDONTWRITEBYTECODE", "LANG", "LC_ALL", "TZ"}
    allowed |= {"LC_CTYPE", "__CF_USER_TEXT_ENCODING"}
    assert env <= allowed
    assert Path(result.result["cwd"]).resolve() == Path(result.result["scratch"]).resolve()


def test_exception_is_reported_without_message(tmp_path: Path) -> None:
    result = _run(tmp_path, "fail")
    assert result.outcome is Outcome.FAILED
    assert result.error is not None
    assert "RuntimeError" in result.error
    assert "package content" not in result.error


def test_hard_crash_is_detected(tmp_path: Path) -> None:
    result = _run(tmp_path, "crash", exit_code=139)
    assert result.outcome is Outcome.CRASHED
    assert "139" in (result.error or "")


def test_timeout_kills_the_whole_process_group(tmp_path: Path) -> None:
    pid_file = tmp_path / "grandchild.pid"
    result = _run(tmp_path, "hang", timeout=2, pid_file=str(pid_file))
    assert result.outcome is Outcome.TIMEOUT
    grandchild = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(grandchild, 0)


def test_request_reaches_child_as_json(tmp_path: Path) -> None:
    # payload with characters that would break naive quoting
    result = _run(tmp_path, "ok", note="'; rm -rf / #\"")
    assert result.outcome is Outcome.OK
    json.dumps(result.result)
