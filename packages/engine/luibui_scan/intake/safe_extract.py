"""The only way a ZIP archive is unpacked (CLAUDE.md rule 2, threat model T1–T4).

All entries are checked before the first byte is written. Only the central directory counts;
nested archives stay packed. On rejection the caller deletes the scratch directory.
"""

import stat
import zipfile
from itertools import pairwise
from pathlib import Path

from luibui_scan.intake.errors import Ablehnung, IntakeRejectedError
from luibui_scan.intake.limits import DEFAULT_LIMITS, Limits
from luibui_scan.intake.paths import Budget, NameRegistry, check_path, make_dirs, write_file

_UNIX = 3
_WINDOWS_DIR = 0x10
_WINDOWS_REPARSE_POINT = 0x400
_LOCAL_HEADER_MIN = 30


def extract_archive(archive: Path, root: Path, limits: Limits = DEFAULT_LIMITS) -> list[str]:
    """Unpack a ZIP or tar archive (also .tar.gz/.tgz/.tar.bz2/.tar.xz), chosen by content."""
    from luibui_scan.intake.safe_tar import extract_tar, is_tar

    if zipfile.is_zipfile(archive):
        return extract_zip(archive, root, limits)
    if is_tar(archive):
        return extract_tar(archive, root, limits)
    raise IntakeRejectedError(Ablehnung.DEFEKTES_ARCHIV)


def extract_zip(archive: Path, root: Path, limits: Limits = DEFAULT_LIMITS) -> list[str]:
    """Unpack ``archive`` into the existing directory ``root``; return the file paths, sorted."""
    packed = archive.stat().st_size
    if packed > limits.zip_gepackt_bytes:
        raise IntakeRejectedError(Ablehnung.ZU_GROSS)
    try:
        with zipfile.ZipFile(archive) as zf:
            files, dirs = _check_entries(zf.infolist(), packed, limits)
            for d in dirs:
                make_dirs(root, root.joinpath(*d.split("/")))
            budget = Budget(limits.zip_entpackt_bytes)
            for info in files:
                with zf.open(info) as src:
                    write_file(root, info.orig_filename, src, budget, max_bytes=info.file_size)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError, EOFError) as exc:
        raise IntakeRejectedError(Ablehnung.DEFEKTES_ARCHIV, detail=None) from exc
    return sorted(i.orig_filename for i in files)


def _check_entries(
    infos: list[zipfile.ZipInfo], packed: int, limits: Limits
) -> tuple[list[zipfile.ZipInfo], list[str]]:
    if len(infos) > limits.zip_eintraege:
        raise IntakeRejectedError(Ablehnung.ZU_VIELE_DATEIEN)
    names = NameRegistry()
    files: list[zipfile.ZipInfo] = []
    dirs: list[str] = []
    declared = 0
    for info in infos:
        # orig_filename keeps what zipfile strips (everything after a NUL byte).
        raw = info.orig_filename
        if info.flag_bits & 0x1:
            raise IntakeRejectedError(Ablehnung.VERSCHLUESSELT, raw)
        if _is_dir(info):
            names.add_dir(check_path(raw.removesuffix("/"), limits))
            dirs.append(raw.removesuffix("/"))
            continue
        names.add_file(check_path(raw, limits))
        declared += info.file_size
        if declared > limits.zip_entpackt_bytes:
            raise IntakeRejectedError(Ablehnung.ZU_GROSS, raw)
        if (
            info.file_size >= limits.kompressionsrate_ab_bytes
            and info.file_size > limits.kompressionsrate * max(info.compress_size, 1)
        ):
            raise IntakeRejectedError(Ablehnung.KOMPRESSIONSRATE, raw)
        files.append(info)
    if declared >= limits.kompressionsrate_ab_bytes and declared > limits.kompressionsrate * max(
        packed, 1
    ):
        raise IntakeRejectedError(Ablehnung.KOMPRESSIONSRATE)
    _check_overlap(infos)
    return files, dirs


def _is_dir(info: zipfile.ZipInfo) -> bool:
    if info.create_system == _UNIX:
        fmt = stat.S_IFMT(info.external_attr >> 16)
        if fmt not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise IntakeRejectedError(Ablehnung.VERKNUEPFUNG, info.orig_filename)
        if fmt == stat.S_IFDIR:
            return True
    elif info.external_attr & _WINDOWS_REPARSE_POINT:
        raise IntakeRejectedError(Ablehnung.VERKNUEPFUNG, info.orig_filename)
    elif info.external_attr & _WINDOWS_DIR:
        return True
    return info.orig_filename.endswith("/")


def _check_overlap(infos: list[zipfile.ZipInfo]) -> None:
    """Refuse entries whose data overlaps (overlapping-file zip bombs, parser confusion)."""
    ordered = sorted(infos, key=lambda i: i.header_offset)
    for prev, nxt in pairwise(ordered):
        prev_end = (
            prev.header_offset
            + _LOCAL_HEADER_MIN
            + len(prev.orig_filename.encode())
            + prev.compress_size
        )
        if nxt.header_offset < prev_end:
            raise IntakeRejectedError(Ablehnung.DEFEKTES_ARCHIV, nxt.orig_filename)
