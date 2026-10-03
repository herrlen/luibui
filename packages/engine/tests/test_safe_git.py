"""S1-3: only public HTTPS repositories on three hosts; clones pass the folder intake."""

import os
import subprocess
from pathlib import Path

import pytest

from luibui_scan.intake import Ablehnung, IntakeRejectedError, Limits
from luibui_scan.intake.safe_git import (
    GIT_LIMITS,
    GitError,
    _clone_checked,
    canonical_url,
    clone_into,
    tag_commits,
)

# --- URL -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "url"),
    [
        ("https://github.com/anthropics/skills", "https://github.com/anthropics/skills.git"),
        ("https://GitHub.com/a/b.git", "https://github.com/a/b.git"),
        ("  https://codeberg.org/a/b/  ", "https://codeberg.org/a/b.git"),
        ("https://gitlab.com/group/sub/repo", "https://gitlab.com/group/sub/repo.git"),
        ("https://github.com:443/a/b", "https://github.com/a/b.git"),
    ],
)
def test_valid_urls(raw: str, url: str) -> None:
    assert canonical_url(raw) == url


@pytest.mark.parametrize(
    "raw",
    [
        "http://github.com/a/b",
        "file:///etc/passwd",
        "ext::sh -c touch% /tmp/pwned",
        "git@github.com:a/b.git",
        "ssh://git@github.com/a/b",
        "https://evil.example/a/b",
        "https://github.com.evil.example/a/b",
        "https://evilgithub.com/a/b",
        "https://169.254.169.254/latest/meta-data",
        "https://localhost/a/b",
        "https://user:pass@github.com/a/b",
        "https://token@github.com/a/b",
        "https://github.com@evil.example/a/b",
        "https://github.com:8443/a/b",
        "https://github.com/a/b?x=1",
        "https://github.com/a/b#frag",
        "https://github.com/a",
        "https://github.com/a/b/c",
        "https://github.com/a/../b",
        "https://github.com/-u/b",
        "https://github.com/a/b\n",
        "https://github.com/a/b c",
        "https://github.com/a/%2e%2e",
        "https://github.com/a/b\x00",
        "https://" + "a" * 600,
        "",
    ],
)
def test_invalid_urls(raw: str) -> None:
    with pytest.raises(ValueError):
        canonical_url(raw)


# --- clone (local repositories, file protocol allowed only in these tests) -------------------

GIT_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
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
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def make_repo(
    tmp_path: Path, files: dict[str, bytes], symlinks: dict[str, str] | None = None
) -> Path:
    repo = tmp_path / "origin"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    for rel, data in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_bytes(data)
    for rel, target in (symlinks or {}).items():
        os.symlink(target, repo / rel)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "LUIBUI-TESTFIXTURE")
    return repo


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    root, work = tmp_path / "scratch" / "job", tmp_path / "scratch"
    root.mkdir(parents=True)
    return root, work


def clone(repo: Path, dirs: tuple[Path, Path], **kw: object):  # type: ignore[no-untyped-def]
    root, work = dirs
    opts: dict[str, object] = {"timeout": 30, "max_bytes": 50 * 1024 * 1024, "limits": GIT_LIMITS}
    opts.update(kw)
    return _clone_checked(f"file://{repo}", root, work, protocols=("file",), **opts)  # type: ignore[arg-type]


def leftovers(work: Path) -> list[str]:
    return [p.name for p in work.iterdir() if p.name.startswith(".clone-")]


def test_clone_copies_working_tree_without_git_dir(tmp_path: Path, dirs: tuple[Path, Path]) -> None:
    repo = make_repo(tmp_path, {"SKILL.md": b"# Skill", "src/a.py": b"print(1)"})
    result = clone(repo, dirs)
    root, work = dirs
    assert result.files == ["SKILL.md", "src/a.py"]
    assert result.commit == git(repo, "rev-parse", "HEAD")
    assert not (root / ".git").exists()
    assert (root / "src/a.py").read_bytes() == b"print(1)"
    assert leftovers(work) == []


def test_symlinks_become_plain_files_and_are_reported(
    tmp_path: Path, dirs: tuple[Path, Path]
) -> None:
    repo = make_repo(
        tmp_path,
        {"AGENTS.md": b"# Agents"},
        symlinks={"CLAUDE.md": "AGENTS.md", "passwd": "/etc/passwd"},
    )
    result = clone(repo, dirs)
    root, _ = dirs
    assert result.symlinks == ["CLAUDE.md", "passwd"]
    assert not (root / "passwd").is_symlink()
    assert (root / "passwd").read_bytes() == b"/etc/passwd"
    assert (root / "CLAUDE.md").read_bytes() == b"AGENTS.md"


def test_submodules_are_not_fetched(tmp_path: Path, dirs: tuple[Path, Path]) -> None:
    gitmodules = b'[submodule "x"]\n\tpath = x\n\turl = https://example.invalid/x.git\n'
    repo = make_repo(tmp_path, {".gitmodules": gitmodules, "a.md": b"x"})
    result = clone(repo, dirs)
    assert result.submodules
    assert result.files == [".gitmodules", "a.md"]


def test_file_protocol_is_refused_by_default(tmp_path: Path, dirs: tuple[Path, Path]) -> None:
    repo = make_repo(tmp_path, {"a.md": b"x"})
    root, work = dirs
    with pytest.raises(GitError):
        _clone_checked(f"file://{repo}", root, work, timeout=30, max_bytes=10**8, limits=GIT_LIMITS)
    assert list(root.iterdir()) == []
    assert leftovers(work) == []


def test_size_limit_during_clone(tmp_path: Path, dirs: tuple[Path, Path]) -> None:
    repo = make_repo(tmp_path, {"big.bin": os.urandom(2 * 1024 * 1024)})
    with pytest.raises(IntakeRejectedError) as exc:
        clone(repo, dirs, max_bytes=1024 * 1024)
    assert exc.value.grund is Ablehnung.ZU_GROSS
    assert leftovers(dirs[1]) == []


def test_repository_limits_of_the_intake_apply(tmp_path: Path, dirs: tuple[Path, Path]) -> None:
    repo = make_repo(tmp_path, {f"{i}.md": b"x" for i in range(5)})
    with pytest.raises(IntakeRejectedError) as exc:
        clone(repo, dirs, limits=Limits(auswahl_dateien=3))
    assert exc.value.grund is Ablehnung.ZU_VIELE_DATEIEN


def test_hostile_file_names_are_refused(tmp_path: Path, dirs: tuple[Path, Path]) -> None:
    repo = make_repo(tmp_path, {"a\\..\\b.md": b"x"})
    with pytest.raises(IntakeRejectedError) as exc:
        clone(repo, dirs)
    assert exc.value.grund is Ablehnung.UNGUELTIGER_NAME


def test_missing_repository(tmp_path: Path, dirs: tuple[Path, Path]) -> None:
    with pytest.raises(GitError):
        clone(tmp_path / "gibt-es-nicht", dirs)
    assert leftovers(dirs[1]) == []


def test_timeout(tmp_path: Path, dirs: tuple[Path, Path]) -> None:
    repo = make_repo(tmp_path, {"a.md": b"x"})
    with pytest.raises(GitError):
        clone(repo, dirs, timeout=0)
    assert leftovers(dirs[1]) == []


def test_tag_commits_resolves_light_and_annotated_tags(
    tmp_path: Path, dirs: tuple[Path, Path]
) -> None:
    repo = make_repo(tmp_path, {"SKILL.md": b"# Skill"})
    head = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "tag", "v1.0.0")
    git(repo, "tag", "-a", "1.1.0", "-m", "LUIBUI-TESTFIXTURE")
    _, work = dirs
    found = tag_commits(f"file://{repo}", ["v1.0.0", "1.1.0", "v2.0.0"], work, protocols=("file",))
    assert found == {"v1.0.0": head, "1.1.0": head}
    assert not [p for p in work.iterdir() if p.name.startswith(".ls-remote-")]


def test_clone_of_a_tag(tmp_path: Path, dirs: tuple[Path, Path]) -> None:
    repo = make_repo(tmp_path, {"SKILL.md": b"# alt"})
    git(repo, "tag", "v1.0.0")
    (repo / "SKILL.md").write_bytes(b"# neu")
    git(repo, "commit", "-qam", "LUIBUI-TESTFIXTURE")
    clone(repo, dirs, tag="v1.0.0")
    assert (dirs[0] / "SKILL.md").read_bytes() == b"# alt"


@pytest.mark.parametrize("tag", ["-v1", "a..b", "v1.lock", "v 1", "v1/../x", "", "x" * 101])
def test_bad_tag_names(tag: str, dirs: tuple[Path, Path]) -> None:
    with pytest.raises(ValueError):
        clone_into("https://github.com/a/b", dirs[0], dirs[1], tag=tag)
    with pytest.raises(ValueError):
        tag_commits("https://github.com/a/b", [tag], dirs[1])
