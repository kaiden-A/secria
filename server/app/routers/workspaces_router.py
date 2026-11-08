import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..dependencies import require_user
from ..models import User
from ..schemas.workspaces import (
    WorkspaceCreate,
    WorkspaceMemberOut,
    WorkspaceMemberPatch,
    WorkspaceOut,
    WorkspacePatch,
)
from ..services import workspace_services

router = APIRouter(prefix="/api/v1", tags=["workspaces"])


@router.get("/workspaces", response_model=list[WorkspaceOut])
def list_workspaces(
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> list[WorkspaceOut]:
    return workspace_services.list_workspaces(db, user)


@router.post("/workspaces", response_model=WorkspaceOut, status_code=201)
def create_workspace(
    data: WorkspaceCreate,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> WorkspaceOut:
    return workspace_services.create_workspace(db, user, data)


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(
    workspace_id: uuid.UUID,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> WorkspaceOut:
    return workspace_services.get_workspace(db, user, workspace_id)


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceOut)
def update_workspace(
    workspace_id: uuid.UUID,
    patch: WorkspacePatch,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> WorkspaceOut:
    return workspace_services.update_workspace(db, user, workspace_id, patch)


@router.get("/workspaces/{workspace_id}/members", response_model=list[WorkspaceMemberOut])
def list_members(
    workspace_id: uuid.UUID,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> list[WorkspaceMemberOut]:
    return workspace_services.list_members(db, user, workspace_id)


@router.patch(
    "/workspaces/{workspace_id}/members/{member_id}",
    response_model=WorkspaceMemberOut,
)
def update_member_role(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    patch: WorkspaceMemberPatch,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> WorkspaceMemberOut:
    return workspace_services.update_member_role(db, user, workspace_id, member_id, patch)


@router.delete("/workspaces/{workspace_id}/members/{member_id}", status_code=204)
def remove_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> None:
    workspace_services.remove_member(db, user, workspace_id, member_id)
