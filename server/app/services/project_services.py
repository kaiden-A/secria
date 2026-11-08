import uuid
from collections import defaultdict
from datetime import datetime
from typing import Literal

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from ..models import (
    Environment,
    Project,
    ProjectKey,
    ProjectMember,
    ProjectMemberEnv,
    ProjectRole,
    User,
    WorkspaceMember,
    WorkspaceRole,
    utcnow,
)
from ..schemas.projects import (
    EnvironmentCreate,
    EnvironmentOut,
    ProjectCreate,
    ProjectDetail,
    ProjectMemberOut,
    ProjectMemberPut,
    ProjectOut,
    ProjectPatch,
)
from ..utils import to_ms
from . import audit_services
from .encryption import get_master_key, new_dek
from .errors import ConflictError, InvalidError, NotFoundError, UnavailableError
from .permissions import (
    ProjectAccess,
    require_project_access,
    require_workspace_admin,
    require_workspace_member,
)
from .slugs import normalize_slug

DEFAULT_ENVIRONMENTS = (
    ("Development", "dev", 0),
    ("Staging", "staging", 1),
    ("Production", "prod", 2),
)


def _clean_name(value: str) -> str:
    clean = value.strip()
    if not clean:
        raise InvalidError("A name is required.")
    return clean


def _project_out(
    project: Project,
    *,
    role: ProjectRole,
    environment_count: int,
    member_count: int,
) -> ProjectOut:
    return ProjectOut(
        id=str(project.id),
        workspaceId=str(project.workspace_id),
        name=project.name,
        slug=project.slug,
        description=project.description,
        role=role,
        archivedAt=to_ms(project.archived_at),
        environmentCount=environment_count,
        memberCount=member_count,
        createdAt=int(to_ms(project.created_at) or 0),
        updatedAt=int(to_ms(project.updated_at) or 0),
    )


def _env_out(environment: Environment) -> EnvironmentOut:
    return EnvironmentOut(
        id=str(environment.id),
        name=environment.name,
        slug=environment.slug,
        position=environment.position,
        createdAt=int(to_ms(environment.created_at) or 0),
    )


def _member_count(db: DbSession, project_id: uuid.UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(ProjectMember)
        .where(ProjectMember.project_id == project_id)
    )
    return count or 0


def _project_detail(db: DbSession, access: ProjectAccess) -> ProjectDetail:
    query = (
        select(Environment)
        .where(Environment.project_id == access.project.id)
        .order_by(Environment.position, Environment.name)
    )
    if access.allowed_environment_ids is not None:
        query = query.where(Environment.id.in_(access.allowed_environment_ids))
    environments = db.scalars(query).all()
    base = _project_out(
        access.project,
        role=access.project_role,
        environment_count=len(environments),
        member_count=_member_count(db, access.project.id),
    )
    return ProjectDetail(
        **base.model_dump(),
        environments=[_env_out(environment) for environment in environments],
    )


def list_projects(db: DbSession, user: User, workspace_id: uuid.UUID) -> list[ProjectOut]:
    member = require_workspace_member(db, user, workspace_id)
    environment_count = (
        select(func.count(Environment.id))
        .where(Environment.project_id == Project.id)
        .correlate(Project)
        .scalar_subquery()
    )
    member_count = (
        select(func.count(ProjectMember.user_id))
        .where(ProjectMember.project_id == Project.id)
        .correlate(Project)
        .scalar_subquery()
    )
    if member.role in {WorkspaceRole.owner, WorkspaceRole.admin}:
        rows = db.execute(
            select(Project, environment_count, member_count)
            .where(Project.workspace_id == workspace_id, Project.archived_at.is_(None))
            .order_by(Project.name)
        ).all()
        return [
            _project_out(
                project,
                role=ProjectRole.admin,
                environment_count=environments or 0,
                member_count=members or 0,
            )
            for project, environments, members in rows
        ]

    restricted_environment_count = (
        select(func.count(ProjectMemberEnv.environment_id))
        .where(
            ProjectMemberEnv.project_id == Project.id,
            ProjectMemberEnv.user_id == user.id,
        )
        .correlate(Project)
        .scalar_subquery()
    )
    rows = db.execute(
        select(
            Project,
            ProjectMember.role,
            environment_count,
            restricted_environment_count,
            member_count,
        )
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(
            Project.workspace_id == workspace_id,
            ProjectMember.user_id == user.id,
            Project.archived_at.is_(None),
        )
        .order_by(Project.name)
    ).all()
    return [
        _project_out(
            project,
            role=role,
            environment_count=restricted or environments or 0,
            member_count=members or 0,
        )
        for project, role, environments, restricted, members in rows
    ]


def get_project(db: DbSession, user: User, project_id: uuid.UUID) -> ProjectDetail:
    access = require_project_access(db, user, project_id)
    return _project_detail(db, access)


def create_project(
    db: DbSession,
    user: User,
    workspace_id: uuid.UUID,
    data: ProjectCreate,
) -> ProjectDetail:
    require_workspace_admin(db, user, workspace_id)
    slug = normalize_slug(data.slug, fallback=data.name)
    if (
        db.scalar(
            select(Project).where(
                Project.workspace_id == workspace_id,
                Project.slug == slug,
            )
        )
        is not None
    ):
        raise ConflictError("That project slug is already in use.")

    project = Project(
        workspace_id=workspace_id,
        name=_clean_name(data.name),
        slug=slug,
        description=(data.description or "").strip()[:1000],
    )
    db.add(project)
    db.flush()

    for name, env_slug, position in DEFAULT_ENVIRONMENTS:
        db.add(
            Environment(
                project_id=project.id,
                name=name,
                slug=env_slug,
                position=position,
            )
        )

    try:
        master = get_master_key()
        wrapped = master.wrap_dek(new_dek(), project_id=project.id, key_version=1)
    except (RuntimeError, ValueError) as exc:
        db.rollback()
        raise UnavailableError("Encryption is not configured.") from exc

    db.add(
        ProjectKey(
            project_id=project.id,
            key_version=1,
            encrypted_dek=wrapped,
            kek_version=master.version,
        )
    )
    audit_services.record(
        db,
        workspace_id=workspace_id,
        project_id=project.id,
        actor=user,
        action="project.created",
        target=f"project:{project.slug}",
        metadata={"environments": [env_slug for _name, env_slug, _pos in DEFAULT_ENVIRONMENTS]},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("That project slug is already in use.") from exc

    access = require_project_access(db, user, project.id)
    return _project_detail(db, access)


def update_project(
    db: DbSession,
    user: User,
    project_id: uuid.UUID,
    patch: ProjectPatch,
) -> ProjectDetail:
    access = require_project_access(db, user, project_id, roles={ProjectRole.admin})
    project = access.project

    if patch.name is not None:
        project.name = _clean_name(patch.name)
    if patch.slug is not None:
        slug = normalize_slug(patch.slug)
        if slug != project.slug:
            conflict = db.scalar(
                select(Project).where(
                    Project.workspace_id == project.workspace_id,
                    Project.slug == slug,
                    Project.id != project.id,
                )
            )
            if conflict is not None:
                raise ConflictError("That project slug is already in use.")
            project.slug = slug
    if patch.description is not None:
        project.description = patch.description.strip()[:1000]
    if patch.archived is not None:
        project.archived_at = utcnow() if patch.archived else None

    fields = [
        field
        for field in ("name", "slug", "description", "archived")
        if getattr(patch, field) is not None
    ]
    if patch.archived is True:
        action = "project.archived"
    elif patch.archived is False:
        action = "project.restored"
    else:
        action = "project.updated"
    audit_services.record(
        db,
        workspace_id=access.workspace.id,
        project_id=project.id,
        actor=user,
        action=action,
        target=f"project:{project.slug}",
        metadata={"fields": fields},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("That project slug is already in use.") from exc
    return _project_detail(db, access)


def delete_project(db: DbSession, user: User, project_id: uuid.UUID) -> None:
    access = require_project_access(db, user, project_id, roles={ProjectRole.admin})
    audit_services.record(
        db,
        workspace_id=access.workspace.id,
        project_id=access.project.id,
        actor=user,
        action="project.deleted",
        target=f"project:{access.project.slug}",
        metadata={},
    )
    db.flush()
    db.delete(access.project)
    db.commit()


def list_environments(
    db: DbSession, user: User, project_id: uuid.UUID
) -> list[EnvironmentOut]:
    access = require_project_access(db, user, project_id)
    query = (
        select(Environment)
        .where(Environment.project_id == project_id)
        .order_by(Environment.position, Environment.name)
    )
    if access.allowed_environment_ids is not None:
        query = query.where(Environment.id.in_(access.allowed_environment_ids))
    return [_env_out(environment) for environment in db.scalars(query).all()]


def create_environment(
    db: DbSession,
    user: User,
    project_id: uuid.UUID,
    data: EnvironmentCreate,
) -> EnvironmentOut:
    access = require_project_access(db, user, project_id, roles={ProjectRole.admin})
    slug = normalize_slug(data.slug, fallback=data.name)
    if (
        db.scalar(
            select(Environment).where(
                Environment.project_id == project_id,
                Environment.slug == slug,
            )
        )
        is not None
    ):
        raise ConflictError("That environment slug is already in use.")

    max_position = db.scalar(
        select(func.max(Environment.position)).where(Environment.project_id == project_id)
    )
    next_position = 0 if max_position is None else max_position + 1
    position = data.position if data.position is not None else next_position
    environment = Environment(
        id=uuid.uuid4(),
        project_id=project_id,
        name=_clean_name(data.name),
        slug=slug,
        position=position,
    )
    db.add(environment)
    db.flush()
    audit_services.record(
        db,
        workspace_id=access.workspace.id,
        project_id=project_id,
        environment_id=environment.id,
        actor=user,
        action="environment.created",
        target=f"environment:{environment.slug}",
        metadata={"position": position},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("That environment slug is already in use.") from exc
    return _env_out(environment)


def _environment_ids_by_user(
    db: DbSession, project_id: uuid.UUID
) -> dict[uuid.UUID, list[str]]:
    rows = db.execute(
        select(ProjectMemberEnv.user_id, ProjectMemberEnv.environment_id).where(
            ProjectMemberEnv.project_id == project_id
        )
    ).all()
    result: dict[uuid.UUID, list[str]] = defaultdict(list)
    for user_id, environment_id in rows:
        result[user_id].append(str(environment_id))
    return result


def list_project_members(
    db: DbSession, user: User, project_id: uuid.UUID
) -> list[ProjectMemberOut]:
    access = require_project_access(db, user, project_id)
    environment_ids = _environment_ids_by_user(db, project_id)
    result: dict[uuid.UUID, ProjectMemberOut] = {}

    admin_rows = db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(
            WorkspaceMember.workspace_id == access.workspace.id,
            WorkspaceMember.role.in_([WorkspaceRole.owner, WorkspaceRole.admin]),
        )
    ).all()
    for membership, member_user in admin_rows:
        result[membership.user_id] = ProjectMemberOut(
            userId=str(member_user.id),
            name=member_user.name,
            email=member_user.email,
            role=ProjectRole.admin,
            environmentIds=None,
            joinedAt=int(to_ms(membership.created_at) or 0),
            source="workspace",
        )

    project_rows = db.execute(
        select(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
    ).all()
    for project_member, member_user in project_rows:
        existing = result.get(project_member.user_id)
        if existing is not None and existing.role == ProjectRole.admin:
            continue
        result[project_member.user_id] = ProjectMemberOut(
            userId=str(member_user.id),
            name=member_user.name,
            email=member_user.email,
            role=project_member.role,
            environmentIds=environment_ids.get(project_member.user_id) or None,
            joinedAt=int(to_ms(project_member.created_at) or 0),
            source="project",
        )

    return sorted(result.values(), key=lambda member: (member.name.lower(), member.email.lower()))


def _project_member_out(
    db: DbSession,
    project_id: uuid.UUID,
    member_id: uuid.UUID,
    member_user: User,
    *,
    role: ProjectRole,
    joined_at: datetime,
    source: Literal["workspace", "project"] = "project",
) -> ProjectMemberOut:
    environment_ids = (
        []
        if role == ProjectRole.admin
        else list(
            db.scalars(
                select(ProjectMemberEnv.environment_id).where(
                    ProjectMemberEnv.project_id == project_id,
                    ProjectMemberEnv.user_id == member_id,
                )
            ).all()
        )
    )
    return ProjectMemberOut(
        userId=str(member_user.id),
        name=member_user.name,
        email=member_user.email,
        role=role,
        environmentIds=[str(environment_id) for environment_id in environment_ids] or None,
        joinedAt=int(to_ms(joined_at) or 0),
        source=source,
    )


def put_project_member(
    db: DbSession,
    user: User,
    project_id: uuid.UUID,
    member_id: uuid.UUID,
    data: ProjectMemberPut,
) -> ProjectMemberOut:
    access = require_project_access(db, user, project_id, roles={ProjectRole.admin})
    target_membership = db.get(WorkspaceMember, (access.workspace.id, member_id))
    if target_membership is None:
        raise NotFoundError("Add that person to the workspace first.")
    target_user = db.get(User, member_id)
    if target_user is None:
        raise NotFoundError("Add that person to the workspace first.")

    requested = set(data.environmentIds or [])
    if requested:
        valid = set(
            db.scalars(
                select(Environment.id).where(
                    Environment.project_id == project_id,
                    Environment.id.in_(requested),
                )
            ).all()
        )
        if valid != requested:
            raise InvalidError("One or more environments do not belong to this project.")

    row = db.get(ProjectMember, (project_id, member_id))
    if row is None:
        row = ProjectMember(project_id=project_id, user_id=member_id, role=data.role)
        db.add(row)
    else:
        row.role = data.role

    db.execute(
        delete(ProjectMemberEnv).where(
            ProjectMemberEnv.project_id == project_id,
            ProjectMemberEnv.user_id == member_id,
        )
    )
    for environment_id in requested:
        db.add(
            ProjectMemberEnv(
                project_id=project_id,
                user_id=member_id,
                environment_id=environment_id,
            )
        )

    effective_role = (
        ProjectRole.admin
        if target_membership.role in {WorkspaceRole.owner, WorkspaceRole.admin}
        else data.role
    )
    audit_services.record(
        db,
        workspace_id=access.workspace.id,
        project_id=project_id,
        actor=user,
        action="project.member_granted",
        target=f"user:{target_user.email}",
        metadata={
            "role": effective_role.value,
            "environmentIds": sorted(str(environment_id) for environment_id in requested),
        },
    )
    db.commit()

    return _project_member_out(
        db,
        project_id,
        member_id,
        target_user,
        role=effective_role,
        joined_at=row.created_at,
        source=(
            "workspace"
            if target_membership.role in {WorkspaceRole.owner, WorkspaceRole.admin}
            else "project"
        ),
    )


def remove_project_member(
    db: DbSession,
    user: User,
    project_id: uuid.UUID,
    member_id: uuid.UUID,
) -> None:
    access = require_project_access(db, user, project_id, roles={ProjectRole.admin})
    row = db.get(ProjectMember, (project_id, member_id))
    if row is None:
        raise NotFoundError("Project member not found.")
    target_user = db.get(User, member_id)
    audit_services.record(
        db,
        workspace_id=access.workspace.id,
        project_id=project_id,
        actor=user,
        action="project.member_removed",
        target=f"user:{target_user.email if target_user else member_id}",
        metadata={},
    )
    db.delete(row)
    db.commit()
