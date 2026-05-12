from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ClassOut(BaseModel):
    id: UUID
    school_id: UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class ClassCreate(BaseModel):
    school_id: UUID
    name: str = Field(min_length=1, max_length=120)


class AssignTeachersIn(BaseModel):
    teacher_ids: list[UUID]


class AssignStudentsIn(BaseModel):
    student_ids: list[UUID]


class ReplaceTeachersIn(BaseModel):
    teacher_ids: list[UUID]


class ReplaceStudentsIn(BaseModel):
    student_ids: list[UUID]


class ClassMiniOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
