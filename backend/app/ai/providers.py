import os
from dataclasses import dataclass

from agno.models.groq import Groq

# IMPORT OPENAI (lo activamos cuando confirmemos el import correcto en tu versión)
# from agno.models.openai import OpenAIChat  # <-- este puede variar según versión


@dataclass(frozen=True)
class ModelInfo:
    provider: str
    model: str

    @property
    def name(self) -> str:
        # Para guardar en DB: "groq:llama-3.3-70b-versatile"
        return f"{self.provider}:{self.model}"


def get_model_info() -> ModelInfo:
    provider = os.getenv("AI_PROVIDER", "groq").strip().lower()
    model = os.getenv("AI_MODEL", "llama-3.3-70b-versatile").strip()
    return ModelInfo(provider=provider, model=model)


def get_ai_model():
    """
    Factory del modelo.
    Deja el sistema intercambiable por proveedor sin tocar el resto del código.
    """
    info = get_model_info()

    if info.provider == "groq":
        # Groq usa GROQ_API_KEY en env
        return Groq(id=info.model)

    if info.provider == "openai":
        # OpenAI usa OPENAI_API_KEY en env
        # IMPORTANTE: esta clase puede variar según tu versión de agno.
        # Cuando lo vayamos a activar, confirmamos el import correcto y lo descomentamos.
        # return OpenAIChat(id=info.model)
        raise ValueError(
            "AI_PROVIDER=openai está configurado, pero OpenAI aún no está conectado en providers.py. "
            "Actívalo cuando confirmemos el import correcto para tu versión de agno."
        )

    raise ValueError(f"Unknown AI_PROVIDER={info.provider}")
