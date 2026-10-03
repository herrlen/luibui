"""S4-1: namespaces per account, unique and not mistakable (H04)."""

from .conftest import Api


def test_create_list_and_delete(api: Api) -> None:
    a = api.user("anna@example.org")
    r = a.post("/api/v1/namespaces", json={"name": " Anna-Tools "})
    assert r.status_code == 201 and r.json()["name"] == "anna-tools"
    a.post("/api/v1/namespaces", json={"name": "anna-privat"})
    assert [n["name"] for n in a.get("/api/v1/namespaces").json()] == ["anna-privat", "anna-tools"]
    assert a.delete(f"/api/v1/namespaces/{r.json()['id']}").status_code == 204
    assert [n["name"] for n in a.get("/api/v1/namespaces").json()] == ["anna-privat"]


def test_names_of_others_and_look_alikes_are_refused(api: Api) -> None:
    a = api.user("anna@example.org")
    b = api.user("bert@example.org")
    assert a.post("/api/v1/namespaces", json={"name": "acme-tools"}).status_code == 201
    for name in ("acme-tools", "acmetools", "acme-to0ls", "anthropic", "0penai"):
        r = b.post("/api/v1/namespaces", json={"name": name})
        assert r.status_code == 409 and r.json()["detail"]["code"] == "verwechselbar", name
    assert b.post("/api/v1/namespaces", json={"name": "bert"}).status_code == 201
    # The owner may hold close names; they fool nobody.
    assert a.post("/api/v1/namespaces", json={"name": "acme-tool"}).status_code == 201
    assert a.post("/api/v1/namespaces", json={"name": "acme-tools"}).status_code == 409


def test_invalid_names_limit_and_token_access(api: Api) -> None:
    a = api.user("anna@example.org")
    assert a.post("/api/v1/namespaces", json={"name": "-x-"}).status_code == 422
    for i in range(5):
        assert a.post("/api/v1/namespaces", json={"name": f"anna-{'abcde'[i]}x"}).status_code == 201
    assert a.post("/api/v1/namespaces", json={"name": "anna-zz"}).json()["detail"]["code"] == (
        "zu_viele"
    )
    token = a.post("/api/v1/tokens", json={"name": "ci"}).json()["token"]
    api_host = api.client(base_url="https://api.luibui.com")
    h = {"Authorization": f"Bearer {token}"}
    assert api_host.get("/api/v1/namespaces", headers=h).status_code == 200  # reading is fine
    assert api_host.post("/api/v1/namespaces", json={"name": "ci-ns"}, headers=h).status_code in (
        401,
        403,
    )
