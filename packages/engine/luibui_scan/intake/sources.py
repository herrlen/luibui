"""Single file, file selection (also folder uploads), local folders and pasted text.

Relative paths from folder uploads are checked exactly like ZIP entries.
"""

import io
import os
import stat
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import IO

from luibui_scan.intake.errors import Ablehnung, IntakeRejectedError
from luibui_scan.intake.limits import DEFAULT_LIMITS, Limits
from luibui_scan.intake.paths import Budget, NameRegistry, check_path, write_file

TEXT_NAME = "eingabe.md"
SKIPPED_DIRS = frozenset({".git"})
"""Version-control metadata is not part of a package and is left out of local folder scans."""


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


def accept_directory(source: Path, root: Path, limits: Limits = DEFAULT_LIMITS) -> list[str]:
    """Copy a local folder (CLI ``luibui scan <ordner>``) like a file selection.

    Symlinks and special files are refused instead of followed. ``.git`` folders are skipped.
    """
    return accept_selection(_walk_local(source), root, limits)


def _walk_local(source: Path) -> Iterator[tuple[str, IO[bytes]]]:
    pending = [""]
    while pending:
        rel = pending.pop()
        with os.scandir(source / rel if rel else source) as it:
            entries = sorted(it, key=lambda e: e.name)
        for item in entries:
            child = f"{rel}/{item.name}" if rel else item.name
            mode = item.stat(follow_symlinks=False).st_mode
            if stat.S_ISDIR(mode):
                if item.name not in SKIPPED_DIRS:
                    pending.append(child)
            elif stat.S_ISREG(mode):
                fd = os.open(item.path, os.O_RDONLY | os.O_NOFOLLOW)
                with os.fdopen(fd, "rb") as f:
                    yield child, f
            else:
                raise IntakeRejectedError(Ablehnung.VERKNUEPFUNG, child)
