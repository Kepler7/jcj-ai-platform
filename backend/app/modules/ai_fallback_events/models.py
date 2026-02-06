from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIFallbackEvent(Base):
    __tablename__ = "ai_fallback_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("student_reports.id"), nullable=False)
    ai_report_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_reports.id"), nullable=True)

    topic_nucleo: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    context: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    reason: Mapped[str] = mapped_column(String(32), nullable=False)

    query_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


Index("idx_fallback_school_id", AIFallbackEvent.school_id)
Index("idx_fallback_created_at", AIFallbackEvent.created_at)
Index("idx_fallback_resolved_at", AIFallbackEvent.resolved_at)
