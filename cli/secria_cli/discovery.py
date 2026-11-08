from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from . import config
from .errors import AuthError


@dataclass(frozen=True)
class ServerConfig:
    api_url: str
    issuer: str
    client_id: str


def fetch(server: str, *, client: httpx.Client | None = None) -> ServerConfig:
    """Read the public bootstrap values from a Secria server.

    The queried origin is treated as the API URL; the response's apiUrl is
    informational so a compromised server cannot silently move the CLI.
    """
    base = config.validate_server_url(server)
    own_client = client is None
    http = client or httpx.Client(timeout=10.0)
    try:
        try:
            response = http.get(f"{base}/api/v1/config")
        except httpx.HTTPError as exc:
            raise AuthError(
                f"Could not reach the Secria API at {base} ({type(exc).__name__})."
            ) from exc
    finally:
        if own_client:
            http.close()

    if response.status_code == 404:
        raise AuthError(
            f"{base} does not expose /api/v1/config. "
            "Check that the server is up to date."
        )
    if response.status_code >= 400:
        raise AuthError(
            f"The Secria API returned HTTP {response.status_code} "
            "for its public configuration."
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise AuthError("The Secria API returned an invalid configuration.") from exc
    if not isinstance(data, dict):
        raise AuthError("The Secria API returned an invalid configuration.")

    issuer = config.normalize_url(str(data.get("issuer") or ""))
    client_id = str(data.get("clientId") or "").strip()
    if not issuer or not client_id:
        raise AuthError(
            "The Secria API is missing its Zitadel configuration. "
            "Ask the administrator to set ZITADEL_ISSUER and ZITADEL_CLIENT_ID."
        )
    parsed = urlparse(issuer)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AuthError("The Secria API returned an invalid Zitadel issuer.")

    return ServerConfig(api_url=base, issuer=issuer, client_id=client_id)
