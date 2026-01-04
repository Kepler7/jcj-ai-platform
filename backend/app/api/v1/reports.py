from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID

from app.db.db import get_db
from app.modules.users.models import User
from app.modules.students.models import Student
from app.modules.reports.models import StudentReport
from app.modules.reports.schemas import ReportCreate, ReportOut

from app.auth.deps import require_role
from app.auth.roles import Role

router = APIRouter(prefix="/v1/reports", tags=["reports"])

def ensure_same_school(user: User, school_id: UUID):
    if user.role == Role.platform_admin.value:
        return
    if not user.school_id or UUID(str(user.school_id)) != school_id:
        raise HTTPException(status_code=403, detail="Forbidden (different school)")

@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.platform_admin, Role.school_admin, Role.teacher)),
):
    # Student must exist
    student = db.get(Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    ensure_same_school(current_user, UUID(str(student.school_id)))

    report = StudentReport(
        school_id=student.school_id,
        student_id=student.id,
        teacher_id=current_user.id,
        mood=payload.mood,
        participation=payload.participation,
        strengths=payload.strengths,
        challenges=payload.challenges,
        notes=payload.notes,
        is_submitted=True,
    )

    db.add(report)
    db.commit()
    db.refresh(report)
    return report

@router.get("", response_model=list[ReportOut])
def list_reports(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.platform_admin, Role.school_admin, Role.teacher)),
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    ensure_same_school(current_user, UUID(str(student.school_id)))

    reports = db.execute(
        select(StudentReport)
        .where(StudentReport.student_id == student_id)
        .order_by(StudentReport.created_at.desc())
    ).scalars().all()

    return reports
