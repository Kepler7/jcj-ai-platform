import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Boolean, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class AIReport(Base):
    __tablename__ = "ai_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    generated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    teacher_version: Mapped[dict] = mapped_column(JSONB, nullable=False)
    parent_version: Mapped[dict] = mapped_column(JSONB, nullable=False)
    signals_detected: Mapped[list] = mapped_column(JSONB, nullable=False)

    guardrails_passed: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    guardrails_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    engine_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="2", server_default="2"
    )
    ai_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
