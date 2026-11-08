from typing import Any

import httpx

from .errors import ApiError


class SecriaAPI:
    def __init__(
        self,
        base_url: str,
        token: str | None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = client or httpx.Client(timeout=30.0)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _handle_error(self, response: httpx.Response) -> None:
        message = f"HTTP {response.status_code}"
        try:
            body = response.json()
            if isinstance(body, dict) and isinstance(body.get("error"), str):
                message = body["error"]
        except ValueError:
            pass
        if response.status_code == 401:
            message = "Not signed in. Run `secria login`."
        elif response.status_code == 403:
            message = message if message != "HTTP 403" else "Your role does not allow that action."
        elif response.status_code == 409:
            message = message if message != "HTTP 409" else "That conflicts with an existing item."
        raise ApiError(response.status_code, message)

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = self.client.request(
            method,
            f"{self.base_url}{path}",
            json=json_body,
            params=params,
            headers=self._headers(),
        )
        if response.status_code >= 400:
            self._handle_error(response)
        if response.status_code == 204:
            return None
        if "application/json" in response.headers.get("content-type", ""):
            return response.json()
        return response.text

    def request_text(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> str:
        response = self.client.request(
            method,
            f"{self.base_url}{path}",
            params=params,
            headers=self._headers(),
        )
        if response.status_code >= 400:
            self._handle_error(response)
        return response.text
