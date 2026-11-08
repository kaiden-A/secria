from pydantic import BaseModel, Field

from ..models import ProjectRole, WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=64)


class WorkspacePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=64)


class WorkspaceOut(BaseModel):
    id: str
    name: str
    slug: str
    role: WorkspaceRole
    memberCount: int
    projectCount: int
    createdAt: int


class ProjectGrantOut(BaseModel):
    projectId: str
    projectName: str
    role: ProjectRole


class WorkspaceMemberOut(BaseModel):
    userId: str
    name: str
    email: str
    role: WorkspaceRole
    joinedAt: int
    projectGrants: list[ProjectGrantOut] = Field(default_factory=list)


class WorkspaceMemberPatch(BaseModel):
    role: WorkspaceRole
