import uuid
from collections import defaultdict

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from ..models import Project, ProjectMember, User, Workspace, WorkspaceMember, WorkspaceRole
from ..schemas.workspaces import (
    ProjectGrantOut,
    WorkspaceCreate,
    WorkspaceMemberOut,
    WorkspaceMemberPatch,
    WorkspaceOut,
    WorkspacePatch,
)
from ..utils import to_ms
from .errors import ConflictError, ForbiddenError, InvalidError, NotFoundError
from .permissions import require_workspace_admin, require_workspace_member
from .slugs import normalize_slug


def _clean_name(value: str) -> str:
    clean = value.strip()
    if not clean:
        raise InvalidError("A name is required.")
    return clean


def _workspace_out(
    db: DbSession,
    workspace: Workspace,
    *,
    role: WorkspaceRole,
) -> WorkspaceOut:
    member_count = db.scalar(
        select(func.count())
        .select_from(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == workspace.id)
    )
    project_count = db.scalar(
        select(func.count())
        .select_from(Project)
        .where(Project.workspace_id == workspace.id, Project.archived_at.is_(None))
    )
    return WorkspaceOut(
        id=str(workspace.id),
        name=workspace.name,
        slug=workspace.slug,
        role=role,
        memberCount=member_count or 0,
        projectCount=project_count or 0,
        createdAt=int(to_ms(workspace.created_at) or 0),
    )


def list_workspaces(db: DbSession, user: User) -> list[WorkspaceOut]:
    member_count = (
        select(func.count(WorkspaceMember.user_id))
        .where(WorkspaceMember.workspace_id == Workspace.id)
        .correlate(Workspace)
        .scalar_subquery()
    )
    project_count = (
        select(func.count(Project.id))
        .where(Project.workspace_id == Workspace.id, Project.archived_at.is_(None))
        .correlate(Workspace)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Workspace, WorkspaceMember.role, member_count, project_count)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.name)
    ).all()
    return [
        WorkspaceOut(
            id=str(workspace.id),
            name=workspace.name,
            slug=workspace.slug,
            role=role,
            memberCount=members or 0,
            projectCount=projects or 0,
            createdAt=int(to_ms(workspace.created_at) or 0),
        )
        for workspace, role, members, projects in rows
    ]


def get_workspace(db: DbSession, user: User, workspace_id: uuid.UUID) -> WorkspaceOut:
    member = require_workspace_member(db, user, workspace_id)
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise NotFoundError("Workspace not found.")
    return _workspace_out(db, workspace, role=member.role)


def create_workspace(db: DbSession, user: User, data: WorkspaceCreate) -> WorkspaceOut:
    slug = normalize_slug(data.slug, fallback=data.name)
    if db.scalar(select(Workspace).where(Workspace.slug == slug)) is not None:
        raise ConflictError("That workspace slug is already in use.")
    workspace = Workspace(name=_clean_name(data.name), slug=slug, created_by=user.id)
    db.add(workspace)
    db.flush()
    db.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=WorkspaceRole.owner,
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("That workspace slug is already in use.") from exc
    return _workspace_out(db, workspace, role=WorkspaceRole.owner)


def update_workspace(
    db: DbSession,
    user: User,
    workspace_id: uuid.UUID,
    patch: WorkspacePatch,
) -> WorkspaceOut:
    member = require_workspace_admin(db, user, workspace_id)
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise NotFoundError("Workspace not found.")

    if patch.name is not None:
        workspace.name = _clean_name(patch.name)
    if patch.slug is not None:
        slug = normalize_slug(patch.slug)
        if slug != workspace.slug:
            conflict = db.scalar(
                select(Workspace).where(Workspace.slug == slug, Workspace.id != workspace.id)
            )
            if conflict is not None:
                raise ConflictError("That workspace slug is already in use.")
            workspace.slug = slug
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("That workspace slug is already in use.") from exc
    return _workspace_out(db, workspace, role=member.role)


def _grants_by_user(
    db: DbSession, workspace_id: uuid.UUID
) -> dict[uuid.UUID, list[ProjectGrantOut]]:
    rows = db.execute(
        select(ProjectMember.user_id, Project.id, Project.name, ProjectMember.role)
        .join(Project, Project.id == ProjectMember.project_id)
        .where(Project.workspace_id == workspace_id, Project.archived_at.is_(None))
    ).all()
    grants: dict[uuid.UUID, list[ProjectGrantOut]] = defaultdict(list)
    for user_id, project_id, project_name, role in rows:
        grants[user_id].append(
            ProjectGrantOut(projectId=str(project_id), projectName=project_name, role=role)
        )
    return grants


def _member_out(
    db: DbSession,
    workspace_id: uuid.UUID,
    member: WorkspaceMember,
    member_user: User,
    *,
    grants: dict[uuid.UUID, list[ProjectGrantOut]] | None = None,
) -> WorkspaceMemberOut:
    if grants is None:
        grants = _grants_by_user(db, workspace_id)
    return WorkspaceMemberOut(
        userId=str(member.user_id),
        name=member_user.name,
        email=member_user.email,
        role=member.role,
        joinedAt=int(to_ms(member.created_at) or 0),
        projectGrants=grants.get(member.user_id, []),
    )


def list_members(db: DbSession, user: User, workspace_id: uuid.UUID) -> list[WorkspaceMemberOut]:
    require_workspace_member(db, user, workspace_id)
    grants = _grants_by_user(db, workspace_id)
    rows = db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(User.name, User.email)
    ).all()
    return [
        _member_out(db, workspace_id, member, member_user, grants=grants)
        for member, member_user in rows
    ]


def _owner_count(db: DbSession, workspace_id: uuid.UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(WorkspaceMember)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role == WorkspaceRole.owner,
        )
    )
    return count or 0


def _target_member(
    db: DbSession, workspace_id: uuid.UUID, member_id: uuid.UUID
) -> WorkspaceMember:
    target = db.get(WorkspaceMember, (workspace_id, member_id))
    if target is None:
        raise NotFoundError("Workspace member not found.")
    return target


def update_member_role(
    db: DbSession,
    actor: User,
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    patch: WorkspaceMemberPatch,
) -> WorkspaceMemberOut:
    actor_member = require_workspace_admin(db, actor, workspace_id)
    target = _target_member(db, workspace_id, member_id)

    if (
        target.role == WorkspaceRole.owner or patch.role == WorkspaceRole.owner
    ) and actor_member.role != WorkspaceRole.owner:
        raise ForbiddenError("Only a workspace owner can manage owners.")
    if (
        target.role == WorkspaceRole.owner
        and patch.role != WorkspaceRole.owner
        and _owner_count(db, workspace_id) <= 1
    ):
        raise ConflictError("A workspace must keep at least one owner.")

    target.role = patch.role
    db.commit()
    target_user = db.get(User, member_id)
    if target_user is None:
        raise NotFoundError("Workspace member not found.")
    return _member_out(db, workspace_id, target, target_user)


def remove_member(
    db: DbSession,
    actor: User,
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
) -> None:
    actor_member = require_workspace_admin(db, actor, workspace_id)
    target = _target_member(db, workspace_id, member_id)

    if target.role == WorkspaceRole.owner:
        if actor_member.role != WorkspaceRole.owner:
            raise ForbiddenError("Only a workspace owner can remove an owner.")
        if _owner_count(db, workspace_id) <= 1:
            raise ConflictError("A workspace must keep at least one owner.")

    project_ids = select(Project.id).where(Project.workspace_id == workspace_id)
    db.execute(
        delete(ProjectMember).where(
            ProjectMember.project_id.in_(project_ids),
            ProjectMember.user_id == member_id,
        )
    )
    db.delete(target)
    db.commit()
