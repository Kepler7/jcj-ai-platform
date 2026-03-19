import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from uuid import UUID

from app.db.db import get_db

from app.modules.students.schemas import StudentCreate, StudentUpdate, StudentOut

from app.auth.deps import get_current_user, require_role
from app.auth.roles import Role
from app.modules.users.models import User

from app.modules.classes.models import Class, StudentClass
from app.modules.students.models import Student
from app.modules.users.models import User
from app.modules.students.bulk_schemas import (
    BulkStudentsPreviewResponse,
    BulkStudentsApplyResponse,
    BulkRowError,
)

from app.modules.students.schemas import StudentOutWithClasses

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
    current_user: User = Depends(
        require_role(Role.platform_admin, Role.school_admin, Role.teacher)
    ),
):
    ensure_same_school(current_user, payload.school_id)

    student = Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get(
    "",
    response_model=list[StudentOutWithClasses],
    dependencies=[
        Depends(require_role(Role.platform_admin, Role.school_admin, Role.teacher))
    ],
)
def list_students_with_classes(
    school_id: UUID,  # query param obligatorio: /v1/students?school_id=...
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role in ("school_admin", "teacher"):
        if current_user.school_id != school_id:
            raise HTTPException(status_code=403, detail="Forbidden")

    stmt = (
        select(Student)
        .where(Student.school_id == school_id)
        .options(selectinload(Student.classes))
        .order_by(Student.full_name.asc())
    )
    students = list(db.execute(stmt).scalars().all())

    return [
        StudentOutWithClasses(
            id=s.id,
            school_id=s.school_id,
            full_name=s.full_name,
            age=getattr(s, "age", None),
            notes=getattr(s, "notes", None),
            is_active=getattr(s, "is_active", None),
            created_at=getattr(s, "created_at", None),
            classes=[{"id": c.id, "name": c.name} for c in getattr(s, "classes", [])],
        )
        for s in students
    ]


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
    # Carga student + clases en 2 queries (selectinload) sin recursion
    stmt = (
        select(Student)
        .where(Student.id == student_id)
        .options(selectinload(Student.classes))  # requiere relationship Student.classes
    )
    s = db.execute(stmt).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")

    # school_admin/teacher solo su escuela
    if current_user.role in ("school_admin", "teacher"):
        if current_user.school_id != s.school_id:
            raise HTTPException(status_code=403, detail="Forbidden")

    # Construcción explícita (evita loops y controla payload)
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


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: UUID,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(Role.platform_admin, Role.school_admin, Role.teacher)
    ),
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

    # delimiter
    delimiter = _sniff_delimiter(text[:2048])
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    required = {"full_name"}
    errors: list[BulkRowError] = []
    sample: list[dict] = []
    will_create_classes: set[str] = set()

    total = 0
    valid = 0

    for i, row in enumerate(reader, start=2):  # header is row 1
        total += 1

        full_name = (row.get("full_name") or "").strip()
        if not full_name:
            errors.append(
                BulkRowError(row=i, field="full_name", message="full_name is required")
            )
            continue

        # school_id resolution
        try:
            resolved_school_id = _get_school_id_for_row(row, current_user, school_id)
        except Exception as e:
            errors.append(BulkRowError(row=i, field="school_id", message=str(e)))
            continue

        # parse classes list (optional)
        class_names = _parse_classes(row)

        # validate age if present
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

        # Check which classes would be created (preview only; do NOT create)
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

            # Create student
            s = Student(
                school_id=resolved_school_id,
                full_name=full_name,
                age=age_val,
                group=group,
                notes=notes,
            )
            db.add(s)
            db.flush()  # gets s.id

            created_students += 1

            # Create classes + pivot links
            for cname in class_names:
                c, was_created = _get_or_create_class(db, resolved_school_id, cname)
                if was_created:
                    created_classes += 1

                # avoid duplicates
                exists_link = db.execute(
                    select(StudentClass.id).where(
                        StudentClass.student_id == s.id,
                        StudentClass.class_id == c.id,
                    )
                ).scalar_one_or_none()

                if not exists_link:
                    db.add(StudentClass(student_id=s.id, class_id=c.id))
                    created_links += 1

        # If any row errors, stop and rollback (safer)
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

    # validar que todas las class_ids pertenezcan a la misma school del student
    from app.modules.classes.models import Class

    classes = db.execute(select(Class).where(Class.id.in_(class_ids))).scalars().all()
    if len(classes) != len(set(class_ids)):
        raise HTTPException(status_code=400, detail="Some classes not found")

    if any(c.school_id != s.school_id for c in classes):
        raise HTTPException(
            status_code=400, detail="All classes must belong to student's school"
        )

    # reemplazo
    db.query(StudentClass).filter(StudentClass.student_id == student_id).delete(
        synchronize_session=False
    )
    for cid in class_ids:
        db.add(StudentClass(student_id=student_id, class_id=cid))

    db.commit()
    return {"ok": True}
