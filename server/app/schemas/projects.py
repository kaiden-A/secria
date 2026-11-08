from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from ..models import ProjectRole


class EnvironmentOut(BaseModel):
    id: str
    name: str
    slug: str
    position: int
    createdAt: int


class EnvironmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    slug: str | None = Field(default=None, max_length=64)
    position: int | None = Field(default=None, ge=0)


class ProjectOut(BaseModel):
    id: str
    workspaceId: str
    name: str
    slug: str
    description: str
    role: ProjectRole
    archivedAt: int | None = None
    environmentCount: int
    memberCount: int
    createdAt: int
    updatedAt: int


class ProjectDetail(ProjectOut):
    environments: list[EnvironmentOut]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=64)
    description: str = Field(default="", max_length=1000)


class ProjectPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=1000)
    archived: bool | None = None


class ProjectMemberOut(BaseModel):
    userId: str
    name: str
    email: str
    role: ProjectRole
    environmentIds: list[str] | None = None
    joinedAt: int
    source: Literal["workspace", "project"] = "project"


class ProjectMemberPut(BaseModel):
    role: ProjectRole
    environmentIds: list[UUID] | None = None
