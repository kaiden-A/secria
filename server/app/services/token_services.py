import secrets
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..models import (
    Environment,
    Project,
    ProjectRole,
    ServiceToken,
    ServiceTokenAccess,
    User,
    Workspace,
    WorkspaceRole,
    utcnow,
)
from ..schemas.tokens import (
    ServiceTokenCreate,
    ServiceTokenCreateResult,
    ServiceTokenOut,
    ServiceTokenScope,
)
from ..utils import from_ms, to_ms
from . import audit_services, security
from .audit_services import AuditContext
from .errors import ForbiddenError, InvalidError, NotFoundError, UnauthorizedError
from .permissions import ProjectAccess, require_project_access

LAST_USED_THROTTLE = timedelta(minutes=5)


def _token_out(token: ServiceToken) -> ServiceTokenOut:
    return ServiceTokenOut(
        id=str(token.id),
        projectId=str(token.project_id),
        environmentId=str(token.environment_id),
        name=token.name,
        access=token.access,
        expiresAt=to_ms(token.expires_at),
        lastUsedAt=to_ms(token.last_used_at),
        revokedAt=to_ms(token.revoked_at),
        createdAt=int(to_ms(token.created_at) or 0),
    )


def _admin_access(
    db: DbSession,
    user: User,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
):
    access = require_project_access(
        db,
        user,
        project_id,
        roles={ProjectRole.admin},
        environment_id=environment_id,
    )
    environment = db.get(Environment, environment_id)
    if environment is None or environment.project_id != project_id:
        raise NotFoundError("Environment not found.")
    return access, environment


def list_tokens(
    db: DbSession,
    user: User,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
) -> list[ServiceTokenOut]:
    _admin_access(db, user, project_id, environment_id)
    tokens = db.scalars(
        select(ServiceToken)
        .where(
            ServiceToken.project_id == project_id,
            ServiceToken.environment_id == environment_id,
        )
        .order_by(ServiceToken.created_at.desc())
    ).all()
    return [_token_out(token) for token in tokens]


def create_token(
    db: DbSession,
    user: User,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    data: ServiceTokenCreate,
    *,
    context: AuditContext | None = None,
) -> ServiceTokenCreateResult:
    access, _environment = _admin_access(db, user, project_id, environment_id)
    name = data.name.strip()
    if not name:
        raise InvalidError("A token name is required.")
    expires_at = from_ms(data.expiresAt)
    if expires_at is not None and expires_at <= utcnow():
        raise InvalidError("The expiry must be in the future.")

    raw = f"secria_st_{secrets.token_urlsafe(32)}"
    token = ServiceToken(
        id=uuid.uuid4(),
        project_id=project_id,
        environment_id=environment_id,
        name=name,
        token_hash=security.hash_token(raw),
        access=data.access,
        expires_at=expires_at,
        created_by=user.id,
        created_at=utcnow(),
    )
    db.add(token)
    audit_services.record(
        db,
        workspace_id=access.workspace.id,
        project_id=project_id,
        environment_id=environment_id,
        actor=user,
        action="service_token.created",
        target=f"token:{name}",
        metadata={
            "access": data.access.value,
            "expiresAt": data.expiresAt,
        },
        context=context,
    )
    db.commit()
    out = _token_out(token)
    return ServiceTokenCreateResult(**out.model_dump(), token=raw)


def revoke_token(
    db: DbSession,
    user: User,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    token_id: uuid.UUID,
    *,
    context: AuditContext | None = None,
) -> None:
    access, _environment = _admin_access(db, user, project_id, environment_id)
    token = db.get(ServiceToken, token_id)
    if (
        token is None
        or token.project_id != project_id
        or token.environment_id != environment_id
    ):
        raise NotFoundError("Service token not found.")
    if token.revoked_at is not None:
        return
    token.revoked_at = utcnow()
    audit_services.record(
        db,
        workspace_id=access.workspace.id,
        project_id=project_id,
        environment_id=environment_id,
        actor=user,
        action="service_token.revoked",
        target=f"token:{token.name}",
        metadata={},
        context=context,
    )
    db.commit()


def authenticate_service_token(db: DbSession, raw: str) -> ServiceToken:
    token = db.scalar(
        select(ServiceToken).where(ServiceToken.token_hash == security.hash_token(raw))
    )
    if token is None or token.revoked_at is not None:
        raise UnauthorizedError("Service token is invalid or revoked.")
    now = utcnow()
    if token.expires_at is not None and token.expires_at <= now:
        raise UnauthorizedError("Service token has expired.")
    if token.last_used_at is None or now - token.last_used_at > LAST_USED_THROTTLE:
        token.last_used_at = now
        db.commit()
    return token


def scope_for_token(db: DbSession, token: ServiceToken) -> ServiceTokenScope:
    project = db.get(Project, token.project_id)
    environment = db.get(Environment, token.environment_id)
    if project is None or environment is None or environment.project_id != project.id:
        raise NotFoundError("Service token scope is no longer available.")
    workspace = db.get(Workspace, project.workspace_id)
    if workspace is None:
        raise NotFoundError("Service token scope is no longer available.")
    return ServiceTokenScope(
        tokenId=str(token.id),
        name=token.name,
        access=token.access,
        workspaceId=str(workspace.id),
        workspaceSlug=workspace.slug,
        workspaceName=workspace.name,
        projectId=str(project.id),
        projectSlug=project.slug,
        projectName=project.name,
        environmentId=str(environment.id),
        environmentSlug=environment.slug,
        environmentName=environment.name,
    )


def require_service_access(
    db: DbSession,
    token: ServiceToken,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    *,
    write: bool = False,
):
    """Resolve a service token's one project/environment scope.

    The caller is a service token, not a user, so there is no workspace
    membership. A request for any other project/environment is a 404.
    """
    if token.project_id != project_id or token.environment_id != environment_id:
        raise NotFoundError("Environment not found.")
    if write and token.access != ServiceTokenAccess.read_write:
        raise ForbiddenError("This service token is read-only.")
    project = db.get(Project, project_id)
    environment = db.get(Environment, environment_id)
    if project is None or environment is None or environment.project_id != project.id:
        raise NotFoundError("Environment not found.")
    workspace = db.get(Workspace, project.workspace_id)
    if workspace is None:
        raise NotFoundError("Environment not found.")
    return ProjectAccess(
        workspace=workspace,
        project=project,
        workspace_role=WorkspaceRole.member,
        project_role=ProjectRole.editor if write else ProjectRole.viewer,
        allowed_environment_ids=frozenset({environment.id}),
    ), environment
