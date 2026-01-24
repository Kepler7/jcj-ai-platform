from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GuardianRelationship(str, Enum):
    mother = "mother"
    father = "father"
    tutor = "tutor"
    grandparent = "grandparent"
    other = "other"


class Guardian(Base):
    __tablename__ = "guardians"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # relación con alumno
    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # seguridad por escuela (muy útil para filtros y permisos)
    school_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # WhatsApp en formato E.164 recomendado: +5213312345678
    whatsapp_phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    relationship: Mapped[GuardianRelationship] = mapped_column(
        SAEnum(GuardianRelationship, name="guardian_relationship"),
        nullable=False,
        default=GuardianRelationship.tutor,
    )

    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # opcional: relationship ORM (si tu Student model define back_populates)
    student = relationship("Student", back_populates="guardians", lazy="joined")
