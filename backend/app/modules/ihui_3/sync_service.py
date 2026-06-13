from __future__ import annotations

import csv
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.settings import settings


class IHUI3SyncError(Exception):
    """
    Error controlado para sync IHUI 3.0.
    """

    pass


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def split_pipe(value: Any) -> list[str]:
    text = clean_text(value)

    if not text:
        return []

    return [part.strip() for part in text.split("|") if part.strip()]


def parse_float(value: Any) -> float | None:
    text = clean_text(value)

    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def parse_strategy_steps(value: Any) -> list[str]:
    text = clean_text(value)

    if not text:
        return []

    parts = re.split(r"\bE\d+\.\s*", text)
    steps = [part.strip() for part in parts if part.strip()]

    if len(steps) <= 1 and "|" in text:
        steps = split_pipe(text)

    return steps


def normalize_header(value: str) -> str:
    """
    Normaliza encabezados para tolerar espacios, mayúsculas y textos extra.

    Ejemplo:
    'Hipótesis funcionalCognitiva | No entiende...'
    puede matchear con:
    'Hipótesis funcional'
    """
    text = clean_text(value).lower()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }

    for original, replacement in replacements.items():
        text = text.replace(original, replacement)

    text = " ".join(text.split())

    return text


def get_first_existing(row: dict[str, Any], possible_names: list[str]) -> str:
    """
    Busca una columna considerando:
    1. Match exacto.
    2. Match tolerante por encabezado normalizado.
    3. Match por prefijo para encabezados con texto extra.

    Esto arregla casos como:
    'Hipótesis funcionalCognitiva | No entiende la tarea | ...'
    """
    # 1. Match exacto
    for name in possible_names:
        if name in row:
            return clean_text(row.get(name))

    normalized_possible_names = [normalize_header(name) for name in possible_names]

    # 2 y 3. Match flexible
    for header, value in row.items():
        normalized_header = normalize_header(header)

        for normalized_name in normalized_possible_names:
            if normalized_header == normalized_name:
                return clean_text(value)

            if normalized_header.startswith(normalized_name):
                return clean_text(value)

    return ""


def normalize_row(row: dict[str, Any]) -> dict[str, Any] | None:
    nucleus = get_first_existing(row, ["Núcleo", "Nucleo"])
    subskill = get_first_existing(row, ["Subhabilidad", "Sub habilidad"])

    observable_signals = split_pipe(
        get_first_existing(row, ["Señal observable", "Senal observable"])
    )

    functional_hypotheses = split_pipe(
        get_first_existing(row, ["Hipótesis funcional", "Hipotesis funcional"])
    )

    observable_triggers = split_pipe(
        get_first_existing(row, ["Disparadores observables"])
    )

    validation_questions = split_pipe(
        get_first_existing(row, ["Preguntas de validación", "Preguntas de validacion"])
    )

    micro_objective = get_first_existing(row, ["Microobjetivo", "Micro objetivo"])

    strategy_steps = parse_strategy_steps(
        get_first_existing(
            row,
            [
                "Estrategias paso a paso",
                "Estrategia paso a paso",
            ],
        )
    )

    family_strategy_steps = parse_strategy_steps(
        get_first_existing(
            row,
            [
                "Estrategias paso a paso Familia",
                "Estrategias paso a paso familia",
                "Estrategia paso a paso Familia",
                "Estrategia paso a paso familia",
            ],
        )
    )

    frequency = get_first_existing(row, ["Frecuencia"])
    duration = get_first_existing(row, ["Duración", "Duracion"])
    progress_indicator = get_first_existing(row, ["Indicador de avance"])
    escalation = get_first_existing(row, ["Escalamiento"])

    age_min_expected = parse_float(
        get_first_existing(row, ["Age min esperado", "Edad min esperada", "Age min"])
    )

    age_max_expected = parse_float(
        get_first_existing(row, ["Age max esperado", "Edad max esperada", "Age max"])
    )

    if not nucleus and not subskill and not observable_signals:
        return None

    return {
        "nucleus": nucleus,
        "subskill": subskill,
        "observable_signals": observable_signals,
        "age_min_expected": age_min_expected,
        "age_max_expected": age_max_expected,
        "functional_hypotheses": functional_hypotheses,
        "observable_triggers": observable_triggers,
        "validation_questions": validation_questions,
        "micro_objective": micro_objective,
        "strategy_steps": strategy_steps,
        "family_strategy_steps": family_strategy_steps,
        "frequency": frequency,
        "duration": duration,
        "progress_indicator": progress_indicator,
        "escalation": escalation,
    }


def download_csv(url: str) -> str:
    if not url:
        raise IHUI3SyncError("IHUI3_SHEET_CSV_URL está vacío.")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
    except Exception as exc:
        raise IHUI3SyncError(f"No se pudo descargar Google Sheet CSV: {exc}") from exc

    return raw.decode("utf-8-sig")


def normalize_csv_content(csv_content: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(csv_content.splitlines())

    items: list[dict[str, Any]] = []

    for row_number, row in enumerate(reader, start=2):
        item = normalize_row(row)

        if item is None:
            continue

        item["_source_row"] = row_number
        items.append(item)

    return items


def write_jsonl(items: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for item in items:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


def get_status_path() -> Path:
    return Path("/app/data/ihui3/ihui3_sync_status.json")


def write_sync_status(status: dict[str, Any]) -> None:
    path = get_status_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(status, file, ensure_ascii=False, indent=2)


def read_latest_sync_status() -> dict[str, Any] | None:
    path = get_status_path()

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def sync_ihui3_knowledge() -> dict[str, Any]:
    source_url = getattr(settings, "IHUI3_SHEET_CSV_URL", "")
    output = getattr(
        settings,
        "IHUI3_KNOWLEDGE_SOURCE",
        "/app/data/ihui3/ihui3_knowledge.normalized.jsonl",
    )

    output_path = Path(output)

    started_at = datetime.now(timezone.utc).isoformat()

    try:
        csv_content = download_csv(source_url)
        items = normalize_csv_content(csv_content)

        if not items:
            raise IHUI3SyncError(
                "No se generaron items IHUI 3.0. Revisa encabezados o acceso al Sheet."
            )

        write_jsonl(items, output_path)

        dictionary_items: list[dict[str, Any]] = []
        dictionary_source_url = getattr(settings, "IHUI3_DICTIONARY_CSV_URL", "")
        dictionary_output = getattr(
            settings,
            "IHUI3_DICTIONARY_SOURCE",
            "/app/data/ihui3/ihui3_dictionary.normalized.jsonl",
        )

        if dictionary_source_url:
            dictionary_csv_content = download_csv(dictionary_source_url)
            dictionary_items = normalize_dictionary_csv_content(dictionary_csv_content)
            write_jsonl(dictionary_items, Path(dictionary_output))

        finished_at = datetime.now(timezone.utc).isoformat()

        status = {
            "status": "finished",
            "source": source_url,
            "output": str(output_path),
            "items_count": len(items),
            "dictionary_items_count": len(dictionary_items),
            "dictionary_output": dictionary_output,
            "started_at": started_at,
            "finished_at": finished_at,
            "sample": items[0],
        }

        write_sync_status(status)
        return status

    except Exception as exc:
        failed_at = datetime.now(timezone.utc).isoformat()

        status = {
            "status": "failed",
            "source": source_url,
            "output": str(output_path),
            "items_count": 0,
            "started_at": started_at,
            "finished_at": failed_at,
            "error": str(exc),
        }

        write_sync_status(status)

        if isinstance(exc, IHUI3SyncError):
            raise

        raise IHUI3SyncError(str(exc)) from exc


def normalize_dictionary_section_title(value: str) -> tuple[str, str]:
    """
    Convierte:
    '🧩 1. ATENCIÓN / CONCENTRACIÓN'
    en:
    ('Atención', 'Concentración')
    """
    text = clean_text(value)

    # Quita emoji/número inicial.
    text = re.sub(r"^.*?\d+\.\s*", "", text).strip()

    if "/" in text:
        left, right = text.split("/", 1)
        return left.strip().title(), right.strip().title()

    return text.title(), ""


def normalize_dictionary_csv_content(csv_content: str) -> list[dict[str, Any]]:
    """
    Normaliza la tab Diccionario.

    La tab tiene formato tipo:
    🧩 1. ATENCIÓN / CONCENTRACIÓN
    Entrada humana:
    no pone atención
    se distrae mucho
    Salida IHUI:
    👉 Baja atención sostenida / permanencia en tarea
    """
    reader = csv.reader(csv_content.splitlines())

    rows = [row for row in reader if row]
    values = [clean_text(row[0]) for row in rows if row and clean_text(row[0])]

    items: list[dict[str, Any]] = []

    current_nucleus = ""
    current_subskill = ""
    collecting_inputs = False
    collecting_output = False
    input_expressions: list[str] = []
    canonical_signal = ""

    def flush_section() -> None:
        nonlocal input_expressions, canonical_signal, current_nucleus, current_subskill

        for expression in input_expressions:
            items.append(
                {
                    "expression": expression,
                    "nucleus": current_nucleus,
                    "subskill": current_subskill,
                    "canonical_signal": canonical_signal.replace("👉", "").strip(),
                    "notes": "",
                }
            )

        input_expressions = []
        canonical_signal = ""

    for value in values:
        if value.startswith("🧩"):
            flush_section()
            current_nucleus, current_subskill = normalize_dictionary_section_title(
                value
            )
            collecting_inputs = False
            collecting_output = False
            continue

        lowered = value.lower()

        if "entrada humana" in lowered:
            collecting_inputs = True
            collecting_output = False
            continue

        if "salida ihui" in lowered:
            collecting_inputs = False
            collecting_output = True
            continue

        if collecting_inputs:
            input_expressions.append(value)
            continue

        if collecting_output:
            canonical_signal = value
            collecting_output = False
            continue

    flush_section()

    return items
