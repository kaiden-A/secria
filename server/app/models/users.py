import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import utcnow


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_public_users_email", "email", unique=True),
        Index("ix_public_users_zitadel_sub", "zitadel_sub", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Source of truth for authentication is Zitadel; this is the local link to it.
    zitadel_sub: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
