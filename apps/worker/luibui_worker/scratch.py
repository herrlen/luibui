"""Per-job scratch directories under SCRATCH_ROOT, removed no matter how the job ended."""

import logging
import os
import shutil
import stat
import uuid
from collections.abc import Iterable
from pathlib import Path

log = logging.getLogger(__name__)


def scratch_path(root: Path, job_id: uuid.UUID) -> Path:
    return root / str(job_id)


def create_scratch(root: Path, job_id: uuid.UUID) -> Path:
    path = scratch_path(root, job_id)
    path.mkdir(mode=0o700)
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


def sweep_orphans(root: Path, keep: Iterable[uuid.UUID] = ()) -> list[str]:
    """Remove leftovers from crashed workers. Returns the removed entry names."""
    keep_names = {str(k) for k in keep}
    removed = []
    for entry in root.iterdir():
        if entry.name in keep_names:
            continue
        try:
            remove_scratch(entry)
        except OSError:
            log.exception("could not remove orphaned scratch entry %s", entry.name)
            continue
        removed.append(entry.name)
    return removed
