"""S5-8: webhooks per Git project. Only a correct signature starts a check, only for a push to
the default branch or a tag of the project's own repository, at most one per minute."""

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from luibui_api import uploads
from luibui_scan.intake.safe_git import CloneResult, canonical_url

from .conftest import Api
from .test_scans import db_rows, project

COMMIT = "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
REPO = "https://github.com/anna/wetter"


@pytest.fixture
def klone(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    aufrufe: list[str] = []

    def clone(raw: str, root: Path, work: Path) -> CloneResult:
        aufrufe.append(raw)
        (root / "SKILL.md").write_text("# LUIBUI-TESTFIXTURE Skill")
        return CloneResult(canonical_url(raw), COMMIT, ["SKILL.md"], [], False)

    monkeypatch.setattr(uploads, "clone_into", clone)
    return aufrufe


def einrichten(api: Api) -> tuple[Any, str, str]:
    a = api.user("anna@example.org")
    pid = project(a, name="wetter-git", quelle="git", git_url=REPO)
    r = a.post(f"/api/v1/projects/{pid}/webhook")
    assert r.status_code == 200, r.text
    assert r.json()["url"].endswith(f"/api/v1/webhooks/{pid}")
    return a, pid, r.json()["geheimnis"]


def push(ref: str = "refs/heads/main", repo: str = REPO, **mehr: Any) -> bytes:
    return json.dumps(
        {"ref": ref, "after": COMMIT, "repository": {"clone_url": repo + ".git", "html_url": repo,
                                                      "default_branch": "main"}, **mehr}
    ).encode()  # fmt: skip


def github(api: Api, pid: str, body: bytes, geheimnis: str, ereignis: str = "push") -> Any:
    sig = "sha256=" + hmac.new(geheimnis.encode(), body, hashlib.sha256).hexdigest()
    c = api.client(base_url="https://api.luibui.com")  # no login, no bearer: the signature counts
    return c.post(
        f"/api/v1/webhooks/{pid}",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": ereignis,
            "Content-Type": "application/json",
        },
    )


def pruefungen(url: str, pid: str) -> int:
    return int(db_rows(url, f"SELECT count(*) FROM scans WHERE project_id = '{pid}'")[0][0])  # noqa: S608


def test_a_signed_push_to_the_default_branch_starts_a_check(
    api: Api, klone: list[str], _migrated: str
) -> None:
    _, pid, geheimnis = einrichten(api)
    assert github(api, pid, b"{}", geheimnis, "ping").json() == {"status": "ok"}
    r = github(api, pid, push(), geheimnis)
    assert r.json() == {"status": "geplant"}
    assert klone == ["https://github.com/anna/wetter.git"] and pruefungen(_migrated, pid) == 1
    assert (
        db_rows(_migrated, "SELECT count(*) FROM audit_log WHERE action = 'webhook.pruefung'")[0][0]
        == 1
    )
    again = github(api, pid, push(), geheimnis)
    assert again.json()["grund"] == "höchstens eine Prüfung pro Minute"


@pytest.mark.parametrize(
    ("body", "grund"),
    [
        (push(ref="refs/heads/feature"), "nicht der Standard-Branch"),
        (push(repo="https://github.com/mallory/wetter"), "anderes Repository"),
        (push(deleted=True), "gelöschter Branch oder Tag"),
    ],
)
def test_pushes_that_do_not_count(
    api: Api, klone: list[str], _migrated: str, body: bytes, grund: str
) -> None:
    _, pid, geheimnis = einrichten(api)
    assert github(api, pid, body, geheimnis).json() == {"status": "ignoriert", "grund": grund}
    assert pruefungen(_migrated, pid) == 0


def test_tags_count_and_other_events_do_not(api: Api, klone: list[str], _migrated: str) -> None:
    _, pid, geheimnis = einrichten(api)
    assert github(api, pid, push(), geheimnis, "issues").json()["status"] == "ignoriert"
    assert github(api, pid, push(ref="refs/tags/v1.0.0"), geheimnis).json()["status"] == "geplant"


def test_wrong_or_missing_signatures_look_like_404(
    api: Api, klone: list[str], _migrated: str
) -> None:
    a, pid, geheimnis = einrichten(api)
    assert github(api, pid, push(), "falsch").status_code == 404
    c = api.client(base_url="https://api.luibui.com")
    assert c.post(f"/api/v1/webhooks/{pid}", content=push()).status_code == 404
    unbekannt = "00000000-0000-0000-0000-000000000000"
    assert github(api, unbekannt, push(), geheimnis).status_code == 404
    neu = a.post(f"/api/v1/projects/{pid}/webhook").json()["geheimnis"]  # rotate
    assert github(api, pid, push(), geheimnis).status_code == 404
    assert a.delete(f"/api/v1/projects/{pid}/webhook").status_code == 204
    assert github(api, pid, push(), neu).status_code == 404
    assert pruefungen(_migrated, pid) == 0


def test_gitlab_and_forgejo(api: Api, klone: list[str], _migrated: str) -> None:
    _, pid, geheimnis = einrichten(api)
    c = api.client(base_url="https://api.luibui.com")
    gitlab = json.dumps(
        {"ref": "refs/heads/main", "after": COMMIT,
         "project": {"git_http_url": REPO + ".git", "default_branch": "main"}}
    ).encode()  # fmt: skip
    r = c.post(f"/api/v1/webhooks/{pid}", content=gitlab,
               headers={"X-Gitlab-Token": geheimnis, "X-Gitlab-Event": "Push Hook"})  # fmt: skip
    assert r.json() == {"status": "geplant"}
    from sqlalchemy import create_engine, text

    engine = create_engine(_migrated)
    with engine.begin() as conn:  # the one-per-minute limit
        conn.execute(text("UPDATE projects SET webhook_letzter_lauf = :t"),
                     {"t": datetime.now(UTC) - timedelta(minutes=2)})  # fmt: skip
    engine.dispose()
    body = push()
    sig = hmac.new(geheimnis.encode(), body, hashlib.sha256).hexdigest()
    r = c.post(f"/api/v1/webhooks/{pid}", content=body,
               headers={"X-Forgejo-Signature": sig, "X-Forgejo-Event": "push"})  # fmt: skip
    assert r.json() == {"status": "geplant"}
    assert pruefungen(_migrated, pid) == 2


def test_only_git_projects_and_only_with_a_session(api: Api) -> None:
    a = api.user("anna@example.org")
    pid = project(a, name="zip")
    assert a.post(f"/api/v1/projects/{pid}/webhook").json()["detail"]["code"] == "kein_git"
    git = project(a, name="git", quelle="git", git_url=REPO)
    token = a.post("/api/v1/tokens", json={"name": "ci"}).json()["token"]
    c = api.client(base_url="https://api.luibui.com")
    r = c.post(f"/api/v1/projects/{git}/webhook", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (401, 403)
    info = a.get(f"/api/v1/projects/{git}/webhook").json()
    assert info["aktiv"] is False and info["geheimnis"] is None
