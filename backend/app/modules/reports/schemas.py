from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Optional
from datetime import datetime

class ReportCreate(BaseModel):
    student_id: UUID
    mood: Optional[str] = Field(default=None, max_length=50)
    participation: Optional[str] = Field(default=None, max_length=50)
    strengths: Optional[str] = None
    challenges: Optional[str] = None
    notes: Optional[str] = None

class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    school_id: UUID
    student_id: UUID
    teacher_id: UUID
    mood: Optional[str]
    participation: Optional[str]
    strengths: Optional[str]
    challenges: Optional[str]
    notes: Optional[str]
    is_submitted: bool
    created_at: datetime
