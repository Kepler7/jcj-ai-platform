from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.classes.schemas import ClassMiniOut


class StudentCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    school_id: UUID
    full_name: str = Field(min_length=2, max_length=160)
    age: int = Field(ge=0, le=12)
    # para create: nombres de clases (si así lo manejas en tu lógica)
    classes: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class StudentUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    age: Optional[int] = Field(default=None, ge=0, le=18)
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    # si viene, reemplaza clases (por ids)
    class_ids: Optional[list[UUID]] = None

    # si tú también soportas update por nombres, déjalo; si no, bórralo
    classes: Optional[list[str]] = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    school_id: UUID
    full_name: str
    age: int | None = None
    # salida “simple”: lista de strings (si la usas en algún endpoint)
    classes: list[str] = Field(default_factory=list)
    notes: str | None = None
    created_at: datetime | None = None


class StudentOutWithClasses(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    school_id: UUID
    full_name: str
    age: int | None = None
    notes: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    classes: list[ClassMiniOut] = Field(default_factory=list)
