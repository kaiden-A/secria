from typing import Any

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    workspaceId: str
    projectId: str | None = None
    environmentId: str | None = None
    actorType: str
    actorId: str | None = None
    actorName: str | None = None
    actorEmail: str | None = None
    action: str
    target: str
    metadata: dict[str, Any]
    ip: str | None = None
    userAgent: str | None = None
    createdAt: int


class AuditLogPage(BaseModel):
    items: list[AuditLogOut]
    nextCursor: str | None = None
