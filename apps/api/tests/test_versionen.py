"""S2-8 and S2-7: the version list of a project, deleting single versions, the source."""

from pathlib import Path

from .conftest import Api
from .test_scans import blobs, db_rows, project, upload_zip


def test_versions_are_listed_newest_first_with_their_check(api: Api) -> None:
    a = api.user("anna@example.org")
    pid = project(a)
    erste = upload_zip(a, pid).json()["id"]
    upload_zip(a, pid, {"SKILL.md": b"# LUIBUI-TESTFIXTURE Skill\nneu\n"})
    versionen = a.get(f"/api/v1/projects/{pid}/versions").json()
    assert [v["nummer"] for v in versionen] == [2, 1]
    assert versionen[1]["dateien"] == 2 and versionen[1]["bytes"] > 0
    assert versionen[1]["pruefung"]["id"] == erste
    assert versionen[0]["dateien_geloescht"] is False


def test_deleting_a_version_removes_its_files_and_keeps_the_report(
    api: Api, tmp_path: Path, _migrated: str
) -> None:
    a = api.user("anna@example.org")
    pid = project(a)
    scan = upload_zip(a, pid).json()["id"]
    upload_zip(a, pid)
    assert len(blobs(tmp_path)) == 4
    alt = a.get(f"/api/v1/projects/{pid}/versions").json()[1]
    assert a.delete(f"/api/v1/projects/{pid}/versions/{alt['id']}").status_code == 204
    assert len(blobs(tmp_path)) == 2
    assert [v["nummer"] for v in a.get(f"/api/v1/projects/{pid}/versions").json()] == [2]
    assert a.get(f"/api/v1/scans/{scan}").status_code == 200  # the check and its report stay
    assert db_rows(_migrated, "SELECT count(*) FROM stored_files")[0][0] == 2
    aktion = db_rows(_migrated, "SELECT action FROM audit_log WHERE action = 'version.geloescht'")
    assert aktion == [("version.geloescht",)]


def test_a_version_is_only_reached_through_its_own_project(api: Api, tmp_path: Path) -> None:
    a, b = api.user("anna@example.org"), api.user("bert@example.org")
    pid, anderes = project(a), project(a, "anderes")
    upload_zip(a, pid)
    (v,) = a.get(f"/api/v1/projects/{pid}/versions").json()
    assert a.delete(f"/api/v1/projects/{anderes}/versions/{v['id']}").status_code == 404
    b_pid = project(b)
    assert b.delete(f"/api/v1/projects/{b_pid}/versions/{v['id']}").status_code == 404
    assert b.get(f"/api/v1/projects/{pid}/versions").status_code == 404
    assert len(blobs(tmp_path)) == 2


def test_source_git_needs_an_address(api: Api) -> None:
    a = api.user("anna@example.org")
    r = a.post("/api/v1/projects", json={"name": "x", "typ": "skill", "quelle": "git"})
    assert r.status_code == 422
    r = a.post(
        "/api/v1/projects", json={"name": "x", "typ": "skill", "quelle": "git", "git_url": ""}
    )
    assert r.status_code == 422
    pid = project(a, "y", quelle="auswahl", git_url="")
    assert a.get(f"/api/v1/projects/{pid}").json()["quelle"] == "auswahl"
