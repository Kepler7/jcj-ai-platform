from __future__ import annotations

import os
from sqlalchemy.orm import Session

from app.modules.ai_feedback.models import (
    AIPrediction,
    AIPredictionFeedback,
)
from app.modules.ai_feedback.schemas import (
    AIPredictionCreate,
    AIPredictionFeedbackCreate,
)
from app.modules.ai_reports.models import AIReport
from app.ai.orchestrator import parse_playbook_doc_v2
from app.rag.chroma_client import ChromaPlaybookStore

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "jcj_playbooks_v1")


def _load_playbook_by_id(playbook_id: str):
    """
    Busca un playbook por id recorriendo la colección completa.
    Con el corpus actual esto está bien por ahora.
    """
    store = ChromaPlaybookStore(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
        collection_name=CHROMA_COLLECTION,
    )

    result = (
        store.query(
            query_text="playbook",
            age=None,
            n_results=100,
        )
        or {}
    )

    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    # Chroma viene así:
    # documents = [doc1, doc2, ...]
    # metadatas = [[md1, md2, ...]]
    if metadatas and isinstance(metadatas[0], list):
        metadatas = metadatas[0]

    for i, doc in enumerate(documents):
        md = metadatas[i] if i < len(metadatas) else {}
        md_id = str(md.get("id") or "").strip()

        if md_id == str(playbook_id):
            parsed = parse_playbook_doc_v2(doc)
            if not parsed:
                return None

            # inyectar id/base_row desde metadata
            parsed["id"] = md_id
            parsed["base_row"] = str(
                md.get("base_row") or parsed.get("base_row") or ""
            ).strip()
            return parsed

    return None


def create_ai_prediction(db: Session, data: AIPredictionCreate) -> AIPrediction:
    obj = AIPrediction(
        school_id=data.school_id,
        student_id=data.student_id,
        report_id=data.report_id,
        predicted_playbook_id=data.predicted_playbook_id,
        predicted_playbook_base_row=data.predicted_playbook_base_row,
        status=data.status,
        confidence_score=data.confidence_score,
        confidence_gap=data.confidence_gap,
        top_candidates_json=data.top_candidates_json,
        top_scores_json=data.top_scores_json,
        retrieval_version=data.retrieval_version,
        reranker_version=data.reranker_version,
        used_hyde=data.used_hyde,
        model_name=data.model_name,
        final_playbook_id=data.final_playbook_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def create_ai_prediction_feedback(
    db: Session,
    data: AIPredictionFeedbackCreate,
    reviewed_by_user_id,
):
    obj = AIPredictionFeedback(
        prediction_id=data.prediction_id,
        verdict=data.verdict,
        corrected_playbook_id=data.corrected_playbook_id,
        corrected_playbook_base_row=data.corrected_playbook_base_row,
        note=data.note,
        reviewed_by_user_id=reviewed_by_user_id,
    )
    db.add(obj)

    prediction = db.get(AIPrediction, data.prediction_id)
    if not prediction:
        db.commit()
        db.refresh(obj)
        return obj

    prediction.resolved_by_human = True

    # ----------------------------
    # 1) Resolver playbook final
    # ----------------------------
    final_playbook_id = None

    if data.verdict == "correct":
        final_playbook_id = prediction.predicted_playbook_id

    elif data.verdict == "incorrect":
        final_playbook_id = data.corrected_playbook_id

    elif data.verdict == "none_apply":
        final_playbook_id = None

    if final_playbook_id:
        prediction.final_playbook_id = final_playbook_id
        prediction.status = "confirmed_jcj"
    elif data.verdict == "none_apply":
        prediction.final_playbook_id = None
        prediction.status = "general_fallback"

    # ----------------------------
    # 2) Actualizar AI report si hay playbook final
    # ----------------------------
    if final_playbook_id:
        pb = _load_playbook_by_id(final_playbook_id)

        if pb:
            from app.ai.generate_support_v2 import build_confirmed_response

            # obtener edad desde el prediction/student si la necesitas luego
            # por ahora usamos edad neutra si no está disponible
            student_age = None
            try:
                if prediction.student_id:
                    from app.modules.students.models import Student

                    student = db.get(Student, prediction.student_id)
                    student_age = student.age if student else None
            except Exception:
                student_age = None

            support = build_confirmed_response(
                pb=pb,
                age=student_age or 0,
                prediction_id=prediction.id,
            )

            ai_report = (
                db.query(AIReport)
                .filter(AIReport.report_id == prediction.report_id)
                .order_by(AIReport.created_at.desc())
                .first()
            )

            if ai_report:
                ai_report.teacher_version = support.teacher_version.model_dump()
                ai_report.parent_version = support.parent_version.model_dump()
                ai_report.signals_detected = support.teacher_version.signals_detected
                ai_report.guardrails_notes = "Validado/corregido por revisión humana"
            else:
                # si no existe, aquí luego podemos crear uno nuevo
                pass

    db.commit()
    db.refresh(obj)
    return obj
