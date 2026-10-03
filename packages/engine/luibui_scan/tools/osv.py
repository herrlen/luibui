"""OSV-Scanner adapter (Prüfkatalog D01, D02; S1-9).

Always offline: ``--offline`` and ``--offline-vulnerabilities`` against a database that a cron job
puts under ``LUIBUI_OSV_DB`` (layout ``<dir>/osv-scalibr/<Ökosystem>/all.zip``). Never with call
analysis (it would run build scripts, CLAUDE.md rule 1) and never with transitive resolution.
Our own empty ``--config`` (otherwise an ``osv-scanner.toml`` in the package could ignore its own
vulnerabilities), empty environment, temporary HOME outside the package, timeout.
"""

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from luibui_scan.tools import ToolError

TIMEOUT_SECONDS = 180
EXIT_OK = (0, 1)
"""0: nothing found, 1: vulnerabilities found."""
EXIT_NO_PACKAGES = 128


@dataclass(frozen=True, slots=True)
class Vuln:
    id: str
    aliases: tuple[str, ...]
    summary: str
    package: str
    version: str
    ecosystem: str
    datei: str
    """Lockfile or manifest, relative to the package root."""
    cvss: float | None
    """Highest CVSS base score OSV-Scanner reported for the group, if any."""


def binary() -> str:
    path = os.environ.get("LUIBUI_OSV_SCANNER") or shutil.which("osv-scanner")
    if not path:
        raise ToolError("osv-scanner nicht installiert")
    return path


def database() -> Path:
    db = Path(os.environ.get("LUIBUI_OSV_DB", "/rules/osv"))
    if not (db / "osv-scalibr").is_dir() or not any((db / "osv-scalibr").iterdir()):
        raise ToolError("OSV-Datenbank fehlt")
    return db


def _score(value: object) -> float | None:
    try:
        return float(str(value))
    except ValueError:
        return None


def scan(root: Path, timeout: float = TIMEOUT_SECONDS) -> list[Vuln]:
    db = database()
    home = Path(tempfile.mkdtemp(prefix="luibui-osv-"))
    # Our own empty config: otherwise osv-scanner reads osv-scanner.toml from the package, and an
    # upload could hide its own vulnerabilities with [[IgnoredVulns]] or [[PackageOverrides]].
    config = home / "osv-scanner.toml"
    config.write_text("")
    argv = [
        binary(),
        "scan", "source", "--recursive",
        "--config", str(config),
        "--offline", "--offline-vulnerabilities",
        "--no-resolve",
        "--no-call-analysis=all",
        "--allow-no-lockfiles",
        "--format", "json",
        "--verbosity", "error",
        str(root),
    ]  # fmt: skip
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "XDG_CACHE_HOME": str(home),
        "OSV_SCALIBR_LOCAL_DB_CACHE_DIRECTORY": str(db),
        "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY": str(db),
        "LANG": "C",
    }
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            argv,
            env=env,
            cwd=home,
            capture_output=True,
            timeout=timeout,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        raise ToolError("osv-scanner: Zeitlimit überschritten") from None
    finally:
        shutil.rmtree(home, ignore_errors=True)
    if proc.returncode == EXIT_NO_PACKAGES:
        return []
    if proc.returncode not in EXIT_OK:
        raise ToolError(f"osv-scanner: Exit-Code {proc.returncode}")
    try:
        data = json.loads(proc.stdout or b"{}")
    except ValueError:
        raise ToolError("osv-scanner: Ausgabe nicht lesbar") from None
    return _parse(data, root)


def _parse(data: object, root: Path) -> list[Vuln]:
    if not isinstance(data, dict):
        raise ToolError("osv-scanner: Ausgabe nicht lesbar")
    root_str = str(root.resolve()) + os.sep
    out: list[Vuln] = []
    for result in data.get("results") or []:
        source = str(((result or {}).get("source") or {}).get("path", ""))
        resolved = str(Path(source).resolve()) if source else ""
        datei = (
            resolved[len(root_str) :].replace(os.sep, "/") if resolved.startswith(root_str) else ""
        )
        for pkg in result.get("packages") or []:
            info = pkg.get("package") or {}
            vulns = {str(v.get("id", ""))[:100]: v for v in pkg.get("vulnerabilities") or []}
            vulns.pop("", None)
            groups = [
                [str(i) for i in g.get("ids") or [] if str(i) in vulns]
                for g in pkg.get("groups") or []
            ]
            grouped = {i for g in groups for i in g}
            groups += [[vid] for vid in vulns if vid not in grouped]
            scores = {
                str(i): _score(g.get("max_severity"))
                for g in pkg.get("groups") or []
                for i in g.get("ids") or []
            }
            for ids in groups:
                if not ids:
                    continue
                # One finding per vulnerability: prefer GHSA, then the rest as aliases.
                ids = sorted(ids, key=lambda i: (not i.startswith(("MAL-", "GHSA-")), i))
                main = vulns[ids[0]]
                aliases = [*ids[1:], *(str(a)[:100] for a in main.get("aliases") or [])]
                out.append(
                    Vuln(
                        id=ids[0],
                        aliases=tuple(dict.fromkeys(a for a in aliases if a != ids[0]))[:10],
                        summary=str(main.get("summary", ""))[:300],
                        package=str(info.get("name", ""))[:200],
                        version=str(info.get("version", ""))[:100],
                        ecosystem=str(info.get("ecosystem", ""))[:50],
                        datei=datei,
                        cvss=scores.get(ids[0]),
                    )
                )
    return out
