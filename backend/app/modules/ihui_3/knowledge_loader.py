from __future__ import annotations

import json
from pathlib import Path
from typing import List

from app.settings import settings
from app.modules.ihui_3.schemas import IHUI3KnowledgeItem


class IHUI3KnowledgeLoadError(Exception):
    """
    Error controlado para problemas al cargar conocimiento IHUI 3.0.
    """

    pass


def get_knowledge_source_path() -> Path:
    """
    Regresa la ruta del archivo normalizado de conocimiento IHUI 3.0.

    Por default usa:
    /app/data/ihui3/ihui3_knowledge.normalized.jsonl

    Pero se puede cambiar con:
    IHUI3_KNOWLEDGE_SOURCE
    """
    source = getattr(
        settings,
        "IHUI3_KNOWLEDGE_SOURCE",
        "/app/data/ihui3/ihui3_knowledge.normalized.jsonl",
    )

    if not source:
        raise IHUI3KnowledgeLoadError(
            "IHUI3_KNOWLEDGE_SOURCE está vacío. Define la ruta del archivo JSONL."
        )

    return Path(source)


def load_ihui3_knowledge() -> List[IHUI3KnowledgeItem]:
    """
    Carga el conocimiento IHUI 3.0 desde un archivo JSONL.

    Cada línea del archivo debe representar un IHUI3KnowledgeItem.

    Ejemplo de línea JSONL:
    {
      "nucleus": "Atención",
      "subskill": "Permanencia en tarea",
      "observable_signals": ["se distrae", "no termina actividades"],
      ...
    }
    """
    path = get_knowledge_source_path()

    if not path.exists():
        raise IHUI3KnowledgeLoadError(
            f"No existe el archivo de conocimiento IHUI 3.0: {path}"
        )

    items: List[IHUI3KnowledgeItem] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            try:
                payload = json.loads(line)
                item = IHUI3KnowledgeItem.model_validate(payload)
                items.append(item)
            except Exception as exc:
                raise IHUI3KnowledgeLoadError(
                    f"Error leyendo IHUI 3.0 knowledge en línea {line_number}: {exc}"
                ) from exc

    if not items:
        raise IHUI3KnowledgeLoadError(
            f"El archivo de conocimiento IHUI 3.0 está vacío: {path}"
        )

    return items
