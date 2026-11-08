import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..dependencies import require_user
from ..models import User
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
from ..services import project_services

router = APIRouter(prefix="/api/v1", tags=["projects"])


@router.get("/workspaces/{workspace_id}/projects", response_model=list[ProjectOut])
def list_projects(
    workspace_id: uuid.UUID,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> list[ProjectOut]:
    return project_services.list_projects(db, user, workspace_id)


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectDetail,
    status_code=201,
)
def create_project(
    workspace_id: uuid.UUID,
    data: ProjectCreate,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> ProjectDetail:
    return project_services.create_project(db, user, workspace_id, data)


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: uuid.UUID,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> ProjectDetail:
    return project_services.get_project(db, user, project_id)


@router.patch("/projects/{project_id}", response_model=ProjectDetail)
def update_project(
    project_id: uuid.UUID,
    patch: ProjectPatch,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> ProjectDetail:
    return project_services.update_project(db, user, project_id, patch)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: uuid.UUID,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> None:
    project_services.delete_project(db, user, project_id)


@router.get(
    "/projects/{project_id}/environments",
    response_model=list[EnvironmentOut],
)
def list_environments(
    project_id: uuid.UUID,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> list[EnvironmentOut]:
    return project_services.list_environments(db, user, project_id)


@router.post(
    "/projects/{project_id}/environments",
    response_model=EnvironmentOut,
    status_code=201,
)
def create_environment(
    project_id: uuid.UUID,
    data: EnvironmentCreate,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> EnvironmentOut:
    return project_services.create_environment(db, user, project_id, data)


@router.get(
    "/projects/{project_id}/members",
    response_model=list[ProjectMemberOut],
)
def list_project_members(
    project_id: uuid.UUID,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> list[ProjectMemberOut]:
    return project_services.list_project_members(db, user, project_id)


@router.put(
    "/projects/{project_id}/members/{member_id}",
    response_model=ProjectMemberOut,
)
def put_project_member(
    project_id: uuid.UUID,
    member_id: uuid.UUID,
    data: ProjectMemberPut,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> ProjectMemberOut:
    return project_services.put_project_member(db, user, project_id, member_id, data)


@router.delete("/projects/{project_id}/members/{member_id}", status_code=204)
def remove_project_member(
    project_id: uuid.UUID,
    member_id: uuid.UUID,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> None:
    project_services.remove_project_member(db, user, project_id, member_id)
