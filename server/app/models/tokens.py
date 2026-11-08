import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import utcnow
from .enums import ServiceTokenAccess, enum_values


class ServiceToken(Base):
    __tablename__ = "service_tokens"
    __table_args__ = (
        Index("ix_public_service_tokens_project_id", "project_id"),
        Index("ix_public_service_tokens_environment_id", "environment_id"),
        Index("ix_public_service_tokens_token_hash", "token_hash", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    environment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("environments.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    access: Mapped[ServiceTokenAccess] = mapped_column(
        Enum(ServiceTokenAccess, name="service_token_access", values_callable=enum_values),
        default=ServiceTokenAccess.read,
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
