"""Handlers for tests and operational self-checks. Not registered by default."""

import os
import subprocess
import sys
import time
from typing import Any

from luibui_worker.handlers import JobContext


def ok(ctx: JobContext) -> dict[str, Any]:
    (ctx.scratch / "work.txt").write_text("x")
    return {"env": sorted(os.environ), "scratch": str(ctx.scratch), "cwd": os.getcwd()}


def crash(ctx: JobContext) -> dict[str, Any]:
    """Leave files behind, then die hard, as a segfault in a parser would."""
    nested = ctx.scratch / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "leftover.bin").write_bytes(b"\x00" * 1024)
    nested.chmod(0o500)
    sys.stdout.flush()
    os._exit(int(ctx.payload.get("exit_code", 139)))


def fail(ctx: JobContext) -> dict[str, Any]:
    (ctx.scratch / "partial").write_text("x")
    raise RuntimeError("package content that must not reach the database")


def hang(ctx: JobContext) -> dict[str, Any]:
    """Start a grandchild (like a scanner subprocess) and hang, so the timeout must kill both."""
    child = subprocess.Popen(["sleep", "300"])  # noqa: S607 - fixed test command
    (ctx.scratch / "grandchild.pid").write_text(str(child.pid))
    if pid_file := ctx.payload.get("pid_file"):
        with open(pid_file, "w") as f:
            f.write(str(child.pid))
    time.sleep(300)
    return {}


def progress(ctx: JobContext) -> dict[str, Any]:
    """Valid and hostile progress messages, then a flood, then a grandchild that tries the pipe."""
    if ctx.melden is None:
        return {"ohne_kanal": True}
    ctx.melden({"schritt": 1, "von": 2, "titel": "A – Dateien"})
    ctx.melden({"schritt": 9, "von": 2, "titel": "zu weit"})
    ctx.melden({"schritt": 2, "von": 2, "titel": "B\u202e\x1b[31m" + "x" * 500})
    ctx.melden({"schritt": 2, "von": 2, "titel": "C", "extra": "nein"})
    for _ in range(5000):  # more than the pipe buffer: the child must never block
        ctx.melden({"schritt": 2, "von": 2, "titel": "Flut"})
    zaehlen = (
        "import os\n"
        "def offen(fd):\n"
        "    try:\n        os.fstat(fd)\n    except OSError:\n        return False\n"
        "    return True\n"
        "print(sum(offen(fd) for fd in range(3, 1024)))"
    )
    enkel = subprocess.run(  # noqa: S603 - fixed test command
        [sys.executable, "-I", "-c", zaehlen], check=True, capture_output=True, text=True
    )
    return {"offene_fds_im_enkel": int(enkel.stdout)}


def net(ctx: JobContext) -> dict[str, Any]:
    """Report the network interfaces the child sees (isolation check)."""
    import socket

    return {"interfaces": sorted(name for _, name in socket.if_nameindex())}


SELFTEST_HANDLERS: dict[str, str] = {
    "selftest.net": "luibui_worker.selftest:net",
    "selftest.progress": "luibui_worker.selftest:progress",
    "selftest.ok": "luibui_worker.selftest:ok",
    "selftest.crash": "luibui_worker.selftest:crash",
    "selftest.fail": "luibui_worker.selftest:fail",
    "selftest.hang": "luibui_worker.selftest:hang",
}
