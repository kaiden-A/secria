import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..dependencies import Principal, require_principal, require_user
from ..models import User
from ..rate_limit import SCOPE_LIMIT, TOKEN_CREATE_LIMIT, limiter
from ..schemas.tokens import (
    ServiceTokenCreate,
    ServiceTokenCreateResult,
    ServiceTokenOut,
    ServiceTokenScope,
)
from ..services import token_services
from ..services.audit_services import AuditContext
from ..services.errors import UnauthorizedError

router = APIRouter(prefix="/api/v1", tags=["service-tokens"])


def _context(request: Request) -> AuditContext:
    return AuditContext(
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/service-tokens/current", response_model=ServiceTokenScope)
@limiter.limit(SCOPE_LIMIT)
def current_token_scope(
    request: Request,
    principal: Principal = Depends(require_principal),
    db: DbSession = Depends(get_db),
) -> ServiceTokenScope:
    """Resolve the workspace/project/environment a CI token is scoped to."""
    if principal.service_token is None:
        raise UnauthorizedError("A service token is required.")
    return token_services.scope_for_token(db, principal.service_token)


@router.get(
    "/projects/{project_id}/environments/{environment_id}/service-tokens",
    response_model=list[ServiceTokenOut],
)
def list_service_tokens(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> list[ServiceTokenOut]:
    return token_services.list_tokens(db, user, project_id, environment_id)


@router.post(
    "/projects/{project_id}/environments/{environment_id}/service-tokens",
    response_model=ServiceTokenCreateResult,
    status_code=201,
)
@limiter.limit(TOKEN_CREATE_LIMIT)
def create_service_token(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    data: ServiceTokenCreate,
    request: Request,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> ServiceTokenCreateResult:
    return token_services.create_token(
        db,
        user,
        project_id,
        environment_id,
        data,
        context=_context(request),
    )


@router.delete(
    "/projects/{project_id}/environments/{environment_id}/service-tokens/{token_id}",
    status_code=204,
)
def revoke_service_token(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    token_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> None:
    token_services.revoke_token(
        db,
        user,
        project_id,
        environment_id,
        token_id,
        context=_context(request),
    )
