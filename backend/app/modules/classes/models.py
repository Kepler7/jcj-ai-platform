import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base  # ajusta si tu Base vive en otro path


class Class(Base):
    __tablename__ = "classes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )

    name = Column(String(120), nullable=False)  # ej: "PreK2-A"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_classes_school_name"),
        Index("ix_classes_school_id", "school_id"),
    )

    # Many-to-many
    teachers = relationship(
        "User",
        secondary="teacher_classes",
        back_populates="classes_taught",
        lazy="selectin",
    )

    students = relationship(
        "Student",
        secondary="student_classes",
        back_populates="classes",
        lazy="selectin",
    )


class TeacherClass(Base):
    __tablename__ = "teacher_classes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    class_id = Column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("teacher_id", "class_id", name="uq_teacher_class"),
        Index("ix_teacher_classes_teacher_id", "teacher_id"),
        Index("ix_teacher_classes_class_id", "class_id"),
    )


class StudentClass(Base):
    __tablename__ = "student_classes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    class_id = Column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "class_id", name="uq_student_class"),
        Index("ix_student_classes_student_id", "student_id"),
        Index("ix_student_classes_class_id", "class_id"),
    )
