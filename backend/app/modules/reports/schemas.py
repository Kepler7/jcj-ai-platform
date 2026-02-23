from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Optional
from datetime import datetime


class ReportCreate(BaseModel):
    student_id: UUID
    mood: Optional[str] = Field(default=None, max_length=50)
    participation: Optional[str] = Field(default=None, max_length=50)
    signals_observed: str = Field(min_length=5)  # Nuevo campo obligatorio
    notes: Optional[str] = None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    school_id: UUID
    student_id: UUID
    teacher_id: UUID
    mood: Optional[str]
    participation: Optional[str]
    signals_observed: str
    notes: Optional[str]
    is_submitted: bool
    created_at: datetime
