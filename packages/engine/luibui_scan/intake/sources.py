"""Single file, file selection (also folder uploads) and pasted text.

Relative paths from folder uploads are checked exactly like ZIP entries.
"""

import io
from collections.abc import Iterable
from pathlib import Path
from typing import IO

from luibui_scan.intake.errors import Ablehnung, IntakeRejectedError
from luibui_scan.intake.limits import DEFAULT_LIMITS, Limits
from luibui_scan.intake.paths import Budget, NameRegistry, check_path, write_file

TEXT_NAME = "eingabe.md"


def accept_file(name: str, src: IO[bytes], root: Path, limits: Limits = DEFAULT_LIMITS) -> str:
    """Store one uploaded file under its own name; return that name."""
    check_path(name, limits)
    if "/" in name:
        raise IntakeRejectedError(Ablehnung.UNGUELTIGER_NAME, name)
    write_file(root, name, src, Budget(limits.einzeldatei_bytes))
    return name


def accept_selection(
    items: Iterable[tuple[str, IO[bytes]]], root: Path, limits: Limits = DEFAULT_LIMITS
) -> list[str]:
    """Store several files with their relative paths; return the paths, sorted."""
    names = NameRegistry()
    budget = Budget(limits.auswahl_bytes)
    stored: list[str] = []
    for rel, src in items:
        if len(stored) >= limits.auswahl_dateien:
            raise IntakeRejectedError(Ablehnung.ZU_VIELE_DATEIEN)
        names.add_file(check_path(rel, limits))
        write_file(root, rel, src, budget)
        stored.append(rel)
    return sorted(stored)


def accept_text(text: str, root: Path, limits: Limits = DEFAULT_LIMITS) -> str:
    """Store pasted text as UTF-8 in ``eingabe.md``; return that name."""
    data = text.encode("utf-8", errors="replace")
    if len(data) > limits.text_bytes:
        raise IntakeRejectedError(Ablehnung.ZU_GROSS)
    write_file(root, TEXT_NAME, io.BytesIO(data), Budget(limits.text_bytes))
    return TEXT_NAME
