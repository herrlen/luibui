"""S1-3 in the API: Git scans for projects and the public quick scan."""

from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text

from luibui_api import uploads
from luibui_scan.intake.safe_git import CloneResult, GitError, canonical_url

from .conftest import Api
from .test_scans import blobs, db_rows, project, scratch_dirs

pytestmark = pytest.mark.db

COMMIT = "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"


@pytest.fixture
def fake_clone(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stand-in for the network clone; the real one is tested in test_safe_git.py."""
    calls: list[str] = []

    def clone(raw: str, root: Path, work: Path) -> CloneResult:
        url = canonical_url(raw)
        calls.append(url)
        if "kaputt" in url:
            raise GitError("x")
        (root / "SKILL.md").write_text("# LUIBUI-TESTFIXTURE Skill")
        return CloneResult(url, COMMIT, ["SKILL.md"], [], False)

    monkeypatch.setattr(uploads, "clone_into", clone)
    return calls


def git_scan(c, pid: str, **data: str):  # type: ignore[no-untyped-def]
    return c.post(
        f"/api/v1/projects/{pid}/scans", data={"art": "git", **data}, files={"x": ("", b"")}
    )


# --- projects with Git -----------------------------------------------------------------------


def test_project_git_url_is_validated_and_canonical(api: Api) -> None:
    c = api.user("anna@example.org")
    bad = c.post(
        "/api/v1/projects", json={"name": "x", "typ": "skill", "git_url": "http://evil.example/a/b"}
    )
    assert bad.status_code == 422
    pid = project(c, quelle="git", git_url="https://GitHub.com/a/b")
    assert c.get(f"/api/v1/projects/{pid}").json()["git_url"] == "https://github.com/a/b.git"


def test_git_scan_stores_commit(api: Api, fake_clone: list[str], _migrated: str) -> None:
    c = api.user("anna@example.org")
    pid = project(c, quelle="git", git_url="https://github.com/a/b")
    r = git_scan(c, pid)
    assert r.status_code == 202, r.text
    assert fake_clone == ["https://github.com/a/b.git"]
    assert db_rows(_migrated, "SELECT commit_sha FROM project_versions")[0][0] == COMMIT


def test_git_scan_url_from_form(api: Api, fake_clone: list[str]) -> None:
    c = api.user("anna@example.org")
    assert git_scan(c, project(c), git_url="https://codeberg.org/x/y").status_code == 202
    assert fake_clone == ["https://codeberg.org/x/y.git"]


@pytest.mark.parametrize(
    ("url", "grund"),
    [
        ("https://github.com/a/kaputt", "git_fehler"),
        ("file:///etc", "ungueltige_url"),
        ("", "ungueltige_url"),
    ],
)
def test_git_scan_errors_leave_nothing(
    api: Api, fake_clone: list[str], tmp_path: Path, url: str, grund: str
) -> None:
    c = api.user("anna@example.org")
    r = git_scan(c, project(c), git_url=url)
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == grund
    assert scratch_dirs(tmp_path) == [] and blobs(tmp_path) == []


# --- quick scan ------------------------------------------------------------------------------


def quick(api: Api, url: str = "https://github.com/a/b", ip_client: Any = None):  # type: ignore[no-untyped-def]
    c = ip_client or api.client("https://luibui.com")
    return c.post("/api/v1/quickscans", json={"git_url": url})


def test_quickscan_without_account(
    api: Api, fake_clone: list[str], tmp_path: Path, _migrated: str
) -> None:
    r = quick(api)
    assert r.status_code == 202, r.text
    s = r.json()
    assert (s["scan_art"], s["status"], s["project_id"]) == ("schnell", "wartend", None)
    ((owner, expires_in_days),) = db_rows(
        _migrated,
        "SELECT owner_id, extract(day FROM expires_at - now()) FROM scans",
    )
    assert owner is None and 6 <= expires_in_days <= 7
    assert blobs(tmp_path) == []  # nothing stored
    assert len(scratch_dirs(tmp_path)) == 1  # only the worker's input
    anyone = api.client("https://luibui.com")
    assert anyone.get(f"/api/v1/quickscans/{s['id']}").status_code == 200


def test_quickscan_route_never_shows_account_scans(api: Api, fake_clone: list[str]) -> None:
    """The public route must not become a way around the owner check."""
    c = api.user("anna@example.org")
    scan_id = git_scan(c, project(c), git_url="https://github.com/a/b").json()["id"]
    assert api.client().get(f"/api/v1/quickscans/{scan_id}").status_code == 404
    assert c.get(f"/api/v1/quickscans/{scan_id}").status_code == 404


def test_expired_quickscan_is_gone(api: Api, fake_clone: list[str], _migrated: str) -> None:
    scan_id = quick(api).json()["id"]
    engine = create_engine(_migrated)
    with engine.begin() as conn:
        conn.execute(text("UPDATE scans SET expires_at = now() - interval '1 second'"))
    engine.dispose()
    assert api.client().get(f"/api/v1/quickscans/{scan_id}").status_code == 404


def test_quickscan_rate_limit(api: Api, fake_clone: list[str]) -> None:
    for _ in range(3):
        assert quick(api).status_code == 202
    r = quick(api)
    assert r.status_code == 429
    assert len(fake_clone) == 3


def test_invalid_url_does_not_count(api: Api, fake_clone: list[str]) -> None:
    for _ in range(5):
        assert quick(api, "http://evil.example/a/b").status_code == 422
    assert quick(api).status_code == 202


def test_quickscan_queue_limit(
    api: Api, fake_clone: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUICKSCAN_QUEUE_MAX", "1")
    from luibui_api.settings import get_settings

    get_settings.cache_clear()
    assert quick(api).status_code == 202
    assert quick(api).status_code == 503


def test_quickscan_end_to_end_says_ohne_gewaehr(
    api: Api, fake_clone: list[str], tmp_path: Path, _migrated: str
) -> None:
    from luibui_worker.main import Worker
    from luibui_worker.settings import WorkerSettings

    scan_id = quick(api).json()["id"]
    engine = create_engine(_migrated)
    Worker(
        WorkerSettings(database_url=_migrated, scratch_root=tmp_path / "scratch"),  # type: ignore[arg-type]
        engine=engine,
    ).run_once()
    engine.dispose()
    s = api.client().get(f"/api/v1/quickscans/{scan_id}").json()
    assert s["status"] == "fertig", s
    assert any("ohne Gewähr" in h for h in s["bericht"]["hinweise"])
    assert s["bericht"]["paket"]["name"] == "github.com/a/b"
    assert s["bericht"]["paket"]["quelle"] == "git"
