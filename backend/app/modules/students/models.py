import uuid
from sqlalchemy import String, Integer, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)   # 5–8 (validación en schema)
    group: Mapped[str] = mapped_column(String(60), nullable=False)  # ej. "PreK2-A"

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # notas educativas opcionales

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    guardians = relationship("Guardian", back_populates="student", cascade="all, delete-orphan")
