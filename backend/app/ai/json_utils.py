import json
import re
from typing import Any

def _extract_raw_text(resp) -> str:
    # Agno RunOutput trae el texto final en .content
    if hasattr(resp, "content") and isinstance(resp.content, str):
        return resp.content

    # fallback por compatibilidad
    if hasattr(resp, "messages") and resp.messages:
        last = resp.messages[-1]
        c = getattr(last, "content", None)
        if isinstance(c, str):
            return c

    return str(resp)


def extract_json_object(text: str) -> dict:
    """
    Extrae el PRIMER objeto JSON válido desde un texto.
    Soporta respuestas envueltas en ```json ... ```
    """

    if not text:
        raise ValueError("Empty response text")

    # 1️⃣ Si viene dentro de ```json ... ```
    fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_match:
        return json.loads(fenced_match.group(1))

    # 2️⃣ Buscar primer bloque {...}
    brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace_match:
        return json.loads(brace_match.group(1))

    raise ValueError("No JSON object found in model output")