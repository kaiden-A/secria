from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Root .env lives next to package.json; server/.env is accepted as a fallback.
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
SERVER_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
ENV_FILE = ROOT_ENV_FILE if ROOT_ENV_FILE.exists() else SERVER_ENV_FILE


def _normalize_database_url(url: str) -> str:
    """Normalize a Postgres URL for SQLAlchemy + pg8000.

    pg8000 is a pure-Python driver: libpq-only query parameters (sslmode,
    channel_binding, ...) are dropped; SSL is configured via ssl_context in
    database.py and alembic/env.py instead.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+pg8000://", 1)
    head, sep, query = url.partition("?")
    if not sep:
        return url
    dropped = ("channel_binding=", "sslmode=", "sslrootcert=", "sslcert=", "sslkey=")
    kept = [part for part in query.split("&") if part and not part.startswith(dropped)]
    return f"{head}?{'&'.join(kept)}" if kept else head


def _ssl_required(url: str) -> bool:
    return any(
        part.startswith("sslmode=") and part.split("=", 1)[1] in {"require", "verify-ca", "verify-full"}
        for part in url.partition("?")[2].split("&")
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str
    database_url_direct: str = ""
    # Neon's pooler runs in transaction mode, so session state (search_path)
    # cannot be trusted: every table is addressed with an explicit schema.
    db_schema: str = "public"

    environment: str = "development"
    log_level: str = "INFO"

    app_secret: str = "dev-only-insecure-secret"
    secria_master_key: str = ""
    secria_master_key_version: int = 1

    api_base_url: str = "http://localhost:8000"
    app_url: str = "http://localhost:3000"
    web_origin: str = "http://localhost:3000"

    session_cookie_name: str = "secria_session"
    session_ttl_days: int = 30
    cookie_secure: bool = False

    zitadel_issuer: str = "https://<instance>.zitadel.cloud"
    zitadel_client_id: str = ""
    zitadel_redirect_uri: str = "http://localhost:3000/api/auth/callback"
    zitadel_post_logout_uri: str = "http://localhost:3000/login"
    zitadel_api_audience: str = ""

    rate_limit_enabled: bool = True
    cors_origins: str = ""

    resend_api_key: str = ""
    email_from: str = "Secria <onboarding@resend.dev>"
    email_reply_to: str = ""
    email_override_to: str = ""

    @property
    def sqlalchemy_url(self) -> str:
        return _normalize_database_url(self.database_url)

    @property
    def alembic_database_url(self) -> str:
        return _normalize_database_url(self.database_url_direct or self.database_url)

    @property
    def ssl_required(self) -> bool:
        return _ssl_required(self.database_url)

    @property
    def alembic_ssl_required(self) -> bool:
        return _ssl_required(self.database_url_direct or self.database_url)

    @property
    def master_key_bytes(self) -> bytes:
        import base64
        import binascii

        if not self.secria_master_key:
            raise RuntimeError("SECRIA_MASTER_KEY is not configured.")
        try:
            raw = base64.b64decode(self.secria_master_key, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise RuntimeError("SECRIA_MASTER_KEY must be valid base64.") from exc
        if len(raw) != 32:
            raise RuntimeError("SECRIA_MASTER_KEY must decode to exactly 32 bytes.")
        return raw

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def email_configured(self) -> bool:
        return bool(self.resend_api_key and self.email_from)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]  # values come from .env / environment
