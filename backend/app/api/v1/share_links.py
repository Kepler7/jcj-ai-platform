from __future__ import annotations

import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.auth.deps import get_current_user, require_role
from app.api.v1.ai_reports import ensure_same_school

from app.modules.ai_reports.models import AIReport
from app.modules.share_links.models import ShareLink
from app.modules.share_links.schemas import ShareLinkCreate, ShareLinkOut
from app.modules.share_links.tokens import generate_raw_token, sha256_hex
from app.settings import settings
from app.modules.students.models import Student
from app.modules.guardians.models import Guardian

router = APIRouter(prefix="/v1/share-links", tags=["share-links"])

def build_parent_url(raw_token: str) -> str:
    # Ajusta si tu settings se llama distinto
    base = getattr(settings, "PUBLIC_APP_URL", "http://localhost:5173").rstrip("/")
    return f"{base}/p/{raw_token}"

def _create_share_link(
    db: Session,
    *,
    school_id: UUID,
    ai_report_id: UUID,
    guardian_id: UUID | None,
    created_by_user_id: UUID | None,
    expires_in_days: int = 7,
) -> tuple[ShareLink, str]:
    """
    Crea un link nuevo. Devuelve (row, raw_token).
    Guarda SOLO token_hash.
    """
    raw_token = generate_raw_token()
    token_hash = sha256_hex(raw_token)

    link = ShareLink(
        school_id=school_id,
        ai_report_id=ai_report_id,
        guardian_id=guardian_id,
        created_by_user_id=created_by_user_id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
        revoked_at=None,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return link, raw_token

def looks_like_phone_e164(phone: str) -> bool:
    # validación básica MVP (no perfecta)
    p = phone.strip().replace(" ", "")
    if not p.startswith("+"):
        return False
    if len(p) < 8 or len(p) > 20:
        return False
    return p[1:].isdigit()

@router.post("", response_model=ShareLinkOut, status_code=status.HTTP_201_CREATED)
def create_share_link(
    payload: ShareLinkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # quién puede generar links
    require_role(current_user, ["platform_admin", "school_admin", "teacher"])

    ai_report = db.get(AIReport, payload.ai_report_id)
    if not ai_report:
        raise HTTPException(status_code=404, detail="AI report not found")

    # seguridad por escuela (platform_admin bypass)
    ensure_same_school(current_user, ai_report.school_id)

    # generar token crudo + hash
    raw_token = generate_raw_token()
    token_hash = sha256_hex(raw_token)

    expires_at = datetime.utcnow() + timedelta(days=payload.expires_in_days)

    row = ShareLink(
        school_id=ai_report.school_id,
        ai_report_id=ai_report.id,
        guardian_id=payload.guardian_id,
        created_by_user_id=current_user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        revoked_at=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    public_url = f"{settings.PUBLIC_APP_URL.rstrip('/')}/p/{raw_token}"

    return ShareLinkOut(
        id=row.id,
        ai_report_id=row.ai_report_id,
        guardian_id=row.guardian_id,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        url=public_url,
    )

@router.get("/p/{token}")
def get_parent_share(token: str, db: Session = Depends(get_db)):
    token_hash = sha256_hex(token)

    link = db.query(ShareLink).filter(ShareLink.token_hash == token_hash).first()
    if not link:
        raise HTTPException(status_code=404, detail="Invalid link")

    now = datetime.now(timezone.utc)

    if link.revoked_at is not None:
        raise HTTPException(status_code=410, detail="Link revoked")

    if link.expires_at is not None and link.expires_at < now:
        raise HTTPException(status_code=410, detail="Link expired")

    ai = db.get(AIReport, link.ai_report_id)
    if not ai:
        raise HTTPException(status_code=404, detail="AI report not found")

    # Devuelve SOLO lo necesario para UI pública (padres)
    return {
        "ai_report_id": str(ai.id),
        "student_id": str(ai.student_id),
        "report_id": str(ai.report_id),
        "created_at": ai.created_at.isoformat() if ai.created_at else None,
        "parent_version": ai.parent_version,
    }

@router.post("/{ai_report_id}/send-preview", status_code=status.HTTP_200_OK)
def send_preview(
    ai_report_id: UUID,
    guardian_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # solo maestros/admin
    require_role(current_user, ["platform_admin", "school_admin", "teacher"])

    ai = db.get(AIReport, ai_report_id)
    if not ai:
        raise HTTPException(status_code=404, detail="AI report not found")

    ensure_same_school(current_user, ai.school_id)

    guardian = db.get(Guardian, guardian_id)
    if not guardian or not guardian.is_active:
        raise HTTPException(status_code=404, detail="Guardian not found")

    if guardian.student_id != ai.student_id:
        raise HTTPException(status_code=422, detail="Guardian does not belong to this student")

    # Checks legales / preferencias
    if not getattr(guardian, "consent_to_contact", False):
        raise HTTPException(status_code=422, detail="Guardian has no consent_to_contact")

    if not getattr(guardian, "receive_whatsapp", True):
        raise HTTPException(status_code=422, detail="Guardian opted out of WhatsApp")

    if not guardian.whatsapp_phone:
        raise HTTPException(status_code=422, detail="Guardian has no whatsapp_phone")

    phone_clean = guardian.whatsapp_phone.strip().replace(" ", "")
    if not looks_like_phone_e164(phone_clean):
        raise HTTPException(status_code=422, detail="Invalid whatsapp_phone format")

    # ============================================================
    # MVP: SIEMPRE crear un link nuevo (porque solo guardamos hash).
    # en el futuro crear ligica para borrar links viejos
    # ============================================================
    raw_token = generate_raw_token()
    token_hash = sha256_hex(raw_token)

    expires_at = datetime.utcnow() + timedelta(days=7)

    link = ShareLink(
        id=uuid.uuid4(),
        school_id=ai.school_id,  # IMPORTANTÍSIMO para evitar NotNullViolation
        ai_report_id=ai.id,
        guardian_id=guardian.id,
        created_by_user_id=current_user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        revoked_at=None,
        created_at=datetime.utcnow(),
        last_accessed_at=None,
    )

    db.add(link)
    db.commit()

    parent_url = build_parent_url(raw_token)

    student = db.get(Student, ai.student_id)
    student_name = (student.full_name if student and getattr(student, "full_name", None) else "tu hijo/a")

    # Mensaje MVP: corto, educacional, sin lenguaje clínico
    msg = (
        f"Hola {guardian.full_name}.\n\n"
        f"Te comparto el apoyo para casa de {student_name}.\n"
        f"Abre aquí (link seguro): {parent_url}\n\n"
        f"Si tienes dudas, me dices y lo revisamos juntos."
    )

    text = urllib.parse.quote(msg)
    wa_url = f"https://wa.me/{phone_clean.lstrip('+')}?text={text}"

    return {
        "share_link_id": str(link.id),
        "expires_at": expires_at.isoformat() + "Z",
        "wa_url": wa_url,
    }

