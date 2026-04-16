from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.modules.ai_reports.models import AIReport
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List, Optional, Dict

from app.db.db import get_db
from app.auth.deps import get_current_user, require_role
from app.api.v1.ai_reports import ensure_same_school

from app.modules.ai_fallback_events.models import AIFallbackEvent
from app.modules.ai_fallback_events.schemas import AIFallbackOut, ResolveFallbackRequest
from app.ai.utils.normalization import normalize_topic_nucleo

router = APIRouter(prefix="/v1/ai-fallbacks", tags=["ai-fallbacks"])


def _extract_signals_from_ai(ai: Optional[AIReport]) -> List[str]:
    if not ai:
        return []

    def _get(obj: Any, path: str) -> Any:
        cur = obj
        for p in path.split("."):
            if cur is None:
                return None
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                cur = getattr(cur, p, None)
        return cur

    # teacher_version.signals_detected o parent_version.signals_detected
    sigs = _get(ai, "teacher_version.signals_detected")
    if not sigs:
        sigs = _get(ai, "parent_version.signals_detected")

    if isinstance(sigs, list):
        out = []
        seen = set()
        for s in sigs:
            ss = str(s).strip() if s is not None else ""
            key = ss.lower()
            if ss and key not in seen:
                seen.add(key)
                out.append(ss)
        return out[:10]
    return []


def _extract_topic_from_ai(ai: Optional[AIReport]) -> Optional[List[str]]:
    """
    Si el evento no trae topic_nucleo, lo derivamos de la primera microintervención.
    Ojo: esto solo existirá cuando fallback_used=False y tu orchestrator construyó microintervenciones desde playbook.
    """
    if not ai:
        return None

    def _get(obj: Any, path: str) -> Any:
        cur = obj
        for p in path.split("."):
            if cur is None:
                return None
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                cur = getattr(cur, p, None)
        return cur

    mi = _get(ai, "teacher_version.microintervenciones")
    if not mi:
        mi = _get(ai, "parent_version.microintervenciones")

    if isinstance(mi, list) and len(mi) > 0:
        first = mi[0]
        if isinstance(first, dict):
            t = normalize_topic_nucleo(first.get("topic_nucleo"))
        else:
            t = normalize_topic_nucleo(getattr(first, "topic_nucleo", None))
        return t or None

    return None


@router.get("", response_model=list[AIFallbackOut])
def list_fallbacks(
    pending_only: bool = True,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_role(current_user, ["platform_admin"])

    q = db.query(AIFallbackEvent)

    if pending_only:
        q = q.filter(AIFallbackEvent.resolved_at.is_(None))

    events: List[AIFallbackEvent] = (
        q.order_by(AIFallbackEvent.created_at.desc()).limit(min(limit, 200)).all()
    )

    # ✅ Prefetch AI reports (evita N+1)
    ai_ids = [e.ai_report_id for e in events if getattr(e, "ai_report_id", None)]
    ai_by_id: Dict[Any, AIReport] = {}
    if ai_ids:
        ais = db.query(AIReport).filter(AIReport.id.in_(ai_ids)).all()
        ai_by_id = {a.id: a for a in ais}

    out: List[AIFallbackOut] = []
    for e in events:
        ai = ai_by_id.get(getattr(e, "ai_report_id", None))

        signals = _extract_signals_from_ai(ai)

        topic = normalize_topic_nucleo(getattr(e, "topic_nucleo", None))
        if not topic:
            topic = _extract_topic_from_ai(ai)

        # construimos el schema manual para meter campos extra
        out.append(
            AIFallbackOut(
                id=e.id,
                school_id=e.school_id,
                student_id=e.student_id,
                report_id=e.report_id,
                ai_report_id=getattr(e, "ai_report_id", None),
                topic_nucleo=topic,
                reason=e.reason,
                query_text=e.query_text,
                model_output_summary=e.model_output_summary,
                created_by_user_id=getattr(e, "created_by_user_id", None),
                created_at=e.created_at,
                resolved_at=e.resolved_at,
                signals_detected=signals,
            )
        )

    return out


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
