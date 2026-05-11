from __future__ import annotations

import json
from pathlib import Path

from app.settings import settings
from app.modules.ihui_3.schemas import IHUI3DictionaryItem


class IHUI3DictionaryLoadError(Exception):
    pass


def get_dictionary_source_path() -> Path:
    source = getattr(
        settings,
        "IHUI3_DICTIONARY_SOURCE",
        "/app/data/ihui3/ihui3_dictionary.normalized.jsonl",
    )

    if not source:
        raise IHUI3DictionaryLoadError("IHUI3_DICTIONARY_SOURCE está vacío.")

    return Path(source)


def load_ihui3_dictionary() -> list[IHUI3DictionaryItem]:
    path = get_dictionary_source_path()

    if not path.exists():
        return []

    items: list[IHUI3DictionaryItem] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            try:
                payload = json.loads(line)
                items.append(IHUI3DictionaryItem.model_validate(payload))
            except Exception as exc:
                raise IHUI3DictionaryLoadError(
                    f"Error leyendo diccionario IHUI 3.0 en línea {line_number}: {exc}"
                ) from exc

    return items
