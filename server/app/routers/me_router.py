import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session as DbSession

from ..config import Settings, get_settings
from ..database import get_db
from ..dependencies import require_user
from ..models import User
from ..schemas.users import ProfilePatch, PublicUser, SessionOut
from ..services import auth_services, security

router = APIRouter(prefix="/api/v1", tags=["me"])


@router.get("/me", response_model=PublicUser)
def get_me(user: User = Depends(require_user)) -> PublicUser:
    return auth_services.public_user(user)


@router.patch("/me", response_model=PublicUser)
def patch_me(
    patch: ProfilePatch,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> PublicUser:
    auth_services.update_name(db, user, patch.name)
    return auth_services.public_user(user)


@router.get("/me/sessions", response_model=list[SessionOut])
def list_sessions(
    request: Request,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[SessionOut]:
    token = request.cookies.get(settings.session_cookie_name)
    current_hash = security.hash_token(token) if token else None
    return auth_services.list_sessions(db, user, current_token_hash=current_hash)


@router.delete("/me/sessions/{session_id}", status_code=204)
def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    row = auth_services.revoke_session_by_id(db, user, session_id)
    token = request.cookies.get(settings.session_cookie_name)
    response = Response(status_code=204)
    if token and row.token_hash == security.hash_token(token):
        security.clear_cookie(response, settings.session_cookie_name, settings=settings)
    return response
