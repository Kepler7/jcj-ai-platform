from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GuardianCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    whatsapp_phone: str = Field(min_length=8, max_length=32)
    relationship: str = Field(min_length=2, max_length=32)

    is_primary: bool = False
    notes: Optional[str] = Field(default=None, max_length=2000)


class GuardianUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    whatsapp_phone: Optional[str] = Field(default=None, min_length=8, max_length=32)
    relationship: Optional[str] = Field(default=None, min_length=2, max_length=32)

    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class GuardianOut(BaseModel):
    id: UUID
    student_id: UUID
    school_id: UUID
    full_name: str
    whatsapp_phone: Optional[str] = None
    relationship: Optional[str] = None
    is_primary: bool
    is_active: bool
    notes: Optional[str] = None

    # ✅ agrega estos dos
    receive_whatsapp: bool
    consent_to_contact: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
