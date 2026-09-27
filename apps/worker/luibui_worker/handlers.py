"""Job kinds and the dotted path of the function that handles them in the child process.

A handler receives a JobContext and returns a JSON-serialisable dict. It runs in a child process
with an empty environment and must never execute package content.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class JobContext:
    job_id: str
    kind: str
    payload: dict[str, Any]
    scratch: Path


class Handler(Protocol):
    def __call__(self, ctx: JobContext) -> dict[str, Any]: ...


def scan(ctx: JobContext) -> dict[str, Any]:
    """Scan the files the API unpacked into the scratch directory and return the report."""
    import uuid

    from luibui_scan.models import ScanArt
    from luibui_scan.report import build_report
    from luibui_scan.scan import Eingabe, scan_prepared

    if not any(ctx.scratch.iterdir()):
        raise RuntimeError("leeres Prüfverzeichnis")
    options = ctx.payload.get("options")
    result = scan_prepared(
        ctx.scratch,
        Eingabe(ctx.payload["eingabe"]),
        ScanArt(ctx.payload["scan_art"]),
        options=options if isinstance(options, dict) else None,
    )
    report = build_report(
        result, name=str(ctx.payload["name"]), scan_id=uuid.UUID(ctx.payload["scan_id"])
    )
    return {"report": report}


DEFAULT_HANDLERS: dict[str, str] = {
    "scan": "luibui_worker.handlers:scan",
}
