import re
import json
from typing import Tuple

from agno.agent import Agent

from app.ai.providers import get_ai_model, get_model_info
from app.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from app.ai.schemas import AIGeneratedSupport
from app.ai.guardrails import check_guardrails

def extract_json_object(raw: str) -> dict:
    """
    Extrae el primer objeto JSON válido desde una respuesta del LLM.
    Soporta:
    - ```json ... ```
    - texto extra antes/después
    """
    s = raw.strip()

    # 1) Bloque ```json ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        s = fence.group(1).strip()

    # 2) Si aún hay texto extra: recorta de { hasta }
    if not s.startswith("{"):
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            s = s[start : end + 1].strip()

    return json.loads(s)


def _extract_raw_text(response) -> str:
    """
    Agno puede devolver distintos tipos según versión.
    Esta función lo normaliza a string.
    """
    raw = getattr(response, "content", None)
    if raw is None:
        raw = str(response)
    return raw.strip()


def generate_support(
    *,
    student_name: str,
    age: int,
    group: str,
    report_text: str,
) -> Tuple[AIGeneratedSupport, str]:
    """
    Genera apoyo educativo (teacher_version + parent_version) y aplica:
    1) JSON strict (Pydantic)
    2) Guardrails post-procesado (bloqueo de lenguaje clínico/diagnóstico)

    Returns:
      (parsed_output, model_name) donde model_name = "provider:model"
    """
    model_info = get_model_info()

    agent = Agent(
        model=get_ai_model(),
        tools=[],  # en US-0401 lo dejamos vacío intencionalmente
        instructions=[SYSTEM_PROMPT],
    )

    prompt = build_user_prompt(student_name, age, group, report_text)

    # 1) Llamada al modelo
    resp = agent.run(prompt)
    raw = _extract_raw_text(resp)

    # 2) Parsear JSON (fallar rápido si no cumple)
    try:
        data = extract_json_object(raw)
    except Exception:
        raise ValueError(f"Model did not return valid JSON. Raw (first 600 chars): {raw[:600]}")


    # 3) Validar contra el contrato estricto
    parsed = AIGeneratedSupport.model_validate(data)

    # 4) Guardrails post-salida
    combined_text = json.dumps(data, ensure_ascii=False).lower()
    ok, hits = check_guardrails(combined_text)
    if not ok:
        # Política MVP: bloquear. (Más adelante podemos “reparar” y reintentar)
        raise ValueError(f"Guardrails failed. Banned terms found: {hits}")

    return parsed, model_info.name

