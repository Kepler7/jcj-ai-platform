from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    ai_report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_reports.id", ondelete="CASCADE"), nullable=False)

    # opcional (futuro): amarrar a un tutor específico
    guardian_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("guardians.id", ondelete="SET NULL"), nullable=True)

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# Índices (equivalentes a los del SQL; SQLAlchemy los crea si usas create_all)
Index("idx_share_links_ai_report_id", ShareLink.ai_report_id)
Index("idx_share_links_school_id", ShareLink.school_id)
Index("idx_share_links_expires_at", ShareLink.expires_at)
