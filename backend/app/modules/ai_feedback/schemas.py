from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.modules.ai_feedback.models import AIFeedbackVerdict, AIPredictionStatus


class AIPredictionCreate(BaseModel):
    school_id: Optional[UUID] = None
    student_id: Optional[UUID] = None
    report_id: UUID

    predicted_playbook_id: Optional[str] = None
    predicted_playbook_base_row: Optional[str] = None

    status: AIPredictionStatus

    confidence_score: Optional[float] = None
    confidence_gap: Optional[float] = None

    top_candidates_json: Optional[List[Any]] = None
    top_scores_json: Optional[List[Any]] = None

    retrieval_version: Optional[str] = None
    reranker_version: Optional[str] = None
    used_hyde: bool = False

    model_name: Optional[str] = None
    final_playbook_id: Optional[str] = None


class PlaybookPreviewOut(BaseModel):
    id: str
    topic_nucleo: Optional[str] = None
    subhabilidad: Optional[str] = None
    senal_observable: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None


class AIPredictionOut(BaseModel):
    id: UUID
    report_id: UUID
    predicted_playbook_id: Optional[str] = None
    predicted_playbook_base_row: Optional[str] = None
    status: AIPredictionStatus
    confidence_score: Optional[float] = None
    confidence_gap: Optional[float] = None
    top_candidates_json: Optional[List[Any]] = None
    top_scores_json: Optional[List[Any]] = None
    retrieval_version: Optional[str] = None
    reranker_version: Optional[str] = None
    used_hyde: bool
    model_name: Optional[str] = None
    resolved_by_human: bool
    final_playbook_id: Optional[str] = None
    created_at: datetime

    predicted_playbook_preview: Optional[PlaybookPreviewOut] = None
    top_candidates_preview: Optional[List[PlaybookPreviewOut]] = None

    model_config = {"from_attributes": True}


class AIPredictionFeedbackCreate(BaseModel):
    prediction_id: UUID
    verdict: AIFeedbackVerdict
    corrected_playbook_id: Optional[str] = None
    corrected_playbook_base_row: Optional[str] = None
    note: Optional[str] = None


class AIPredictionFeedbackOut(BaseModel):
    id: UUID
    prediction_id: UUID
    verdict: AIFeedbackVerdict
    corrected_playbook_id: Optional[str] = None
    corrected_playbook_base_row: Optional[str] = None
    note: Optional[str] = None
    reviewed_by_user_id: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}
