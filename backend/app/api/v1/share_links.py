from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

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

router = APIRouter(prefix="/v1/share-links", tags=["share-links"])


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
