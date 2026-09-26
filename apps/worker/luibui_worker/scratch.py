"""Per-job scratch directories under SCRATCH_ROOT, removed no matter how the job ended."""

import logging
import os
import shutil
import stat
import time
import uuid
from collections.abc import Iterable
from pathlib import Path

log = logging.getLogger(__name__)


def scratch_path(root: Path, job_id: uuid.UUID) -> Path:
    return root / str(job_id)


def create_scratch(root: Path, job_id: uuid.UUID) -> Path:
    """Create the job's directory, or take over the one the API prepared for a scan upload."""
    path = scratch_path(root, job_id)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        if path.is_symlink() or not path.is_dir():
            raise
        os.chmod(path, stat.S_IRWXU)
    return path


def _make_writable_and_retry(func: object, path: str, exc: BaseException) -> None:
    """rmtree error hook: hostile content may leave read-only directories behind."""
    if not isinstance(exc, PermissionError):
        raise exc
    parent = os.path.dirname(path)
    os.chmod(parent, stat.S_IRWXU)
    if os.path.isdir(path) and not os.path.islink(path):
        os.chmod(path, stat.S_IRWXU)
        shutil.rmtree(path, onexc=_make_writable_and_retry)
    else:
        os.unlink(path)


def remove_scratch(path: Path) -> None:
    """Delete a scratch directory completely. Never follows symlinks out of it."""
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or not path.is_dir():
        path.unlink()
        return
    os.chmod(path, stat.S_IRWXU)
    shutil.rmtree(path, onexc=_make_writable_and_retry)


def sweep_orphans(
    root: Path,
    keep: Iterable[uuid.UUID] = (),
    known: Iterable[uuid.UUID] | None = None,
    min_age_seconds: float = 0,
) -> list[str]:
    """Remove leftovers from crashed workers. Returns the removed entry names.

    ``keep`` stays. Entries of ``known`` jobs go. Entries no job row knows go only once they are
    older than ``min_age_seconds``: the API writes an upload before its job row is committed.
    Without ``known`` every entry counts as known.
    """
    keep_names = {str(k) for k in keep}
    known_names = None if known is None else {str(k) for k in known}
    cutoff = time.time() - min_age_seconds
    removed = []
    for entry in root.iterdir():
        if entry.name in keep_names:
            continue
        if known_names is not None and entry.name not in known_names:
            try:
                if entry.lstat().st_mtime > cutoff:
                    continue
            except FileNotFoundError:
                continue
        try:
            remove_scratch(entry)
        except OSError:
            log.exception("could not remove orphaned scratch entry %s", entry.name)
            continue
        removed.append(entry.name)
    return removed
