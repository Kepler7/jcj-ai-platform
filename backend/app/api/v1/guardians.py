from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.db import get_db
from app.auth.deps import get_current_user, require_role

from app.api.v1.ai_reports import ensure_same_school  # reutilizamos el helper

from app.modules.students.models import Student
from app.modules.guardians.models import Guardian
from app.modules.guardians.schemas import GuardianCreate, GuardianUpdate, GuardianOut
from app.modules.guardians.validators import looks_like_phone_e164
from app.modules.guardians.rules import unset_other_primaries


router = APIRouter(prefix="/v1", tags=["guardians"])


@router.post(
    "/students/{student_id}/guardians",
    response_model=GuardianOut,
    status_code=status.HTTP_201_CREATED,
)
def create_guardian(
    student_id: UUID,
    payload: GuardianCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Solo platform_admin/school_admin pueden crear
    require_role(current_user, ["platform_admin", "school_admin"])

    student = db.get(Student, student_id)
    if not student or not student.is_active:
        raise HTTPException(status_code=404, detail="Student not found")

    ensure_same_school(current_user, student.school_id)

    if not looks_like_phone_e164(payload.whatsapp_phone):
        raise HTTPException(status_code=422, detail="Invalid whatsapp_phone format")

    guardian = Guardian(
        id=uuid.uuid4(),
        student_id=student.id,
        school_id=student.school_id,
        full_name=payload.full_name.strip(),
        whatsapp_phone=payload.whatsapp_phone.strip(),
        relationship=payload.relationship.strip(),
        is_primary=bool(payload.is_primary),
        is_active=True,
        notes=(payload.notes.strip() if payload.notes else None),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(guardian)
    db.flush()  # ya tenemos guardian.id sin commit

    # Regla: solo 1 primary por alumno
    # Si este nuevo guardian es primary, apagamos los demás (excepto este).
    if guardian.is_primary:
        unset_other_primaries(db, student_id=student.id, keep_guardian_id=guardian.id)

    db.commit()
    db.refresh(guardian)
    return guardian


@router.get(
    "/students/{student_id}/guardians",
    response_model=List[GuardianOut],
)
def list_guardians(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # platform_admin / school_admin / teacher pueden ver
    require_role(current_user, ["platform_admin", "school_admin", "teacher"])

    student = db.get(Student, student_id)
    if not student or not student.is_active:
        raise HTTPException(status_code=404, detail="Student not found")

    ensure_same_school(current_user, student.school_id)

    rows = (
        db.execute(
            select(Guardian)
            .where(Guardian.student_id == student.id, Guardian.is_active == True)
            .order_by(Guardian.is_primary.desc(), Guardian.created_at.asc())
        )
        .scalars()
        .all()
    )
    return rows


@router.patch(
    "/guardians/{guardian_id}",
    response_model=GuardianOut,
)
def update_guardian(
    guardian_id: UUID,
    payload: GuardianUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Solo platform_admin/school_admin pueden editar (MVP)
    require_role(current_user, ["platform_admin", "school_admin"])

    guardian = db.get(Guardian, guardian_id)
    if not guardian or not guardian.is_active:
        raise HTTPException(status_code=404, detail="Guardian not found")

    ensure_same_school(current_user, guardian.school_id)

    data = payload.model_dump(exclude_unset=True)

    # Validación phone si viene
    if "whatsapp_phone" in data and data["whatsapp_phone"] is not None:
        phone = data["whatsapp_phone"].strip()
        if not looks_like_phone_e164(phone):
            raise HTTPException(status_code=422, detail="Invalid whatsapp_phone format")
        data["whatsapp_phone"] = phone

    # Normalizar strings
    for k in ["full_name", "relationship", "notes"]:
        if k in data and isinstance(data[k], str):
            data[k] = data[k].strip()

    # Aplicar cambios
    for k, v in data.items():
        setattr(guardian, k, v)

    guardian.updated_at = datetime.utcnow()

    # Regla primary
    if payload.is_primary is True:
        unset_other_primaries(db, student_id=guardian.student_id, keep_guardian_id=guardian.id)
        guardian.is_primary = True

    if payload.is_primary:
        db.query(Guardian).filter(
            Guardian.student_id == guardian.student_id,
            Guardian.is_primary == True,
            Guardian.is_active == True,
            Guardian.id != guardian.id,
        ).update({"is_primary": False})

    # Si lo pusieron false, no forzamos que exista otro primary (MVP)
    db.commit()
    db.refresh(guardian)
    return guardian


@router.delete(
    "/guardians/{guardian_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_guardian_soft(
    guardian_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Solo platform_admin/school_admin pueden borrar (soft)
    require_role(current_user, ["platform_admin", "school_admin"])

    guardian = db.get(Guardian, guardian_id)
    if not guardian or not guardian.is_active:
        raise HTTPException(status_code=404, detail="Guardian not found")

    ensure_same_school(current_user, guardian.school_id)

    guardian.is_active = False
    guardian.is_primary = False
    guardian.updated_at = datetime.utcnow()
    db.commit()
    return None
