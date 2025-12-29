from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional

class SchoolCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    legal_name: Optional[str] = Field(default=None, max_length=180)
    city: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)

class SchoolUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    legal_name: Optional[str] = Field(default=None, max_length=180)
    city: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    is_active: Optional[bool] = None

class SchoolOut(BaseModel):
    id: UUID
    name: str
    legal_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True
