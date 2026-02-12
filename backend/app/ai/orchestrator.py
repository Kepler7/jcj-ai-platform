# backend/app/ai/orchestrator.py

from __future__ import annotations

import json
import re
from typing import List, Tuple, Optional, Any, Dict

from agno.agent import Agent

from app.ai.providers import get_ai_model, get_model_info
from app.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from app.ai.json_utils import extract_json_object, _extract_raw_text
from app.ai.guardrails import check_guardrails
from app.ai.schemas import AIGeneratedSupport, SupportMeta

from app.rag.chroma_client import ChromaPlaybookStore

def _count_strategies(playbooks_by_context: Dict[str, Any]) -> int:
    """
    Cuenta estrategias reales sin asumir demasiado la estructura.
    Esperado: dict(context -> list(items)), donde item tiene 'strategies' o 'strategies' dentro.
    """
    total = 0
    if not isinstance(playbooks_by_context, dict):
        return 0

    for _ctx, items in playbooks_by_context.items():
        if not items:
            continue
        if isinstance(items, dict):
            # por si viene anidado
            items = items.get("items") or items.get("results") or []
        if not isinstance(items, list):
            continue

        for it in items:
            if isinstance(it, dict):
                strategies = it.get("strategies") or []
            else:
                strategies = getattr(it, "strategies", None) or []
            if isinstance(strategies, list):
                total += len([s for s in strategies if str(s).strip()])
    return total



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

def _as_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    s = str(x).strip()
    return [s] if s else []

def _bullets(items: List[str], prefix: str = "- ") -> str:
    if not items:
        return "- (vacío)"
    return "\n".join([f"{prefix}{it}" for it in items if it and it.strip()])

def format_one_playbook(pb_text: str) -> str:
    """
    Intenta formatear un playbook como bloque estructurado.
    Si pb_text es JSON (recomendado), lo imprime con Goal/Strategies en bullets.
    Si no es JSON, lo devuelve tal cual.
    """
    raw = (pb_text or "").strip()
    if not raw:
        return "(vacío)"

    # Intentar parsear JSON
    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            return raw
    except Exception:
        return raw

    problem_title = str(obj.get("problem_title") or "").strip()
    topic_nucleo = str(obj.get("topic_nucleo") or "").strip()
    age_min = obj.get("age_min")
    age_max = obj.get("age_max")

    contexts = _as_list(obj.get("contexts"))
    tags = _as_list(obj.get("tags"))
    behavior = str(obj.get("behavior") or "").strip()

    goals = _as_list(obj.get("goal"))
    strategies = _as_list(obj.get("strategies"))
    constraints = _as_list(obj.get("constraints"))
    extra_notes = str(obj.get("extra_notes") or "").strip()

    # Identificadores opcionales
    base_row = str(obj.get("base_row") or "").strip()
    raw_id_name = str(obj.get("raw_id_name") or "").strip()
    pid = str(obj.get("id") or "").strip()

    parts: List[str] = []
    parts.append(f"Problem: {problem_title or '-'}")
    if topic_nucleo:
        parts.append(f"Topic NUCLEO: {topic_nucleo}")
    if age_min is not None or age_max is not None:
        parts.append(f"Age expected: {age_min if age_min is not None else '-'} to {age_max if age_max is not None else '-'}")
    if contexts:
        parts.append(f"Contexts: {', '.join(contexts)}")
    if tags:
        parts.append(f"Tags/Emotion: {', '.join(tags)}")
    if behavior:
        parts.append("Observed behavior:")
        parts.append(behavior)

    parts.append("Goal (JCJ):")
    parts.append(_bullets(goals))

    parts.append("Strategies (JCJ):")
    parts.append(_bullets(strategies))

    if constraints:
        parts.append("Constraints / rules:")
        parts.append(_bullets(constraints))

    if extra_notes:
        parts.append("Extra notes:")
        parts.append(extra_notes)

    # Debug mínimo (no molesta, pero ayuda)
    debug_bits = []
    if base_row:
        debug_bits.append(f"base_row={base_row}")
    if raw_id_name:
        debug_bits.append(f"raw_id_name={raw_id_name}")
    if pid:
        debug_bits.append(f"id={pid}")
    if debug_bits:
        parts.append(f"Meta: {', '.join(debug_bits)}")

    return "\n".join(parts)



def format_playbooks_by_context(playbooks_by_context: Dict[str, List[str]]) -> str:
    """
    Formatea los playbooks agrupados por contexto para inyectarlos en el prompt.
    Asegura que el LLM vea Goal/Strategies en bullets (cuando pb_text es JSON).
    """
    blocks: List[str] = []

    for ctx, playbooks in (playbooks_by_context or {}).items():
        blocks.append(f"## Context: {str(ctx).upper()}")

        if not playbooks:
            blocks.append("No hay playbooks JCJ relevantes para este contexto.")
            continue

        for i, pb_text in enumerate(playbooks, start=1):
            blocks.append(f"[Playbook {i}]\n{format_one_playbook(pb_text)}")

    return "\n\n".join(blocks).strip()


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

# ... tus imports existentes: Agent, ChromaPlaybookStore, etc.

MAX_FULL = 4000  # protección contra textos enormes en DB (ajústalo si quieres)

def _count_strategies(playbooks_by_context: Any) -> int:
    """
    Cuenta estrategias reales sin asumir demasiado la estructura.
    Esperado típico:
      dict(ctx -> list[dict]) donde cada dict tiene 'strategies': list[str]
    Pero lo hacemos tolerante por si cambia la forma.
    """
    total = 0
    if not isinstance(playbooks_by_context, dict):
        return 0

    for _ctx, items in playbooks_by_context.items():
        if not items:
            continue

        # por si viene dict anidado tipo {"items": [...]}
        if isinstance(items, dict):
            items = items.get("items") or items.get("results") or items.get("matches") or []

        if not isinstance(items, list):
            continue

        for it in items:
            strategies = None

            if isinstance(it, dict):
                strategies = it.get("strategies")
                # por si viene anidado
                if strategies is None and "document" in it and isinstance(it["document"], dict):
                    strategies = it["document"].get("strategies")
            else:
                strategies = getattr(it, "strategies", None)

            if isinstance(strategies, list):
                total += len([s for s in strategies if str(s).strip()])

    return total


def _clip(s: str, n: int) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[:n].rstrip() + "..."

def _try_json_dict(s: str) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads((s or "").strip())
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None

def _as_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    s = str(x).strip()
    return [s] if s else []

def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        it = (it or "").strip()
        if not it or it in seen:
            continue
        seen.add(it)
        out.append(it)
    return out

def parse_playbook_doc(pb_text: str) -> Optional[Dict[str, Any]]:
    """
    Intenta convertir un doc devuelto por Chroma a dict JSON del playbook.
    - Caso ideal: el doc ES JSON puro.
    - Caso real: el doc viene con texto extra; extraemos el primer objeto JSON con extract_json_object.
    """
    s = (pb_text or "").strip()
    if not s:
        return None

    # 1) intento directo
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    # 2) intento robusto: extraer { ... } del string
    try:
        raw_obj = extract_json_object(s)  # <- tu helper existente
        obj = json.loads(json.dumps(raw_obj, ensure_ascii=False))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None

def _prepend_goals_to_summary(summary: str, goals: List[str]) -> str:
    goals = _dedupe_keep_order([g.strip() for g in (goals or []) if g and g.strip()])
    if not goals:
        return summary
    block = "Objetivos (JCJ):\n" + "\n".join([f"- {g}" for g in goals])
    if "Objetivos (JCJ):" in (summary or ""):
        return summary
    return (block + "\n\n" + (summary or "")).strip()

def _build_recommendations_from_playbook(
    *,
    strategies: List[str],
    when_to_use: str,
    title_prefix: str,
    max_recs: int,
) -> List[Dict[str, Any]]:
    """
    Convierte strategies JCJ en recomendaciones 'agrupadas' para no perder pasos.
    """
    strategies = _dedupe_keep_order([s.strip() for s in strategies if s and s.strip()])
    if not strategies:
        return []

    # Heurística simple: divide en 3 bloques (base, práctica, progresión) sin inventar
    # (Si hay pocas, cae en 1 bloque)
    n = len(strategies)
    if n <= 4:
        chunks = [strategies]
        titles = [f"{title_prefix}: Estrategia principal"]
    elif n <= 8:
        chunks = [strategies[:4], strategies[4:]]
        titles = [f"{title_prefix}: Base y técnica", f"{title_prefix}: Práctica y progresión"]
    else:
        chunks = [strategies[:4], strategies[4:8], strategies[8:]]
        titles = [f"{title_prefix}: Base y técnica", f"{title_prefix}: Práctica guiada", f"{title_prefix}: Progresión"]

    recs = []
    for t, chunk in zip(titles, chunks):
        if not chunk:
            continue
        recs.append(
            {
                "title": t[:120],
                "steps": chunk,
                "when_to_use": when_to_use[:200],
            }
        )

    return recs[:max_recs]


CODEBLOCK_JSON_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)

def extract_json_object_lenient(raw: str) -> Dict[str, Any]:
    """
    Intenta extraer un objeto JSON desde:
    - ```json { ... } ```
    - texto con JSON embebido
    - JSON puro
    """
    if not raw:
        raise ValueError("Empty model output")

    s = raw.strip()

    # 1) si viene dentro de codefence ```json ... ```
    m = CODEBLOCK_JSON_RE.search(s)
    if m:
        s = m.group(1).strip()

    # 2) recorta entre primer '{' y último '}'
    if not s.startswith("{"):
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            s = s[start : end + 1].strip()

    return json.loads(s)


def generate_support(
    *,
    student_name: str,
    age: int,
    group: str,
    report_text: str,
    contexts: List[str] | None = None,
) -> Tuple["AIGeneratedSupport", str, Dict[str, Any]]:
    model_info = get_model_info()

    # 0) contexts default
    if contexts is None:
        contexts_used = ["aula", "casa"]
    else:
        contexts_used = [c.strip().lower() for c in contexts if c and c.strip()]
        if not contexts_used:
            contexts_used = ["aula", "casa"]

    # 1) RAG
    store = ChromaPlaybookStore(
        host="chroma",
        port=8000,
        collection_name="jcj_playbooks_v1",
    )

    playbooks_by_context = retrieve_playbooks_for_contexts(
        store,
        report_text=report_text,
        age=age,
        contexts=contexts_used,
        n_results_per_context=3,
    )

    rag_docs_count = sum(len(v or []) for v in (playbooks_by_context or {}).values())
    print("DEBUG RAG: contexts=", contexts_used, "rag_docs_count=", rag_docs_count)
    for k, v in (playbooks_by_context or {}).items():
        print("DEBUG RAG ctx:", k, "items:", len(v or []))

    playbooks_block = format_playbooks_by_context(playbooks_by_context)

    # ✅ fallback SOLO si no hay docs
    fallback_used = rag_docs_count == 0
    fallback_reason = "no_match" if fallback_used else None
    print("DEBUG fallback_used=", fallback_used)

    # 2) Extraer goals/strategies (determinístico)
    extracted_goals: List[str] = []
    extracted_strategies: List[str] = []
    parse_fail_count = 0

    for _ctx, docs in (playbooks_by_context or {}).items():
        for pb_text in (docs or []):
            obj = parse_playbook_doc(pb_text)
            if not obj:
                parse_fail_count += 1
                continue
            extracted_goals += _as_list(obj.get("goal"))
            extracted_strategies += _as_list(obj.get("strategies"))

    extracted_goals = _dedupe_keep_order(extracted_goals)
    extracted_strategies = _dedupe_keep_order(extracted_strategies)

    # 3) Agent + prompt
    agent = Agent(
        model=get_ai_model(),
        tools=[],
        instructions=[SYSTEM_PROMPT],
    )

    base_prompt = build_user_prompt(student_name, age, group, report_text)

    rag_header = "=== Estrategias JCJ disponibles (RAG) ===\n"
    if fallback_used:
        rag_header += (
            "(NO SE ENCONTRARON estrategias JCJ relevantes para este caso. "
            "Puedes proponer sugerencias generales y prácticas, pero NO digas que vienen del playbook.)\n"
        )

    # ✅ regla anti-bullets dentro de strings (reduce JSON roto)
    prompt = (
        f"{base_prompt}\n\n"
        f"{rag_header}"
        f"{playbooks_block}\n\n"
        "Instrucciones adicionales:\n"
        "- Prioriza estas estrategias JCJ cuando sean relevantes.\n"
        "- Si el bloque JCJ tiene OBJETIVOS/ESTRATEGIAS, úsalo.\n"
        "- NO metas listas con guiones, numeración o bloques multi-línea dentro de 'summary'.\n"
        "- Si mencionas objetivos, colócalos SOLO en el campo goals como arreglo.\n"
        "- Si el bloque JCJ está vacío, propón recomendaciones generales y seguras.\n"
        "- Devuelve SOLO JSON válido (sin ```json, sin markdown, sin texto extra).\n"
        "- No uses lenguaje clínico/diagnóstico.\n"
    )

    # 4) Llamada al modelo + parse lenient + retry 1 vez
    resp = agent.run(prompt)
    raw = _extract_raw_text(resp)

    try:
        data = extract_json_object_lenient(raw)
    except Exception:
        fix_prompt = (
            "Tu respuesta NO es JSON válido.\n"
            "Devuelve SOLO un objeto JSON válido, sin markdown, sin ```json, sin comentarios, sin texto extra.\n"
            "Respeta exactamente el esquema.\n"
            "Aquí está tu salida anterior:\n\n"
            f"{raw}\n"
        )
        resp2 = agent.run(fix_prompt)
        raw2 = _extract_raw_text(resp2)
        data = extract_json_object_lenient(raw2)

    parsed = AIGeneratedSupport.model_validate(data)

    combined_text = json.dumps(data, ensure_ascii=False).lower()
    ok, hits = check_guardrails(combined_text)
    if not ok:
        raise ValueError(f"Guardrails failed. Banned terms found: {hits}")

    # 5) Aplicar playbook determinísticamente (si hubo docs)
    if not fallback_used:
        # (a) Inyectar goals del playbook de forma determinística
        #     - Si el schema tiene goals -> los setea
        #     - Si no tiene goals -> los agrega al summary (prefijo corto y seguro)
        if extracted_goals:
            # 1) Si existe campo goals en schema, setearlo sí o sí
            if hasattr(parsed.teacher_version, "goals"):
                parsed.teacher_version.goals = extracted_goals
            if hasattr(parsed.parent_version, "goals"):
                parsed.parent_version.goals = extracted_goals

            # 2) Backup: si NO hay goals en schema o quedó vacío, prefijar en summary
            def _prefix_goals(summary: str, goals: List[str]) -> str:
                goals_txt = "\n".join([f"- {g}" for g in goals if g.strip()])
                prefix = f"Objetivos (JCJ):\n{goals_txt}\n\n"
                s = (summary or "").strip()
                # evita duplicar si ya lo contiene
                return s if "Objetivos (JCJ):" in s else (prefix + s).strip()

            # si no existe el campo goals, o existe pero quedó vacío, prefijamos summary
            if not hasattr(parsed.teacher_version, "goals") or not getattr(parsed.teacher_version, "goals", None):
                parsed.teacher_version.summary = _prefix_goals(parsed.teacher_version.summary, extracted_goals)
            if not hasattr(parsed.parent_version, "goals") or not getattr(parsed.parent_version, "goals", None):
                parsed.parent_version.summary = _prefix_goals(parsed.parent_version.summary, extracted_goals)


        # (b) Recomendaciones desde strategies del playbook (robusto)
        #     Nota: esto mete varias recomendaciones aunque el LLM haya dado pocas.
        if extracted_strategies:
            teacher_recs_pb = _build_recommendations_from_playbook(
                strategies=extracted_strategies,
                when_to_use="Durante clases y ejercicios en aula",
                title_prefix="JCJ",
                max_recs=8,
            )
            parent_recs_pb = _build_recommendations_from_playbook(
                strategies=extracted_strategies,
                when_to_use="Durante actividades cotidianas en casa",
                title_prefix="JCJ",
                max_recs=8,
            )

            def _merge_recs(
                pb: List[Dict[str, Any]],
                llm: List[Any],
                max_total: int,
            ) -> List[Dict[str, Any]]:
                out: List[Dict[str, Any]] = []
                seen = set()

                for r in pb or []:
                    t = (r.get("title") or "").strip().lower()
                    k = t or json.dumps(r, ensure_ascii=False, sort_keys=True)
                    if k in seen:
                        continue
                    out.append(r)
                    seen.add(k)
                    if len(out) >= max_total:
                        return out[:max_total]

                for r in llm or []:
                    try:
                        d = r.model_dump() if hasattr(r, "model_dump") else dict(r)
                    except Exception:
                        continue
                    t = (d.get("title") or "").strip().lower()
                    k = t or json.dumps(d, ensure_ascii=False, sort_keys=True)
                    if k in seen:
                        continue
                    out.append(d)
                    seen.add(k)
                    if len(out) >= max_total:
                        break

                return out[:max_total]

            # tu schema en schemas.py tenía max_length=6 antes;
            # si lo subiste a 10, perfecto. Si sigue 6, baja max_total a 6.
            parsed.teacher_version.recommendations = _merge_recs(
                teacher_recs_pb,
                getattr(parsed.teacher_version, "recommendations", []),
                max_total=10,
            )
            parsed.parent_version.recommendations = _merge_recs(
                parent_recs_pb,
                getattr(parsed.parent_version, "recommendations", []),
                max_total=10,
            )

    # 6) Meta worker/UI
    def _clip(s: str, n: int) -> str:
        s = (s or "").strip()
        return s if len(s) <= n else (s[:n].rstrip() + "...")

    query_full = (report_text or "").strip()
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
        "context": contexts_used,
        "topic_nucleo": None,
        "query_text": query_text,
        "query_preview": query_preview,
        "model_output_summary": model_output_text,
        "model_output_preview": model_output_preview,
        "rag_docs_count": rag_docs_count,
        "parse_fail_count": parse_fail_count,
    }

    return parsed, model_info.name, meta
