import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..dependencies import require_user
from ..models import User
from ..schemas.audit import AuditLogPage
from ..services import audit_services

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/workspaces/{workspace_id}/audit-logs", response_model=AuditLogPage)
def list_audit_logs(
    workspace_id: uuid.UUID,
    response: Response,
    project: uuid.UUID | None = Query(default=None),
    actor: str | None = Query(default=None, max_length=320),
    action: str | None = Query(default=None, max_length=64),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(require_user),
    db: DbSession = Depends(get_db),
) -> AuditLogPage:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return audit_services.list_audit_logs(
        db,
        user,
        workspace_id,
        project_id=project,
        actor=actor,
        action=action,
        cursor=cursor,
        limit=limit,
    )
