from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SensitiveClassificationResult(BaseModel):
    """
    Resultado estructurado del clasificador contextual de IHUI.

    Este modelo NO decide nada por sí mismo.
    Solo define el contrato que cualquier clasificador debe respetar.
    """

    intent: Literal[
        "normal_educational_request",
        "legitimate_sensitive_report",
        "legitimate_sensitive_help_request",
        "dangerous_request",
        "prompt_attack",
    ]

    topics: List[
        Literal[
            "attention_learning",
            "behavior_regulation",
            "social_interaction",
            "emotional_distress",
            "self_harm_suicidality",
            "sexual_content_exposure",
            "sexual_abuse",
            "physical_violence",
            "abuse_neglect",
            "none",
        ]
    ] = Field(default_factory=list)

    risk_level: Literal["low", "medium", "high"]
    route: Literal["normal", "safeguarding_review", "block"]
    response_mode: Literal["full_support", "restricted_support", "no_generation"]
    human_review_required: bool
    allow_rag: bool
    allow_llm_generation: bool
    blocked_reason: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)


class GuardrailResult(BaseModel):
    """
    Resultado total de guardrails de entrada.

    Combina:
    - sanitización de PII
    - decisión general de seguridad
    - clasificación contextual sensible
    """

    safe: bool
    redacted_text: str
    risk_level: str  # low | medium | high
    flags: List[str]
    blocked_reason: Optional[str] = None

    # Clasificación contextual de IHUI.
    classification: SensitiveClassificationResult
