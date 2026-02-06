from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AIFallbackOut(BaseModel):
    id: UUID
    school_id: UUID
    student_id: UUID
    report_id: UUID
    ai_report_id: Optional[UUID] = None

    topic_nucleo: Optional[str] = None
    context: Optional[str] = None
    reason: str

    query_text: Optional[str] = None
    model_output_summary: Optional[str] = None

    created_by_user_id: Optional[UUID] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_user_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class ResolveFallbackRequest(BaseModel):
    # si quieres capturar nota breve al resolver:
    # resolution_note: Optional[str] = None
    pass
