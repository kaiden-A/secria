import httpx
import pytest

from secria_cli.api import SecriaAPI
from secria_cli.errors import ApiError


def _api(handler) -> SecriaAPI:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SecriaAPI("http://api.test", "token-1", client=client)


def test_get_json_and_authorization_header() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("authorization", ""))
        return httpx.Response(200, json={"email": "ada@example.com"})

    api = _api(handler)
    assert api.request("GET", "/api/v1/me") == {"email": "ada@example.com"}
    assert seen == ["Bearer token-1"]


def test_error_statuses_map_to_exit_codes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        status = int(request.url.path.rsplit("/", 1)[-1])
        return httpx.Response(status, json={"error": f"status {status}"})

    api = _api(handler)
    for status, code in [(401, 2), (403, 3), (409, 4), (422, 1)]:
        with pytest.raises(ApiError) as caught:
            api.request("GET", f"/api/v1/{status}")
        assert caught.value.exit_code == code


def test_no_content_and_plain_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/empty"):
            return httpx.Response(204)
        return httpx.Response(200, text="A=one\n", headers={"content-type": "text/plain"})

    api = _api(handler)
    assert api.request("DELETE", "/api/v1/empty") is None
    assert api.request_text("GET", "/api/v1/env") == "A=one\n"
