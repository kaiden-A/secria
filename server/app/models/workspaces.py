import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import utcnow
from .enums import WorkspaceRole, enum_values


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (Index("ix_public_workspaces_slug", "slug", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (Index("ix_public_workspace_members_user_id", "user_id"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole, name="workspace_role", values_callable=enum_values),
        default=WorkspaceRole.member,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
