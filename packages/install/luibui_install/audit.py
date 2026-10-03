"""``luibui audit`` (S5-3): are the installed packages still what luibui checked?

For every package in ``~/.luibui/luibui.lock``:

1. **Files:** every installed file is compared with the SHA-256 recorded at installation (or,
   for entries from before that, with the archive fetched again and verified against luibui's
   signature). Changed, missing and added files are listed: something on the machine changed
   the package after it was checked.
2. **Register:** withdrawn by the author? Is there a newer version, and what does it bring?

Nothing from the package is executed. The local scan with current rules (``--scan``) lives in
the ``luibui`` CLI, which has the engine; this module needs none.
"""

import hashlib
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from luibui_install.entpacken import entpacken
from luibui_install.register import InstallError, info, laden, verlauf

MAX_LISTE = 20


def datei_hashes(ordner: Path) -> dict[str, str]:
    """SHA-256 of every regular file below ``ordner``, by relative POSIX path. Symlinks count
    as files of their own (never followed): an installer never creates them."""
    out: dict[str, str] = {}
    for p in sorted(ordner.rglob("*")):
        rel = p.relative_to(ordner).as_posix()
        if p.is_symlink():
            out[rel] = "symlink"
        elif p.is_file():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


@dataclass
class Befund:
    paket: str
    version: str
    ziel: str
    ordner: str
    geaendert: list[str] = field(default_factory=list)
    fehlt: list[str] = field(default_factory=list)
    neu: list[str] = field(default_factory=list)
    hinweise: list[str] = field(default_factory=list)
    """Register state: withdrawn, newer version and what it brings."""
    fehler: str | None = None
    zurueckgezogen: bool = False

    @property
    def problem(self) -> bool:
        return bool(self.geaendert or self.fehlt or self.neu or self.fehler or self.zurueckgezogen)


def _erwartet(eintrag: dict[str, Any]) -> dict[str, str]:
    gespeichert = eintrag.get("dateien")
    if isinstance(gespeichert, dict) and gespeichert:
        return {str(k): str(v) for k, v in gespeichert.items()}
    # Installed before per-file hashes: fetch the same version again, verified as on install.
    v = laden(f"{eintrag.get('paket')}@{eintrag.get('version')}")
    if v.aussage.get("archiv_sha256") != eintrag.get("archiv_sha256"):
        raise InstallError("Das Register liefert für diese Version ein anderes Archiv.")
    with tempfile.TemporaryDirectory(prefix="luibui-audit-") as tmp:
        entpacken(v.archiv, Path(tmp) / "paket")
        return datei_hashes(Path(tmp) / "paket")


def pruefe_eintrag(eintrag: dict[str, Any], *, register: bool = True) -> Befund:
    b = Befund(
        paket=str(eintrag.get("paket")),
        version=str(eintrag.get("version")),
        ziel=str(eintrag.get("ziel")),
        ordner=str(eintrag.get("ordner")),
    )
    ordner = Path(b.ordner)
    if not ordner.is_dir():
        b.fehler = "Der Installationsordner fehlt."
        return b
    try:
        erwartet = _erwartet(eintrag)
    except InstallError as exc:
        b.fehler = str(exc)
        erwartet = None
    if erwartet is not None:
        ist = datei_hashes(ordner)
        b.geaendert = sorted(p for p in erwartet if p in ist and ist[p] != erwartet[p])
        b.fehlt = sorted(p for p in erwartet if p not in ist)
        b.neu = sorted(p for p in ist if p not in erwartet)
    if register:
        try:
            _, versionen = info(b.paket)
        except InstallError as exc:
            b.hinweise.append(f"Register: {exc}")
            return b
        b.zurueckgezogen = any(
            v.get("version") == b.version and v.get("zurueckgezogen") for v in versionen
        )
        if b.zurueckgezogen:
            b.hinweise.append("Diese Version wurde vom Autor zurückgezogen.")
        neueste = next((v for v in versionen if not v.get("zurueckgezogen")), None)
        if neueste and neueste.get("version") != b.version:
            ziel = str(neueste.get("version"))
            b.hinweise.append(f"Neuere Version {ziel} verfügbar.")
            from luibui_install.main import seit  # avoid a cycle at import time

            b.hinweise.extend(f"! {t}" for t in seit(verlauf(versionen), b.version, ziel))
    return b
