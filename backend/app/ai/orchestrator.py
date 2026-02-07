# backend/app/ai/orchestrator.py

from __future__ import annotations

import json
from typing import List, Tuple, Optional, Any, Dict

from agno.agent import Agent

from app.ai.providers import get_ai_model, get_model_info
from app.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from app.ai.json_utils import extract_json_object, _extract_raw_text
from app.ai.guardrails import check_guardrails
from app.ai.schemas import AIGeneratedSupport, SupportMeta

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

def _count_playbook_items(playbooks_by_context: Any) -> int:
    """
    Cuenta cuántas estrategias/items recuperó el RAG.
    No asumimos estructura exacta; soporta:
      - dict[str, list]
      - dict[str, dict{items: [...]}
      - list directo
    """
    if not playbooks_by_context:
        return 0

    # dict por contexto
    if isinstance(playbooks_by_context, dict):
        total = 0
        for _, v in playbooks_by_context.items():
            if v is None:
                continue
            if isinstance(v, list):
                total += len(v)
            elif isinstance(v, dict):
                items = v.get("items") or v.get("results") or v.get("playbooks") or []
                if isinstance(items, list):
                    total += len(items)
        return total

    # list directo
    if isinstance(playbooks_by_context, list):
        return len(playbooks_by_context)

    return 0

FALLBACK_DISCLAIMER = (
    "⚠️ Nota: No se encontraron estrategias específicas en el Playbook JCJ para este caso. "
    "Las sugerencias siguientes son generales y deben ser validadas/ajustadas por el equipo profesional."
)

def _prepend_disclaimer(summary: str, disclaimer: str) -> str:
    summary = (summary or "").strip()
    if not summary:
        return disclaimer
    # Evita duplicarlo si ya existe
    if disclaimer.lower() in summary.lower():
        return summary
    return f"{disclaimer}\n\n{summary}"

def generate_support(
    *,
    student_name: str,
    age: int,
    group: str,
    report_text: str,
    contexts: List[str] | None = None,  # ✅ contexts dinámicos
) -> Tuple[AIGeneratedSupport, str, Dict[str, Any]]:
    """
    Genera apoyo educativo (teacher_version + parent_version) y aplica:
    1) JSON strict (Pydantic)
    2) Guardrails post-procesado (bloqueo de lenguaje clínico/diagnóstico)

    Returns:
      (parsed_output, model_name, meta)
      meta incluye fallback_used cuando NO hubo estrategias JCJ en RAG.
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

    # ✅ Detectar si realmente hubo estrategias JCJ recuperadas
    total_items = _count_playbook_items(playbooks_by_context)
    fallback_used = total_items == 0

    # Normaliza razón para el worker/UI
    fallback_reason = None
    if fallback_used:
        fallback_reason = "no_match"  # usa uno de tus enums esperados ("no_match"/"empty_strategies"/"low_confidence")

    # 2) Agente LLM
    agent = Agent(
        model=get_ai_model(),
        tools=[],
        instructions=[SYSTEM_PROMPT],
    )

    # 3) Prompt base (tu prompt actual)
    base_prompt = build_user_prompt(student_name, age, group, report_text)

    # 4) Inyección RAG + instrucciones
    rag_header = "=== Estrategias JCJ disponibles (RAG) ===\n"
    if fallback_used:
        rag_header += (
            "(NO SE ENCONTRARON estrategias JCJ relevantes para este caso. "
            "Puedes proponer sugerencias generales y prácticas, pero NO digas que vienen del playbook.)\n"
        )

    prompt = (
        f"{base_prompt}\n\n"
        f"{rag_header}"
        f"{playbooks_block}\n\n"
        "Instrucciones adicionales:\n"
        "- Prioriza estas estrategias JCJ cuando sean relevantes.\n"
        "- Si el bloque JCJ está vacío o indica que no se encontraron estrategias, "
        "propón recomendaciones generales y prácticas, sencillas y seguras.\n"
        "- Si algo no aplica, di 'No aplica' y sugiere una alternativa simple.\n"
        "- No incluyas nombres propios ni datos sensibles.\n"
        "- Mantén español claro y natural.\n"
        "- No uses lenguaje clínico/diagnóstico.\n"
        # ✅ Cuando sea fallback, pedimos que el lenguaje sea aún más conservador
        + (
            "- IMPORTANTE: estas recomendaciones son generales y deben ser validadas por profesionales.\n"
            if fallback_used
            else ""
        )
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

    # ✅ 8.5) Si hubo fallback: inyectar meta + disclaimer (sin depender del LLM)
    if fallback_used:
        # Inyecta meta estructurada para UI/telemetría
        parsed.meta = SupportMeta(
            source="fallback",
            disclaimer=FALLBACK_DISCLAIMER,
            fallback_reason="no_match",
            contexts=contexts,
            retrieved_count=total_items,
        )

        # Prefija disclaimer en summaries (teacher + parent)
        try:
            parsed.teacher_version.summary = _prepend_disclaimer(
                parsed.teacher_version.summary, FALLBACK_DISCLAIMER
            )
        except Exception:
            pass
        try:
            parsed.parent_version.summary = _prepend_disclaimer(
                parsed.parent_version.summary, FALLBACK_DISCLAIMER
            )
        except Exception:
            pass
    else:
        # Si hubo playbooks, marcamos meta playbook (opcional)
        parsed.meta = SupportMeta(
            source="playbook",
            disclaimer=None,
            fallback_reason=None,
            contexts=contexts,
            retrieved_count=total_items,
        )

    # 9) Meta para "Pendientes de Playbook"
    def _clip(s: str, n: int) -> str:
        s = (s or "").strip()
        if len(s) <= n:
            return s
        return s[:n].rstrip() + "..."

    query_full = (report_text or "").strip()

    # si quieres protegerte de notas enormes
    MAX_FULL = 4000
    query_text = query_full[:MAX_FULL] if len(query_full) > MAX_FULL else query_full
    query_preview = _clip(query_text, 240)

    model_output_full = ""
    try:
        model_output_full = str(parsed.parent_version.summary or "")
    except Exception:
        model_output_full = ""

    model_output_text = model_output_full[:MAX_FULL] if len(model_output_full) > MAX_FULL else model_output_full
    model_output_preview = _clip(model_output_text, 240)

    meta: Dict[str, Any] = {
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "context": contexts,
        "topic_nucleo": None,

        # ✅ FULL + preview
        "query_text": query_text,
        "query_preview": query_preview,
        "model_output_summary": model_output_text,
        "model_output_preview": model_output_preview,

        "rag_items_count": total_items,
    }


    return parsed, model_info.name, meta
