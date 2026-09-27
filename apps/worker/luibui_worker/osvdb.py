"""Keep the offline OSV database current (Prüfkatalog D01, D02).

Runs in the worker's parent process, which has network access; the child that scans packages
never does. Downloads the public ``all.zip`` per ecosystem from osv.dev's storage (approved by Len
on 2026-09-27), at most once per ``max_age``. A new file replaces the old one only after it was
completely written and opens as a ZIP, so a broken download never removes a working database.
"""

import logging
import os
import time
import urllib.request
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)

SOURCE = "https://osv-vulnerabilities.storage.googleapis.com/{ecosystem}/all.zip"
ECOSYSTEMS = ("PyPI", "npm", "Go", "crates.io")
MAX_BYTES = 1024 * 1024 * 1024
TIMEOUT_SECONDS = 120
_CHUNK = 1024 * 1024


def target(db: Path, ecosystem: str) -> Path:
    return db / "osv-scalibr" / ecosystem / "all.zip"


def is_fresh(path: Path, max_age: float) -> bool:
    try:
        return time.time() - path.stat().st_mtime < max_age
    except FileNotFoundError:
        return False


def download_file(url: str, path: Path, max_bytes: int) -> None:
    """Stream ``url`` into ``path`` (https only, at most ``max_bytes``). The caller cleans up."""
    if not url.startswith("https://"):
        raise ValueError("nur https")
    written = 0
    request = urllib.request.Request(url, headers={"User-Agent": "luibui-worker"})  # noqa: S310
    with (
        urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp,  # noqa: S310
        path.open("wb") as out,
    ):
        while chunk := resp.read(_CHUNK):
            written += len(chunk)
            if written > max_bytes:
                raise ValueError("Datenbank größer als erlaubt")
            out.write(chunk)


def download(url: str, dest: Path, max_bytes: int = MAX_BYTES) -> None:
    """Stream ``url`` to ``dest`` via a temporary file; replace only if it is a valid ZIP."""
    if not url.startswith("https://"):
        raise ValueError("nur https")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".zip.part")
    try:
        download_file(url, tmp, max_bytes)
        with zipfile.ZipFile(tmp) as zf:
            if not any(n.endswith(".json") for n in zf.namelist()):
                raise ValueError("ZIP ohne Einträge")
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


def refresh(db: Path, max_age: float, ecosystems: tuple[str, ...] = ECOSYSTEMS) -> list[str]:
    """Update stale databases; return the ecosystems that were updated. Never raises."""
    updated = []
    for ecosystem in ecosystems:
        dest = target(db, ecosystem)
        if is_fresh(dest, max_age):
            continue
        try:
            download(SOURCE.format(ecosystem=ecosystem), dest)
        except Exception as exc:
            log.warning("OSV database %s not updated: %s", ecosystem, type(exc).__name__)
            continue
        updated.append(ecosystem)
    if updated:
        log.info("OSV databases updated: %s", ", ".join(updated))
    return updated
