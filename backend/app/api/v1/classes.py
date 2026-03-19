from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.db import get_db
from app.auth.deps import get_current_user, require_role
from app.auth.roles import Role

from app.modules.users.models import User
from app.modules.students.models import Student
from app.modules.classes.models import Class, TeacherClass, StudentClass
from app.modules.classes.schemas import (
    ClassCreate,
    ClassOut,
    ReplaceTeachersIn,
    ReplaceStudentsIn,
)
from app.modules.students.schemas import StudentOutWithClasses

# ✅ RUTAS CONSISTENTES:
# Todo vive bajo /v1/classes/...
router = APIRouter(prefix="/v1/classes", tags=["classes"])


# ----------------------------
# Helpers
# ----------------------------


def _ensure_teacher_assigned(db: Session, teacher_id: UUID, class_id: UUID) -> None:
    ok = db.execute(
        select(TeacherClass.id).where(
            TeacherClass.teacher_id == teacher_id,
            TeacherClass.class_id == class_id,
        )
    ).scalar_one_or_none()

    if not ok:
        raise HTTPException(
            status_code=403, detail="Teacher is not assigned to this class"
        )


def _get_class_or_404(db: Session, class_id: UUID) -> Class:
    c = db.execute(select(Class).where(Class.id == class_id)).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Class not found")
    return c


def _get_teacher_or_404(db: Session, teacher_id: UUID) -> User:
    t = db.execute(select(User).where(User.id == teacher_id)).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Teacher not found")
    if t.role != "teacher":
        raise HTTPException(status_code=400, detail="User is not a teacher")
    return t


def _get_student_or_404(db: Session, student_id: UUID) -> Student:
    s = db.execute(select(Student).where(Student.id == student_id)).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    return s


def _enforce_school_admin_scope(current_user: User, class_school_id: UUID) -> None:
    # school_admin solo puede operar dentro de su escuela
    if (
        current_user.role == "school_admin"
        and current_user.school_id != class_school_id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")


def _ensure_same_school(
    entity_school_id: UUID, class_school_id: UUID, label: str
) -> None:
    if entity_school_id != class_school_id:
        raise HTTPException(
            status_code=400,
            detail=f"{label} and class must belong to the same school",
        )


# ----------------------------
# Classes CRUD (mínimo)
# ----------------------------


@router.post(
    "",
    response_model=ClassOut,
    dependencies=[Depends(require_role(Role.platform_admin, Role.school_admin))],
)
def create_class(
    payload: ClassCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Si school_admin, fuerza school_id
    if current_user.role == "school_admin":
        payload.school_id = current_user.school_id

    exists = db.execute(
        select(Class.id).where(
            Class.school_id == payload.school_id,
            Class.name == payload.name,
        )
    ).scalar_one_or_none()

    if exists:
        raise HTTPException(
            status_code=409, detail="Class already exists in this school"
        )

    c = Class(school_id=payload.school_id, name=payload.name)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get(
    "/me",
    response_model=list[ClassOut],
    dependencies=[Depends(require_role(Role.teacher))],
)
def get_my_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(Class)
        .join(TeacherClass, TeacherClass.class_id == Class.id)
        .where(TeacherClass.teacher_id == current_user.id)
        .order_by(Class.name.asc())
    )
    return list(db.execute(q).scalars().all())


@router.get(
    "/by-school/{school_id}",
    response_model=list[ClassOut],
    dependencies=[
        Depends(require_role(Role.platform_admin, Role.school_admin, Role.teacher))
    ],
)
def get_classes_by_school(
    school_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # school_admin y teacher solo pueden ver su escuela
    if current_user.role in ("school_admin", "teacher"):
        if current_user.school_id != school_id:
            raise HTTPException(status_code=403, detail="Forbidden")

    q = select(Class).where(Class.school_id == school_id).order_by(Class.name.asc())
    return list(db.execute(q).scalars().all())


# ----------------------------
# Students in class
# ----------------------------


@router.get(
    "/{class_id}/students",
    response_model=List[StudentOutWithClasses],
    dependencies=[
        Depends(require_role(Role.platform_admin, Role.school_admin, Role.teacher))
    ],
)
def get_class_students(
    class_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_class_or_404(db, class_id)

    # school_admin solo puede ver su escuela
    _enforce_school_admin_scope(current_user, c.school_id)

    # teacher solo ve si le pertenece la clase
    if current_user.role == "teacher":
        _ensure_teacher_assigned(db, current_user.id, class_id)

    q = (
        select(Student)
        .options(selectinload(Student.classes))
        .join(StudentClass, StudentClass.student_id == Student.id)
        .where(StudentClass.class_id == class_id)
        .order_by(Student.full_name.asc())
    )
    students = list(db.execute(q).scalars().unique().all())

    # ✅ Construcción explícita para evitar broncas de ORM/Pydantic
    return [
        StudentOutWithClasses(
            id=s.id,
            school_id=s.school_id,
            full_name=s.full_name,
            age=getattr(s, "age", None),
            notes=getattr(s, "notes", None),
            is_active=getattr(s, "is_active", None),
            created_at=getattr(s, "created_at", None),
            classes=[
                {"id": cl.id, "name": cl.name} for cl in getattr(s, "classes", [])
            ],
        )
        for s in students
    ]


# ----------------------------
# Asignación / Reasignación (Teachers)
# ----------------------------


@router.post(
    "/{class_id}/teachers/{teacher_id}",
    dependencies=[Depends(require_role(Role.platform_admin, Role.school_admin))],
)
def assign_teacher_to_class(
    class_id: UUID,
    teacher_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_class_or_404(db, class_id)
    _enforce_school_admin_scope(current_user, c.school_id)

    t = _get_teacher_or_404(db, teacher_id)
    _ensure_same_school(t.school_id, c.school_id, "Teacher")

    exists = db.execute(
        select(TeacherClass.id).where(
            TeacherClass.teacher_id == teacher_id,
            TeacherClass.class_id == class_id,
        )
    ).scalar_one_or_none()

    if exists:
        return {"ok": True}

    db.add(TeacherClass(teacher_id=teacher_id, class_id=class_id))
    db.commit()
    return {"ok": True}


@router.delete(
    "/{class_id}/teachers/{teacher_id}",
    dependencies=[Depends(require_role(Role.platform_admin, Role.school_admin))],
)
def unassign_teacher_from_class(
    class_id: UUID,
    teacher_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_class_or_404(db, class_id)
    _enforce_school_admin_scope(current_user, c.school_id)

    tc = db.execute(
        select(TeacherClass).where(
            TeacherClass.teacher_id == teacher_id,
            TeacherClass.class_id == class_id,
        )
    ).scalar_one_or_none()

    if not tc:
        return {"ok": True}

    db.delete(tc)
    db.commit()
    return {"ok": True}


@router.put(
    "/{class_id}/teachers",
    dependencies=[Depends(require_role(Role.platform_admin, Role.school_admin))],
)
def replace_class_teachers(
    class_id: UUID,
    payload: ReplaceTeachersIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_class_or_404(db, class_id)
    _enforce_school_admin_scope(current_user, c.school_id)

    db.query(TeacherClass).filter(TeacherClass.class_id == class_id).delete(
        synchronize_session=False
    )

    for teacher_id in payload.teacher_ids:
        t = _get_teacher_or_404(db, teacher_id)
        _ensure_same_school(t.school_id, c.school_id, "Teacher")
        db.add(TeacherClass(teacher_id=teacher_id, class_id=class_id))

    db.commit()
    return {"ok": True}


# ----------------------------
# Asignación / Reasignación (Students)
# ----------------------------


@router.post(
    "/{class_id}/students/{student_id}",
    dependencies=[Depends(require_role(Role.platform_admin, Role.school_admin))],
)
def assign_student_to_class(
    class_id: UUID,
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_class_or_404(db, class_id)
    _enforce_school_admin_scope(current_user, c.school_id)

    s = _get_student_or_404(db, student_id)
    _ensure_same_school(s.school_id, c.school_id, "Student")

    exists = db.execute(
        select(StudentClass.id).where(
            StudentClass.student_id == student_id,
            StudentClass.class_id == class_id,
        )
    ).scalar_one_or_none()

    if exists:
        return {"ok": True}

    db.add(StudentClass(student_id=student_id, class_id=class_id))
    db.commit()
    return {"ok": True}


@router.delete(
    "/{class_id}/students/{student_id}",
    dependencies=[Depends(require_role(Role.platform_admin, Role.school_admin))],
)
def unassign_student_from_class(
    class_id: UUID,
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_class_or_404(db, class_id)
    _enforce_school_admin_scope(current_user, c.school_id)

    sc = db.execute(
        select(StudentClass).where(
            StudentClass.student_id == student_id,
            StudentClass.class_id == class_id,
        )
    ).scalar_one_or_none()

    if not sc:
        return {"ok": True}

    db.delete(sc)
    db.commit()
    return {"ok": True}


@router.put(
    "/{class_id}/students",
    dependencies=[Depends(require_role(Role.platform_admin, Role.school_admin))],
)
def replace_class_students(
    class_id: UUID,
    payload: ReplaceStudentsIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_class_or_404(db, class_id)
    _enforce_school_admin_scope(current_user, c.school_id)

    db.query(StudentClass).filter(StudentClass.class_id == class_id).delete(
        synchronize_session=False
    )

    for student_id in payload.student_ids:
        s = _get_student_or_404(db, student_id)
        _ensure_same_school(s.school_id, c.school_id, "Student")
        db.add(StudentClass(student_id=student_id, class_id=class_id))

    db.commit()
    return {"ok": True}
