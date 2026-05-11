from typing import Any, Dict, Optional


def build_guardrail_audit_payload(
    *,
    report_id: Optional[str],
    student_id: Optional[str],
    school_id: Optional[str],
    route: str,
    risk_level: str,
    input_guardrails_meta: Dict[str, Any],
    sanitized_report_text: str,
) -> Dict[str, Any]:
    """
    Construye un payload estructurado para auditoría de guardrails/router.

    ¿Por qué existe esta función?
    - Para no repartir diccionarios improvisados por el código.
    - Para que logs, monitoreo y futuros eventos usen la misma estructura.
    - Para facilitar tests.

    Nota:
    Guardamos un preview del texto sanitizado, no el texto completo,
    para evitar logs enormes y reducir exposición innecesaria.
    """
    preview = (sanitized_report_text or "").strip()
    if len(preview) > 240:
        preview = preview[:240].rstrip() + "..."

    classification = input_guardrails_meta.get("classification", {})

    return {
        "event_type": "ai_input_guardrails_decision",
        "report_id": report_id,
        "student_id": student_id,
        "school_id": school_id,
        "route": route,
        "risk_level": risk_level,
        "should_block": input_guardrails_meta.get("should_block"),
        "should_restrict": input_guardrails_meta.get("should_restrict"),
        "response_mode": input_guardrails_meta.get("response_mode"),
        "human_review_required": input_guardrails_meta.get("human_review_required"),
        "allow_rag": input_guardrails_meta.get("allow_rag"),
        "allow_llm_generation": input_guardrails_meta.get("allow_llm_generation"),
        "flags": input_guardrails_meta.get("flags", []),
        "blocked_reason": input_guardrails_meta.get("blocked_reason"),
        "classification_intent": classification.get("intent"),
        "classification_topics": classification.get("topics", []),
        "classification_confidence": classification.get("confidence"),
        "sanitized_report_preview": preview,
    }
