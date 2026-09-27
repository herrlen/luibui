"""Entry point of the child process: ``python -m luibui_worker.child``.

Reads one job as JSON from stdin, runs the handler and writes {"ok": true, "result": …} to stdout.
On an exception it writes only the exception type and exits with 1, so package content from the
message never reaches the parent or the database.
"""

import importlib
import json
import os
import socket
import sys
import traceback
from pathlib import Path
from typing import Any

from luibui_worker.handlers import Handler, JobContext


def load_handler(dotted: str) -> Handler:
    module_name, _, attr = dotted.partition(":")
    handler: Handler = getattr(importlib.import_module(module_name), attr)
    return handler


class IsolationError(Exception):
    """Network isolation was required but could not be established."""


def isolate_network() -> None:
    """Move this process (and every scanner it starts) into an empty network namespace.

    Uses an unprivileged user namespace that maps only our own uid/gid, so file access in the
    scratch directory stays the same. Afterwards only a loopback interface exists. Required when
    ``LUIBUI_NETZ_ISOLIEREN=1`` (worker image default); fails closed.
    """
    # getattr: os.unshare exists only on Linux; elsewhere isolation fails closed.
    unshare = getattr(os, "unshare", None)
    flags = getattr(os, "CLONE_NEWUSER", 0) | getattr(os, "CLONE_NEWNET", 0)
    if unshare is None or not flags:
        raise IsolationError("nur unter Linux möglich")
    uid, gid = os.getuid(), os.getgid()
    try:
        unshare(flags)
        with open("/proc/self/setgroups", "w") as f:
            f.write("deny")
        with open("/proc/self/uid_map", "w") as f:
            f.write(f"{uid} {uid} 1")
        with open("/proc/self/gid_map", "w") as f:
            f.write(f"{gid} {gid} 1")
    except (OSError, AttributeError) as exc:
        raise IsolationError(type(exc).__name__) from None
    interfaces = {name for _, name in socket.if_nameindex()}
    if interfaces - {"lo"}:
        raise IsolationError("Netzwerkschnittstellen vorhanden")


def main() -> int:
    if os.environ.get("LUIBUI_NETZ_ISOLIEREN") == "1":
        try:
            isolate_network()
        except IsolationError:
            json.dump({"ok": False, "error": "Netzisolation nicht möglich"}, sys.stdout)
            return 1
    request: dict[str, Any] = json.load(sys.stdin)
    ctx = JobContext(
        job_id=request["job_id"],
        kind=request["kind"],
        payload=request["payload"],
        scratch=Path(request["scratch"]),
    )
    try:
        result = load_handler(request["handler"])(ctx)
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        json.dump({"ok": False, "error": type(exc).__name__}, sys.stdout)
        return 1
    json.dump({"ok": True, "result": result}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
