from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.auth.deps import get_current_user
from app.auth.deps import require_role
from app.modules.ai_fallback_events.models import AIFallbackEvent  # ajusta path si difiere

router = APIRouter(prefix="/v1/playbook-fallbacks", tags=["playbook-fallbacks"])


@router.get("")
def list_fallbacks(
    status_filter: str = "pending",  # pending | resolved | all
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_role(current_user, ["platform_admin"])

    q = db.query(AIFallbackEvent).order_by(AIFallbackEvent.created_at.desc())

    if status_filter == "pending":
        q = q.filter(AIFallbackEvent.resolved_at.is_(None))
    elif status_filter == "resolved":
        q = q.filter(AIFallbackEvent.resolved_at.is_not(None))
    elif status_filter == "all":
        pass
    else:
        raise HTTPException(status_code=422, detail="Invalid status_filter")

    rows = q.limit(min(max(limit, 1), 500)).all()

    # MVP: devolvemos lo necesario para el panel
    return [
        {
            "id": str(r.id),
            "school_id": str(r.school_id),
            "student_id": str(r.student_id),
            "report_id": str(r.report_id),
            "ai_report_id": str(r.ai_report_id) if r.ai_report_id else None,
            "topic_nucleo": r.topic_nucleo,
            "context": r.context,
            "reason": r.reason,
            "query_text": r.query_text,
            "model_output_summary": r.model_output_summary,
            "created_by_user_id": str(r.created_by_user_id) if r.created_by_user_id else None,
            "created_at": r.created_at.isoformat(),
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        }
        for r in rows
    ]


@router.post("/{event_id}/resolve", status_code=status.HTTP_200_OK)
def resolve_fallback(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_role(current_user, ["platform_admin"])

    ev = db.get(AIFallbackEvent, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Fallback event not found")

    if ev.resolved_at is None:
        ev.resolved_at = datetime.utcnow()
        db.add(ev)
        db.commit()

    return {"ok": True, "id": str(ev.id), "resolved_at": ev.resolved_at.isoformat()}
