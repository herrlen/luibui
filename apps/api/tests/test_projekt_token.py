"""S5-5: a project token for CI starts and reads checks of one project, nothing else; the report
comes as SARIF for GitHub Code Scanning."""

import json
import uuid
from typing import Any

from .conftest import Api
from .test_pakete import fertig
from .test_scans import project, upload_zip


def ci(api: Api, token: str) -> Any:
    c = api.client("https://api.luibui.com")
    c.headers["Authorization"] = f"Bearer {token}"
    return c


def test_project_token_checks_its_project_and_gets_sarif(api: Api, _migrated: str) -> None:
    anna = api.user("anna@example.org")
    pid, andere = project(anna), project(anna, name="anderes")
    r = anna.post("/api/v1/tokens", json={"name": "ci", "project_id": pid})
    assert r.status_code == 201 and r.json()["project_id"] == pid
    c = ci(api, r.json()["token"])

    sid = upload_zip(c, pid).json()["id"]
    assert c.get(f"/api/v1/scans/{sid}").status_code == 200
    assert c.get(f"/api/v1/projects/{pid}").status_code == 200
    assert c.get(f"/api/v1/scans/{sid}/bericht.sarif").status_code == 409  # not finished
    fertig(_migrated, sid)
    sarif = c.get(f"/api/v1/scans/{sid}/bericht.sarif")
    assert sarif.status_code == 200
    assert sarif.headers["content-type"].startswith("application/sarif+json")
    assert json.loads(sarif.text)["version"] == "2.1.0"

    # The other project of the same account, and its checks: as if they did not exist.
    fremd = upload_zip(anna, andere).json()["id"]
    assert upload_zip(c, andere).status_code == 403
    assert c.get(f"/api/v1/scans/{fremd}").status_code == 404
    assert c.get(f"/api/v1/scans/{fremd}/bericht.sarif").status_code == 404
    # Everything else of the account is closed.
    for methode, pfad in [
        ("GET", "/api/v1/projects"),
        ("GET", "/api/v1/scans"),
        ("GET", f"/api/v1/projects/{pid}/scans"),
        ("GET", f"/api/v1/projects/{pid}/versions"),
        ("DELETE", f"/api/v1/projects/{pid}"),
        ("DELETE", f"/api/v1/scans/{sid}"),
        ("GET", "/api/v1/konto/speicher"),
        ("POST", "/api/v1/scans"),
    ]:
        assert c.request(methode, pfad).status_code == 403, pfad


def test_project_token_only_for_own_projects(api: Api) -> None:
    anna, bert = api.user("anna@example.org"), api.user("bert@example.org")
    pid = project(anna)
    r = bert.post("/api/v1/tokens", json={"name": "ci", "project_id": pid})
    assert r.status_code == 404
    r = bert.post("/api/v1/tokens", json={"name": "ci", "project_id": str(uuid.uuid4())})
    assert r.status_code == 404


def test_sarif_of_another_user_is_not_found(api: Api, _migrated: str) -> None:
    anna, bert = api.user("anna@example.org"), api.user("bert@example.org")
    sid = upload_zip(anna, project(anna)).json()["id"]
    fertig(_migrated, sid)
    assert anna.get(f"/api/v1/scans/{sid}/bericht.sarif").status_code == 200
    assert bert.get(f"/api/v1/scans/{sid}/bericht.sarif").status_code == 404


def test_deleting_the_project_deletes_its_tokens(api: Api) -> None:
    anna = api.user("anna@example.org")
    pid = project(anna)
    token = anna.post("/api/v1/tokens", json={"name": "ci", "project_id": pid}).json()["token"]
    assert anna.delete(f"/api/v1/projects/{pid}").status_code == 204
    assert ci(api, token).get(f"/api/v1/projects/{pid}").status_code == 401
