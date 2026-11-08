import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import utcnow
from .enums import ProjectRole, enum_values


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_projects_workspace_slug"),
        Index("ix_public_projects_workspace_id", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (Index("ix_public_project_members_user_id", "user_id"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[ProjectRole] = mapped_column(
        Enum(ProjectRole, name="project_role", values_callable=enum_values),
        default=ProjectRole.viewer,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Environment(Base):
    __tablename__ = "environments"
    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_environments_project_slug"),
        Index("ix_public_environments_project_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProjectMemberEnv(Base):
    """Optional environment restriction for a project member.

    No rows for a member means every environment in that project is allowed.
    """

    __tablename__ = "project_member_envs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["project_members.project_id", "project_members.user_id"],
            ondelete="CASCADE",
            name="project_member_envs_project_id_user_id_fkey",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    environment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("environments.id", ondelete="CASCADE"), primary_key=True
    )
