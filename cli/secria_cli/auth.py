import base64
import contextlib
import json
import os
import time
import webbrowser
from typing import Any

import httpx
import keyring
from rich.console import Console

from . import config
from .errors import AuthError

console = Console()
SCOPE = "openid profile email offline_access"
TOKEN_SERVICE = "secria"
TOKEN_USERNAME = "session"


def _keyring_enabled() -> bool:
    return os.getenv("SECRIA_DISABLE_KEYRING", "").lower() not in {"1", "true", "yes"}


class TokenStore:
    def get(self) -> dict[str, Any] | None:
        if _keyring_enabled():
            try:
                raw = keyring.get_password(TOKEN_SERVICE, TOKEN_USERNAME)
                if raw:
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
        path = config.credentials_path()
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def set(self, data: dict[str, Any]) -> None:
        raw = json.dumps(data)
        if _keyring_enabled():
            try:
                keyring.set_password(TOKEN_SERVICE, TOKEN_USERNAME, raw)
                with contextlib.suppress(OSError):
                    config.credentials_path().unlink(missing_ok=True)
                return
            except Exception:
                pass
        config.secure_write(config.credentials_path(), raw + "\n")

    def clear(self) -> None:
        if _keyring_enabled():
            with contextlib.suppress(Exception):
                keyring.delete_password(TOKEN_SERVICE, TOKEN_USERNAME)
        with contextlib.suppress(OSError):
            config.credentials_path().unlink(missing_ok=True)


def decode_claims(token: str | None) -> dict[str, Any]:
    if not token or token.count(".") < 2:
        return {}
    try:
        body = token.split(".", 2)[1]
        padded = body + "=" * (-len(body) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _discover(issuer: str) -> dict[str, Any]:
    try:
        response = httpx.get(
            f"{issuer.rstrip('/')}/.well-known/openid-configuration", timeout=10.0
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AuthError("Could not reach the Zitadel instance.") from exc
    if not isinstance(data, dict):
        raise AuthError("Zitadel returned an invalid discovery document.")
    return data


def _issuer_and_client() -> tuple[str, str]:
    issuer = config.zitadel_issuer().rstrip("/")
    client_id = config.zitadel_client_id()
    if not issuer or not client_id:
        raise AuthError(
            "ZITADEL_ISSUER and ZITADEL_CLIENT_ID are not configured. "
            "Set them in the environment or the repository .env."
        )
    return issuer, client_id


def _store_tokens(issuer: str, client_id: str, response: dict[str, Any]) -> dict[str, Any]:
    access_token = response.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise AuthError("The identity provider did not return an access token.")
    id_token = response.get("id_token")
    claims = decode_claims(id_token if isinstance(id_token, str) else access_token)
    expires_in = int(response.get("expires_in") or 3600)
    data: dict[str, Any] = {
        "access_token": access_token,
        "id_token": id_token if isinstance(id_token, str) else None,
        "refresh_token": response.get("refresh_token"),
        "expires_at": int(time.time()) + expires_in,
        "issuer": issuer,
        "client_id": client_id,
        "email": claims.get("email"),
        "sub": claims.get("sub"),
    }
    TokenStore().set(data)
    return data


def device_login(*, open_browser: bool = True) -> dict[str, Any]:
    issuer, client_id = _issuer_and_client()
    discovery = _discover(issuer)
    device_endpoint = discovery.get("device_authorization_endpoint")
    token_endpoint = discovery.get("token_endpoint")
    if not isinstance(device_endpoint, str) or not isinstance(token_endpoint, str):
        raise AuthError("This Zitadel instance does not support the device flow.")

    try:
        response = httpx.post(
            device_endpoint,
            data={"client_id": client_id, "scope": SCOPE},
            timeout=15.0,
        )
        response.raise_for_status()
        device = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AuthError("Could not start the device login.") from exc

    device_code = device.get("device_code")
    user_code = device.get("user_code")
    verification_uri = device.get("verification_uri")
    complete_uri = device.get("verification_uri_complete") or verification_uri
    if not all(isinstance(value, str) and value for value in (device_code, user_code, verification_uri)):
        raise AuthError("Zitadel returned an invalid device authorization response.")

    console.print("Open this page to sign in:")
    console.print(f"  [bold]{verification_uri}[/bold]")
    console.print(f"Code: [bold]{user_code}[/bold]")
    if open_browser:
        with contextlib.suppress(Exception):
            webbrowser.open(str(complete_uri))

    interval = max(1, int(device.get("interval") or 5))
    deadline = time.time() + int(device.get("expires_in") or 300)
    while time.time() < deadline:
        try:
            token_response = httpx.post(
                token_endpoint,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code,
                    "client_id": client_id,
                },
                timeout=15.0,
            )
            payload = token_response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthError("Could not complete the device login.") from exc
        if token_response.status_code == 200 and isinstance(payload, dict):
            data = _store_tokens(issuer, client_id, payload)
            email = data.get("email") or "your account"
            console.print(f"Signed in as [bold]{email}[/bold].")
            return data
        error = payload.get("error") if isinstance(payload, dict) else None
        if error == "authorization_pending":
            time.sleep(interval)
            continue
        if error == "slow_down":
            interval += 5
            time.sleep(interval)
            continue
        if error in {"expired_token", "access_denied"}:
            raise AuthError("The device login expired or was denied. Try `secria login` again.")
        detail = payload.get("error_description") if isinstance(payload, dict) else None
        raise AuthError(str(detail or error or "Device login failed."))
    raise AuthError("The device login timed out. Try `secria login` again.")


def refresh(data: dict[str, Any]) -> dict[str, Any]:
    issuer = str(data.get("issuer") or config.zitadel_issuer()).rstrip("/")
    client_id = str(data.get("client_id") or config.zitadel_client_id())
    refresh_token = data.get("refresh_token")
    if not issuer or not client_id or not refresh_token:
        raise AuthError("Your session expired. Run `secria login`.")
    discovery = _discover(issuer)
    token_endpoint = discovery.get("token_endpoint")
    if not isinstance(token_endpoint, str):
        raise AuthError("Zitadel did not expose a token endpoint.")

    try:
        response = httpx.post(
            token_endpoint,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "refresh_token": refresh_token,
            },
            timeout=15.0,
        )
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AuthError("Your session expired. Run `secria login`.") from exc
    if response.status_code >= 400 or not isinstance(payload, dict):
        raise AuthError("Your session expired. Run `secria login`.")
    updated = _store_tokens(issuer, client_id, payload)
    if not updated.get("refresh_token"):
        updated["refresh_token"] = refresh_token
        TokenStore().set(updated)
    return updated


def get_token() -> str:
    service_token = (os.getenv("SECRIA_TOKEN") or "").strip()
    if service_token:
        return service_token
    store = TokenStore()
    data = store.get()
    if data is None:
        raise AuthError("Not signed in. Run `secria login`.")
    expires_at = int(data.get("expires_at") or 0)
    if expires_at and expires_at <= time.time() + 60:
        data = refresh(data)
    token = data.get("id_token") or data.get("access_token")
    if not isinstance(token, str) or not token:
        raise AuthError("Your stored session is incomplete. Run `secria login`.")
    return token


def is_service_token() -> bool:
    """True when SECRIA_TOKEN carries a service token rather than a JWT."""
    return (os.getenv("SECRIA_TOKEN") or "").strip().startswith("secria_st_")


def logout() -> None:
    TokenStore().clear()
