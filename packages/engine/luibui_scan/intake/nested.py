"""Package formats inside the package are unpacked one level deep (Scanner-Matrix AGT-09, BIN-02).

Wheels, Claude Desktop extensions, VS Code and Firefox extensions are ZIP files that get installed
as they are. Their content is what runs, so it is checked like the rest of the package. Every other
nested archive stays packed (Prüfkatalog A07).

Each archive goes through ``extract_zip`` with what is left of the package limits, so all levels
together never exceed 200 MB and 10,000 files. The content lands next to the archive in
``<name>.inhalt/``. If that name is already taken by the package, the archive stays packed: the
analyzers must never mistake files from the upload for the archive's real content.
"""

import dataclasses
import os
import zipfile
from pathlib import Path, PurePosixPath

from luibui_scan.intake.errors import IntakeRejectedError
from luibui_scan.intake.limits import DEFAULT_LIMITS, Limits
from luibui_scan.intake.safe_extract import extract_zip

PAKET_ENDUNGEN = frozenset({".whl", ".egg", ".dxt", ".mcpb", ".vsix", ".xpi", ".nupkg"})
SUFFIX = ".inhalt"


@dataclasses.dataclass(frozen=True, slots=True)
class Entpackt:
    entpackt: tuple[str, ...] = ()
    """Archive paths whose content now lies in ``<path>.inhalt/``."""
    abgelehnt: tuple[tuple[str, str], ...] = ()
    """Archive path and rejection reason for archives that stayed packed."""


def _files(root: Path) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(dirpath) / name
            st = full.lstat()
            out.append((full.relative_to(root).as_posix(), st.st_size))
    return out


def expand_packages(root: Path, limits: Limits = DEFAULT_LIMITS) -> Entpackt:
    """Unpack every package-format ZIP one level deep; archives inside them stay packed."""
    files = _files(root)
    used_bytes = sum(size for _, size in files)
    used_files = len(files)
    taken = {path for path, _ in files}
    entpackt: list[str] = []
    abgelehnt: list[tuple[str, str]] = []
    for path, _ in files:
        if PurePosixPath(path).suffix.lower() not in PAKET_ENDUNGEN:
            continue
        target = f"{path}{SUFFIX}"
        if any(t == target or t.startswith(target + "/") for t in taken):
            continue
        archive = root.joinpath(*path.split("/"))
        if not zipfile.is_zipfile(archive):
            continue
        rest = dataclasses.replace(
            limits,
            zip_entpackt_bytes=max(0, limits.zip_entpackt_bytes - used_bytes),
            zip_eintraege=max(0, limits.zip_eintraege - used_files),
            tiefe=max(1, limits.tiefe - len(target.split("/"))),
        )
        dest = root.joinpath(*target.split("/"))
        os.mkdir(dest, 0o700)
        try:
            written = extract_zip(archive, dest, rest)
        except IntakeRejectedError as exc:
            _remove(dest)
            abgelehnt.append((path, exc.grund.value))
            continue
        entpackt.append(path)
        used_files += len(written)
        used_bytes += sum((dest.joinpath(*w.split("/"))).stat().st_size for w in written)
    return Entpackt(tuple(entpackt), tuple(abgelehnt))


def _remove(directory: Path) -> None:
    for dirpath, dirnames, filenames in os.walk(directory, topdown=False):
        for name in filenames:
            os.unlink(Path(dirpath) / name)
        for name in dirnames:
            os.rmdir(Path(dirpath) / name)
    os.rmdir(directory)
