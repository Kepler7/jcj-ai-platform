from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.settings import settings
from app.modules.ihui_3.knowledge_loader import (
    IHUI3KnowledgeLoadError,
    load_ihui3_knowledge,
)
from app.modules.ihui_3.matcher import find_top_matches
from app.modules.ai_reports.wizard import select_wizard_questions
from app.modules.ihui_3.dictionary_loader import load_ihui3_dictionary


class IHUI3Microintervention(BaseModel):
    title: str
    objective: str
    steps: List[str] = Field(default_factory=list)
    frequency: str = ""
    duration: str = ""
    progress_indicator: str = ""
    escalation: str | None = None
    status: str = "requires_validation"


class IHUI3TeacherOutput(BaseModel):
    summary: str
    signals_detected: List[str] = Field(default_factory=list)
    microintervenciones: List[IHUI3Microintervention] = Field(default_factory=list)


class IHUI3ParentOutput(BaseModel):
    summary: str
    signals_detected: List[str] = Field(default_factory=list)
    microintervenciones: List[IHUI3Microintervention] = Field(default_factory=list)


class IHUI3SupportOutput(BaseModel):
    teacher_version: IHUI3TeacherOutput
    parent_version: IHUI3ParentOutput


def _confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _build_validation_questions(match_item) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []

    for question in match_item.validation_questions:
        clean_question = str(question).strip()
        if not clean_question:
            continue

        questions.append(
            {
                "question": clean_question,
                "why_it_matters": (
                    "Esta respuesta ayuda a elegir mejor la hipótesis funcional "
                    "y ajustar la estrategia al caso real."
                ),
            }
        )

    return questions


def _build_wizard_candidates(match_results) -> list[dict[str, Any]]:
    """
    Converts IHUI3MatchResult objects into the normalized candidate format
    expected by the wizard helper.
    """

    candidates: list[dict[str, Any]] = []

    for result in match_results:
        item = result.knowledge_item

        playbook_id = (
            getattr(item, "row_id", None)
            or getattr(item, "id", None)
            or getattr(item, "playbook_id", None)
            or f"{item.nucleus}:{item.subskill}"
        )

        candidates.append(
            {
                "playbook_id": str(playbook_id),
                "nucleus": item.nucleus,
                "subskill": item.subskill,
                "score": result.score,
                "matched_terms": result.matched_terms,
                "reason": result.reason,
                "validation_questions": [
                    question
                    for question in item.validation_questions
                    if question and question.strip()
                ],
                "micro_objective": item.micro_objective,
                "strategy_steps": item.strategy_steps,
                "family_strategy_steps": item.family_strategy_steps,
                "frequency": item.frequency,
                "duration": item.duration,
                "progress_indicator": item.progress_indicator,
                "escalation": item.escalation,
            }
        )

    return candidates


def _build_hypotheses(
    match_item, score: float, match_reason: str
) -> list[dict[str, str]]:
    confidence = _confidence_label(score)
    hypotheses: list[dict[str, str]] = []

    for index, hypothesis in enumerate(match_item.functional_hypotheses):
        clean_hypothesis = str(hypothesis).strip()
        if not clean_hypothesis:
            continue

        hypotheses.append(
            {
                "name": clean_hypothesis,
                "confidence": confidence if index == 0 else "low",
                "reasoning": (
                    match_reason
                    if index == 0
                    else "Es una hipótesis alternativa que debe validarse con las preguntas."
                ),
            }
        )

    return hypotheses


def _build_microintervention(
    match_item,
    *,
    steps: list[str] | None = None,
) -> IHUI3Microintervention:
    return IHUI3Microintervention(
        title=match_item.micro_objective or "Estrategia sugerida por IHUI 3.0",
        objective=match_item.micro_objective or "",
        steps=steps if steps is not None else match_item.strategy_steps,
        frequency=match_item.frequency,
        duration=match_item.duration,
        progress_indicator=match_item.progress_indicator,
        escalation=match_item.escalation or None,
        status="requires_validation",
    )


def _build_fallback_support(report_text: str) -> IHUI3SupportOutput:
    """
    Fallback IHUI 3.0 cuando no hay match confiable o no hay preguntas.

    Esto produce el estado parecido al screenshot:
    validación en progreso + humano/WhatsApp.
    """
    message = (
        "IHUI detectó que este caso necesita validación humana para darte una "
        "estrategia clara, segura y útil. Escríbenos por WhatsApp y lo revisamos "
        "contigo."
    )

    detected = (
        [report_text] if report_text and report_text != "Sin observaciones." else []
    )

    return IHUI3SupportOutput(
        teacher_version=IHUI3TeacherOutput(
            summary=message,
            signals_detected=detected,
            microintervenciones=[],
        ),
        parent_version=IHUI3ParentOutput(
            summary=message,
            signals_detected=detected,
            microintervenciones=[],
        ),
    )


def _build_matched_support(
    *,
    report_text: str,
    match_item,
    validation_questions: list[dict[str, str]],
) -> IHUI3SupportOutput:
    """
    Respuesta IHUI 3.0 cuando sí hay match.

    Importante:
    - El wizard sigue siendo requerido.
    - La estrategia queda marcada como requires_validation.
    - La UI después podrá mostrar preguntas antes de cerrar la recomendación final.
    """
    teacher_microintervention = _build_microintervention(
        match_item,
        steps=match_item.strategy_steps,
    )

    family_steps = (
        match_item.family_strategy_steps
        if match_item.family_strategy_steps
        else match_item.strategy_steps
    )

    family_microintervention = _build_microintervention(
        match_item,
        steps=family_steps,
    )

    detected_signals = match_item.observable_signals or []
    if not detected_signals and report_text:
        detected_signals = [report_text]

    teacher_summary = (
        f"IHUI 3.0 detectó señales relacionadas con {match_item.nucleus} "
        f"({match_item.subskill}). Para darte la estrategia más adecuada, "
        f"primero necesitamos validar algunas preguntas clave."
    )

    parent_summary = (
        "IHUI 3.0 encontró una posible explicación funcional para lo observado. "
        "Antes de cerrar la recomendación, necesitamos responder unas preguntas "
        "breves para ajustar mejor el apoyo."
    )

    return IHUI3SupportOutput(
        teacher_version=IHUI3TeacherOutput(
            summary=teacher_summary,
            signals_detected=detected_signals,
            microintervenciones=[teacher_microintervention],
        ),
        parent_version=IHUI3ParentOutput(
            summary=parent_summary,
            signals_detected=detected_signals,
            microintervenciones=[family_microintervention],
        ),
    )


def generate_support_ihui3(
    *,
    db: Session,
    report_id: UUID,
    report_text: str,
    age: int | None,
    student_id: UUID,
    school_id: UUID,
    model_name: str = "ihui-3-initial",
) -> Dict[str, Any]:
    """
    Motor IHUI 3.0 inicial.

    No usa legacy V2.

    Flujo:
    1. Carga conocimiento IHUI 3.0.
    2. Busca match contra el reporte.
    3. Si no hay match: fallback + validación humana.
    4. Si hay match pero no hay preguntas: fallback + validación humana.
    5. Si hay match y preguntas: wizard requerido.
    """

    base_meta: dict[str, Any] = {
        "engine_version": "ihui_3",
        "ihui3_status": "native_ihui3",
        "knowledge_source": getattr(settings, "IHUI3_KNOWLEDGE_SOURCE", None),
        "review_threshold": getattr(settings, "IHUI3_REVIEW_THRESHOLD", 0.70),
        "query_text": report_text,
        "query_preview": report_text[:240],
        "topic_nucleo": [],
    }

    try:
        knowledge_items = load_ihui3_knowledge()
        dictionary_items = load_ihui3_dictionary()

        match_results = find_top_matches(
            report_text=report_text,
            knowledge_items=knowledge_items,
            dictionary_items=dictionary_items,
            limit=3,
        )

        match_result = match_results[0] if match_results else None
    except IHUI3KnowledgeLoadError as exc:
        support = _build_fallback_support(report_text)

        meta = {
            **base_meta,
            "fallback_used": True,
            "fallback_reason": "ihui3_knowledge_load_error",
            "review_status": "pending_human_review",
            "validation_status": "pending_human_review",
            "review_reason": "ihui3_knowledge_load_error",
            "knowledge_error": str(exc),
            "wizard_required": False,
            "model_output_summary": support.parent_version.summary,
        }

        return {
            "support": support,
            "model_name": model_name,
            "meta": meta,
        }

    if match_result is None:
        support = _build_fallback_support(report_text)

        meta = {
            **base_meta,
            "fallback_used": True,
            "fallback_reason": "ihui3_no_knowledge_match",
            "review_status": "pending_human_review",
            "validation_status": "pending_human_review",
            "review_reason": "ihui3_no_knowledge_match",
            "confidence_score": 0.0,
            "wizard_required": False,
            "ihui3_match": None,
            "model_output_summary": support.parent_version.summary,
        }

        return {
            "support": support,
            "model_name": model_name,
            "meta": meta,
        }

    match_item = match_result.knowledge_item
    validation_questions = _build_validation_questions(match_item)

    wizard_candidates = _build_wizard_candidates(match_results)
    wizard_questions = select_wizard_questions(wizard_candidates)

    # Regla nueva:
    # En IHUI 3.0, si no hay preguntas de validación, no cerramos estrategia.
    # Escalamos igual que en el screenshot.
    if not wizard_questions:
        support = _build_fallback_support(report_text)

        meta = {
            **base_meta,
            "fallback_used": True,
            "fallback_reason": "ihui3_missing_validation_questions",
            "review_status": "pending_human_review",
            "validation_status": "pending_human_review",
            "review_reason": "ihui3_missing_validation_questions",
            "confidence_score": match_result.score,
            "wizard_required": False,
            "topic_nucleo": [match_item.nucleus, match_item.subskill],
            "ihui3_match": {
                "nucleus": match_item.nucleus,
                "subskill": match_item.subskill,
                "score": match_result.score,
                "matched_terms": match_result.matched_terms,
                "reason": match_result.reason,
            },
            "model_output_summary": support.parent_version.summary,
        }

        return {
            "support": support,
            "model_name": model_name,
            "meta": meta,
        }

    hypotheses = _build_hypotheses(
        match_item=match_item,
        score=match_result.score,
        match_reason=match_result.reason,
    )

    support = _build_matched_support(
        report_text=report_text,
        match_item=match_item,
        validation_questions=validation_questions,
    )

    meta = {
        **base_meta,
        "fallback_used": False,
        "fallback_reason": None,
        "review_status": "pending_validation",
        "validation_status": "needs_validation_answers",
        "review_reason": None,
        "confidence_score": match_result.score,
        "wizard_required": True,
        "wizard": {
            "questions": wizard_questions,
            "allowed_answers": ["yes", "no", "sometimes"],
        },
        "ihui3_wizard_candidates": wizard_candidates,
        "ihui3_wizard_questions": wizard_questions,
        "topic_nucleo": [match_item.nucleus, match_item.subskill],
        "ihui3_match": {
            "nucleus": match_item.nucleus,
            "subskill": match_item.subskill,
            "score": match_result.score,
            "matched_terms": match_result.matched_terms,
            "reason": match_result.reason,
        },
        "ihui3_hypotheses": hypotheses,
        "ihui3_validation_questions": validation_questions,
        "ihui3_strategy": {
            "micro_objective": match_item.micro_objective,
            "steps": match_item.strategy_steps,
            "frequency": match_item.frequency,
            "duration": match_item.duration,
            "progress_indicator": match_item.progress_indicator,
            "escalation": match_item.escalation,
            "status": "requires_validation",
        },
        "ihui3_escalation": match_item.escalation,
        "model_output_summary": support.parent_version.summary,
    }

    return {
        "support": support,
        "model_name": model_name,
        "meta": meta,
    }
