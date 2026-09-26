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
    raise NotImplementedError("Scan-Jobs kommen mit Sprint 1 (S1-1).")


DEFAULT_HANDLERS: dict[str, str] = {
    "scan": "luibui_worker.handlers:scan",
}
