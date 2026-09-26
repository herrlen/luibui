"""Path checks shared by ZIP entries, folder uploads and single files, and the only file writer.

A path is accepted only as a relative, '/'-separated name without '..', '.', empty segments,
backslashes, drive letters or control characters. Bidi and other format characters are allowed
here; the content analyzer reports them (Prüfkatalog B).
"""

import os
import re
import unicodedata
from pathlib import Path
from typing import IO

from luibui_scan.intake.errors import Ablehnung, IntakeRejectedError
from luibui_scan.intake.limits import Limits

_DRIVE = re.compile(r"^[A-Za-z]:")
_CHUNK = 64 * 1024


def check_path(raw: str, limits: Limits) -> str:
    """Return ``raw`` unchanged if it is a safe relative file path.

    Raises ``IntakeRejectedError`` otherwise.
    """
    if raw.startswith("/") or _DRIVE.match(raw):
        raise IntakeRejectedError(Ablehnung.PFAD_AUSSERHALB, raw)
    if not raw or "\\" in raw or any(unicodedata.category(c) == "Cc" for c in raw):
        raise IntakeRejectedError(Ablehnung.UNGUELTIGER_NAME, raw)
    segments = raw.split("/")
    if ".." in segments:
        raise IntakeRejectedError(Ablehnung.PFAD_AUSSERHALB, raw)
    if any(s in ("", ".") for s in segments):
        raise IntakeRejectedError(Ablehnung.UNGUELTIGER_NAME, raw)
    if len(raw.encode()) > limits.pfad_bytes or any(
        len(s.encode()) > limits.segment_bytes for s in segments
    ):
        raise IntakeRejectedError(Ablehnung.NAME_ZU_LANG, raw)
    if len(segments) > limits.tiefe:
        raise IntakeRejectedError(Ablehnung.ZU_TIEF, raw)
    return raw


def _key(path: str) -> str:
    return unicodedata.normalize("NFC", path).casefold()


class NameRegistry:
    """Refuses names that collide on a case-insensitive or normalizing file system.

    Also refuses a file whose name is used as a folder by another entry, in either order.
    """

    def __init__(self) -> None:
        self._files: set[str] = set()
        self._dirs: set[str] = set()

    def add_file(self, path: str) -> None:
        key = _key(path)
        parents = self._parents(key)
        if key in self._files or key in self._dirs or any(p in self._files for p in parents):
            raise IntakeRejectedError(Ablehnung.DOPPELTER_NAME, path)
        self._files.add(key)
        self._dirs.update(parents)

    def add_dir(self, path: str) -> None:
        key = _key(path)
        parents = [*self._parents(key), key]
        if any(p in self._files for p in parents):
            raise IntakeRejectedError(Ablehnung.DOPPELTER_NAME, path)
        self._dirs.update(parents)

    @staticmethod
    def _parents(key: str) -> list[str]:
        segments = key.split("/")
        return ["/".join(segments[:i]) for i in range(1, len(segments))]


class Budget:
    """Counts bytes as they are written. Header sizes are never trusted."""

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes
        self.used = 0

    def take(self, n: int, path: str) -> None:
        self.used += n
        if self.used > self.max_bytes:
            raise IntakeRejectedError(Ablehnung.ZU_GROSS, path)


def write_file(
    root: Path, rel: str, src: IO[bytes], budget: Budget, max_bytes: int | None = None
) -> int:
    """Copy ``src`` to ``root/rel`` and return the number of bytes written.

    ``rel`` must have passed ``check_path``. The file is created new (never overwritten, never
    through a symlink) with mode 0600. ``max_bytes`` caps this one file.
    """
    target = root.joinpath(*rel.split("/"))
    make_dirs(root, target.parent)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    written = 0
    with os.fdopen(fd, "wb") as out:
        while chunk := src.read(_CHUNK):
            written += len(chunk)
            if max_bytes is not None and written > max_bytes:
                raise IntakeRejectedError(Ablehnung.ZU_GROSS, rel)
            budget.take(len(chunk), rel)
            out.write(chunk)
    return written


def make_dirs(root: Path, directory: Path) -> None:
    """Create ``directory`` below ``root`` with mode 0700, refusing to pass through symlinks."""
    rel = directory.relative_to(root)
    current = root
    for part in rel.parts:
        current = current / part
        try:
            os.mkdir(current, 0o700)
        except FileExistsError:
            if current.is_symlink() or not current.is_dir():
                raise IntakeRejectedError(Ablehnung.VERKNUEPFUNG, str(rel)) from None
