from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.db import get_db
from app.modules.ai_reports.models import AIReport
from app.modules.ihui_3.schemas import (
    IHUI3LatestSyncResponse,
    IHUI3SyncResponse,
    IHUI3ValidationAnswersRequest,
    IHUI3ValidationAnswersResponse,
)
from app.modules.ai_reports.wizard import score_wizard_answers
from app.auth.deps import require_role
from app.auth.roles import Role
from app.auth.deps import get_current_user

from app.modules.ihui_3.sync_service import (
    IHUI3SyncError,
    read_latest_sync_status,
    sync_ihui3_knowledge,
)

router = APIRouter(prefix="/v1/ihui3", tags=["ihui3"])


def _normalize_question(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _validate_answers_match_questions(
    *,
    expected_questions: list[dict],
    answers: list[dict],
) -> None:
    expected = {
        _normalize_question(item.get("question", ""))
        for item in expected_questions
        if item.get("question")
    }

    received = {
        _normalize_question(item.get("question", ""))
        for item in answers
        if item.get("question")
    }

    missing = expected - received
    unknown = received - expected

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing validation answers for required questions.",
                "missing_questions": sorted(missing),
            },
        )

    if unknown:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Some answers do not match this AI report's validation questions.",
                "unknown_questions": sorted(unknown),
            },
        )


def _answers_to_text(answers: list[dict]) -> str:
    """
    Convierte respuestas del wizard en texto para re-evaluar el caso.
    """
    parts: list[str] = []

    for item in answers:
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()

        if question or answer:
            parts.append(f"Pregunta: {question}\nRespuesta: {answer}")

    return "\n\n".join(parts)


def _strategy_from_match_item(match_item) -> dict:
    """
    Construye estrategia desde la fila IHUI 3.0 seleccionada.
    """
    return {
        "micro_objective": match_item.micro_objective,
        "steps": match_item.strategy_steps,
        "frequency": match_item.frequency,
        "duration": match_item.duration,
        "progress_indicator": match_item.progress_indicator,
        "escalation": match_item.escalation,
        "status": "validated",
    }


def _strategy_from_wizard_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """
    Construye estrategia desde un candidato guardado en ai_metadata.

    Ya no necesitamos volver a cargar el spreadsheet ni correr el matcher.
    Usamos la estrategia que quedó congelada cuando se generó el AI report.
    """
    teacher_steps = candidate.get("strategy_steps") or []
    family_steps = candidate.get("family_strategy_steps") or teacher_steps

    return {
        "micro_objective": candidate.get("micro_objective"),
        "steps": teacher_steps,
        "family_steps": family_steps,
        "frequency": candidate.get("frequency"),
        "duration": candidate.get("duration"),
        "progress_indicator": candidate.get("progress_indicator"),
        "escalation": candidate.get("escalation"),
        "status": "validated",
    }


def _find_candidate_by_playbook_id(
    candidates: list[dict[str, Any]],
    playbook_id: str | None,
) -> dict[str, Any] | None:
    """
    Busca un candidato dentro de ihui3_wizard_candidates.
    """
    if not playbook_id:
        return None

    for candidate in candidates:
        if str(candidate.get("playbook_id")) == str(playbook_id):
            return candidate

    return None


def _combined_strategy_from_candidates(
    candidates: list[dict[str, Any]],
    playbook_ids: list[str],
) -> dict[str, Any]:
    """
    Combina estrategias solo de candidatos permitidos.

    Importante:
    - No inventa pasos.
    - Solo concatena pasos existentes de los playbooks empatados.
    - Mantiene separados los pasos para maestro y familia.
    """
    selected_candidates = [
        candidate
        for candidate in candidates
        if str(candidate.get("playbook_id")) in {str(item) for item in playbook_ids}
    ]

    teacher_steps: list[str] = []
    family_steps: list[str] = []

    for candidate in selected_candidates:
        candidate_teacher_steps = candidate.get("strategy_steps") or []
        candidate_family_steps = (
            candidate.get("family_strategy_steps") or candidate_teacher_steps
        )

        for step in candidate_teacher_steps:
            clean_step = str(step).strip()
            if clean_step and clean_step not in teacher_steps:
                teacher_steps.append(clean_step)

        for step in candidate_family_steps:
            clean_step = str(step).strip()
            if clean_step and clean_step not in family_steps:
                family_steps.append(clean_step)

    return {
        "micro_objective": "Estrategia combinada por empate dentro del mismo núcleo.",
        "steps": teacher_steps,
        "family_steps": family_steps,
        "frequency": (
            selected_candidates[0].get("frequency") if selected_candidates else None
        ),
        "duration": (
            selected_candidates[0].get("duration") if selected_candidates else None
        ),
        "progress_indicator": (
            selected_candidates[0].get("progress_indicator")
            if selected_candidates
            else None
        ),
        "escalation": (
            selected_candidates[0].get("escalation") if selected_candidates else None
        ),
        "status": "validated_combined",
    }


def _hypotheses_from_match_item(match_item, score: float, reason: str) -> list[dict]:
    """
    Construye hipótesis funcionales después de validar respuestas.
    """
    hypotheses: list[dict] = []

    for index, hypothesis in enumerate(match_item.functional_hypotheses):
        clean_hypothesis = str(hypothesis).strip()
        if not clean_hypothesis:
            continue

        hypotheses.append(
            {
                "name": clean_hypothesis,
                "confidence": "high" if index == 0 and score >= 0.75 else "medium",
                "reasoning": (
                    reason
                    if index == 0
                    else "Se mantiene como hipótesis alternativa después de revisar las respuestas."
                ),
            }
        )

    return hypotheses


@router.post(
    "/reports/{ai_report_id}/validation-answers",
    response_model=IHUI3ValidationAnswersResponse,
)
def submit_validation_answers(
    ai_report_id: UUID,
    payload: IHUI3ValidationAnswersRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IHUI3ValidationAnswersResponse:
    # 1) Roles permitidos
    require_role(current_user, ["platform_admin", "school_admin", "teacher"])

    ai_report = db.get(AIReport, ai_report_id)

    if not ai_report:
        raise HTTPException(status_code=404, detail="AI report not found")

    if ai_report.engine_version != "ihui_3":
        raise HTTPException(
            status_code=400,
            detail="This AI report was not generated with IHUI 3.0",
        )

    metadata = dict(ai_report.ai_metadata or {})

    answers = [answer.model_dump() for answer in payload.answers]

    if not answers:
        raise HTTPException(
            status_code=400,
            detail="At least one validation answer is required",
        )

    wizard_candidates = metadata.get("ihui3_wizard_candidates") or []
    wizard_questions = metadata.get("ihui3_wizard_questions") or []

    if not wizard_candidates:
        raise HTTPException(
            status_code=400,
            detail="This AI report does not have wizard candidates to score.",
        )

    if not wizard_questions:
        raise HTTPException(
            status_code=400,
            detail="This AI report does not have wizard questions to validate.",
        )

    # Guardamos las respuestas originales para auditoría.
    metadata["ihui3_validation_answers"] = answers

    # Score determinístico:
    # yes = 2, sometimes = 1, no = 0
    wizard_result = score_wizard_answers(
        candidates=wizard_candidates,
        answers=answers,
    )

    wizard_metadata = wizard_result["wizard"]

    metadata["wizard_required"] = False
    metadata["wizard"] = {
        **metadata.get("wizard", {}),
        **wizard_metadata,
        "required": False,
    }
    metadata["ihui3_wizard_result"] = {
        **wizard_metadata,
        "required": False,
    }

    decision = wizard_metadata.get("decision")
    selected_playbook_id = wizard_metadata.get("selected_playbook_id")
    combined_playbook_ids = wizard_metadata.get("combined_playbook_ids") or []

    if decision in {"selected", "selected_low_confidence"}:
        selected_candidate = _find_candidate_by_playbook_id(
            candidates=wizard_candidates,
            playbook_id=selected_playbook_id,
        )

        if not selected_candidate:
            raise HTTPException(
                status_code=400,
                detail="Selected wizard candidate was not found in metadata.",
            )

        metadata["fallback_used"] = False
        metadata["fallback_reason"] = None
        metadata["review_status"] = "validated"
        metadata["validation_status"] = "validated"
        metadata["review_reason"] = None
        metadata["confidence_after_validation"] = wizard_metadata.get(
            "confidence_after_validation"
        )

        metadata["topic_nucleo"] = [
            selected_candidate.get("nucleus"),
            selected_candidate.get("subskill"),
        ]

        metadata["ihui3_match"] = {
            "playbook_id": selected_candidate.get("playbook_id"),
            "nucleus": selected_candidate.get("nucleus"),
            "subskill": selected_candidate.get("subskill"),
            "score": selected_candidate.get("score"),
            "matched_terms": selected_candidate.get("matched_terms") or [],
            "reason": wizard_metadata.get("decision_reason"),
            "source": "wizard_scoring",
        }

        metadata["ihui3_strategy"] = _strategy_from_wizard_candidate(selected_candidate)

        metadata["validation_result"] = {
            "status": decision,
            "message": (
                "Las respuestas fueron guardadas y el wizard seleccionó "
                "la estrategia con base en scoring cerrado."
            ),
        }

        ai_report.validation_status = "validated"

    elif decision == "combined_same_nucleus":
        metadata["fallback_used"] = False
        metadata["fallback_reason"] = None
        metadata["review_status"] = "validated"
        metadata["validation_status"] = "validated_combined"
        metadata["review_reason"] = None
        metadata["confidence_after_validation"] = wizard_metadata.get(
            "confidence_after_validation"
        )

        combined_candidates = [
            candidate
            for candidate in wizard_candidates
            if str(candidate.get("playbook_id"))
            in {str(item) for item in combined_playbook_ids}
        ]

        metadata["topic_nucleo"] = [
            combined_candidates[0].get("nucleus") if combined_candidates else None,
            "combined_same_nucleus",
        ]

        metadata["ihui3_match"] = {
            "playbook_id": None,
            "combined_playbook_ids": combined_playbook_ids,
            "nucleus": (
                combined_candidates[0].get("nucleus") if combined_candidates else None
            ),
            "subskill": "combined_same_nucleus",
            "score": None,
            "matched_terms": [],
            "reason": wizard_metadata.get("decision_reason"),
            "source": "wizard_scoring",
        }

        metadata["ihui3_strategy"] = _combined_strategy_from_candidates(
            candidates=wizard_candidates,
            playbook_ids=combined_playbook_ids,
        )

        metadata["validation_result"] = {
            "status": "validated_combined",
            "message": (
                "Las respuestas empataron entre estrategias del mismo núcleo. "
                "IHUI combinó únicamente pasos existentes de los playbooks candidatos."
            ),
        }

        ai_report.validation_status = "validated_combined"

    else:
        metadata["fallback_used"] = True
        metadata["fallback_reason"] = "ihui3_wizard_unresolved"
        metadata["review_status"] = "pending_human_review"
        metadata["validation_status"] = "pending_human_review"
        metadata["review_reason"] = wizard_metadata.get("decision_reason")
        metadata["confidence_after_validation"] = wizard_metadata.get(
            "confidence_after_validation"
        )

        metadata["ihui3_match"] = {
            "playbook_id": None,
            "combined_playbook_ids": combined_playbook_ids,
            "nucleus": None,
            "subskill": None,
            "score": None,
            "matched_terms": [],
            "reason": wizard_metadata.get("decision_reason"),
            "source": "wizard_scoring",
        }

        metadata["ihui3_strategy"] = {
            "micro_objective": None,
            "steps": [],
            "frequency": None,
            "duration": None,
            "progress_indicator": None,
            "escalation": None,
            "status": "pending_human_review",
        }

        metadata["model_output_summary"] = (
            "IHUI revisó las respuestas, pero las hipótesis siguen siendo ambiguas. "
            "Se recomienda validación humana para elegir una estrategia segura."
        )

        metadata["validation_result"] = {
            "status": "pending_human_review",
            "message": (
                "Las respuestas fueron guardadas, pero el wizard no encontró "
                "una diferencia suficiente entre candidatos."
            ),
        }

        ai_report.validation_status = "pending_human_review"

    ai_report.ai_metadata = metadata

    # Importante:
    # SQLAlchemy no siempre detecta cambios internos en JSONB.
    flag_modified(ai_report, "ai_metadata")

    db.add(ai_report)
    db.commit()
    db.refresh(ai_report)

    return IHUI3ValidationAnswersResponse(
        ai_report_id=str(ai_report.id),
        validation_status=ai_report.validation_status or "validated",
        wizard_required=False,
        message="Validation answers saved successfully.",
    )


@router.post("/sync", response_model=IHUI3SyncResponse)
def sync_ihui3_sheet(
    current_user=Depends(get_current_user),
) -> IHUI3SyncResponse:
    # 1) Roles permitidos
    require_role(current_user, ["platform_admin", "school_admin", "teacher"])
    try:
        result = sync_ihui3_knowledge()
    except IHUI3SyncError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return IHUI3SyncResponse(
        status=result.get("status", "finished"),
        source=result.get("source"),
        output=result.get("output"),
        items_count=int(result.get("items_count") or 0),
        dictionary_items_count=int(result.get("dictionary_items_count") or 0),
        dictionary_output=result.get("dictionary_output"),
        started_at=result.get("started_at"),
        finished_at=result.get("finished_at"),
        error=result.get("error"),
    )


@router.get("/sync/latest", response_model=IHUI3LatestSyncResponse)
def get_latest_ihui3_sync(
    current_user=Depends(get_current_user),
) -> IHUI3LatestSyncResponse:
    # 1) Roles permitidos
    require_role(current_user, ["platform_admin", "school_admin", "teacher"])
    result = read_latest_sync_status()

    if result is None:
        return IHUI3LatestSyncResponse(
            status="not_started",
            items_count=0,
        )

    return IHUI3LatestSyncResponse(
        status=result.get("status", "unknown"),
        source=result.get("source"),
        output=result.get("output"),
        items_count=int(result.get("items_count") or 0),
        dictionary_items_count=int(result.get("dictionary_items_count") or 0),
        dictionary_output=result.get("dictionary_output"),
        started_at=result.get("started_at"),
        finished_at=result.get("finished_at"),
        error=result.get("error"),
    )


@router.get("/reports/{ai_report_id}/wizard")
def get_ihui3_wizard(
    ai_report_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    # 1) Roles permitidos
    require_role(current_user, ["platform_admin", "school_admin", "teacher"])
    ai_report = db.get(AIReport, ai_report_id)

    if not ai_report:
        raise HTTPException(status_code=404, detail="AI report not found")

    if ai_report.engine_version != "ihui_3":
        raise HTTPException(
            status_code=400,
            detail="This AI report was not generated with IHUI 3.0",
        )

    metadata = ai_report.ai_metadata or {}

    return {
        "ai_report_id": str(ai_report.id),
        "report_id": str(ai_report.report_id),
        "student_id": str(ai_report.student_id),
        "school_id": str(ai_report.school_id),
        "engine_version": ai_report.engine_version,
        "validation_status": ai_report.validation_status,
        "wizard_required": bool(metadata.get("wizard_required")),
        "questions": (
            metadata.get("ihui3_wizard_questions")
            or metadata.get("ihui3_validation_questions")
            or []
        ),
        "wizard": metadata.get("wizard") or {},
        "wizard_candidates": metadata.get("ihui3_wizard_candidates") or [],
        "wizard_result": metadata.get("ihui3_wizard_result"),
        "hypotheses": metadata.get("ihui3_hypotheses") or [],
        "strategy": metadata.get("ihui3_strategy") or {},
        "match": metadata.get("ihui3_match"),
        "fallback_used": bool(metadata.get("fallback_used")),
        "fallback_reason": metadata.get("fallback_reason"),
        "review_status": metadata.get("review_status"),
        "validation_result": metadata.get("validation_result"),
        "answers": metadata.get("ihui3_validation_answers") or [],
    }
