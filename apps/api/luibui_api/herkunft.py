"""Origin check when publishing (S5-7, Prüfkatalog H03).

A package names its source in ``luibui.json`` (``repository``); Git projects also have the
repository they were checked from. luibui looks for the tag of the version (``v1.2.0`` or
``1.2.0``) and compares: every file of the package must exist in the tag with the same bytes,
in the repository root or in the folder that holds the same ``luibui.json``. Further files in
the repository (tests, CI) are fine. If the Git project was checked at exactly the commit of the
tag, nothing needs to be cloned.

The result never blocks publishing (Len, 2026-10-03); it goes into the signed statement and is
shown on the package page. The clone goes through ``safe_git`` like any Git check.
"""

import shutil
import uuid
from pathlib import Path
from typing import Any

from luibui_api.settings import get_settings
from luibui_scan.intake.errors import IntakeRejectedError
from luibui_scan.intake.safe_git import GitError, canonical_url, clone_into, tag_commits

UEBEREINSTIMMEND = "uebereinstimmend"
ABWEICHEND = "abweichend"
KEIN_TAG = "kein_tag"
NICHT_PRUEFBAR = "nicht_pruefbar"
KEINE_ANGABE = "keine_angabe"

MAX_ABWEICHUNGEN = 20
KLON_ZEITLIMIT = 45.0


def _vergleichen(paket: dict[str, bytes], klon: Path) -> list[str]:
    """Paths of the package that are missing or different in the clone (sorted, capped)."""
    manifest = paket.get("luibui.json")
    ordner: list[Path] = [klon]
    if manifest is not None:
        gleich = sorted(
            (p.parent for p in klon.rglob("luibui.json") if p.is_file()),
            key=lambda d: (len(d.relative_to(klon).parts), str(d)),
        )
        gleich = [d for d in gleich if (d / "luibui.json").read_bytes() == manifest]
        ordner = gleich[:1] or ordner
    basis = ordner[0]
    abweichend = []
    for pfad, inhalt in sorted(paket.items()):
        ziel = basis / pfad
        if not ziel.is_file() or ziel.read_bytes() != inhalt:
            abweichend.append(pfad)
    return abweichend


def pruefen(
    *,
    manifest_repository: str | None,
    version: str,
    dateien: dict[str, bytes],
    git_url: str | None = None,
    git_commit: str | None = None,
    work_dir: Path | None = None,
) -> dict[str, Any]:
    """Compare the package with the tag of ``version``; the result for the statement.

    ``git_url``/``git_commit`` are the repository and commit a Git project was checked from.
    """
    roh = manifest_repository or git_url
    if not roh:
        return {"status": KEINE_ANGABE}
    try:
        repo = canonical_url(roh)
    except ValueError:
        return {
            "status": NICHT_PRUEFBAR,
            "repository": roh[:200],
            "hinweis": "Abgleichen lassen sich nur Repositories auf github.com, codeberg.org "
            "und gitlab.com.",
        }
    ergebnis: dict[str, Any] = {"repository": repo}
    if git_url and canonical_url(git_url) != repo:
        return {
            **ergebnis,
            "status": ABWEICHEND,
            "hinweis": "luibui.json nennt ein anderes Repository als das geprüfte.",
        }
    work = work_dir or get_settings().scratch_root
    tags = [f"v{version}", version]
    try:
        gefunden = tag_commits(repo, tags, work)
    except (GitError, ValueError):
        return {
            **ergebnis,
            "status": NICHT_PRUEFBAR,
            "hinweis": "Repository nicht erreichbar oder nicht öffentlich.",
        }
    tag = next((t for t in tags if t in gefunden), None)
    if tag is None:
        return {
            **ergebnis,
            "status": KEIN_TAG,
            "hinweis": f"Im Repository gibt es keinen Tag v{version} oder {version}.",
        }
    ergebnis |= {"tag": tag, "commit": gefunden[tag]}
    if git_commit and git_commit == gefunden[tag]:
        return {**ergebnis, "status": UEBEREINSTIMMEND}
    tmp = work / f".herkunft-{uuid.uuid4().hex}"
    root = tmp / "root"
    root.mkdir(parents=True, mode=0o700)
    try:
        clone_into(repo, root, tmp, tag=tag, timeout=KLON_ZEITLIMIT)
        abweichend = _vergleichen(dateien, root)
    except (GitError, ValueError, IntakeRejectedError):
        return {
            **ergebnis,
            "status": NICHT_PRUEFBAR,
            "hinweis": f"Der Tag {tag} ließ sich nicht laden.",
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not abweichend:
        return {**ergebnis, "status": UEBEREINSTIMMEND}
    return {
        **ergebnis,
        "status": ABWEICHEND,
        "abweichungen": abweichend[:MAX_ABWEICHUNGEN],
        "abweichungen_gesamt": len(abweichend),
        "hinweis": f"{len(abweichend)} Dateien des Pakets fehlen im Tag {tag} oder unterscheiden "
        "sich.",
    }
