import httpx
import pytest

from secria_cli import discovery
from secria_cli.errors import AuthError


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_reads_public_config() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/config"
        return httpx.Response(
            200,
            json={
                "apiUrl": "https://ignored.example.com",
                "issuer": "https://idp.example.com/",
                "clientId": "cli-client",
            },
        )

    found = discovery.fetch("https://api.example.com/", client=_client(handler))
    assert found.api_url == "https://api.example.com"
    assert found.issuer == "https://idp.example.com"
    assert found.client_id == "cli-client"


def test_fetch_rejects_old_servers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "Not Found"})

    with pytest.raises(AuthError, match="does not expose"):
        discovery.fetch(
            "https://api.example.com",
            client=_client(handler),
        )


def test_fetch_rejects_missing_zitadel_config() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"apiUrl": "https://api.example.com", "issuer": "", "clientId": ""},
        )

    with pytest.raises(AuthError, match="missing its Zitadel configuration"):
        discovery.fetch(
            "https://api.example.com",
            client=_client(handler),
        )
