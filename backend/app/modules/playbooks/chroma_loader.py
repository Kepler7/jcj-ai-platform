from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.rag.chroma_client import ChromaPlaybookStore
from app.ai.utils.normalization import normalize_topic_nucleo


def _s(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def format_doc_from_row(row: Dict[str, Any]) -> str:
    """
    Documento rico para retrieval en Chroma.
    """
    topic = normalize_topic_nucleo(row.get("topic_nucleo"))
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

    steps_block = "\n".join([f"- {_s(s)}" for s in steps if _s(s)])

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


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
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


def build_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
    doc_id = _s(row.get("id"))
    if not doc_id:
        raise RuntimeError("Row missing 'id' field in JSONL")

    return {
        "id": doc_id,
        "source": _s(row.get("source")) or "sheet",
        "topic_nucleo": normalize_topic_nucleo(row.get("topic_nucleo")),
        "subskill": _s(row.get("subskill")),
        "age_min": int(row.get("age_min")) if row.get("age_min") is not None else None,
        "age_max": int(row.get("age_max")) if row.get("age_max") is not None else None,
        "frequency": _s(row.get("frequency")),
        "duration": _s(row.get("duration")),
    }


def load_jsonl_playbooks(store: ChromaPlaybookStore, jsonl_path: Path) -> int:
    rows = read_jsonl(jsonl_path)

    loaded = 0
    for row in rows:
        doc_id = _s(row.get("id"))
        if not doc_id:
            raise RuntimeError("Row missing 'id' field in JSONL")

        metadata = build_metadata(row)
        doc_text = format_doc_from_row(row)

        store.add_document(
            doc_id=doc_id,
            text=doc_text,
            metadata=metadata,
        )
        loaded += 1

    return loaded


def reload_playbooks_into_chroma(
    *,
    host: str,
    port: int,
    collection_name: str,
    jsonl_path: Path,
    reset: bool = True,
) -> int:
    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL not found: {jsonl_path}")

    store = ChromaPlaybookStore(
        host=host,
        port=port,
        collection_name=collection_name,
    )

    if reset:
        store.reset()

    count = load_jsonl_playbooks(store, jsonl_path)
    return count
