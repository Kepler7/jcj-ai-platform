from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_db, get_current_user, require_role
from app.ai.orchestrator import parse_playbook_doc_v2
from app.modules.ai_feedback.models import AIPrediction, AIPredictionStatus
from app.modules.ai_feedback.schemas import (
    AIPredictionFeedbackCreate,
    AIPredictionFeedbackOut,
    AIPredictionOut,
    PlaybookPreviewOut,
)
from app.modules.ai_feedback.service import create_ai_prediction_feedback
from app.rag.chroma_client import ChromaPlaybookStore
from app.ai.utils.normalization import normalize_topic_nucleo

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "jcj_playbooks_v1")

router = APIRouter(prefix="/v1/ai-feedback", tags=["ai-feedback"])


@router.post("", response_model=AIPredictionFeedbackOut)
def submit_ai_feedback(
    payload: AIPredictionFeedbackCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_role(current_user, ["platform_admin", "school_admin", "teacher"])
    return create_ai_prediction_feedback(
        db=db,
        data=payload,
        reviewed_by_user_id=current_user.id,
    )


def _load_all_playbooks_index() -> dict[str, dict]:
    store = ChromaPlaybookStore(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
        collection_name=CHROMA_COLLECTION,
    )

    result = (
        store.query(
            query_text="playbook",
            age=None,
            n_results=200,
        )
        or {}
    )

    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    if metadatas and isinstance(metadatas[0], list):
        metadatas = metadatas[0]

    index: dict[str, dict] = {}

    for i, doc in enumerate(documents):
        md = metadatas[i] if i < len(metadatas) else {}
        pb_id = str(md.get("id") or "").strip()
        if not pb_id:
            continue

        parsed = parse_playbook_doc_v2(doc)
        if not parsed:
            continue

        parsed["id"] = pb_id
        parsed["base_row"] = str(
            md.get("base_row") or parsed.get("base_row") or ""
        ).strip()

        index[pb_id] = parsed

    return index


def _to_preview(pb: Optional[dict]) -> Optional[PlaybookPreviewOut]:
    if not pb:
        return None

    return PlaybookPreviewOut(
        id=str(pb.get("id") or ""),
        topic_nucleo=normalize_topic_nucleo(pb.get("topic_nucleo")) or None,
        subhabilidad=(pb.get("subhabilidad") or None),
        senal_observable=(pb.get("senal_observable") or None),
        age_min=pb.get("age_min"),
        age_max=pb.get("age_max"),
    )


@router.get("/pending", response_model=list[AIPredictionOut])
def list_pending_ai_feedback(
    limit: int = Query(default=100, ge=1, le=500),
    school_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_role(current_user, ["platform_admin", "school_admin", "teacher"])

    q = db.query(AIPrediction).filter(
        AIPrediction.status == AIPredictionStatus.pending_human_review
    )

    if school_id:
        q = q.filter(AIPrediction.school_id == school_id)

    rows = q.order_by(AIPrediction.created_at.desc()).limit(limit).all()

    playbook_index = _load_all_playbooks_index()

    out: list[AIPredictionOut] = []

    for row in rows:
        predicted_preview = _to_preview(
            playbook_index.get(str(row.predicted_playbook_id or ""))
        )

        top_candidates_preview = []
        for candidate_id in row.top_candidates_json or []:
            pb = playbook_index.get(str(candidate_id or ""))
            preview = _to_preview(pb)
            if preview:
                top_candidates_preview.append(preview)

        out.append(
            AIPredictionOut(
                id=row.id,
                report_id=row.report_id,
                predicted_playbook_id=row.predicted_playbook_id,
                predicted_playbook_base_row=row.predicted_playbook_base_row,
                status=row.status,
                confidence_score=row.confidence_score,
                confidence_gap=row.confidence_gap,
                top_candidates_json=row.top_candidates_json,
                top_scores_json=row.top_scores_json,
                retrieval_version=row.retrieval_version,
                reranker_version=row.reranker_version,
                used_hyde=row.used_hyde,
                model_name=row.model_name,
                resolved_by_human=row.resolved_by_human,
                final_playbook_id=row.final_playbook_id,
                created_at=row.created_at,
                predicted_playbook_preview=predicted_preview,
                top_candidates_preview=top_candidates_preview,
            )
        )

    return out
