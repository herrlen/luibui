import pytest
from fastapi.testclient import TestClient

from luibui_api.main import create_app


def test_health_reports_503_without_database(caplog: pytest.LogCaptureFixture) -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
    assert "not-the-password" not in response.text
    assert "not-the-password" not in caplog.text


@pytest.mark.db
def test_health_ok_with_database(use_database: str) -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_health_reports_the_baked_in_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """scripts/release.sh waits until /health reports the new image tag."""
    assert TestClient(create_app()).get("/health").json()["version"] == "lokal"
    monkeypatch.setenv("LUIBUI_VERSION", "sha-abc")
    assert TestClient(create_app()).get("/health").json()["version"] == "sha-abc"


def test_docs_are_disabled_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    from luibui_api.settings import get_settings

    monkeypatch.setenv("LUIBUI_ENV", "prod")
    get_settings.cache_clear()
    client = TestClient(create_app())
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
