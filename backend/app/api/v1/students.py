import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func
from app.modules.reports.models import StudentReport
from uuid import UUID

from app.db.db import get_db

from app.modules.students.schemas import (
    StudentCreate,
    StudentUpdate,
    StudentOut,
    StudentOutWithClasses,
)

from app.auth.deps import get_current_user, require_role
from app.auth.roles import Role
from app.modules.users.models import User

from app.modules.classes.models import Class, StudentClass, TeacherClass
from app.modules.students.models import Student
from app.modules.students.bulk_schemas import (
    BulkStudentsPreviewResponse,
    BulkStudentsApplyResponse,
    BulkRowError,
)

router = APIRouter(prefix="/v1/students", tags=["students"])


def _sniff_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t"]).delimiter
    except Exception:
        return ","


def _parse_classes(row: dict) -> list[str]:
    # Prefer classes column; fallback to group
    classes_raw = (row.get("classes") or "").strip()
    if classes_raw:
        parts = [p.strip() for p in classes_raw.replace(";", "|").split("|")]
        return [p for p in parts if p]

    group = (row.get("group") or "").strip()
    return [group] if group else []


def _get_school_id_for_row(
    row: dict, current_user: User, school_id_param: UUID | None
) -> UUID:
    if current_user.role == "school_admin":
        if not current_user.school_id:
            raise ValueError("school_admin has no school_id")
        return current_user.school_id

    # platform_admin
    if row.get("school_id"):
        return UUID(str(row["school_id"]).strip())
    if school_id_param:
        return school_id_param

    raise ValueError(
        "school_id is required (CSV column or query param) for platform_admin"
    )


def _get_or_create_class(db: Session, school_id: UUID, name: str) -> tuple[Class, bool]:
    existing = db.execute(
        select(Class).where(Class.school_id == school_id, Class.name == name)
    ).scalar_one_or_none()

    if existing:
        return existing, False

    c = Class(school_id=school_id, name=name)
    db.add(c)
    db.flush()  # get id without commit
    return c, True


def _get_classes_by_names(
    db: Session, school_id: UUID, class_names: list[str]
) -> list[Class]:
    if not class_names:
        return []

    normalized = []
    seen = set()
    for name in class_names:
        clean = (name or "").strip()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)

    if not normalized:
        return []

    found_classes = (
        db.execute(
            select(Class).where(
                Class.school_id == school_id,
                Class.name.in_(normalized),
            )
        )
        .scalars()
        .all()
    )

    found_names = {c.name for c in found_classes}
    missing_names = [name for name in normalized if name not in found_names]
    if missing_names:
        raise HTTPException(
            status_code=400,
            detail=f"Classes not found for this school: {missing_names}",
        )

    return found_classes


def ensure_same_school(current_user: User, school_id: UUID):
    # platform_admin puede todo
    if current_user.role == Role.platform_admin.value:
        return
    # teacher/school_admin: deben tener school_id y coincidir
    if not current_user.school_id or UUID(str(current_user.school_id)) != school_id:
        raise HTTPException(status_code=403, detail="Forbidden (different school)")


def _students_with_reports_response(rows):
    return [
        StudentOutWithClasses(
            id=s.id,
            school_id=s.school_id,
            full_name=s.full_name,
            age=getattr(s, "age", None),
            notes=getattr(s, "notes", None),
            is_active=getattr(s, "is_active", None),
            created_at=getattr(s, "created_at", None),
            reports_count=int(reports_count or 0),
            classes=[{"id": c.id, "name": c.name} for c in getattr(s, "classes", [])],
        )
        for s, reports_count in rows
    ]


def _students_with_reports_base_stmt():
    reports_count_sq = (
        select(func.count(StudentReport.id))
        .where(StudentReport.student_id == Student.id)
        .correlate(Student)
        .scalar_subquery()
    )

    return (
        select(
            Student,
            func.coalesce(reports_count_sq, 0).label("reports_count"),
        )
        .options(selectinload(Student.classes))
        .order_by(Student.full_name.asc())
    )


def _teacher_assigned_student_ids(teacher_id: UUID):
    return (
        select(StudentClass.student_id)
        .join(TeacherClass, TeacherClass.class_id == StudentClass.class_id)
        .where(TeacherClass.teacher_id == teacher_id)
        .distinct()
    )


def _ensure_teacher_assigned_to_student(
    db: Session, teacher_id: UUID, student_id: UUID
) -> None:
    exists = db.execute(
        select(StudentClass.id)
        .join(TeacherClass, TeacherClass.class_id == StudentClass.class_id)
        .where(
            TeacherClass.teacher_id == teacher_id,
            StudentClass.student_id == student_id,
        )
    ).scalar_one_or_none()

    if not exists:
        raise HTTPException(status_code=403, detail="Teacher is not assigned to this student")


@router.post(
    "", response_model=StudentOutWithClasses, status_code=status.HTTP_201_CREATED
)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(Role.platform_admin, Role.school_admin, Role.teacher)
    ),
):
    ensure_same_school(current_user, payload.school_id)

    class_names = payload.classes or []

    student_data = payload.model_dump(exclude={"classes"})
    student = Student(**student_data)
    db.add(student)
    db.flush()

    if class_names:
        found_classes = _get_classes_by_names(db, payload.school_id, class_names)
        student.classes = found_classes

    db.commit()

    student = db.execute(
        select(Student)
        .where(Student.id == student.id)
        .options(selectinload(Student.classes))
    ).scalar_one()

    return StudentOutWithClasses(
        id=student.id,
        school_id=student.school_id,
        full_name=student.full_name,
        age=getattr(student, "age", None),
        notes=getattr(student, "notes", None),
        is_active=getattr(student, "is_active", None),
        created_at=getattr(student, "created_at", None),
        classes=[{"id": c.id, "name": c.name} for c in getattr(student, "classes", [])],
    )


@router.get(
    "",
    response_model=list[StudentOutWithClasses],
    dependencies=[
        Depends(require_role(Role.platform_admin, Role.school_admin, Role.teacher))
    ],
)
def list_students_with_classes(
    school_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role in ("school_admin", "teacher"):
        if current_user.school_id != school_id:
            raise HTTPException(status_code=403, detail="Forbidden")

    stmt = _students_with_reports_base_stmt().where(Student.school_id == school_id)

    if current_user.role == Role.teacher.value:
        stmt = stmt.where(Student.id.in_(_teacher_assigned_student_ids(current_user.id)))

    rows = db.execute(stmt).all()
    return _students_with_reports_response(rows)


@router.get(
    "/me",
    response_model=list[StudentOutWithClasses],
    dependencies=[Depends(require_role(Role.teacher))],
)
def list_my_students_with_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = _students_with_reports_base_stmt().where(
        Student.id.in_(_teacher_assigned_student_ids(current_user.id))
    )
    rows = db.execute(stmt).all()
    return _students_with_reports_response(rows)


@router.get(
    "/{student_id}",
    response_model=StudentOutWithClasses,
    dependencies=[
        Depends(require_role(Role.platform_admin, Role.school_admin, Role.teacher))
    ],
)
def get_student_with_classes(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Student)
        .where(Student.id == student_id)
        .options(selectinload(Student.classes))
    )
    s = db.execute(stmt).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")

    if current_user.role in ("school_admin", "teacher"):
        if current_user.school_id != s.school_id:
            raise HTTPException(status_code=403, detail="Forbidden")

    if current_user.role == Role.teacher.value:
        _ensure_teacher_assigned_to_student(db, current_user.id, student_id)

    return StudentOutWithClasses(
        id=s.id,
        school_id=s.school_id,
        full_name=s.full_name,
        age=getattr(s, "age", None),
        notes=getattr(s, "notes", None),
        is_active=getattr(s, "is_active", None),
        created_at=getattr(s, "created_at", None),
        classes=[{"id": c.id, "name": c.name} for c in getattr(s, "classes", [])],
    )


@router.patch("/{student_id}", response_model=StudentOutWithClasses)
def update_student(
    student_id: UUID,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(Role.platform_admin, Role.school_admin, Role.teacher)
    ),
):
    student = db.execute(
        select(Student)
        .where(Student.id == student_id)
        .options(selectinload(Student.classes))
    ).scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    ensure_same_school(current_user, UUID(str(student.school_id)))

    if current_user.role == Role.teacher.value:
        _ensure_teacher_assigned_to_student(db, current_user.id, student_id)

    data = payload.model_dump(exclude_unset=True)

    class_ids = data.pop("class_ids", None)
    class_names = data.pop("classes", None)

    for k, v in data.items():
        setattr(student, k, v)

    if class_ids is not None:
        classes = (
            db.execute(
                select(Class).where(
                    Class.id.in_(class_ids),
                    Class.school_id == student.school_id,
                )
            )
            .scalars()
            .all()
        )

        if len(classes) != len(set(class_ids)):
            raise HTTPException(status_code=400, detail="Some classes not found")

        student.classes = classes

    elif class_names is not None:
        classes = _get_classes_by_names(db, student.school_id, class_names)
        student.classes = classes

    db.commit()

    student = db.execute(
        select(Student)
        .where(Student.id == student.id)
        .options(selectinload(Student.classes))
    ).scalar_one()

    return StudentOutWithClasses(
        id=student.id,
        school_id=student.school_id,
        full_name=student.full_name,
        age=getattr(student, "age", None),
        notes=getattr(student, "notes", None),
        is_active=getattr(student, "is_active", None),
        created_at=getattr(student, "created_at", None),
        classes=[{"id": c.id, "name": c.name} for c in getattr(student, "classes", [])],
    )


@router.post(
    "/bulk/preview",
    response_model=BulkStudentsPreviewResponse,
    dependencies=[Depends(require_role(Role.platform_admin, Role.school_admin))],
)
async def bulk_students_preview(
    file: UploadFile = File(...),
    school_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    raw = await file.read()
    text = raw.decode("utf-8-sig", errors="replace")

    delimiter = _sniff_delimiter(text[:2048])
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    errors: list[BulkRowError] = []
    sample: list[dict] = []
    will_create_classes: set[str] = set()

    total = 0
    valid = 0

    for i, row in enumerate(reader, start=2):
        total += 1

        full_name = (row.get("full_name") or "").strip()
        if not full_name:
            errors.append(
                BulkRowError(row=i, field="full_name", message="full_name is required")
            )
            continue

        try:
            resolved_school_id = _get_school_id_for_row(row, current_user, school_id)
        except Exception as e:
            errors.append(BulkRowError(row=i, field="school_id", message=str(e)))
            continue

        class_names = _parse_classes(row)

        age_raw = (row.get("age") or "").strip()
        if age_raw:
            try:
                age_int = int(age_raw)
                if age_int < 1 or age_int > 120:
                    raise ValueError
            except Exception:
                errors.append(
                    BulkRowError(
                        row=i,
                        field="age",
                        message="age must be an integer between 1 and 120",
                    )
                )
                continue

        for cname in class_names:
            exists = db.execute(
                select(Class.id).where(
                    Class.school_id == resolved_school_id, Class.name == cname
                )
            ).scalar_one_or_none()
            if not exists:
                will_create_classes.add(cname)

        valid += 1
        if len(sample) < 20:
            sample.append(
                {
                    "full_name": full_name,
                    "age": age_raw or None,
                    "group": (row.get("group") or "").strip() or None,
                    "classes": class_names,
                    "notes": (row.get("notes") or "").strip() or None,
                    "school_id": str(resolved_school_id),
                }
            )

    invalid = len(errors)
    return BulkStudentsPreviewResponse(
        total_rows=total,
        valid_rows=valid,
        invalid_rows=invalid,
        will_create_classes=sorted(list(will_create_classes)),
        errors=errors,
        sample=sample,
    )


@router.post(
    "/bulk/apply",
    response_model=BulkStudentsApplyResponse,
    dependencies=[Depends(require_role(Role.platform_admin, Role.school_admin))],
)
async def bulk_students_apply(
    file: UploadFile = File(...),
    school_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    raw = await file.read()
    text = raw.decode("utf-8-sig", errors="replace")

    delimiter = _sniff_delimiter(text[:2048])
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    created_students = 0
    created_classes = 0
    created_links = 0
    skipped_rows = 0

    errors: list[BulkRowError] = []

    try:
        for i, row in enumerate(reader, start=2):
            full_name = (row.get("full_name") or "").strip()
            if not full_name:
                errors.append(
                    BulkRowError(
                        row=i, field="full_name", message="full_name is required"
                    )
                )
                continue

            try:
                resolved_school_id = _get_school_id_for_row(
                    row, current_user, school_id
                )
            except Exception as e:
                errors.append(BulkRowError(row=i, field="school_id", message=str(e)))
                continue

            age_raw = (row.get("age") or "").strip()
            age_val = None
            if age_raw:
                try:
                    age_val = int(age_raw)
                    if age_val < 1 or age_val > 120:
                        raise ValueError
                except Exception:
                    errors.append(
                        BulkRowError(
                            row=i,
                            field="age",
                            message="age must be an integer between 1 and 120",
                        )
                    )
                    continue

            notes = (row.get("notes") or "").strip() or None
            group = (row.get("group") or "").strip() or None
            class_names = _parse_classes(row)

            s = Student(
                school_id=resolved_school_id,
                full_name=full_name,
                age=age_val,
                group=group,
                notes=notes,
            )
            db.add(s)
            db.flush()

            created_students += 1

            for cname in class_names:
                c, was_created = _get_or_create_class(db, resolved_school_id, cname)
                if was_created:
                    created_classes += 1

                exists_link = db.execute(
                    select(StudentClass.id).where(
                        StudentClass.student_id == s.id,
                        StudentClass.class_id == c.id,
                    )
                ).scalar_one_or_none()

                if not exists_link:
                    db.add(StudentClass(student_id=s.id, class_id=c.id))
                    created_links += 1

            if class_names and not group:
                s.group = class_names[0]

        if errors:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "CSV has validation errors. No changes were applied.",
                    "errors": [e.dict() for e in errors[:50]],
                    "errors_count": len(errors),
                },
            )

        db.commit()
        return BulkStudentsApplyResponse(
            created_students=created_students,
            created_classes=created_classes,
            created_student_class_links=created_links,
            skipped_rows=skipped_rows,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{student_id}/classes",
    dependencies=[Depends(require_role(Role.platform_admin, Role.school_admin))],
)
def replace_student_classes(
    student_id: UUID,
    class_ids: list[UUID],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.execute(select(Student).where(Student.id == student_id)).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")

    if current_user.role == "school_admin" and current_user.school_id != s.school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    classes = db.execute(select(Class).where(Class.id.in_(class_ids))).scalars().all()
    if len(classes) != len(set(class_ids)):
        raise HTTPException(status_code=400, detail="Some classes not found")

    if any(c.school_id != s.school_id for c in classes):
        raise HTTPException(
            status_code=400, detail="All classes must belong to student's school"
        )

    db.query(StudentClass).filter(StudentClass.student_id == student_id).delete(
        synchronize_session=False
    )
    for cid in class_ids:
        db.add(StudentClass(student_id=student_id, class_id=cid))

    if classes:
        s.group = classes[0].name
    else:
        s.group = None

    db.commit()
    return {"ok": True}
