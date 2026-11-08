from urllib.parse import urlparse

from fastapi import APIRouter, Request, Response

from ..config import get_settings

router = APIRouter(prefix="/api/v1", tags=["config"])


def _is_local(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _public_base_url(request: Request, configured: str) -> str:
    """Prefer API_BASE_URL, but never advertise localhost from Cloud Run."""
    configured = configured.rstrip("/")
    if configured and not _is_local(configured):
        return configured
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if host:
        return f"{proto}://{host}".rstrip("/")
    return configured or str(request.base_url).rstrip("/")


@router.get("/config")
def public_config(request: Request, response: Response) -> dict[str, str]:
    """Public bootstrap values for the CLI. Never contains secrets."""
    settings = get_settings()
    response.headers["Cache-Control"] = "public, max-age=300"
    return {
        "apiUrl": _public_base_url(request, settings.api_base_url),
        "issuer": settings.zitadel_issuer.rstrip("/"),
        "clientId": settings.zitadel_cli_client_id or settings.zitadel_client_id,
    }
