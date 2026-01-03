from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID

from app.db.db import get_db
from app.modules.students.models import Student
from app.modules.students.schemas import StudentCreate, StudentUpdate, StudentOut

from app.auth.deps import get_current_user, require_role
from app.auth.roles import Role
from app.modules.users.models import User

router = APIRouter(prefix="/v1/students", tags=["students"])

def ensure_same_school(current_user: User, school_id: UUID):
    # platform_admin puede todo
    if current_user.role == Role.platform_admin.value:
        return
    # teacher/school_admin: deben tener school_id y coincidir
    if not current_user.school_id or UUID(str(current_user.school_id)) != school_id:
        raise HTTPException(status_code=403, detail="Forbidden (different school)")

@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.platform_admin, Role.school_admin, Role.teacher)),
):
    ensure_same_school(current_user, payload.school_id)

    student = Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

@router.get("", response_model=list[StudentOut])
def list_students(
    school_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.platform_admin, Role.school_admin, Role.teacher)),
):
    ensure_same_school(current_user, school_id)

    students = db.execute(
        select(Student).where(Student.school_id == school_id, Student.is_active == True)
    ).scalars().all()
    return students

@router.get("/{student_id}", response_model=StudentOut)
def get_student(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.platform_admin, Role.school_admin, Role.teacher)),
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    ensure_same_school(current_user, UUID(str(student.school_id)))
    return student

@router.patch("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: UUID,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.platform_admin, Role.school_admin, Role.teacher)),
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    ensure_same_school(current_user, UUID(str(student.school_id)))

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(student, k, v)

    db.commit()
    db.refresh(student)
    return student