import json
import re
from typing import Any

def _extract_raw_text(resp: Any) -> str:
    """
    Extrae texto plano desde la respuesta del Agent de Agno.
    Maneja distintos formatos posibles.
    """
    if resp is None:
        return ""

    # Caso común: resp.output_text
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text

    # Algunos modelos regresan lista de mensajes
    if hasattr(resp, "messages") and resp.messages:
        parts = []
        for m in resp.messages:
            if isinstance(m, dict) and "content" in m:
                parts.append(str(m["content"]))
            else:
                parts.append(str(m))
        return "\n".join(parts)

    # Fallback
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