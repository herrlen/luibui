"""The only way a Git repository is fetched (CLAUDE.md rule 3, threat model T7–T11).

Only public HTTPS repositories on github.com, codeberg.org and gitlab.com. The URL is parsed
strictly and rebuilt from its parts; git runs without system or global config, without hooks,
submodules, redirects or any protocol but HTTPS, with a timeout and a size limit on the clone.
The working tree is then copied into the scratch directory through the same checks as a folder
upload, so nothing from the clone reaches the analyzers unchecked.
"""

import os
import re
import shutil
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from luibui_scan.intake.errors import Ablehnung, IntakeRejectedError
from luibui_scan.intake.limits import MB, Limits
from luibui_scan.intake.sources import accept_directory

ALLOWED_HOSTS = frozenset({"github.com", "codeberg.org", "gitlab.com"})
GIT_LIMITS = Limits(auswahl_dateien=10_000, auswahl_bytes=200 * MB)
"""A repository is treated like an unpacked archive: 10,000 files, 200 MB."""
CLONE_MAX_BYTES = 300 * MB
"""Limit for the clone directory itself (history of depth 1 plus working tree)."""
CLONE_TIMEOUT_SECONDS = 60.0

_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_SHA = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
_POLL = 0.2


class GitError(Exception):
    """Clone failed for a reason other than hostile content (not found, timeout, network)."""


@dataclass(frozen=True, slots=True)
class CloneResult:
    url: str
    """Canonical URL that was cloned."""
    commit: str
    files: list[str]
    symlinks: list[str]
    """Paths git stores as symlinks. They are checked out as plain files holding the target."""
    submodules: bool
    """``.gitmodules`` exists; submodules are never fetched."""


def canonical_url(raw: str) -> str:
    """Validate a user-supplied repository URL and rebuild it from its parts.

    Raises ``ValueError`` with a German message for anything but a public HTTPS URL of the form
    ``https://<host>/<owner>/<repo>`` (GitLab also with subgroups).
    """
    raw = raw.strip(" ")
    if len(raw) > 500 or any(c.isspace() or ord(c) < 0x20 or ord(c) == 0x7F for c in raw):
        raise ValueError("Ungültige URL")
    try:
        parts = urlsplit(raw)
        port = parts.port
    except ValueError:
        raise ValueError("Ungültige URL") from None
    if parts.scheme != "https":
        raise ValueError("Nur https:// ist erlaubt")
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        raise ValueError("Zugangsdaten in der URL sind nicht erlaubt")
    host = (parts.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError("Erlaubt sind nur github.com, codeberg.org und gitlab.com")
    if port not in (None, 443) or parts.query or parts.fragment:
        raise ValueError("Ungültige URL")
    segments = [s for s in parts.path.split("/") if s]
    if segments and segments[-1].endswith(".git"):
        segments[-1] = segments[-1][:-4]
    max_segments = 10 if host == "gitlab.com" else 2
    if not 2 <= len(segments) <= max_segments or not all(_SEGMENT.match(s) for s in segments):
        raise ValueError("Erwartet wird https://<host>/<besitzer>/<repository>")
    if any(s in (".", "..") or s.endswith(".") for s in segments):
        raise ValueError("Ungültige URL")
    return f"https://{host}/{'/'.join(segments)}.git"


def _env(home: Path, protocols: tuple[str, ...]) -> dict[str, str]:
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "/bin/false",
        "SSH_ASKPASS": "/bin/false",
        "GIT_LFS_SKIP_SMUDGE": "1",
        "GIT_ALLOW_PROTOCOL": ":".join(protocols),
        "LANG": "C",
    }


_HARDENING = (
    "-c", "core.hooksPath=/dev/null",
    "-c", "core.fsmonitor=false",
    "-c", "core.symlinks=false",
    "-c", "core.sshCommand=/bin/false",
    "-c", "protocol.allow=never",
    "-c", "http.followRedirects=false",
    "-c", "submodule.recurse=false",
    "-c", "transfer.fsckObjects=true",
    "-c", "credential.helper=",
)  # fmt: skip
HTTPS_ONLY = ("https",)


def _argv(protocols: tuple[str, ...]) -> list[str]:
    allow = [a for p in protocols for a in ("-c", f"protocol.{p}.allow=always")]
    deny = [] if "file" in protocols else ["-c", "protocol.file.allow=never"]
    return ["git", *_HARDENING, *allow, *deny]


def _tree_size(path: Path) -> int:
    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    st = entry.stat(follow_symlinks=False)
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
                    else:
                        total += st.st_size
        except FileNotFoundError:
            continue
    return total


def _git(args: list[str], cwd: Path, home: Path, timeout: float) -> str:
    proc = subprocess.run(  # noqa: S603 - fixed argv, no shell, validated URL
        [*_argv(HTTPS_ONLY), *args],
        cwd=cwd,
        env=_env(home, HTTPS_ONLY),
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise GitError("git fehlgeschlagen")
    return proc.stdout.decode("utf-8", errors="replace")


def _clone(
    url: str,
    dest: Path,
    home: Path,
    *,
    timeout: float,
    max_bytes: int,
    protocols: tuple[str, ...],
) -> None:
    """Run ``git clone`` and kill it when it runs too long or the clone grows too large."""
    argv = [
        *_argv(protocols),
        "clone",
        "--depth=1",
        "--single-branch",
        "--no-tags",
        "--no-recurse-submodules",
        "--quiet",
        "--",
        url,
        str(dest),
    ]
    proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell, validated URL
        argv,
        cwd=home,
        env=_env(home, protocols),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.monotonic() + timeout
    try:
        while proc.poll() is None:
            if time.monotonic() > deadline:
                raise GitError("Zeitlimit beim Klonen überschritten")
            if _tree_size(dest) > max_bytes:
                raise IntakeRejectedError(Ablehnung.ZU_GROSS, detail="Das Repository ist zu groß.")
            time.sleep(_POLL)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
    if proc.returncode != 0:
        raise GitError("Repository nicht gefunden oder nicht öffentlich")
    if _tree_size(dest) > max_bytes:
        raise IntakeRejectedError(Ablehnung.ZU_GROSS, detail="Das Repository ist zu groß.")


def _symlinks(clone: Path, home: Path) -> list[str]:
    out = _git(["ls-tree", "-r", "-z", "HEAD"], clone, home, 30)
    paths = []
    for record in out.split("\0"):
        meta, _, path = record.partition("\t")
        if meta.startswith("120000 "):
            paths.append(path)
    return sorted(paths)


def clone_into(
    raw_url: str,
    root: Path,
    work_dir: Path,
    *,
    timeout: float = CLONE_TIMEOUT_SECONDS,
    max_bytes: int = CLONE_MAX_BYTES,
    limits: Limits = GIT_LIMITS,
) -> CloneResult:
    """Clone ``raw_url`` and copy its working tree into ``root`` through the folder intake.

    ``work_dir`` holds the temporary clone and is emptied afterwards. Raises ``ValueError`` for a
    bad URL, ``GitError`` if the clone fails and ``IntakeRejectedError`` for hostile content.
    """
    url = canonical_url(raw_url)
    return _clone_checked(url, root, work_dir, timeout=timeout, max_bytes=max_bytes, limits=limits)


def _clone_checked(
    url: str,
    root: Path,
    work_dir: Path,
    *,
    timeout: float,
    max_bytes: int,
    limits: Limits,
    protocols: tuple[str, ...] = HTTPS_ONLY,
) -> CloneResult:
    """``protocols`` exists for tests with local repositories; ``clone_into`` never passes it."""
    tmp = work_dir / f".clone-{uuid.uuid4().hex}"
    home = tmp / "home"
    home.mkdir(parents=True, mode=0o700)
    clone = tmp / "repo"
    try:
        _clone(url, clone, home, timeout=timeout, max_bytes=max_bytes, protocols=protocols)
        commit = _git(["rev-parse", "HEAD"], clone, home, 30).strip()
        if not _SHA.match(commit):
            raise GitError("Commit nicht lesbar")
        symlinks = _symlinks(clone, home)
        submodules = (clone / ".gitmodules").is_file()
        files = accept_directory(clone, root, limits)
    except subprocess.TimeoutExpired:
        raise GitError("Zeitlimit überschritten") from None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return CloneResult(url, commit, files, symlinks, submodules)
