import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..dependencies import require_user
from ..models import User
from ..rate_limit import INVITE_CREATE_LIMIT, INVITE_RESEND_LIMIT, limiter
from ..schemas.invites import (
    InviteAcceptResult,
    InviteCreate,
    InviteCreateResult,
    InviteOut,
    InvitePatch,
    InvitePreview,
    InviteResendResult,
)
from ..services import invite_services
from ..services.audit_services import AuditContext

router = APIRouter(prefix="/api/v1", tags=["invites"])


def _context(request: Request) -> AuditContext:
    return AuditContext(
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/workspaces/{workspace_id}/invites",
    response_model=InviteCreateResult,
    status_code=201,
)
@limiter.limit(INVITE_CREATE_LIMIT)
def create_invite(
    workspace_id: uuid.UUID,
    data: InviteCreate,
    request: Request,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> InviteCreateResult:
    return invite_services.create_invite(
        db,
        user,
        workspace_id,
        data,
        context=_context(request),
    )


@router.get("/workspaces/{workspace_id}/invites", response_model=list[InviteOut])
def list_invites(
    workspace_id: uuid.UUID,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> list[InviteOut]:
    return invite_services.list_invites(db, user, workspace_id)


@router.patch(
    "/workspaces/{workspace_id}/invites/{invite_id}",
    response_model=InviteOut,
)
def update_invite(
    workspace_id: uuid.UUID,
    invite_id: uuid.UUID,
    data: InvitePatch,
    request: Request,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> InviteOut:
    return invite_services.update_invite(
        db,
        user,
        workspace_id,
        invite_id,
        data,
        context=_context(request),
    )


@router.post(
    "/workspaces/{workspace_id}/invites/{invite_id}/resend",
    response_model=InviteResendResult,
)
@limiter.limit(INVITE_RESEND_LIMIT)
def resend_invite(
    workspace_id: uuid.UUID,
    invite_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> InviteResendResult:
    return invite_services.resend_invite(
        db,
        user,
        workspace_id,
        invite_id,
        context=_context(request),
    )


@router.delete("/workspaces/{workspace_id}/invites/{invite_id}", status_code=204)
def revoke_invite(
    workspace_id: uuid.UUID,
    invite_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> None:
    invite_services.revoke_invite(
        db,
        user,
        workspace_id,
        invite_id,
        context=_context(request),
    )


@router.get("/invites/{token}", response_model=InvitePreview)
def preview_invite(
    token: str,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> InvitePreview:
    return invite_services.preview_invite(db, user, token)


@router.post("/invites/{token}/accept", response_model=InviteAcceptResult)
def accept_invite(
    token: str,
    request: Request,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> InviteAcceptResult:
    return invite_services.accept_invite(
        db,
        user,
        token,
        context=_context(request),
    )
