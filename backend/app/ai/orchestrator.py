from __future__ import annotations

import hashlib
import json
import math
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from agno.agent import Agent

from app.ai.guardrails import check_guardrails
from app.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from app.ai.providers import get_ai_model, get_model_info
from app.ai.rerank_bm25 import bm25_coverage, bm25_rank
from app.ai.schemas import AIGeneratedSupport
from app.rag.chroma_client import ChromaPlaybookStore
import os

try:
    from app.ai.schemas import SupportMeta  # type: ignore
except Exception:
    SupportMeta = None  # type: ignore

from app.ai.utils.normalization import normalize_topic_nucleo


# =========================
# Constants
# =========================

FALLBACK_NOTE = (
    "⚠️ Nota: No se encontraron estrategias específicas en el Playbook JCJ para este caso. "
    "Las sugerencias siguientes son generales y deben ser validadas/ajustadas por el equipo profesional."
)

MAX_FULL = 4000  # protección contra textos enormes en DB (ajústalo si quieres)

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "jcj_playbooks_v1")


# =========================
# Generic helpers (module-level)
# =========================

SECTION_HEADERS = [
    "TOPIC_NUCLEO",
    "SUBHABILIDAD",
    "SEÑAL_OBSERVABLE",
    "EDAD",
    "HIPOTESIS_FUNCIONAL",
    "MICROOBJETIVO",
    "ESTRATEGIAS_PASO_A_PASO",
    "FRECUENCIA",
    "DURACION",
    "INDICADOR_DE_AVANCE",
    "ESCALAMIENTO",
]

CODEBLOCK_JSON_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)


def _clip(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else (s[:n].rstrip() + "...")


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        k = (x or "").strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append((x or "").strip())
    return out


def _parse_bullets(block: str) -> List[str]:
    if not block:
        return []
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    steps: List[str] = []
    for ln in lines:
        ln = re.sub(r"^[-•]\s*", "", ln).strip()
        if ln:
            steps.append(ln)
    return steps


def _line_value(text: str, prefix: str) -> str:
    m = re.search(rf"^{re.escape(prefix)}\s*:\s*(.+?)\s*$", text, re.MULTILINE)
    return (m.group(1) if m else "").strip()


def _extract_block(text: str, header: str) -> str:
    pat = re.compile(
        rf"^{re.escape(header)}\s*:\s*\n(?P<body>.*?)(?=^(?:[A-Z_]+)\s*:|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pat.search(text)
    return (m.group("body") if m else "").strip()


def _strip_code_fences(text: str) -> str:
    if not text:
        return text
    s = text.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1 :]
        s = s.strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    return s.strip()


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

    m = CODEBLOCK_JSON_RE.search(s)
    if m:
        s = m.group(1).strip()

    if not s.startswith("{"):
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            s = s[start : end + 1].strip()

    return json.loads(s)


def _try_parse_playbook_json(doc: str) -> Optional[Dict[str, Any]]:
    if not doc or not isinstance(doc, str):
        return None
    s = doc.strip()
    if not s.startswith("{"):
        return None
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _pb_to_search_text(doc: str) -> str:
    """
    Convierte playbook (JSON o texto con headers) a un texto consistente para:
    - bm25_rank
    - bm25_coverage
    - evidence_overlap_ratio
    - debug / logs
    """
    if not doc:
        return ""

    pbj = _try_parse_playbook_json(doc)
    if pbj:
        topic = normalize_topic_nucleo(pbj.get("topic_nucleo"))
        sub = (pbj.get("subskill") or pbj.get("subhabilidad") or "").strip()
        sig = (
            pbj.get("signal_observable") or pbj.get("senal_observable") or ""
        ).strip()
        hyp = (
            pbj.get("functional_hypothesis") or pbj.get("hipotesis_funcional") or ""
        ).strip()
        micro = (pbj.get("micro_objective") or pbj.get("microobjetivo") or "").strip()

        steps = pbj.get("steps") or pbj.get("estrategias_paso_a_paso") or []
        if isinstance(steps, str):
            steps = [steps]
        if not isinstance(steps, list):
            steps = []
        steps_txt = " ".join([str(x).strip() for x in steps if str(x).strip()])

        return (
            f"TOPIC_NUCLEO: {topic}\n"
            f"SUBHABILIDAD: {sub}\n"
            f"SEÑAL_OBSERVABLE: {sig}\n"
            f"HIPOTESIS_FUNCIONAL: {hyp}\n"
            f"MICROOBJETIVO: {micro}\n"
            f"ESTRATEGIAS_PASO_A_PASO: {steps_txt}\n"
        ).strip()

    # Formato con headers ya es usable tal cual
    return doc.strip()


def _pb_debug_info(pb_doc: str) -> Dict[str, Any]:
    """
    Devuelve info mínima para debug y UI (no rompe si doc es texto con headers).
    """
    pbj = _try_parse_playbook_json(pb_doc)
    if pbj:
        return {
            "id": (pbj.get("id") or ""),
            "topic_nucleo": normalize_topic_nucleo(pbj.get("topic_nucleo")),
            "subhabilidad": (pbj.get("subskill") or pbj.get("subhabilidad") or ""),
            "signal_observable": (
                pbj.get("signal_observable") or pbj.get("senal_observable") or ""
            ),
            "source": (pbj.get("source") or "json"),
            "base_row": (pbj.get("base_row") or ""),
        }

    # texto con headers
    pb_text = _pb_to_search_text(pb_doc)
    return {
        "id": "",
        "topic_nucleo": normalize_topic_nucleo(_line_value(pb_text, "TOPIC_NUCLEO")),
        "subhabilidad": _line_value(pb_text, "SUBHABILIDAD"),
        "signal_observable": _extract_block(pb_text, "SEÑAL_OBSERVABLE"),
        "source": "text",
        "base_row": "",
    }


def parse_playbook_doc_v2(doc: str) -> Optional[Dict[str, Any]]:
    """
    Devuelve dict con keys internas:
      id, base_row,
      topic_nucleo, subhabilidad, senal_observable, hipotesis_funcional,
      microobjetivo, estrategias_paso_a_paso, frecuencia, duracion,
      indicador_de_avance, escalamiento, age_min, age_max
    """
    if not doc or not isinstance(doc, str):
        return None

    text = doc.strip()

    def _to_int_or_none(v: Any) -> Optional[int]:
        try:
            if v is None or str(v).strip() == "":
                return None
            return int(str(v).strip())
        except Exception:
            return None

    # 1) JSON
    pbj = _try_parse_playbook_json(text)
    if pbj:
        topic = normalize_topic_nucleo(pbj.get("topic_nucleo"))
        sub = (pbj.get("subskill") or pbj.get("subhabilidad") or "").strip()
        sig = (
            pbj.get("signal_observable") or pbj.get("senal_observable") or ""
        ).strip()
        hyp = (
            pbj.get("functional_hypothesis") or pbj.get("hipotesis_funcional") or ""
        ).strip()
        micro = (pbj.get("micro_objective") or pbj.get("microobjetivo") or "").strip()
        freq = (pbj.get("frequency") or pbj.get("frecuencia") or "").strip()
        dur = (pbj.get("duration") or pbj.get("duracion") or "").strip()
        ind = (
            pbj.get("progress_indicator") or pbj.get("indicador_de_avance") or ""
        ).strip()
        esc = (pbj.get("escalation") or pbj.get("escalamiento") or "").strip()

        steps = pbj.get("steps") or pbj.get("estrategias_paso_a_paso") or []
        if isinstance(steps, str):
            steps = [steps]
        if not isinstance(steps, list):
            steps = []
        steps_list = _dedupe_keep_order(
            [str(x).strip() for x in steps if str(x).strip()]
        )[:8]

        out = {
            "id": (pbj.get("id") or "").strip(),
            "base_row": str(pbj.get("base_row") or "").strip(),
            "topic_nucleo": topic,
            "subhabilidad": sub,
            "senal_observable": sig,
            "hipotesis_funcional": hyp,
            "microobjetivo": micro,
            "estrategias_paso_a_paso": steps_list,
            "frecuencia": freq,
            "duracion": dur,
            "indicador_de_avance": ind,
            "escalamiento": esc,
            "age_min": _to_int_or_none(pbj.get("age_min")),
            "age_max": _to_int_or_none(pbj.get("age_max")),
        }

        if (
            not out["topic_nucleo"]
            and not out["senal_observable"]
            and not out["estrategias_paso_a_paso"]
        ):
            return None

        return out

    # 2) Texto con headers
    inline: Dict[str, str] = {}
    for m in re.finditer(r"^(FRECUENCIA|DURACION)\s*:\s*(.+?)\s*$", text, re.MULTILINE):
        inline[m.group(1)] = (m.group(2) or "").strip()

    age_min_raw = (
        _line_value(text, "AGE_MIN")
        or _line_value(text, "AGE MIN ESPERADO")
        or _line_value(text, "EDAD_MIN")
        or _line_value(text, "EDAD MINIMA ESPERADA")
    )
    age_max_raw = (
        _line_value(text, "AGE_MAX")
        or _line_value(text, "AGE MAX ESPERADO")
        or _line_value(text, "EDAD_MAX")
        or _line_value(text, "EDAD MAXIMA ESPERADA")
    )

    out2: Dict[str, Any] = {
        "id": "",
        "base_row": "",
        "topic_nucleo": normalize_topic_nucleo(_line_value(text, "TOPIC_NUCLEO")),
        "subhabilidad": _line_value(text, "SUBHABILIDAD"),
        "senal_observable": _extract_block(text, "SEÑAL_OBSERVABLE"),
        "hipotesis_funcional": _extract_block(text, "HIPOTESIS_FUNCIONAL"),
        "microobjetivo": _extract_block(text, "MICROOBJETIVO"),
        "estrategias_paso_a_paso": _parse_bullets(
            _extract_block(text, "ESTRATEGIAS_PASO_A_PASO")
        ),
        "frecuencia": inline.get("FRECUENCIA", ""),
        "duracion": inline.get("DURACION", ""),
        "indicador_de_avance": _extract_block(text, "INDICADOR_DE_AVANCE"),
        "escalamiento": _extract_block(text, "ESCALAMIENTO"),
        "age_min": _to_int_or_none(age_min_raw),
        "age_max": _to_int_or_none(age_max_raw),
    }

    out2["estrategias_paso_a_paso"] = _dedupe_keep_order(
        [s for s in out2["estrategias_paso_a_paso"] if s and s.strip()]
    )[:8]

    if (
        not out2["topic_nucleo"]
        and not out2["senal_observable"]
        and not out2["estrategias_paso_a_paso"]
    ):
        return None

    return out2


def retrieve_playbooks(
    store: ChromaPlaybookStore,
    *,
    report_text: str,
    n_results: int = 40,
) -> List[str]:
    """
    Recupera playbooks por similitud semántica.

    Soporta dos tipos de retorno de store.query():
    1) list[str] -> solo documentos
    2) dict -> respuesta cruda de Chroma con documents/metadatas

    Si hay metadatas, enriquece el documento con:
    id, base_row, age_min, age_max
    y regresa JSON string para que parse_playbook_doc_v2 lo lea bien.
    """
    res = (
        store.query(
            query_text=report_text,
            age=None,
            n_results=max(80, n_results),
        )
        or []
    )

    docs: List[str] = []
    metas: List[Dict[str, Any]] = []

    # Caso 1: wrapper ya regresó lista de documentos
    if isinstance(res, list):
        docs = [d for d in res if isinstance(d, str)]

    # Caso 2: respuesta cruda de Chroma
    elif isinstance(res, dict):
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []

        if docs and isinstance(docs[0], list):
            docs = docs[0]
        if metas and isinstance(metas[0], list):
            metas = metas[0]

        docs = [d for d in docs if isinstance(d, str)]

    else:
        print("DEBUG retrieve_playbooks: unsupported_response_type=", type(res))
        return []

    if not docs:
        print("DEBUG retrieve_playbooks: no_docs")
        return []

    out: List[str] = []

    for idx, d in enumerate(docs):
        s = d.strip()
        if not s:
            continue

        pb = parse_playbook_doc_v2(s) or {}

        md = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}

        if md:
            if not pb.get("id"):
                pb["id"] = str(md.get("id") or "")
            if not pb.get("base_row"):
                pb["base_row"] = str(md.get("base_row") or "")
            if pb.get("age_min") is None:
                pb["age_min"] = md.get("age_min")
            if pb.get("age_max") is None:
                pb["age_max"] = md.get("age_max")

            if pb.get("age_min") is None:
                pb["age_min"] = md.get("edad_min")
            if pb.get("age_max") is None:
                pb["age_max"] = md.get("edad_max")

        if pb:
            pb["topic_nucleo"] = normalize_topic_nucleo(pb.get("topic_nucleo"))
            out.append(json.dumps(pb, ensure_ascii=False))
        else:
            out.append(s)

        if len(out) >= n_results:
            break

    print("DEBUG retrieve_playbooks: semantic_only_count=", len(out))
    return out[:n_results]


# =========================
# LEGACY (YA NO USAMOS)
# Motivo: el flujo final usa parse_playbook_doc_v2() + _micro_from_pb().
# Dejamos esto comentado por claridad / rollback rápido.
# =========================

# def parse_playbook_doc(pb_text: str) -> Optional[Dict[str, Any]]:
#     """
#     YA NO USAMOS ESTA FUNCIÓN.
#     Antes: intentaba extraer JSON embebido en texto.
#     Ahora: el doc viene como JSON puro o texto con headers.
#     """
#     return None
#
# def _build_recommendations_from_sheet_playbook(...):
#     """YA NO USAMOS ESTA FUNCIÓN."""
#     return []
#
# def _parse_playbook_doc_v2(...):
#     """YA NO USAMOS ESTA FUNCIÓN (otra variante vieja con PASOS:)."""
#     return None
#
# def _recommendations_from_playbook_fields(...):
#     """YA NO USAMOS ESTA FUNCIÓN."""
#     return []


# =========================
# Main generator
# =========================


def generate_support(
    *,
    student_name: str,
    age: int,
    group: str,
    report_text: str,
    contexts: List[str] | None = None,
    job_id: str | None = None,
) -> Tuple["AIGeneratedSupport", str, Dict[str, Any]]:
    """
    REGLA:
    - Si hay playbook relevante: NO usamos LLM para crear estrategias.
      Construimos microintervenciones SOLO desde el playbook (sin inventar).
    - Si no hay playbook relevante (fallback): usamos LLM para recomendaciones generales
      y agregamos FALLBACK_NOTE al inicio del summary (forzado).
    """

    # ✅ Tokenizador local (evita depender de _tokenize “privado”)
    _TOKEN_RE = re.compile(r"[a-záéíóúñü0-9]+", re.IGNORECASE)
    _STOPWORDS_ES = {
        "a",
        "al",
        "algo",
        "algunas",
        "algunos",
        "ante",
        "antes",
        "como",
        "con",
        "contra",
        "cual",
        "cuales",
        "cuando",
        "de",
        "del",
        "desde",
        "donde",
        "dos",
        "el",
        "ella",
        "ellas",
        "ellos",
        "en",
        "entre",
        "es",
        "esa",
        "esas",
        "ese",
        "eso",
        "esos",
        "esta",
        "estaba",
        "estaban",
        "estan",
        "estar",
        "estas",
        "este",
        "esto",
        "estos",
        "fue",
        "ha",
        "hace",
        "hacen",
        "hacer",
        "hacia",
        "han",
        "hasta",
        "hay",
        "he",
        "hemos",
        "la",
        "las",
        "le",
        "les",
        "lo",
        "los",
        "mas",
        "me",
        "mi",
        "mis",
        "mucha",
        "muchas",
        "mucho",
        "muchos",
        "muy",
        "no",
        "nos",
        "o",
        "os",
        "otra",
        "otras",
        "otro",
        "otros",
        "para",
        "pero",
        "por",
        "porque",
        "que",
        "quien",
        "quienes",
        "se",
        "sea",
        "ser",
        "si",
        "sin",
        "sobre",
        "su",
        "sus",
        "tambien",
        "te",
        "ti",
        "tiene",
        "tienen",
        "todo",
        "todos",
        "tu",
        "tus",
        "un",
        "una",
        "uno",
        "unos",
        "unas",
        "y",
        "ya",
        # tokens frecuentes en reportes
        "alumno",
        "alumna",
        "grupo",
        "años",
        "anio",
        "pre",
        "k",
        "prek",
        "pre-k",
        "fortalezas",
        "retos",
        "notas",
        "señales",
        "senales",
        "observables",
        "opcional",
    }

    def _tokenize_local(text: str) -> List[str]:
        if not text:
            return []
        toks = _TOKEN_RE.findall(text.lower())
        out: List[str] = []
        for t in toks:
            if t in _STOPWORDS_ES:
                continue
            if len(t) <= 2:
                continue
            out.append(t)
        return out

    def build_query_text(report_text_in: str) -> str:
        """
        Query limpio para retrieval/rerank (prioriza señales + notas; quita headers y bullets).
        """
        if not report_text_in:
            return ""
        lines: List[str] = []
        for ln in report_text_in.splitlines():
            s = ln.strip()
            if not s:
                continue
            low = s.lower()

            if low.startswith("señales observables") or low.startswith(
                "senales observables"
            ):
                continue
            if low.startswith("notas") or low.startswith("nota"):
                continue
            if low.startswith("crear nuevo reporte"):
                continue

            s = re.sub(r"^[-•*]\s*", "", s).strip()
            if s:
                lines.append(s)

        txt = " ".join(lines).strip()
        return txt[:800]

    def evidence_overlap_ratio(query_text: str, pb_doc: str) -> float:
        """
        Overlap de tokens entre el reporte y campos clave del playbook.
        Funciona tanto para JSON como para texto con headers.
        """
        q = set(_tokenize_local(query_text))
        if not q:
            return 0.0

        pb = parse_playbook_doc_v2(pb_doc)  # <- tu parser unificado (JSON + texto)
        if not pb:
            return 0.0

        sig = (pb.get("senal_observable") or "").strip()
        micro = (pb.get("microobjetivo") or "").strip()
        sub = (pb.get("subhabilidad") or "").strip()

        # opcional: incluir pasos para mejorar recall de evidencia
        steps = pb.get("estrategias_paso_a_paso") or []
        if isinstance(steps, list):
            steps_txt = " ".join([str(x).strip() for x in steps if str(x).strip()])
        else:
            steps_txt = ""

        text = f"{sig} {micro} {sub} {steps_txt}".strip()
        d = set(_tokenize_local(text))
        if not d:
            return 0.0

        return len(q & d) / len(q)

    def _pick_subset_from_pool(
        pool_docs: List[str],
        *,
        job_id_seed: str | None,
        min_k: int = 2,
        max_k: int = 3,
    ) -> List[str]:
        if not pool_docs:
            return []

        pool_size = len(pool_docs)

        k = math.ceil(pool_size / 2)
        k = min(max_k, k)
        k = min(k, pool_size)
        if pool_size >= min_k:
            k = max(min_k, k)

        seed_src = job_id_seed or ("|".join(pool_docs[:3]) + f":{pool_size}")
        seed_int = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest()[:16], 16)
        rng = random.Random(seed_int)

        if k >= pool_size:
            return pool_docs[:]
        return rng.sample(pool_docs, k=k)

    def _to_int_or_none(v: Any) -> Optional[int]:
        try:
            if v is None or str(v).strip() == "":
                return None
            return int(v)
        except Exception:
            return None

    def _age_status_for_playbook(pb: Dict[str, Any], student_age: int) -> str:
        """
        Regresa:
        - 'below_range'
        - 'in_range'
        - 'above_range'
        - 'unknown_range'
        """
        amin = _to_int_or_none(pb.get("age_min"))
        amax = _to_int_or_none(pb.get("age_max"))

        if amin is None or amax is None:
            return "unknown_range"

        if student_age < amin:
            return "below_range"
        if student_age > amax:
            return "above_range"
        return "in_range"

    def _micro_from_pb(
        pb: Dict[str, Any], student_age: int
    ) -> Optional[Dict[str, Any]]:
        def _s(x: Any) -> str:
            return (x or "").strip()

        mi = {
            "topic_nucleo": normalize_topic_nucleo(pb.get("topic_nucleo")),
            "subhabilidad": _s(pb.get("subhabilidad")),
            "senal_observable": _s(pb.get("senal_observable")),
            "hipotesis_funcional": _s(pb.get("hipotesis_funcional")),
            "microobjetivo": _s(pb.get("microobjetivo")),
            "estrategias_paso_a_paso": list(pb.get("estrategias_paso_a_paso") or [])[
                :8
            ],
            "frecuencia": _s(pb.get("frecuencia")),
            "duracion": _s(pb.get("duracion")),
            "indicador_de_avance": _s(pb.get("indicador_de_avance")),
            "escalamiento": _s(pb.get("escalamiento")),
            "age_status": _age_status_for_playbook(pb, student_age),
            "age_min": pb.get("age_min"),
            "age_max": pb.get("age_max"),
        }

        if len(normalize_topic_nucleo(mi.get("topic_nucleo"))) < 1:
            return None
        if len(mi["subhabilidad"]) < 2:
            return None
        if len(mi["senal_observable"]) < 5:
            return None
        if len(mi["hipotesis_funcional"]) < 5:
            return None
        if len(mi["microobjetivo"]) < 3:
            return None
        if not mi["estrategias_paso_a_paso"]:
            return None
        if len(mi["frecuencia"]) < 1:
            return None
        if len(mi["duracion"]) < 1:
            return None
        if len(mi["indicador_de_avance"]) < 3:
            return None
        if len(mi["escalamiento"]) < 3:
            return None

        return mi

    def _resolve_final_micro(pb_micro: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        above = [x for x in pb_micro if x.get("age_status") == "above_range"]
        in_range = [x for x in pb_micro if x.get("age_status") == "in_range"]
        below = [x for x in pb_micro if x.get("age_status") == "below_range"]
        unknown = [x for x in pb_micro if x.get("age_status") == "unknown_range"]

        print(
            "DEBUG AGE buckets:",
            {
                "above_range": len(above),
                "in_range": len(in_range),
                "below_range": len(below),
                "unknown_range": len(unknown),
            },
        )

        # Prioridad:
        # 1) above_range
        # 2) in_range
        # 3) below_range
        # 4) unknown_range
        if above:
            print("DEBUG AGE decision=above_range")
            return above
        if in_range:
            print("DEBUG AGE decision=in_range")
            return in_range
        if below:
            print("DEBUG AGE decision=below_range")
            return below
        if unknown:
            print("DEBUG AGE decision=unknown_range")
            return unknown

        print("DEBUG AGE decision=empty")
        return pb_micro

    def _dedupe_micro(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        seen = set()
        for it in items or []:
            key = (
                (
                    " ".join(normalize_topic_nucleo(it.get("topic_nucleo")))
                    + "|"
                    + (it.get("microobjetivo") or "")
                    + "|"
                    + (it.get("senal_observable") or "")
                )
                .strip()
                .lower()
            )
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(it)
        return out

    def _extract_raw_text(resp: Any) -> str:
        if resp is None:
            return ""
        for attr in ("output", "content", "text", "message"):
            if hasattr(resp, attr):
                v = getattr(resp, attr)
                if isinstance(v, str):
                    return v
        if isinstance(resp, str):
            return resp
        return str(resp)

    # ----------------------------
    # 0) Model info
    # ----------------------------
    model_info = get_model_info()

    # ----------------------------
    # 1) Query limpio
    # ----------------------------
    query_text_for_rag = build_query_text(report_text)
    if not query_text_for_rag:
        query_text_for_rag = (report_text or "").strip()[:800]

    # ----------------------------
    # 2) Retrieve pool
    # ----------------------------
    store = ChromaPlaybookStore(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
        collection_name=CHROMA_COLLECTION,
    )
    pool_playbooks: List[str] = (
        retrieve_playbooks(store, report_text=query_text_for_rag, n_results=40) or []
    )

    rag_pool_count = len(pool_playbooks)
    print("DEBUG RAG: age=", age, "rag_pool_count=", rag_pool_count)

    # ----------------------------
    # 3) Rerank + fallback decision
    # ----------------------------
    fallback_used = False
    fallback_reason: Optional[str] = None

    playbooks: List[str] = []
    best_score = 0.0
    second_score = 0.0
    gap = 0.0
    anchor_coverage = 0.0
    anchor_evidence = 0.0
    bucket_docs: List[str] = []
    reranked_pool: List[str] = []
    min_ratio_used = None

    if pool_playbooks:
        pool_norm: List[str] = [_pb_to_search_text(d) for d in pool_playbooks]

        ranked = bm25_rank(query_text_for_rag, pool_norm, top_k=None)
        best_score = ranked[0][1] if ranked else 0.0
        second_score = ranked[1][1] if ranked and len(ranked) > 1 else 0.0
        gap = best_score - second_score

        TOP_RERANK = 10
        top_pairs = ranked[: min(TOP_RERANK, len(ranked))]

        top_debug: List[Dict[str, Any]] = []
        for idx, sc in top_pairs:
            cand = pool_playbooks[idx]
            cov = bm25_coverage(query_text_for_rag, _pb_to_search_text(cand))
            ev = evidence_overlap_ratio(query_text_for_rag, cand)
            info = _pb_debug_info(cand)
            top_debug.append(
                {
                    "rank_idx": idx,
                    "bm25_score": sc,
                    "coverage": cov,
                    "evidence": ev,
                    "id": info.get("id"),
                    "topic_nucleo": normalize_topic_nucleo(info.get("topic_nucleo")),
                    "subhabilidad": info.get("subhabilidad"),
                    "signal_observable": _clip(
                        (info.get("signal_observable") or ""), 120
                    ),
                    "source": info.get("source"),
                    "base_row": info.get("base_row"),
                }
            )

        reranked_pool = [pool_playbooks[i] for (i, _s) in top_pairs]

        anchor_doc = ""
        anchor_cov = 0.0
        anchor_ev = 0.0

        EVIDENCE_MIN = 0.05
        COVERAGE_MIN_ANCHOR = 0.02

        for item in top_debug:
            if (item["evidence"] >= EVIDENCE_MIN) and (
                item["coverage"] >= COVERAGE_MIN_ANCHOR
            ):
                anchor_doc = pool_playbooks[item["rank_idx"]]
                anchor_cov = float(item["coverage"])
                anchor_ev = float(item["evidence"])
                break

        if not anchor_doc and ranked:
            anchor_doc = pool_playbooks[ranked[0][0]]
            anchor_cov = bm25_coverage(
                query_text_for_rag, _pb_to_search_text(anchor_doc)
            )
            anchor_ev = evidence_overlap_ratio(query_text_for_rag, anchor_doc)

        anchor_coverage = anchor_cov
        anchor_evidence = anchor_ev

        print(
            "DEBUG RERANK: top=",
            len(reranked_pool),
            "of pool=",
            rag_pool_count,
            "best_score=",
            best_score,
            "second_score=",
            second_score,
            "gap=",
            gap,
            "anchor_coverage=",
            anchor_coverage,
            "anchor_evidence=",
            anchor_evidence,
        )

        # Thresholds (más estables)
        MIN_EVIDENCE_FOUND = 0.07  # más estricto para "found"
        MIN_COVERAGE_FOUND = 0.035
        MIN_EVIDENCE_POSSIBLE = 0.05  # tu actual
        MIN_COVERAGE_POSSIBLE = 0.02

        decision = "not_found"  # "found" | "possible" | "not_found"
        fallback_reason = None

        if best_score <= 0.0:
            decision = "not_found"
            fallback_reason = "bm25_zero"
        elif (anchor_evidence >= MIN_EVIDENCE_FOUND) and (
            anchor_coverage >= MIN_COVERAGE_FOUND
        ):
            decision = "found"
        elif (anchor_evidence >= MIN_EVIDENCE_POSSIBLE) and (
            anchor_coverage >= MIN_COVERAGE_POSSIBLE
        ):
            decision = "possible"
            fallback_reason = "weak_match"
        else:
            decision = "not_found"
            # conserva razón más específica
            if anchor_evidence < MIN_EVIDENCE_POSSIBLE:
                fallback_reason = "low_evidence"
            elif anchor_coverage < MIN_COVERAGE_POSSIBLE:
                fallback_reason = "low_coverage"
            else:
                fallback_reason = "low_match"

        fallback_used = decision == "not_found"

        print(
            "DEBUG decision=",
            decision,
            "fallback_used=",
            fallback_used,
            "reason=",
            fallback_reason,
        )

        if not fallback_used:
            MIN_RATIO = 0.75
            min_ratio_used = MIN_RATIO

            bucket_pairs = (
                [(i, s) for (i, s) in top_pairs if s >= MIN_RATIO * best_score]
                if best_score > 0
                else top_pairs
            )
            bucket_docs = [pool_playbooks[i] for (i, _s) in bucket_pairs]
            if len(bucket_docs) < 4:
                bucket_docs = reranked_pool[:]

            # asegurar anchor incluido
            if anchor_doc and anchor_doc not in bucket_docs:
                bucket_docs = [anchor_doc] + [d for d in bucket_docs if d != anchor_doc]

            rest_docs = [d for d in bucket_docs if d != anchor_doc]

            # Si es match débil, intenta traer 2 en vez de 1 para mejorar recall
            min_k = 2 if decision == "possible" else 1
            max_k = 2 if decision == "possible" else 2

            picked_rest = _pick_subset_from_pool(
                rest_docs, job_id_seed=job_id, min_k=min_k, max_k=max_k
            )

            playbooks = ([anchor_doc] if anchor_doc else []) + picked_rest
            playbooks = _dedupe_keep_order(playbooks)
        else:
            playbooks = []
    else:
        fallback_used = True
        fallback_reason = "no_candidates"
        print("DEBUG fallback_used=", fallback_used, "reason=", fallback_reason)

    rag_selected_count = len(playbooks)
    print("DEBUG RAG selected_count=", rag_selected_count, "job_id_seed=", job_id)

    # ----------------------------
    # 4) Build output
    # ----------------------------
    if not fallback_used and playbooks:
        parsed_pbs: List[Dict[str, Any]] = []
        for pb_text in playbooks:
            obj = parse_playbook_doc_v2(pb_text)
            if obj:
                parsed_pbs.append(obj)

        print(
            "DEBUG AGE parsed_pbs=",
            [
                {
                    "senal_observable": (pb.get("senal_observable") or "")[:120],
                    "age_min": pb.get("age_min"),
                    "age_max": pb.get("age_max"),
                    "escalamiento": (pb.get("escalamiento") or "")[:120],
                }
                for pb in parsed_pbs
            ],
        )

        pb_micro = _dedupe_micro(
            [mi for pb in parsed_pbs for mi in [_micro_from_pb(pb, age)] if mi]
        )

        print(
            "DEBUG AGE raw_micro=",
            [
                {
                    "senal_observable": (x.get("senal_observable") or "")[:120],
                    "age_status": x.get("age_status"),
                    "age_min": x.get("age_min"),
                    "age_max": x.get("age_max"),
                }
                for x in pb_micro
            ],
        )

        pb_micro = _resolve_final_micro(pb_micro)[:10]

        print(
            "DEBUG AGE final_micro=",
            [
                {
                    "senal_observable": (x.get("senal_observable") or "")[:120],
                    "age_status": x.get("age_status"),
                    "age_min": x.get("age_min"),
                    "age_max": x.get("age_max"),
                }
                for x in pb_micro
            ],
        )

        def _resolve_final_micro(
            pb_micro: List[Dict[str, Any]],
        ) -> List[Dict[str, Any]]:
            above = [x for x in pb_micro if x.get("age_status") == "above_range"]
            in_range = [x for x in pb_micro if x.get("age_status") == "in_range"]
            below = [x for x in pb_micro if x.get("age_status") == "below_range"]

            # PRIORIDAD:
            # 1) above_range
            # 2) in_range
            # 3) below_range

            if above:
                return above
            if in_range:
                return in_range
            if below:
                return below

            return pb_micro

        signals_detected = _dedupe_keep_order(
            [
                (pb.get("senal_observable") or "").strip()
                for pb in parsed_pbs
                if (pb.get("senal_observable") or "").strip()
            ]
        )[:10]

        problem_lines = _dedupe_keep_order(
            [
                re.sub(r"^[-•*]\s*", "", ln.strip()).strip()
                for ln in (report_text or "").splitlines()
                if ln.strip()
            ]
        )
        problem_preview = " ".join(problem_lines)[:420]

        def _build_age_framing(pb_micro: List[Dict[str, Any]]) -> Dict[str, str]:
            above_items = [x for x in pb_micro if x.get("age_status") == "above_range"]
            below_items = [x for x in pb_micro if x.get("age_status") == "below_range"]

            if above_items:
                escalations: List[str] = []
                for item in above_items:
                    esc = (item.get("escalamiento") or "").strip()
                    if esc and esc not in escalations:
                        escalations.append(esc)

                escalation_text = " ".join(escalations[:2]).strip()

                teacher_intro = (
                    "Por la edad del alumno, esta señal requiere mayor atención. "
                    "Antes de aplicar las estrategias, considera lo siguiente:"
                )
                parent_intro = (
                    "Por la edad del alumno, esta señal merece observarse con mayor atención. "
                    "Antes de aplicar las estrategias, considera lo siguiente:"
                )

                if escalation_text:
                    teacher_intro = f"{teacher_intro}\n{escalation_text}"
                    parent_intro = f"{parent_intro}\n{escalation_text}"

                return {
                    "teacher_intro": teacher_intro,
                    "parent_intro": parent_intro,
                }

            if below_items:
                msg = (
                    "No te preocupes, esta señal puede ser esperada para su edad. "
                    "Aun así, te compartimos algunas estrategias útiles para acompañar su desarrollo."
                )
                return {
                    "teacher_intro": msg,
                    "parent_intro": msg,
                }

            return {
                "teacher_intro": "Estrategias seleccionadas del Playbook JCJ para este caso.",
                "parent_intro": "Sugerencias basadas en el Playbook JCJ para este caso.",
            }

        framing = _build_age_framing(pb_micro)

        teacher_summary = (
            f"Resumen del reporte del maestro: {problem_preview}\n"
            f"{framing['teacher_intro']}"
        )[:800]

        parent_summary = (
            f"Resumen del reporte del maestro: {problem_preview}\n"
            f"{framing['parent_intro']}"
        )[:800]

        data: Dict[str, Any] = {
            "teacher_version": {
                "summary": teacher_summary,
                "signals_detected": signals_detected,
                "microintervenciones": pb_micro[:10],
            },
            "parent_version": {
                "summary": parent_summary,
                "signals_detected": signals_detected,
                "microintervenciones": pb_micro[:10],
            },
            "guardrails": {
                "no_diagnosis_confirmed": True,
                "no_clinical_labels_confirmed": True,
            },
        }

        combined_text = json.dumps(data, ensure_ascii=False).lower()
        ok, hits = check_guardrails(combined_text)
        if not ok:
            raise ValueError(f"Guardrails failed. Banned terms found: {hits}")

        parsed = AIGeneratedSupport.model_validate(data)

    else:
        agent = Agent(model=get_ai_model(), tools=[], instructions=[SYSTEM_PROMPT])
        base_prompt = build_user_prompt(student_name, age, group, report_text)

        prompt = (
            f"{base_prompt}\n\n"
            "=== Playbook JCJ ===\n"
            "(NO SE ENCONTRARON estrategias JCJ relevantes.)\n\n"
            "Instrucciones adicionales:\n"
            "- Devuelve SOLO JSON válido (sin markdown, sin texto extra).\n"
            "- No uses lenguaje clínico/diagnóstico.\n"
            "- Haz recomendaciones GENERALES (no atribuir a JCJ).\n"
            "- En teacher_version.summary y parent_version.summary, INICIA con exactamente esta nota:\n"
            f"{FALLBACK_NOTE}\n"
        )

        resp = agent.run(prompt)
        raw = _strip_code_fences(_extract_raw_text(resp))

        try:
            data = extract_json_object_lenient(raw)
        except Exception:
            fix_prompt = (
                "Tu respuesta NO es JSON válido.\n"
                "Devuelve SOLO un objeto JSON válido, sin markdown, sin comentarios, sin texto extra.\n"
                "Respeta exactamente el esquema.\n\n"
                f"Salida anterior:\n{raw}\n"
            )
            resp2 = agent.run(fix_prompt)
            raw2 = _strip_code_fences(_extract_raw_text(resp2))
            data = extract_json_object_lenient(raw2)

        def _force_note(summary: str) -> str:
            s = (summary or "").strip()
            if not s.startswith("⚠️ Nota:"):
                s = f"{FALLBACK_NOTE}\n\n{s}".strip()
            return s[:800]

        if isinstance(data.get("teacher_version"), dict):
            data["teacher_version"]["summary"] = _force_note(
                data["teacher_version"].get("summary")
            )
        if isinstance(data.get("parent_version"), dict):
            data["parent_version"]["summary"] = _force_note(
                data["parent_version"].get("summary")
            )

        data["guardrails"] = {
            "no_diagnosis_confirmed": True,
            "no_clinical_labels_confirmed": True,
        }

        combined_text = json.dumps(data, ensure_ascii=False).lower()
        ok, hits = check_guardrails(combined_text)
        if not ok:
            raise ValueError(f"Guardrails failed. Banned terms found: {hits}")

        parsed = AIGeneratedSupport.model_validate(data)

    # ----------------------------
    # 5) META worker/UI
    # ----------------------------
    query_full = (report_text or "").strip()
    query_text = query_full[:MAX_FULL] if len(query_full) > MAX_FULL else query_full

    model_output_text = ""
    try:
        model_output_text = str(parsed.parent_version.summary or "")
    except Exception:
        model_output_text = ""

    meta: Dict[str, Any] = {
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "context": contexts or [],
        "query_text": query_text,
        "query_preview": _clip(query_text, 240),
        "model_output_preview": _clip(model_output_text, 240),
        "rag_pool_count": rag_pool_count,
        "rag_selected_count": rag_selected_count,
        "playbook_used": (rag_selected_count > 0) and (not fallback_used),
        "job_id_seed": job_id,
        "rerank_best_score": best_score,
        "rerank_second_score": second_score,
        "rerank_gap": gap,
        "rerank_anchor_coverage": anchor_coverage,
        "rerank_anchor_evidence": anchor_evidence,
        "rerank_top_n": 10 if pool_playbooks else 0,
        "rerank_bucket_size": len(bucket_docs) if bucket_docs else 0,
        "rerank_min_ratio": min_ratio_used,
        "rag_query_text": query_text_for_rag,
        "rerank_decision": decision if pool_playbooks else "not_found",
        "rerank_top_candidates": top_debug[:10] if pool_playbooks else [],
    }

    def _age_status_for_playbook(pb: Dict[str, Any], student_age: int) -> str:
        amin = _to_int_or_none(pb.get("age_min"))
        amax = _to_int_or_none(pb.get("age_max"))

        if amin is None or amax is None:
            print(
                "DEBUG AGE compare:",
                {
                    "student_age": student_age,
                    "age_min": amin,
                    "age_max": amax,
                    "status": "unknown_range",
                    "signal": (pb.get("senal_observable") or "")[:120],
                },
            )
            return "unknown_range"

        if student_age < amin:
            print(
                "DEBUG AGE compare:",
                {
                    "student_age": student_age,
                    "age_min": amin,
                    "age_max": amax,
                    "status": "below_range",
                    "signal": (pb.get("senal_observable") or "")[:120],
                },
            )
            return "below_range"

        if student_age > amax:
            print(
                "DEBUG AGE compare:",
                {
                    "student_age": student_age,
                    "age_min": amin,
                    "age_max": amax,
                    "status": "above_range",
                    "signal": (pb.get("senal_observable") or "")[:120],
                },
            )
            return "above_range"

        print(
            "DEBUG AGE compare:",
            {
                "student_age": student_age,
                "age_min": amin,
                "age_max": amax,
                "status": "in_range",
                "signal": (pb.get("senal_observable") or "")[:120],
            },
        )
        return "in_range"

    return parsed, model_info.name, meta
