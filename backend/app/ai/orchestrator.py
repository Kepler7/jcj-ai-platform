# backend/app/ai/orchestrator.py

from __future__ import annotations

import json
from typing import Tuple, Dict, List

from agno.agent import Agent

from app.ai.providers import get_ai_model, get_model_info
from app.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from app.ai.json_utils import extract_json_object, _extract_raw_text
from app.ai.guardrails import check_guardrails
from app.ai.schemas import AIGeneratedSupport

from app.rag.chroma_client import ChromaPlaybookStore


# =========================
# RAG helpers (NEW)
# =========================

def format_one_playbook(text: str, *, max_chars: int = 1200) -> str:
    """Recorta para el prompt por legibilidad (no por límite del modelo)."""
    snippet = (text or "").strip()
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars] + "..."
    return snippet


def retrieve_playbooks_for_contexts(
    store: ChromaPlaybookStore,
    *,
    report_text: str,
    age: int,
    contexts: List[str],
    n_results_per_context: int = 3,
) -> Dict[str, List[str]]:
    """
    Recupera playbooks por cada contexto (aula, casa, etc.)
    y regresa un dict: { "aula": [doc1, doc2], "casa": [...] }
    """
    results: Dict[str, List[str]] = {}

    for ctx in contexts:
        docs = store.query(
            query_text=report_text,
            age=age,
            context=ctx,
            n_results=n_results_per_context,
        )
        results[ctx] = docs

    return results


def format_playbooks_by_context(playbooks_by_context: Dict[str, List[str]]) -> str:
    """
    Formatea los playbooks agrupados por contexto para inyectarlos en el prompt.
    """
    blocks: List[str] = []

    for ctx, playbooks in playbooks_by_context.items():
        blocks.append(f"## Contexto: {ctx.upper()}")

        if not playbooks:
            blocks.append("No hay playbooks JCJ relevantes para este contexto.")
            continue

        for i, pb_text in enumerate(playbooks, start=1):
            blocks.append(f"[Playbook {i}]\n{format_one_playbook(pb_text)}")

    return "\n\n".join(blocks)


# =========================
# Main generator (MODIFIED)
# =========================

def generate_support(
    *,
    student_name: str,
    age: int,
    group: str,
    report_text: str,
    contexts: List[str] | None = None,     # ✅ nuevo: contexts dinámicos
) -> Tuple[AIGeneratedSupport, str]:
    """
    Genera apoyo educativo (teacher_version + parent_version) y aplica:
    1) JSON strict (Pydantic)
    2) Guardrails post-procesado (bloqueo de lenguaje clínico/diagnóstico)

    Returns:
      (parsed_output, model_name) donde model_name = "provider:model"
    """
    model_info = get_model_info()

    # 0) Define contexts (por default: aula + casa)
    if contexts is None:
        contexts = ["aula", "casa"]
    else:
        contexts = [c.strip().lower() for c in contexts if c and c.strip()]
        if not contexts:
            contexts = ["aula", "casa"]

    # 1) RAG: recuperar estrategias JCJ relevantes (por contexto)
    #    (Más adelante esto vendrá de Settings/env; por ahora funciona en dev)
    store = ChromaPlaybookStore(
        host="chroma",
        port=8000,
        collection_name="jcj_playbooks_v1",
    )

    playbooks_by_context = retrieve_playbooks_for_contexts(
        store,
        report_text=report_text,
        age=age,
        contexts=contexts,
        n_results_per_context=3,
    )

    playbooks_block = format_playbooks_by_context(playbooks_by_context)

    # 2) Agente LLM
    agent = Agent(
        model=get_ai_model(),
        tools=[],  # en US-0401 lo dejamos vacío intencionalmente
        instructions=[SYSTEM_PROMPT],
    )

    # 3) Prompt base (tu prompt actual)
    base_prompt = build_user_prompt(student_name, age, group, report_text)

    # 4) Inyección RAG + instrucciones
    prompt = (
        f"{base_prompt}\n\n"
        "=== Estrategias JCJ disponibles (RAG) ===\n"
        f"{playbooks_block}\n\n"
        "Instrucciones adicionales:\n"
        "- Prioriza estas estrategias JCJ cuando sean relevantes.\n"
        "- Si algo no aplica, di 'No aplica' y sugiere una alternativa simple.\n"
        "- No incluyas nombres propios ni datos sensibles.\n"
        "- Mantén español claro y natural.\n"
        "- No uses lenguaje clínico/diagnóstico.\n"
    )

    # 5) Llamada al modelo
    resp = agent.run(prompt)
    raw = _extract_raw_text(resp)

    # 6) Parsear JSON (fallar rápido si no cumple)
    try:
        data = extract_json_object(raw)
    except Exception:
        raise ValueError(
            f"Model did not return valid JSON. Raw (first 600 chars): {raw[:600]}"
        )

    # 7) Validar contra el contrato estricto
    parsed = AIGeneratedSupport.model_validate(data)

    # 8) Guardrails post-salida
    combined_text = json.dumps(data, ensure_ascii=False).lower()
    ok, hits = check_guardrails(combined_text)
    if not ok:
        raise ValueError(f"Guardrails failed. Banned terms found: {hits}")

    return parsed, model_info.name
