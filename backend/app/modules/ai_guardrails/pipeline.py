from typing import List, Optional

from pydantic import BaseModel

from app.modules.ai_guardrails.schemas import SensitiveClassificationResult
from app.modules.ai_guardrails.service import run_guardrails


class InputGuardrailPipelineResult(BaseModel):
    """
    Resultado del pipeline de guardrails de entrada.

    Esta clase existe para que el resto del sistema reciba una estructura clara
    y consistente antes de entrar al flujo de RAG o al agente.
    """

    # Texto original recibido por el pipeline.
    original_text: str

    # Texto ya sanitizado (por ejemplo, con PII redactada).
    sanitized_text: str

    # True si NO estamos en bloqueo duro.
    safe: bool

    # True si el caso debe bloquearse antes de RAG/LLM.
    should_block: bool

    # True si el caso NO se bloquea, pero sí requiere tratamiento especial.
    should_restrict: bool

    # low | medium | high
    risk_level: str

    # Flags técnicos simples, por ejemplo:
    # ["pii_email"] o ["pii_email", "prompt_injection"]
    flags: List[str]

    # Motivo de bloqueo si aplica.
    blocked_reason: Optional[str] = None

    # Ruta operativa decidida por el clasificador contextual.
    route: str

    # Modo de respuesta permitido.
    response_mode: str

    # ¿Se necesita revisión humana?
    human_review_required: bool

    # ¿Se permite usar RAG?
    allow_rag: bool

    # ¿Se permite usar generación con LLM?
    allow_llm_generation: bool

    # Clasificación completa para logs, auditoría y pasos futuros.
    classification: SensitiveClassificationResult


def normalize_input_text(text: Optional[str]) -> str:
    """
    Normaliza el texto de entrada.

    Por ahora:
    - None -> ""
    - cualquier otro valor -> str(valor)
    """
    if text is None:
        return ""

    return str(text)


def run_input_guardrails(text: Optional[str]) -> InputGuardrailPipelineResult:
    """
    Ejecuta los guardrails nuevos sobre el texto de entrada.

    Flujo:
    1. Normaliza el input
    2. Ejecuta run_guardrails()
    3. Traduce el resultado a un formato útil para el pipeline AI
    """
    normalized_text = normalize_input_text(text)
    guardrail_result = run_guardrails(normalized_text)

    classification = guardrail_result.classification

    return InputGuardrailPipelineResult(
        original_text=normalized_text,
        sanitized_text=guardrail_result.redacted_text,
        safe=guardrail_result.safe,
        should_block=(classification.route == "block"),
        should_restrict=(classification.route == "safeguarding_review"),
        risk_level=guardrail_result.risk_level,
        flags=guardrail_result.flags,
        blocked_reason=guardrail_result.blocked_reason,
        route=classification.route,
        response_mode=classification.response_mode,
        human_review_required=classification.human_review_required,
        allow_rag=classification.allow_rag,
        allow_llm_generation=classification.allow_llm_generation,
        classification=classification,
    )
