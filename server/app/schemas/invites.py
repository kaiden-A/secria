from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from ..models import ProjectRole, WorkspaceRole


class InviteGrantIn(BaseModel):
    projectId: UUID
    role: ProjectRole = ProjectRole.viewer


class InviteCreate(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.member
    grants: list[InviteGrantIn] = Field(default_factory=list)


class InvitePatch(BaseModel):
    role: WorkspaceRole | None = None
    grants: list[InviteGrantIn] | None = None


class InviteGrantOut(BaseModel):
    projectId: str
    projectName: str
    role: ProjectRole


class InviteOut(BaseModel):
    id: str
    email: str
    role: WorkspaceRole
    grants: list[InviteGrantOut]
    invitedByName: str | None = None
    status: Literal["pending", "accepted", "revoked", "expired"]
    expiresAt: int
    acceptedAt: int | None = None
    revokedAt: int | None = None
    createdAt: int


class InviteCreateResult(InviteOut):
    inviteUrl: str
    emailSent: bool


class InviteResendResult(BaseModel):
    inviteUrl: str
    emailSent: bool
    expiresAt: int


class InvitePreview(BaseModel):
    workspaceName: str
    workspaceSlug: str
    inviterName: str | None = None
    email: str
    role: WorkspaceRole
    grants: list[InviteGrantOut]
    expiresAt: int


class InviteAcceptResult(BaseModel):
    workspaceId: str
    workspaceName: str
    workspaceSlug: str
