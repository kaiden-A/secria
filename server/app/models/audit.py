import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_public_audit_logs_workspace_id", "workspace_id"),
        Index("ix_public_audit_logs_project_id", "project_id"),
        Index("ix_public_audit_logs_action", "action"),
        Index("ix_public_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL")
    )
    environment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("environments.id", ondelete="SET NULL")
    )
    actor_type: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(320), nullable=False)
    # "metadata" is reserved by SQLAlchemy declarative, so the attribute is
    # `meta` while the database column keeps its planned name.
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
