from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Optional

class StudentCreate(BaseModel):
    school_id: UUID
    full_name: str = Field(min_length=2, max_length=160)
    age: int = Field(ge=0, le=8)
    group: str = Field(min_length=1, max_length=60)
    notes: Optional[str] = None

class StudentUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    age: Optional[int] = Field(default=None, ge=0, le=8)
    group: Optional[str] = Field(default=None, min_length=1, max_length=60)
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    school_id: UUID
    full_name: str
    age: int
    group: str
    notes: Optional[str]
    is_active: bool
