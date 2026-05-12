from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIPredictionStatus(str, enum.Enum):
    confirmed_jcj = "confirmed_jcj"
    pending_human_review = "pending_human_review"
    general_fallback = "general_fallback"


class AIFeedbackVerdict(str, enum.Enum):
    correct = "correct"
    incorrect = "incorrect"
    none_apply = "none_apply"


class AIPrediction(Base):
    __tablename__ = "ai_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    school_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    student_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    predicted_playbook_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    predicted_playbook_base_row: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    status: Mapped[AIPredictionStatus] = mapped_column(
        Enum(AIPredictionStatus, name="ai_prediction_status"),
        nullable=False,
        index=True,
    )

    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    confidence_gap: Mapped[float | None] = mapped_column(nullable=True)

    top_candidates_json: Mapped[dict | list | None] = mapped_column(
        JSONB, nullable=True
    )
    top_scores_json: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)

    retrieval_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reranker_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    used_hyde: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    resolved_by_human: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    final_playbook_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )


class AIPredictionFeedback(Base):
    __tablename__ = "ai_prediction_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_predictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    verdict: Mapped[AIFeedbackVerdict] = mapped_column(
        Enum(AIFeedbackVerdict, name="ai_feedback_verdict"),
        nullable=False,
        index=True,
    )

    corrected_playbook_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    corrected_playbook_base_row: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
