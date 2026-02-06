from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.auth.deps import get_current_user, require_role
from app.api.v1.ai_reports import ensure_same_school

from app.modules.ai_fallback_events.models import AIFallbackEvent
from app.modules.ai_fallback_events.schemas import AIFallbackOut, ResolveFallbackRequest

router = APIRouter(prefix="/v1/ai-fallbacks", tags=["ai-fallbacks"])


@router.get("", response_model=list[AIFallbackOut])
def list_fallbacks(
    pending_only: bool = True,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # solo platform_admin ve el panel
    require_role(current_user, ["platform_admin"])

    q = db.query(AIFallbackEvent)

    # si quieres restringir por school_id incluso para platform_admin, quita esto;
    # normalmente platform_admin puede ver todo.
    # Si quieres que platform_admin vea todo, no apliques ensure_same_school aquí.

    if pending_only:
        q = q.filter(AIFallbackEvent.resolved_at.is_(None))

    q = q.order_by(AIFallbackEvent.created_at.desc()).limit(min(limit, 200))
    return q.all()


@router.patch("/{fallback_id}/resolve", response_model=AIFallbackOut)
def resolve_fallback(
    fallback_id: UUID,
    payload: ResolveFallbackRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_role(current_user, ["platform_admin"])

    ev = db.get(AIFallbackEvent, fallback_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Fallback event not found")

    # si quieres aplicar school security incluso al platform_admin, aquí:
    # ensure_same_school(current_user, ev.school_id)

    ev.resolved_at = datetime.utcnow()
    ev.resolved_by_user_id = current_user.id
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev
