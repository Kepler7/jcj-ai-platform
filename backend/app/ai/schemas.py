from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Literal


class Recommendation(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    steps: List[str] = Field(min_length=1)
    when_to_use: str = Field(min_length=3, max_length=200)


class PlanDay(BaseModel):
    day: int = Field(ge=1, le=7)
    focus: str = Field(min_length=2, max_length=120)
    activity: str = Field(min_length=2, max_length=300)
    success_criteria: str = Field(min_length=2, max_length=200)


class TeacherVersion(BaseModel):
    summary: str = Field(min_length=10, max_length=600)
    signals_detected: List[str] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list, max_length=6)
    classroom_plan_7_days: List[PlanDay] = Field(default_factory=list, max_length=7)


class ParentVersion(BaseModel):
    summary: str = Field(min_length=10, max_length=600)
    signals_detected: List[str] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list, max_length=6)
    home_plan_7_days: List[PlanDay] = Field(default_factory=list, max_length=7)


class GuardrailsBlock(BaseModel):
    no_diagnosis_confirmed: bool = True
    no_clinical_labels_confirmed: bool = True


class SupportMeta(BaseModel):
    # "playbook" = se encontraron estrategias JCJ
    # "fallback" = NO se encontraron y se dieron sugerencias generales
    source: Literal["playbook", "fallback"] = "playbook"

    # Solo para fallback
    disclaimer: Optional[str] = None
    fallback_reason: Optional[Literal["no_match", "empty_strategies", "low_confidence"]] = None

    # Debug/auditoría (opcional)
    contexts: Optional[List[str]] = None
    retrieved_count: Optional[int] = None


class AIGeneratedSupport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    teacher_version: TeacherVersion
    parent_version: ParentVersion
    guardrails: GuardrailsBlock

    # ✅ NUEVO (opcional): lo inyectamos nosotros si hace falta
    meta: Optional[SupportMeta] = None

