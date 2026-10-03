"""S5-7 (H03): a package is compared with the Git tag of its version, never blocked."""

import functools
import os
import subprocess
from pathlib import Path

import pytest

from luibui_api import herkunft
from luibui_scan.intake.safe_git import GIT_LIMITS, _clone_checked, tag_commits

MARK = b"<!-- LUIBUI-TESTFIXTURE: entschaerft, nicht ausfuehren -->\n"
MANIFEST = b'{"name": "anna-tools/wetter", "version": "1.0.0"}'
GIT_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "PATH": os.environ["PATH"],
    "HOME": os.devnull,
}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603 - test helper, fixed git commands
        ["git", *args],  # noqa: S607
        cwd=cwd,
        env=GIT_ENV,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()


def repo(tmp_path: Path, files: dict[str, bytes], tag: str | None = "v1.0.0") -> str:
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    for rel, data in files.items():
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        (r / rel).write_bytes(data)
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "LUIBUI-TESTFIXTURE")
    if tag:
        git(r, "tag", tag)
    return f"file://{r}"


@pytest.fixture
def lokal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Real git against local repositories: only the HTTPS restriction is lifted."""
    monkeypatch.setattr(herkunft, "canonical_url", lambda u: u)
    monkeypatch.setattr(
        herkunft, "tag_commits", functools.partial(tag_commits, protocols=("file",))
    )

    def clone(url: str, root: Path, work: Path, *, tag: str, timeout: float) -> object:
        return _clone_checked(
            url, root, work, timeout=timeout, max_bytes=50 * 1024 * 1024, limits=GIT_LIMITS,
            protocols=("file",), tag=tag,
        )  # fmt: skip

    monkeypatch.setattr(herkunft, "clone_into", clone)
    work = tmp_path / "scratch"
    work.mkdir()
    return work


PAKET = {"SKILL.md": MARK + b"# Wetter\n", "luibui.json": MANIFEST}


def pruefen(url: str | None, work: Path, dateien: dict[str, bytes] = PAKET, **kw: object):  # type: ignore[no-untyped-def]
    return herkunft.pruefen(
        manifest_repository=url,
        version="1.0.0",
        dateien=dateien,
        work_dir=work,
        **kw,  # type: ignore[arg-type]
    )


def test_same_files_in_the_tag(tmp_path: Path, lokal: Path) -> None:
    url = repo(tmp_path, {**PAKET, "tests/test_x.py": b"# extra files are fine\n"})
    r = pruefen(url, lokal)
    assert r["status"] == "uebereinstimmend" and r["tag"] == "v1.0.0" and len(r["commit"]) == 40
    assert list(lokal.iterdir()) == []


def test_package_in_a_subfolder_of_the_repository(tmp_path: Path, lokal: Path) -> None:
    url = repo(
        tmp_path, {"README.md": b"# Mono\n", **{f"skills/wetter/{k}": v for k, v in PAKET.items()}}
    )
    assert pruefen(url, lokal)["status"] == "uebereinstimmend"


def test_changed_and_missing_files_are_marked(tmp_path: Path, lokal: Path) -> None:
    url = repo(tmp_path, {**PAKET, "SKILL.md": MARK + b"# Anders\n"})
    r = pruefen(url, lokal, {**PAKET, "extra.py": b"print(1)\n"})
    assert r["status"] == "abweichend"
    assert r["abweichungen"] == ["SKILL.md", "extra.py"] and r["abweichungen_gesamt"] == 2


def test_tag_without_v(tmp_path: Path, lokal: Path) -> None:
    url = repo(tmp_path, PAKET, tag="1.0.0")
    assert pruefen(url, lokal)["tag"] == "1.0.0"


def test_no_tag(tmp_path: Path, lokal: Path) -> None:
    url = repo(tmp_path, PAKET, tag=None)
    assert pruefen(url, lokal)["status"] == "kein_tag"


def test_unreachable_repository(tmp_path: Path, lokal: Path) -> None:
    assert pruefen(f"file://{tmp_path}/fehlt", lokal)["status"] == "nicht_pruefbar"


def test_git_project_at_the_tag_commit_needs_no_clone(
    tmp_path: Path, lokal: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = repo(tmp_path, PAKET)
    commit = git(tmp_path / "repo", "rev-parse", "HEAD")

    def kein_klon(*a: object, **k: object) -> None:
        raise AssertionError("no clone expected")

    monkeypatch.setattr(herkunft, "clone_into", kein_klon)
    r = pruefen(None, lokal, git_url=url, git_commit=commit)
    assert r["status"] == "uebereinstimmend"


def test_without_repository_or_on_another_host(tmp_path: Path) -> None:
    assert pruefen(None, tmp_path) == {"status": "keine_angabe"}
    r = pruefen("https://example.invalid/a/b", tmp_path)
    assert r["status"] == "nicht_pruefbar"


def test_manifest_names_another_repository_than_the_git_project(tmp_path: Path) -> None:
    r = pruefen(
        "https://github.com/mallory/wetter",
        tmp_path,
        git_url="https://github.com/anna/wetter",
        git_commit="0" * 40,
    )
    assert r["status"] == "abweichend" and "anderes Repository" in r["hinweis"]
