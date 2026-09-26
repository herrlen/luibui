"""Entry point of the child process: ``python -m luibui_worker.child``.

Reads one job as JSON from stdin, runs the handler and writes {"ok": true, "result": …} to stdout.
On an exception it writes only the exception type and exits with 1, so package content from the
message never reaches the parent or the database.
"""

import importlib
import json
import sys
import traceback
from pathlib import Path
from typing import Any

from luibui_worker.handlers import Handler, JobContext


def load_handler(dotted: str) -> Handler:
    module_name, _, attr = dotted.partition(":")
    handler: Handler = getattr(importlib.import_module(module_name), attr)
    return handler


def main() -> int:
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
