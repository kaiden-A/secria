import secrets
import uuid
from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DbSession

from ..config import get_settings
from ..models import (
    Invite,
    InviteGrant,
    Project,
    ProjectMember,
    ProjectRole,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
    utcnow,
)
from ..schemas.invites import (
    InviteAcceptResult,
    InviteCreate,
    InviteCreateResult,
    InviteGrantIn,
    InviteGrantOut,
    InviteOut,
    InvitePatch,
    InvitePreview,
    InviteResendResult,
)
from ..utils import to_ms
from . import audit_services, email_services, security
from .audit_services import AuditContext
from .errors import ConflictError, ForbiddenError, InvalidError, NotFoundError
from .permissions import require_workspace_admin

INVITE_TTL = timedelta(days=7)

WORKSPACE_RANK = {
    WorkspaceRole.member: 1,
    WorkspaceRole.admin: 2,
    WorkspaceRole.owner: 3,
}
PROJECT_RANK = {
    ProjectRole.viewer: 1,
    ProjectRole.editor: 2,
    ProjectRole.admin: 3,
}


def _clean_email(email: str) -> str:
    clean = email.strip().lower()
    if not clean or len(clean) > 320:
        raise InvalidError("Enter a valid email address.")
    return clean


def _status(
    invite: Invite, now: datetime
) -> Literal["pending", "accepted", "revoked", "expired"]:
    if invite.accepted_at is not None:
        return "accepted"
    if invite.revoked_at is not None:
        return "revoked"
    if invite.expires_at <= now:
        return "expired"
    return "pending"


def _max_workspace_role(current: WorkspaceRole, invited: WorkspaceRole) -> WorkspaceRole:
    return current if WORKSPACE_RANK[current] >= WORKSPACE_RANK[invited] else invited


def _max_project_role(current: ProjectRole, invited: ProjectRole) -> ProjectRole:
    return current if PROJECT_RANK[current] >= PROJECT_RANK[invited] else invited


def _get_invite(db: DbSession, workspace_id: uuid.UUID, invite_id: uuid.UUID) -> Invite:
    invite = db.get(Invite, invite_id)
    if invite is None or invite.workspace_id != workspace_id:
        raise NotFoundError("Invite not found.")
    return invite


def _find_by_token(db: DbSession, token: str) -> Invite:
    clean = (token or "").strip()
    if not clean:
        raise NotFoundError("Invite not found or already used.")
    invite = db.scalar(select(Invite).where(Invite.token_hash == security.hash_token(clean)))
    if invite is None:
        raise NotFoundError("Invite not found or already used.")
    return invite


def _validate_usable(invite: Invite) -> None:
    if invite.accepted_at is not None:
        raise InvalidError("This invite has already been accepted.")
    if invite.revoked_at is not None:
        raise InvalidError("This invite has been revoked.")
    if invite.expires_at <= utcnow():
        raise InvalidError("This invite has expired.")


def _validate_grants(
    db: DbSession,
    workspace_id: uuid.UUID,
    grants: list[InviteGrantIn],
) -> list[tuple[Project, ProjectRole]]:
    seen: set[uuid.UUID] = set()
    result: list[tuple[Project, ProjectRole]] = []
    for grant in grants:
        if grant.projectId in seen:
            raise InvalidError("Each project can only be granted once.")
        seen.add(grant.projectId)
        project = db.get(Project, grant.projectId)
        if (
            project is None
            or project.workspace_id != workspace_id
            or project.archived_at is not None
        ):
            raise NotFoundError("Project not found.")
        result.append((project, grant.role))
    return result


def _grant_map(
    db: DbSession, invite_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[InviteGrantOut]]:
    if not invite_ids:
        return {}
    rows = db.execute(
        select(InviteGrant.invite_id, Project.id, Project.name, InviteGrant.role)
        .join(Project, Project.id == InviteGrant.project_id)
        .where(InviteGrant.invite_id.in_(invite_ids))
    ).all()
    result: dict[uuid.UUID, list[InviteGrantOut]] = {}
    for invite_id, project_id, project_name, role in rows:
        result.setdefault(invite_id, []).append(
            InviteGrantOut(projectId=str(project_id), projectName=project_name, role=role)
        )
    return result


def _inviter_names(db: DbSession, inviter_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not inviter_ids:
        return {}
    users = db.scalars(select(User).where(User.id.in_(inviter_ids))).all()
    return {user.id: user.name for user in users}


def _invite_out(
    db: DbSession,
    invite: Invite,
    *,
    grants: list[InviteGrantOut] | None = None,
    inviter_names: dict[uuid.UUID, str] | None = None,
) -> InviteOut:
    if grants is None:
        grants = _grant_map(db, [invite.id]).get(invite.id, [])
    if inviter_names is None:
        inviter_names = _inviter_names(
            db, {invite.invited_by} if invite.invited_by else set()
        )
    return InviteOut(
        id=str(invite.id),
        email=invite.email,
        role=invite.role,
        grants=grants,
        invitedByName=inviter_names.get(invite.invited_by) if invite.invited_by else None,
        status=_status(invite, utcnow()),
        expiresAt=int(to_ms(invite.expires_at) or 0),
        acceptedAt=to_ms(invite.accepted_at),
        revokedAt=to_ms(invite.revoked_at),
        createdAt=int(to_ms(invite.created_at) or 0),
    )


def _email_grants(db: DbSession, invite_id: uuid.UUID) -> list[dict[str, str]]:
    rows = db.execute(
        select(Project.name, InviteGrant.role)
        .join(Project, Project.id == InviteGrant.project_id)
        .where(InviteGrant.invite_id == invite_id)
    ).all()
    return [{"project_name": name, "role": role.value} for name, role in rows]


def _invite_url(token: str) -> str:
    return f"{get_settings().app_url.rstrip('/')}/invite/{token}"


def _send_email(db: DbSession, invite: Invite, inviter: User, invite_url: str) -> bool:
    workspace = db.get(Workspace, invite.workspace_id)
    if workspace is None:
        return False
    return email_services.send_invite(
        invite=invite,
        workspace=workspace,
        inviter=inviter,
        grants=_email_grants(db, invite.id),
        invite_url=invite_url,
    )


def create_invite(
    db: DbSession,
    actor: User,
    workspace_id: uuid.UUID,
    data: InviteCreate,
    *,
    context: AuditContext | None = None,
) -> InviteCreateResult:
    actor_member = require_workspace_admin(db, actor, workspace_id)
    if data.role == WorkspaceRole.owner and actor_member.role != WorkspaceRole.owner:
        raise ForbiddenError("Only a workspace owner can invite another owner.")

    email = _clean_email(str(data.email))
    existing_user = db.scalar(select(User).where(func.lower(User.email) == email))
    if existing_user is not None and db.get(
        WorkspaceMember, (workspace_id, existing_user.id)
    ) is not None:
        raise ConflictError("That person is already a workspace member.")

    now = utcnow()
    pending = db.scalar(
        select(Invite).where(
            Invite.workspace_id == workspace_id,
            func.lower(Invite.email) == email,
            Invite.accepted_at.is_(None),
            Invite.revoked_at.is_(None),
            Invite.expires_at > now,
        )
    )
    if pending is not None:
        raise ConflictError("An invite is already pending for that email.")

    projects = _validate_grants(db, workspace_id, data.grants)
    token = secrets.token_urlsafe(32)
    invite = Invite(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        email=email,
        role=data.role,
        token_hash=security.hash_token(token),
        invited_by=actor.id,
        expires_at=now + INVITE_TTL,
        created_at=now,
    )
    db.add(invite)
    for project, role in projects:
        db.add(InviteGrant(invite_id=invite.id, project_id=project.id, role=role))
    audit_services.record(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="invite.created",
        target=f"invite:{email}",
        metadata={
            "role": data.role.value,
            "projectIds": [str(project.id) for project, _role in projects],
        },
        context=context,
    )
    db.commit()

    invite_url = _invite_url(token)
    email_sent = _send_email(db, invite, actor, invite_url)
    out = _invite_out(db, invite)
    return InviteCreateResult(
        **out.model_dump(),
        inviteUrl=invite_url,
        emailSent=email_sent,
    )


def list_invites(
    db: DbSession, actor: User, workspace_id: uuid.UUID
) -> list[InviteOut]:
    require_workspace_admin(db, actor, workspace_id)
    invites = list(
        db.scalars(
            select(Invite)
            .where(Invite.workspace_id == workspace_id)
            .order_by(Invite.created_at.desc())
        ).all()
    )
    grants = _grant_map(db, [invite.id for invite in invites])
    inviters = _inviter_names(
        db,
        {invite.invited_by for invite in invites if invite.invited_by is not None},
    )
    return [
        _invite_out(
            db,
            invite,
            grants=grants.get(invite.id, []),
            inviter_names=inviters,
        )
        for invite in invites
    ]


def update_invite(
    db: DbSession,
    actor: User,
    workspace_id: uuid.UUID,
    invite_id: uuid.UUID,
    patch: InvitePatch,
    *,
    context: AuditContext | None = None,
) -> InviteOut:
    actor_member = require_workspace_admin(db, actor, workspace_id)
    invite = _get_invite(db, workspace_id, invite_id)
    if invite.accepted_at is not None or invite.revoked_at is not None:
        raise InvalidError("Only pending or expired invites can be changed.")
    if patch.role == WorkspaceRole.owner and actor_member.role != WorkspaceRole.owner:
        raise ForbiddenError("Only a workspace owner can grant owner access.")

    if patch.role is not None:
        invite.role = patch.role
    if patch.grants is not None:
        projects = _validate_grants(db, workspace_id, patch.grants)
        db.execute(delete(InviteGrant).where(InviteGrant.invite_id == invite.id))
        for project, role in projects:
            db.add(InviteGrant(invite_id=invite.id, project_id=project.id, role=role))
        project_ids = [str(project.id) for project, _role in projects]
    else:
        project_ids = [
            str(project_id)
            for project_id in db.scalars(
                select(InviteGrant.project_id).where(InviteGrant.invite_id == invite.id)
            ).all()
        ]
    audit_services.record(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="invite.updated",
        target=f"invite:{invite.email}",
        metadata={
            "role": invite.role.value,
            "projectIds": project_ids,
        },
        context=context,
    )
    db.commit()
    return _invite_out(db, invite)


def resend_invite(
    db: DbSession,
    actor: User,
    workspace_id: uuid.UUID,
    invite_id: uuid.UUID,
    *,
    context: AuditContext | None = None,
) -> InviteResendResult:
    require_workspace_admin(db, actor, workspace_id)
    invite = _get_invite(db, workspace_id, invite_id)
    if invite.accepted_at is not None or invite.revoked_at is not None:
        raise InvalidError("Only pending or expired invites can be resent.")
    token = secrets.token_urlsafe(32)
    invite.token_hash = security.hash_token(token)
    invite.expires_at = utcnow() + INVITE_TTL
    audit_services.record(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="invite.resent",
        target=f"invite:{invite.email}",
        metadata={},
        context=context,
    )
    db.commit()
    inviter = db.get(User, invite.invited_by) if invite.invited_by else None
    invite_url = _invite_url(token)
    email_sent = _send_email(db, invite, inviter or actor, invite_url)
    return InviteResendResult(
        inviteUrl=invite_url,
        emailSent=email_sent,
        expiresAt=int(to_ms(invite.expires_at) or 0),
    )


def revoke_invite(
    db: DbSession,
    actor: User,
    workspace_id: uuid.UUID,
    invite_id: uuid.UUID,
    *,
    context: AuditContext | None = None,
) -> None:
    require_workspace_admin(db, actor, workspace_id)
    invite = _get_invite(db, workspace_id, invite_id)
    if invite.accepted_at is not None:
        raise InvalidError("Accepted invites cannot be revoked.")
    if invite.revoked_at is not None:
        return
    invite.revoked_at = utcnow()
    audit_services.record(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="invite.revoked",
        target=f"invite:{invite.email}",
        metadata={},
        context=context,
    )
    db.commit()


def preview_invite(db: DbSession, user: User, token: str) -> InvitePreview:
    invite = _find_by_token(db, token)
    _validate_usable(invite)
    if invite.email.lower() != user.email.lower():
        raise ForbiddenError("This invite was sent to a different email address.")
    workspace = db.get(Workspace, invite.workspace_id)
    if workspace is None:
        raise NotFoundError("Invite not found or already used.")
    inviter = db.get(User, invite.invited_by) if invite.invited_by else None
    return InvitePreview(
        workspaceName=workspace.name,
        workspaceSlug=workspace.slug,
        inviterName=inviter.name if inviter else None,
        email=invite.email,
        role=invite.role,
        grants=_grant_map(db, [invite.id]).get(invite.id, []),
        expiresAt=int(to_ms(invite.expires_at) or 0),
    )


def accept_invite(
    db: DbSession,
    user: User,
    token: str,
    *,
    context: AuditContext | None = None,
) -> InviteAcceptResult:
    invite = _find_by_token(db, token)
    _validate_usable(invite)
    if invite.email.lower() != user.email.lower():
        raise ForbiddenError("This invite was sent to a different email address.")
    workspace = db.get(Workspace, invite.workspace_id)
    if workspace is None:
        raise NotFoundError("Invite not found or already used.")

    membership = db.get(WorkspaceMember, (workspace.id, user.id))
    if membership is None:
        db.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role=invite.role,
            )
        )
    else:
        membership.role = _max_workspace_role(membership.role, invite.role)

    grants = db.scalars(
        select(InviteGrant).where(InviteGrant.invite_id == invite.id)
    ).all()
    for grant in grants:
        existing = db.get(ProjectMember, (grant.project_id, user.id))
        if existing is None:
            db.add(
                ProjectMember(
                    project_id=grant.project_id,
                    user_id=user.id,
                    role=grant.role,
                )
            )
        else:
            existing.role = _max_project_role(existing.role, grant.role)

    invite.accepted_at = utcnow()
    audit_services.record(
        db,
        workspace_id=workspace.id,
        actor=user,
        action="invite.accepted",
        target=f"invite:{invite.email}",
        metadata={
            "role": invite.role.value,
            "projectIds": [str(grant.project_id) for grant in grants],
        },
        context=context,
    )
    db.commit()
    return InviteAcceptResult(
        workspaceId=str(workspace.id),
        workspaceName=workspace.name,
        workspaceSlug=workspace.slug,
    )
