"""Small, dependency-free rate-limit seam.

Limits are per client IP. They are deliberately forgiving: the goal is to blunt
credential stuffing and download scraping, not to throttle normal dashboard use.
Set RATE_LIMIT_ENABLED=false for local load tests.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import get_settings

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
    # Endpoints return Pydantic models, not Response objects. Header injection
    # would require adding a `response` parameter to every route; the 429
    # handler still sends Retry-After.
    headers_enabled=False,
)

# Auth-adjacent limits are intentionally tight; reads are generous.
AUTH_LIMIT = "30/minute"
DOWNLOAD_LIMIT = "60/minute"
COPY_LIMIT = "30/minute"
REVEAL_LIMIT = "120/minute"
INVITE_CREATE_LIMIT = "20/hour"
INVITE_RESEND_LIMIT = "10/hour"
TOKEN_CREATE_LIMIT = "20/hour"
SCOPE_LIMIT = "120/minute"
