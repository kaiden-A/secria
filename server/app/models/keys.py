import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import utcnow


class ProjectKey(Base):
    """A project's data encryption key, wrapped by the master key.

    encrypted_dek is nonce || AES-256-GCM ciphertext. The AAD binds the wrapped
    key to its project and version so a blob cannot be moved between projects.
    """

    __tablename__ = "project_keys"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    key_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    encrypted_dek: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    kek_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
