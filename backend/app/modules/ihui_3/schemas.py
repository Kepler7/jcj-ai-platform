from __future__ import annotations

from typing import Literal, Optional, Any
from pydantic import BaseModel, Field


ConfidenceLevel = Literal["low", "medium", "high"]
ReviewStatus = Literal["approved", "pending_human_review"]
ValidationStatus = Literal[
    "not_required",
    "needs_validation_answers",
    "validated",
    "pending_human_review",
]


class IHUI3KnowledgeItem(BaseModel):
    """
    Representa una fila normalizada de la hoja IHUI 3.0.

    Esta estructura sale del spreadsheet de Deneb.
    No es todavía la respuesta final al usuario.
    """

    nucleus: str
    subskill: str
    observable_signals: list[str] = Field(default_factory=list)

    age_min_expected: Optional[float] = None
    age_max_expected: Optional[float] = None

    functional_hypotheses: list[str] = Field(default_factory=list)
    observable_triggers: list[str] = Field(default_factory=list)
    validation_questions: list[str] = Field(default_factory=list)

    micro_objective: str = ""
    strategy_steps: list[str] = Field(default_factory=list)

    frequency: str = ""
    duration: str = ""
    progress_indicator: str = ""
    escalation: str = ""


class IHUI3Hypothesis(BaseModel):
    """
    Hipótesis funcional seleccionada por IHUI 3.0.
    """

    name: str
    confidence: ConfidenceLevel = "medium"
    reasoning: str = ""


class IHUI3ValidationQuestion(BaseModel):
    """
    Pregunta que el maestro/padre puede responder para afinar la estrategia.
    """

    question: str
    why_it_matters: str = ""


class IHUI3Strategy(BaseModel):
    """
    Estrategia recomendada para maestro/padre.
    """

    micro_objective: str
    steps: list[str] = Field(default_factory=list)
    frequency: str = ""
    duration: str = ""
    progress_indicator: str = ""
    escalation: Optional[str] = None


class IHUI3TeacherVersion(BaseModel):
    """
    Respuesta para maestro.
    """

    summary: str
    detected_nucleus: str
    detected_subskill: str

    main_hypothesis: IHUI3Hypothesis
    alternative_hypotheses: list[IHUI3Hypothesis] = Field(default_factory=list)

    validation_questions: list[IHUI3ValidationQuestion] = Field(default_factory=list)
    recommended_strategy: IHUI3Strategy


class IHUI3ParentVersion(BaseModel):
    """
    Respuesta para padres.
    """

    summary: str
    possible_explanation: str
    home_suggestion: str
    when_to_ask_for_help: Optional[str] = None


class IHUI3Response(BaseModel):
    """
    Contrato principal del motor IHUI 3.0.

    Este objeto será usado internamente para construir:
    - teacher_version
    - parent_version
    - ai_metadata
    - validation_status
    """

    engine_version: Literal["ihui_3"] = "ihui_3"

    confidence_score: float = 0.0
    review_status: ReviewStatus = "pending_human_review"
    validation_status: ValidationStatus = "needs_validation_answers"

    review_reason: Optional[str] = None

    teacher_version: IHUI3TeacherVersion
    parent_version: IHUI3ParentVersion

    knowledge_matches: list[IHUI3KnowledgeItem] = Field(default_factory=list)


class IHUI3ValidationAnswer(BaseModel):
    playbook_id: str
    question_id: str
    answer: Literal["yes", "no", "sometimes"]


class IHUI3ValidationAnswersRequest(BaseModel):
    answers: list[IHUI3ValidationAnswer] = Field(default_factory=list)


class IHUI3ValidationAnswersResponse(BaseModel):
    ai_report_id: str
    validation_status: str
    wizard_required: bool
    message: str


class IHUI3SyncResponse(BaseModel):
    status: str
    source: str | None = None
    output: str | None = None
    items_count: int = 0
    dictionary_items_count: int = 0
    dictionary_output: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class IHUI3LatestSyncResponse(BaseModel):
    status: str
    source: str | None = None
    output: str | None = None
    items_count: int = 0
    dictionary_items_count: int = 0
    dictionary_output: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class IHUI3DictionaryItem(BaseModel):
    expression: str
    nucleus: str = ""
    subskill: str = ""
    canonical_signal: str = ""
    notes: str = ""
