import re
from typing import Tuple, List

# Lista mínima (puedes crecerla)
BANNED_TERMS = [
    "tdah", "t.d.a.h", "autismo", "asperger", "trastorno", "diagnóstico", "diagnostico",
    "dsm", "neurológico", "neurologico", "patología", "patologia",
    "ansiedad generalizada", "depresión", "depresion",
]

def check_guardrails(text: str) -> Tuple[bool, List[str]]:
    hits = []
    low = text.lower()
    for term in BANNED_TERMS:
        if term in low:
            hits.append(term)
    return (len(hits) == 0), hits

def sanitize_language(text: str) -> str:
    # opcional: reemplazos suaves
    return re.sub(r"\bdiagn[oó]stic[oa]\b", "evaluación", text, flags=re.IGNORECASE)
