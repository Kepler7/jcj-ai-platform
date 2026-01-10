from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Any

class AIReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    school_id: UUID
    student_id: UUID
    report_id: UUID

    generated_by_user_id: UUID
    model_name: str

    teacher_version: dict[str, Any]
    parent_version: dict[str, Any]
    signals_detected: list[Any]

    guardrails_passed: bool
    guardrails_notes: str | None
    created_at: datetime

class GenerateAIReportRequest(BaseModel):
    report_id: UUID
    force: bool = False