import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import utcnow


class Secret(Base):
    __tablename__ = "secrets"
    __table_args__ = (
        UniqueConstraint("environment_id", "key", name="uq_secrets_environment_key"),
        Index("ix_public_secrets_environment_id", "environment_id"),
        Index("ix_public_secrets_current_version_id", "current_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    environment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("environments.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    # No FK on purpose: secret_versions references secrets, so a FK here would
    # create a circular dependency. The service layer keeps them consistent.
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SecretVersion(Base):
    __tablename__ = "secret_versions"
    __table_args__ = (
        UniqueConstraint("secret_id", "version", name="uq_secret_versions_number"),
        Index("ix_public_secret_versions_secret_id", "secret_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    secret_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("secrets.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    comment: Mapped[str] = mapped_column(String(500), default="", nullable=False)
