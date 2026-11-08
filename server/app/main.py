from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from .config import get_settings
from .logging_config import configure_logging
from .routers import auth_router, health_router, me_router
from .services.errors import ServiceError

settings = get_settings()
configure_logging(settings.log_level, settings.environment)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("secria.startup", environment=settings.environment)
    yield
    logger.info("secria.shutdown")


app = FastAPI(
    title="Secria API",
    version="0.1.0",
    description="Self-hosted secrets manager API.",
    lifespan=lifespan,
)


class SecurityHeaders:
    """Cheap defense-in-depth headers on every response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Any) -> None:
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                present = {key.lower() for key, _value in headers}
                additions = (
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                )
                for key, value in additions:
                    if key not in present:
                        headers.append((key, value))
            await send(message)

        await self.app(scope, receive, send_with_headers)


# Added before CORS so CORS stays the outermost layer.
app.add_middleware(SecurityHeaders)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _safe_validation_details(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Never echo submitted values: a validation error on a secret payload
    must not put the plaintext in the response body."""
    return [
        {
            "loc": list(error.get("loc", [])),
            "msg": error.get("msg", "Invalid value."),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]


@app.exception_handler(StarletteHTTPException)
async def http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """The client reads {"error": "..."} - keep that shape for string details."""
    if isinstance(exc.detail, str):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code, headers=exc.headers)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        {"error": "Check the details you sent.", "details": _safe_validation_details(exc)},
        status_code=422,
    )


@app.exception_handler(ServiceError)
async def service_error(_request: Request, exc: ServiceError) -> JSONResponse:
    """Services raise framework-free errors; the API surfaces them here."""
    return JSONResponse({"error": exc.message}, status_code=exc.status_code)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"name": "Secria API", "version": "0.1.0", "docs": "/docs"}


app.include_router(health_router.router)
app.include_router(auth_router.router)
app.include_router(me_router.router)
