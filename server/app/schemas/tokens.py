from pydantic import BaseModel, Field

from ..models import ServiceTokenAccess


class ServiceTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    access: ServiceTokenAccess = ServiceTokenAccess.read
    expiresAt: int | None = None


class ServiceTokenOut(BaseModel):
    id: str
    projectId: str
    environmentId: str
    name: str
    access: ServiceTokenAccess
    expiresAt: int | None = None
    lastUsedAt: int | None = None
    revokedAt: int | None = None
    createdAt: int


class ServiceTokenCreateResult(ServiceTokenOut):
    token: str


class ServiceTokenScope(BaseModel):
    tokenId: str
    name: str
    access: ServiceTokenAccess
    workspaceId: str
    workspaceSlug: str
    workspaceName: str
    projectId: str
    projectSlug: str
    projectName: str
    environmentId: str
    environmentSlug: str
    environmentName: str
