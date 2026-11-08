import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import utcnow
from .enums import ProjectRole, WorkspaceRole, enum_values


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = (
        Index("ix_public_invites_workspace_id", "workspace_id"),
        Index("ix_public_invites_email", "email"),
        Index("ix_public_invites_token_hash", "token_hash", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole, name="workspace_role", values_callable=enum_values),
        default=WorkspaceRole.member,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class InviteGrant(Base):
    __tablename__ = "invite_grants"

    invite_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("invites.id", ondelete="CASCADE"), primary_key=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[ProjectRole] = mapped_column(
        Enum(ProjectRole, name="project_role", values_callable=enum_values),
        default=ProjectRole.viewer,
        nullable=False,
    )
