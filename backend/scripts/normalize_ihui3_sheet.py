from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.request
from pathlib import Path
from typing import Any


def clean_text(value: Any) -> str:
    """
    Limpia texto proveniente del CSV.
    """
    if value is None:
        return ""

    return str(value).strip()


def split_pipe(value: Any) -> list[str]:
    """
    Convierte campos separados por | en lista.

    Ejemplo:
    "No entiende | Se mueve mucho"
    ->
    ["No entiende", "Se mueve mucho"]
    """
    text = clean_text(value)

    if not text:
        return []

    return [part.strip() for part in text.split("|") if part.strip()]


def parse_float(value: Any) -> float | None:
    """
    Convierte edad mínima/máxima a float.
    """
    text = clean_text(value)

    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def parse_strategy_steps(value: Any) -> list[str]:
    """
    Convierte estrategias tipo:
    E1. Dar tarea corta. E2. Explicar inicio y fin.
    en:
    ["Dar tarea corta.", "Explicar inicio y fin."]
    """
    text = clean_text(value)

    if not text:
        return []

    # Divide por E1. E2. E3. etc.
    parts = re.split(r"\bE\d+\.\s*", text)

    steps = [part.strip() for part in parts if part.strip()]

    # Fallback por si la hoja viene separada con |
    if len(steps) <= 1 and "|" in text:
        steps = split_pipe(text)

    return steps


def get_first_existing(row: dict[str, Any], possible_names: list[str]) -> str:
    """
    Busca una columna considerando posibles nombres.

    Esto nos protege si Deneb cambia un poco el encabezado.
    """
    for name in possible_names:
        if name in row:
            return clean_text(row.get(name))

    return ""


def normalize_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """
    Convierte una fila del Google Sheet en formato IHUI3KnowledgeItem.
    """
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
        get_first_existing(row, ["Estrategias paso a paso", "Estrategia paso a paso"])
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

    # Evita guardar filas vacías.
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
        "frequency": frequency,
        "duration": duration,
        "progress_indicator": progress_indicator,
        "escalation": escalation,
    }


def download_csv(url: str) -> str:
    """
    Descarga CSV desde Google Sheets.
    """
    if not url:
        raise ValueError("Falta IHUI3_SHEET_CSV_URL o --input-url")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()

    # Google Sheets normalmente entrega utf-8.
    return raw.decode("utf-8-sig")


def normalize_csv_content(csv_content: str) -> list[dict[str, Any]]:
    """
    Lee el CSV descargado y regresa filas normalizadas.
    """
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
    """
    Escribe el archivo JSONL final.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for item in items:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normaliza Google Sheet IHUI 3.0 a JSONL."
    )

    parser.add_argument(
        "--input-url",
        required=True,
        help="URL CSV export de Google Sheets.",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Ruta de salida JSONL.",
    )

    args = parser.parse_args()

    csv_content = download_csv(args.input_url)
    items = normalize_csv_content(csv_content)

    if not items:
        raise RuntimeError(
            "No se generaron items IHUI 3.0. Revisa encabezados o acceso al Sheet."
        )

    output_path = Path(args.output)
    write_jsonl(items, output_path)

    print(
        json.dumps(
            {
                "status": "ok",
                "items_count": len(items),
                "output": str(output_path),
                "sample": items[0],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
