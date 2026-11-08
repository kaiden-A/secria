import hmac
import time
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session as DbSession

from ..config import Settings, get_settings
from ..database import get_db
from ..dependencies import get_zitadel
from ..rate_limit import AUTH_LIMIT, limiter
from ..schemas.auth import LogoutResponse
from ..services import auth_services, security
from ..services.errors import UnauthorizedError, UpstreamError
from ..services.zitadel import ZitadelClient, ZitadelError
from ..utils import local_path

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Only the prompts we use; anything else is ignored rather than forwarded.
ALLOWED_PROMPTS = {"login", "create", "select_account"}


def _start_login(
    request: Request,
    settings: Settings,
    zitadel: ZitadelClient,
    *,
    default_prompt: str | None = None,
) -> RedirectResponse:
    verifier, challenge = security.create_pkce_pair()
    state, nonce = security.new_state_nonce()
    payload = {
        "state": state,
        "nonce": nonce,
        "code_verifier": verifier,
        "next": local_path(request.query_params.get("next"), default="/w"),
        "iat": int(time.time()),
    }
    login_hint = (request.query_params.get("login_hint") or "").strip()[:320] or None
    prompt = (request.query_params.get("prompt") or default_prompt or "").strip().lower()
    try:
        authorize_url = zitadel.authorize_url(
            state=state,
            nonce=nonce,
            code_challenge=challenge,
            redirect_uri=settings.zitadel_redirect_uri,
            login_hint=login_hint,
            prompt=prompt if prompt in ALLOWED_PROMPTS else None,
        )
    except ZitadelError as exc:
        raise UpstreamError("The identity provider is unavailable.") from exc

    response = RedirectResponse(authorize_url, status_code=302)
    security.set_cookie(
        response,
        security.OAUTH_COOKIE,
        security.sign_payload(payload, settings.app_secret),
        settings=settings,
        max_age=security.OAUTH_COOKIE_MAX_AGE,
    )
    return response


@router.get("/login")
@limiter.limit(AUTH_LIMIT)
def login_get(
    request: Request,
    settings: Settings = Depends(get_settings),
    zitadel: ZitadelClient = Depends(get_zitadel),
) -> RedirectResponse:
    """Send the browser to the identity provider."""
    return _start_login(request, settings, zitadel)


@router.post("/login")
@limiter.limit(AUTH_LIMIT)
def login_post(
    request: Request,
    settings: Settings = Depends(get_settings),
    zitadel: ZitadelClient = Depends(get_zitadel),
) -> RedirectResponse:
    return _start_login(request, settings, zitadel)


@router.post("/signup")
@limiter.limit(AUTH_LIMIT)
def signup(
    request: Request,
    settings: Settings = Depends(get_settings),
    zitadel: ZitadelClient = Depends(get_zitadel),
) -> RedirectResponse:
    """Registration happens inside the hosted IdP login."""
    return _start_login(request, settings, zitadel, default_prompt="create")


@router.get("/callback")
@limiter.limit(AUTH_LIMIT)
def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: DbSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    zitadel: ZitadelClient = Depends(get_zitadel),
) -> RedirectResponse:
    failure = f"{settings.app_url.rstrip('/')}/login"
    payload = security.unsign_payload(
        request.cookies.get(security.OAUTH_COOKIE),
        settings.app_secret,
        max_age=security.OAUTH_COOKIE_MAX_AGE,
    )

    if error:
        query = urlencode({"error": "Signing in was cancelled."})
        response = RedirectResponse(f"{failure}?{query}", status_code=302)
        security.clear_cookie(response, security.OAUTH_COOKIE, settings=settings)
        return response
    if (
        payload is None
        or not code
        or not state
        or not hmac.compare_digest(str(payload.get("state", "")), state)
    ):
        raise UnauthorizedError("Could not finish signing in. Please try again.")

    verifier = str(payload.get("code_verifier") or "")
    nonce = str(payload.get("nonce") or "")
    if not verifier or not nonce:
        raise UnauthorizedError("Could not finish signing in. Please try again.")

    try:
        tokens = zitadel.exchange_code(
            code=code,
            code_verifier=verifier,
            redirect_uri=settings.zitadel_redirect_uri,
        )
    except ZitadelError as exc:
        raise UpstreamError("The identity provider could not finish the sign-in.") from exc

    id_token = tokens.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise UnauthorizedError("The identity provider did not return an ID token.")
    try:
        claims = zitadel.verify_id_token(id_token, nonce=nonce)
    except ZitadelError as exc:
        raise UnauthorizedError("Could not verify your sign-in.") from exc

    user = auth_services.upsert_user_from_claims(db, claims)
    token = auth_services.create_session(
        db,
        user,
        settings=settings,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    response = RedirectResponse(local_path(str(payload.get("next"))), status_code=302)
    security.set_cookie(
        response,
        settings.session_cookie_name,
        token,
        settings=settings,
        max_age=settings.session_ttl_days * 24 * 3600,
    )
    security.clear_cookie(response, security.OAUTH_COOKIE, settings=settings)
    return response


@router.post("/logout")
@limiter.limit(AUTH_LIMIT)
def logout(
    request: Request,
    db: DbSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    zitadel: ZitadelClient = Depends(get_zitadel),
) -> JSONResponse:
    """Delete the local session and return the IdP end-session URL.

    Without the IdP round-trip the IdP cookie survives, so the next SSO click
    silently signs the user back in.
    """
    token = request.cookies.get(settings.session_cookie_name)
    auth_services.revoke_session(db, token)
    logout_url: str | None = None
    try:
        logout_url = zitadel.end_session_url(
            post_logout_redirect_uri=settings.zitadel_post_logout_uri
        )
    except ZitadelError:
        # Never trap someone in the app because the IdP is down.
        logout_url = None
    response = JSONResponse(LogoutResponse(logoutUrl=logout_url).model_dump())
    security.clear_cookie(response, settings.session_cookie_name, settings=settings)
    return response
