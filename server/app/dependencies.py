from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import httpx
from fastapi import Depends, Request
from sqlalchemy.orm import Session as DbSession

from .config import Settings, get_settings
from .database import get_db
from .models import ServiceToken, User
from .services import auth_services, security, token_services
from .services.errors import UnauthorizedError
from .services.zitadel import ZitadelClient


@dataclass(frozen=True)
class Principal:
    user: User | None = None
    service_token: ServiceToken | None = None
    via: Literal["session", "bearer", "service_token"] = "session"
    session_token_hash: str | None = None


@lru_cache(maxsize=4)
def _zitadel_client(
    issuer: str,
    client_id: str,
    api_audience: str | None,
    cli_client_id: str | None,
) -> ZitadelClient:
    return ZitadelClient(
        issuer=issuer,
        client_id=client_id,
        api_audience=api_audience,
        cli_client_id=cli_client_id,
        http=httpx.Client(timeout=10.0),
    )


def get_zitadel(settings: Settings = Depends(get_settings)) -> ZitadelClient:
    return _zitadel_client(
        settings.zitadel_issuer.rstrip("/"),
        settings.zitadel_client_id,
        settings.zitadel_api_audience or None,
        settings.zitadel_cli_client_id or None,
    )


def current_principal(
    request: Request,
    db: DbSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    zitadel: ZitadelClient = Depends(get_zitadel),
) -> Principal | None:
    """Resolve a CLI bearer token first, then the web session cookie.

    A present but invalid Authorization header is an error; it never silently
    falls back to the cookie.
    """
    header = request.headers.get("authorization")
    if header is not None:
        scheme, _, token = header.partition(" ")
        raw = token.strip()
        if scheme.lower() != "bearer" or not raw:
            raise UnauthorizedError("Send a Bearer token.")
        if raw.startswith("secria_st_"):
            service_token = token_services.authenticate_service_token(db, raw)
            return Principal(
                service_token=service_token,
                via="service_token",
            )
        user = auth_services.user_from_bearer(db, raw, zitadel)
        return Principal(user=user, via="bearer")

    token = request.cookies.get(settings.session_cookie_name)
    user = auth_services.session_user(db, token, settings=settings)
    if user is None:
        return None
    return Principal(
        user=user,
        via="session",
        session_token_hash=security.hash_token(token) if token else None,
    )


def current_user(principal: Principal | None = Depends(current_principal)) -> User | None:
    return principal.user if principal is not None else None


def require_principal(principal: Principal | None = Depends(current_principal)) -> Principal:
    if principal is None:
        raise UnauthorizedError("Not signed in.")
    return principal


def require_user(principal: Principal = Depends(require_principal)) -> User:
    if principal.user is None:
        raise UnauthorizedError("A user session is required.")
    return principal.user


__all__ = [
    "Principal",
    "current_principal",
    "current_user",
    "get_db",
    "get_zitadel",
    "require_principal",
    "require_user",
]
