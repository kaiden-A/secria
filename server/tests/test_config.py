from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_public_config_is_public_and_cacheable(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "api_base_url", "https://api.example.com/")
    monkeypatch.setattr(settings, "zitadel_issuer", "https://idp.example.com/")
    monkeypatch.setattr(settings, "zitadel_client_id", "web-client")
    monkeypatch.setattr(settings, "zitadel_cli_client_id", "")

    with TestClient(app) as client:
        response = client.get("/api/v1/config")

    assert response.status_code == 200
    assert response.json() == {
        "apiUrl": "https://api.example.com",
        "issuer": "https://idp.example.com",
        "clientId": "web-client",
    }
    assert response.headers["cache-control"] == "public, max-age=300"


def test_public_config_prefers_the_cli_client(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "zitadel_client_id", "web-client")
    monkeypatch.setattr(settings, "zitadel_cli_client_id", "cli-client")

    with TestClient(app) as client:
        response = client.get("/api/v1/config")

    assert response.status_code == 200
    assert response.json()["clientId"] == "cli-client"


def test_public_config_falls_back_to_request_origin(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "api_base_url", "http://localhost:8000")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/config",
            headers={
                "x-forwarded-proto": "https",
                "x-forwarded-host": "secria.example.com",
            },
        )

    assert response.status_code == 200
    assert response.json()["apiUrl"] == "https://secria.example.com"
