from pydantic import BaseModel, ConfigDict, Field
from typing import List, Annotated

ShortTopic = Annotated[str, Field(min_length=2, max_length=80)]
StepText = Annotated[str, Field(min_length=1, max_length=300)]


class MicroIntervention(BaseModel):
    # Nombres alineados al sheet de Deneb (sin acentos por seguridad JSON)
    topic_nucleo: List[ShortTopic] = Field(min_length=1, max_length=8)
    subhabilidad: str = Field(min_length=2, max_length=120)
    senal_observable: str = Field(min_length=5, max_length=600)

    hipotesis_funcional: str = Field(min_length=5, max_length=800)
    microobjetivo: str = Field(min_length=3, max_length=300)

    estrategias_paso_a_paso: List[str] = Field(min_length=1, max_length=8)
    frecuencia: str = Field(min_length=1, max_length=120)
    duracion: str = Field(min_length=1, max_length=120)
    indicador_de_avance: str = Field(min_length=3, max_length=300)
    escalamiento: str = Field(min_length=3, max_length=500)


class TeacherVersion(BaseModel):
    summary: str = Field(min_length=10, max_length=800)
    signals_detected: List[str] = Field(default_factory=list)
    microintervenciones: List[MicroIntervention] = Field(
        default_factory=list, max_length=10
    )


class ParentVersion(BaseModel):
    summary: str = Field(min_length=10, max_length=800)
    signals_detected: List[str] = Field(default_factory=list)
    microintervenciones: List[MicroIntervention] = Field(
        default_factory=list, max_length=10
    )


class GuardrailsBlock(BaseModel):
    no_diagnosis_confirmed: bool = True
    no_clinical_labels_confirmed: bool = True


class AIGeneratedSupport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    teacher_version: TeacherVersion
    parent_version: ParentVersion
    guardrails: GuardrailsBlock
