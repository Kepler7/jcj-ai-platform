#!/usr/bin/env python3
# /app/scripts/load_playbooks.py

"""
Docstring para backend.scripts.load_playbooks

Cómo correrlo dentro del contenedor (1 comando):
PYTHONPATH=/app python /app/scripts/load_playbooks.py --reset

Luego Verificar con el script de conteo:
PYTHONPATH=/app python /app/scripts/debug_chroma_count.py
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.rag.chroma_client import ChromaPlaybookStore

COLLECTION = "jcj_playbooks_v1"

# Default path dentro del contenedor (ajústalo si cambiaste tu montaje)
DEFAULT_JSONL = Path("/app/data/playbooks/playbooks.normalized.jsonl")


def _s(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _format_doc_from_row(row: Dict[str, Any]) -> str:
    """
    Documento “rico” que el LLM entiende y que también permite parse posterior si lo necesitas.
    """
    topic = _s(row.get("topic_nucleo"))
    sub = _s(row.get("subskill"))
    signal = _s(row.get("signal_observable"))
    hyp = _s(row.get("functional_hypothesis"))
    micro = _s(row.get("micro_objective"))
    freq = _s(row.get("frequency"))
    dur = _s(row.get("duration"))
    indicator = _s(row.get("progress_indicator"))
    escalation = _s(row.get("escalation"))

    age_min = row.get("age_min")
    age_max = row.get("age_max")

    steps = row.get("steps") or []
    if not isinstance(steps, list):
        steps = [_s(steps)] if _s(steps) else []

    # Formato consistente
    steps_block = "\n".join([f"- { _s(s) }" for s in steps if _s(s)])

    doc = f"""TOPIC_NUCLEO: {topic}
SUBHABILIDAD: {sub}

SEÑAL_OBSERVABLE:
{signal}

EDAD: {age_min}–{age_max}

HIPOTESIS_FUNCIONAL:
{hyp}

MICROOBJETIVO:
{micro}

ESTRATEGIAS_PASO_A_PASO:
{steps_block}

FRECUENCIA: {freq}
DURACION: {dur}

INDICADOR_DE_AVANCE:
{indicator}

ESCALAMIENTO:
{escalation}
""".strip()

    return doc


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
            except Exception as e:
                raise RuntimeError(f"Invalid JSON on line {i}: {e}")
    return rows


def load_jsonl_playbooks(store: ChromaPlaybookStore, jsonl_path: Path) -> int:
    rows = _read_jsonl(jsonl_path)

    loaded = 0
    for row in rows:
        doc_id = _s(row.get("id")) or None
        if not doc_id:
            # si por algo faltara, genera uno determinístico mínimo
            # (pero en tu normalizador ya viene id)
            raise RuntimeError("Row missing 'id' field in JSONL")

        # ✅ Metadata: SOLO tipos escalares permitidos por Chroma
        meta: Dict[str, Any] = {
            "id": doc_id,
            "source": _s(row.get("source")) or "sheet",
            "topic_nucleo": _s(row.get("topic_nucleo")),
            "subskill": _s(row.get("subskill")),
            "age_min": int(row.get("age_min")) if row.get("age_min") is not None else None,
            "age_max": int(row.get("age_max")) if row.get("age_max") is not None else None,
            "frequency": _s(row.get("frequency")),
            "duration": _s(row.get("duration")),
        }

        # Puedes añadir más metadata scalar si quieres luego filtrar:
        # meta["progress_indicator"] = _s(row.get("progress_indicator"))

        doc_text = _format_doc_from_row(row)

        store.add_document(
            doc_id=doc_id,
            text=doc_text,
            metadata=meta,
        )
        loaded += 1

    return loaded


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(DEFAULT_JSONL), help="Path to normalized JSONL")
    ap.add_argument("--reset", action="store_true", help="Reset (delete+recreate) the collection before loading")
    args = ap.parse_args()

    jsonl_path = Path(args.jsonl)
    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL not found: {jsonl_path}")

    store = ChromaPlaybookStore(
        host="chroma",
        port=8000,
        collection_name=COLLECTION,
    )

    if args.reset:
        print("🧹 Resetting collection...")
        store.reset()

    print("📥 Loading playbooks from JSONL (sheet)...")
    count = load_jsonl_playbooks(store, jsonl_path)

    # Verificación
    final_count = store.count()
    print(f"✅ Loaded {count} playbooks from sheet")
    print(f"📊 Final collection count: {final_count}")


if __name__ == "__main__":
    main()

