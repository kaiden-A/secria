import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..models import (
    Project,
    ProjectMember,
    ProjectMemberEnv,
    ProjectRole,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from .errors import ForbiddenError, NotFoundError


@dataclass(frozen=True)
class ProjectAccess:
    workspace: Workspace
    project: Project
    workspace_role: WorkspaceRole
    project_role: ProjectRole
    # None means every environment in the project is allowed.
    allowed_environment_ids: frozenset[uuid.UUID] | None = None


def require_workspace_member(
    db: DbSession,
    user: User,
    workspace_id: uuid.UUID,
    *,
    roles: set[WorkspaceRole] | None = None,
) -> WorkspaceMember:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise NotFoundError("Workspace not found.")
    member = db.get(WorkspaceMember, (workspace_id, user.id))
    if member is None:
        # Do not reveal that the workspace exists to a non-member.
        raise NotFoundError("Workspace not found.")
    if roles is not None and member.role not in roles:
        raise ForbiddenError("Your workspace role does not allow that action.")
    return member


def require_workspace_admin(
    db: DbSession,
    user: User,
    workspace_id: uuid.UUID,
) -> WorkspaceMember:
    return require_workspace_member(
        db,
        user,
        workspace_id,
        roles={WorkspaceRole.owner, WorkspaceRole.admin},
    )


def require_project_access(
    db: DbSession,
    user: User,
    project_id: uuid.UUID,
    *,
    roles: set[ProjectRole] | None = None,
    environment_id: uuid.UUID | None = None,
) -> ProjectAccess:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found.")

    member = db.get(WorkspaceMember, (project.workspace_id, user.id))
    if member is None:
        raise NotFoundError("Project not found.")

    workspace = db.get(Workspace, project.workspace_id)
    if workspace is None:
        raise NotFoundError("Project not found.")

    if member.role in {WorkspaceRole.owner, WorkspaceRole.admin}:
        effective_role = ProjectRole.admin
        allowed_environment_ids: frozenset[uuid.UUID] | None = None
    else:
        project_member = db.get(ProjectMember, (project_id, user.id))
        if project_member is None:
            raise NotFoundError("Project not found.")
        effective_role = project_member.role
        restricted = frozenset(
            db.scalars(
                select(ProjectMemberEnv.environment_id).where(
                    ProjectMemberEnv.project_id == project_id,
                    ProjectMemberEnv.user_id == user.id,
                )
            ).all()
        )
        allowed_environment_ids = restricted or None

    if (
        environment_id is not None
        and allowed_environment_ids is not None
        and environment_id not in allowed_environment_ids
    ):
        raise NotFoundError("Environment not found.")

    if roles is not None and effective_role not in roles:
        raise ForbiddenError("Your project role does not allow that action.")

    return ProjectAccess(
        workspace=workspace,
        project=project,
        workspace_role=member.role,
        project_role=effective_role,
        allowed_environment_ids=allowed_environment_ids,
    )
