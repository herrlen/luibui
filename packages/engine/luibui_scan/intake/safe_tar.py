"""Unpacking tar archives, plain or compressed with gzip, bzip2 or xz (Scanner-Matrix ARC-01).

Same rules as ``safe_extract`` for ZIP: every member is checked before the first byte is written,
only regular files and folders are accepted, links and devices refuse the whole archive. Tar has no
central directory, so the archive is read twice as a stream: first to check, then to write. The
first pass stops as soon as the unpacked size passes the limit, so a tar bomb costs at most that
much decompression.
"""

import tarfile
from pathlib import Path

from luibui_scan.intake.errors import Ablehnung, IntakeRejectedError
from luibui_scan.intake.limits import DEFAULT_LIMITS, Limits
from luibui_scan.intake.paths import Budget, NameRegistry, check_path, make_dirs, write_file

_TAR_ERRORS = (tarfile.TarError, EOFError, OSError, ValueError)


def is_tar(archive: Path) -> bool:
    """True for a tar archive, also inside gzip, bzip2 or xz. Reads at most one header."""
    try:
        with tarfile.open(archive, "r|*") as tf:
            return tf.next() is not None
    except _TAR_ERRORS:
        return False


def extract_tar(archive: Path, root: Path, limits: Limits = DEFAULT_LIMITS) -> list[str]:
    """Unpack ``archive`` into the existing directory ``root``; return the file paths, sorted."""
    packed = archive.stat().st_size
    if packed > limits.zip_gepackt_bytes:
        raise IntakeRejectedError(Ablehnung.ZU_GROSS)
    try:
        files, dirs = _check(archive, packed, limits)
        for d in dirs:
            make_dirs(root, root.joinpath(*d.split("/")))
        budget = Budget(limits.zip_entpackt_bytes)
        with tarfile.open(archive, "r|*") as tf:
            for member in tf:
                if not member.isfile():
                    continue
                src = tf.extractfile(member)
                if src is None:  # pragma: no cover - isfile() members always have data
                    raise IntakeRejectedError(Ablehnung.DEFEKTES_ARCHIV, member.name)
                write_file(root, member.name, src, budget, max_bytes=member.size)
    except _TAR_ERRORS as exc:
        raise IntakeRejectedError(Ablehnung.DEFEKTES_ARCHIV) from exc
    return sorted(files)


def _check(archive: Path, packed: int, limits: Limits) -> tuple[list[str], list[str]]:
    names = NameRegistry()
    files: list[str] = []
    dirs: list[str] = []
    declared = 0
    with tarfile.open(archive, "r|*") as tf:
        for count, member in enumerate(tf, start=1):
            if count > limits.zip_eintraege:
                raise IntakeRejectedError(Ablehnung.ZU_VIELE_DATEIEN)
            raw = member.name.removesuffix("/")
            if member.isdir():
                names.add_dir(check_path(raw, limits))
                dirs.append(raw)
                continue
            if not member.isfile():
                # Symlinks, hardlinks, devices and FIFOs: refuse, never follow.
                raise IntakeRejectedError(Ablehnung.VERKNUEPFUNG, raw)
            names.add_file(check_path(raw, limits))
            declared += member.size
            if declared > limits.zip_entpackt_bytes:
                raise IntakeRejectedError(Ablehnung.ZU_GROSS, raw)
            files.append(raw)
    if declared >= limits.kompressionsrate_ab_bytes and declared > limits.kompressionsrate * max(
        packed, 1
    ):
        raise IntakeRejectedError(Ablehnung.KOMPRESSIONSRATE)
    return files, dirs
