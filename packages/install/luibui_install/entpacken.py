"""Unpacking a register archive into a fresh directory: never outside it, no links, with limits.
The archive is signed, but the installer checks anyway (defence in depth)."""

import io
import stat
import zipfile
from pathlib import Path, PurePosixPath

from luibui_install.register import InstallError

MAX_DATEIEN = 10_000
MAX_ENTPACKT = 200 * 1024 * 1024


def entpacken(archiv: bytes, ziel: Path) -> int:
    """Unpack into ``ziel``, which must not exist yet. Returns the number of files."""
    ziel.mkdir(parents=True)
    gesamt = 0
    with zipfile.ZipFile(io.BytesIO(archiv)) as zf:
        eintraege = zf.infolist()
        if len(eintraege) > MAX_DATEIEN:
            raise InstallError("Das Archiv enthält zu viele Dateien.")
        for info in eintraege:
            pfad = PurePosixPath(info.filename)
            if (
                info.filename.startswith(("/", "\\"))
                or "\\" in info.filename
                or ":" in info.filename
                or any(t in ("", ".", "..") for t in pfad.parts)
            ):
                raise InstallError(
                    "Das Archiv enthält einen unzulässigen Pfad; nichts installiert."
                )
            modus = info.external_attr >> 16
            if stat.S_ISLNK(modus):
                raise InstallError("Das Archiv enthält einen Link; nichts installiert.")
            if info.is_dir():
                continue
            gesamt += info.file_size
            if gesamt > MAX_ENTPACKT:
                raise InstallError("Das Archiv ist entpackt zu groß.")
            datei = ziel.joinpath(*pfad.parts)
            datei.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as quelle, open(datei, "xb") as aus:
                aus.write(quelle.read(info.file_size + 1)[: info.file_size])
            datei.chmod(0o644)
    return sum(1 for e in eintraege if not e.is_dir())
