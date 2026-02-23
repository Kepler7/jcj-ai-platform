from __future__ import annotations

import json
import re
from typing import List, Tuple, Optional, Any, Dict
import hashlib
import math
import random

from agno.agent import Agent

from app.ai.providers import get_ai_model, get_model_info
from app.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from app.ai.json_utils import extract_json_object, _extract_raw_text
from app.ai.guardrails import check_guardrails
from app.ai.schemas import AIGeneratedSupport

try:
    from app.ai.schemas import SupportMeta  # type: ignore
except Exception:
    SupportMeta = None  # type: ignore


from app.rag.chroma_client import ChromaPlaybookStore
from app.ai.rerank_bm25 import bm25_rank, bm25_coverage, _tokenize


# =========================
# RAG helpers (NEW)
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

_HDR_RE = re.compile(
    r"^(?P<hdr>" + "|".join(map(re.escape, SECTION_HEADERS)) + r")\s*:\s*$",
    re.MULTILINE,
)

_INLINE_RE = re.compile(
    r"^(?P<hdr>FRECUENCIA|DURACION)\s*:\s*(?P<val>.+?)\s*$",
    re.MULTILINE,
)


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
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
        # soporta "- paso" o "• paso"
        ln = re.sub(r"^[-•]\s*", "", ln).strip()
        if ln:
            steps.append(ln)
    return steps


def parse_playbook_doc_v2(doc: str) -> Optional[Dict[str, Any]]:
    """
    Parsea el DOC que guardas en Chroma (formato con headers underscore).
    Regresa dict con keys: topic_nucleo, subskill, signal_observable,
    functional_hypothesis, micro_objective, steps, frequency, duration,
    progress_indicator, escalation.
    """
    if not doc or not isinstance(doc, str):
        return None

    text = doc.strip()

    # Capturar valores INLINE (FRECUENCIA/DURACION) porque vienen en la misma línea
    inline_vals: Dict[str, str] = {}
    for m in _INLINE_RE.finditer(text):
        inline_vals[m.group("hdr")] = (m.group("val") or "").strip()

    # Encontrar headers "solos" (línea con HEADER:)
    matches = list(_HDR_RE.finditer(text))

    # OJO: TOPIC_NUCLEO y SUBHABILIDAD vienen como "TOPIC_NUCLEO: xxx" en la misma línea (según tu doc)
    # así que también hacemos fallback por línea.
    def _line_value(prefix: str) -> str:
        m = re.search(rf"^{re.escape(prefix)}\s*:\s*(.+?)\s*$", text, re.MULTILINE)
        return (m.group(1) if m else "").strip()

    out: Dict[str, Any] = {
        "topic_nucleo": _line_value("TOPIC_NUCLEO"),
        "subskill": _line_value("SUBHABILIDAD"),
        "signal_observable": "",
        "functional_hypothesis": "",
        "micro_objective": "",
        "steps": [],
        "frequency": inline_vals.get("FRECUENCIA", ""),
        "duration": inline_vals.get("DURACION", ""),
        "progress_indicator": "",
        "escalation": "",
    }

    # Helper: extraer bloque entre headers tipo:
    # HEADER:
    # contenido...
    # NEXT_HEADER:
    def _extract_block(header: str) -> str:
        # Caso "HEADER:\n....\n\nNEXT:"
        pat = re.compile(
            rf"^{re.escape(header)}\s*:\s*\n(?P<body>.*?)(?=^\w+[\w_]*\s*:|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        m = pat.search(text)
        return (m.group("body") if m else "").strip()

    # Bloques multi-línea
    out["signal_observable"] = _extract_block("SEÑAL_OBSERVABLE")
    out["functional_hypothesis"] = _extract_block("HIPOTESIS_FUNCIONAL")
    out["micro_objective"] = _extract_block("MICROOBJETIVO")
    out["progress_indicator"] = _extract_block("INDICADOR_DE_AVANCE")
    out["escalation"] = _extract_block("ESCALAMIENTO")

    steps_block = _extract_block("ESTRATEGIAS_PASO_A_PASO")
    out["steps"] = _parse_bullets(steps_block)

    # Limpieza final
    for k in [
        "topic_nucleo",
        "subskill",
        "signal_observable",
        "functional_hypothesis",
        "micro_objective",
        "progress_indicator",
        "escalation",
    ]:
        out[k] = (out.get(k) or "").strip()

    out["steps"] = _dedupe_keep_order(
        [s.strip() for s in (out.get("steps") or []) if s and s.strip()]
    )

    # Si está demasiado vacío, lo descartamos (evita NoneType.get y fallos)
    if not out["topic_nucleo"] and not out["signal_observable"] and not out["steps"]:
        return None

    return out


def _build_recommendations_from_sheet_playbook(
    *,
    pb: Dict[str, Any],
    mode: str,  # "teacher" o "parent"
    max_steps: int = 8,
) -> List[Dict[str, Any]]:
    """
    Convierte un playbook (nuevo schema) a 1 recomendación fuerte (o más si quieres luego).
    """
    micro = (pb.get("micro_objective") or "").strip()
    subskill = (pb.get("subskill") or "").strip()
    steps: List[str] = list(pb.get("steps") or [])

    steps = steps[:max_steps] if steps else []
    if not micro and not steps:
        return []

    title_parts = []
    if micro:
        title_parts.append(micro)
    if subskill:
        title_parts.append(subskill)
    title = " / ".join(title_parts)[:120] if title_parts else "Estrategia JCJ"

    freq = (pb.get("frequency") or "").strip()
    dur = (pb.get("duration") or "").strip()
    ind = (pb.get("progress_indicator") or "").strip()
    esc = (pb.get("escalation") or "").strip()

    when_parts = []
    if mode == "teacher":
        when_parts.append("En aula")
    else:
        when_parts.append("En casa")

    if freq:
        when_parts.append(f"Frecuencia: {freq}")
    if dur:
        when_parts.append(f"Duración: {dur}")
    if ind:
        when_parts.append(f"Indicador: {ind}")

    when_to_use = ". ".join(when_parts)[:200]

    # Meter escalamiento como último paso (sin romper when_to_use)
    final_steps = steps[:]
    if esc:
        final_steps.append(f"Escalamiento: {esc}")

    # Si steps sigue vacío, al menos 1 paso
    if not final_steps:
        final_steps = [micro] if micro else ["Aplicar estrategia según observación."]

    return [
        {
            "title": title,
            "steps": final_steps[:max_steps],
            "when_to_use": when_to_use,
        }
    ]


def retrieve_playbooks(
    store,
    *,
    report_text: str,
    age: int,
    n_results: int = 3,
) -> List[str]:
    """
    Recupera playbooks relevantes desde Chroma usando:
    - similitud semántica (query_text)
    - filtro por edad (age_min <= age <= age_max)
    """
    docs = store.query(
        query_text=report_text,
        age=age,
        n_results=n_results,
    )
    # store.query debe devolver List[str] (docs)
    return docs or []


# =========================
# Main generator (MODIFIED)
# =========================

MAX_FULL = 4000  # protección contra textos enormes en DB (ajústalo si quieres)


def _clip(s: str, n: int) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[:n].rstrip() + "..."


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


# --- helpers para parsear el DOC del playbook nuevo (texto) ---


def _s(x: Any) -> str:
    return "" if x is None else str(x).strip()


def _clip(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else (s[:n].rstrip() + "...")


def _parse_playbook_doc_v2(doc: str) -> Dict[str, Any] | None:
    """
    Espera un doc que tenga etiquetas tipo:
      TOPIC_NUCLEO: ...
      SUBHABILIDAD: ...
      SEÑAL_OBSERVABLE: ...
      EDAD: 2–5
      HIPOTESIS_FUNCIONAL: ...
      MICROOBJETIVO: ...
      PASOS: - ...
      FRECUENCIA: ...
      DURACION: ...
      INDICADOR_DE_AVANCE: ...
      ESCALAMIENTO: ...
    El loader puede formatearlo con saltos o en una sola línea; esto aguanta ambos.
    """
    if not doc or "TOPIC_NUCLEO:" not in doc:
        return None

    # Normaliza espacios / saltos
    text = doc.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)

    def grab(label: str, next_labels: List[str]) -> str:
        # Captura desde "LABEL:" hasta antes del siguiente label
        # Ej: SUBHABILIDAD: ... SEÑAL_OBSERVABLE:
        pattern = (
            label + r"\s*(.*?)\s*(?=(" + "|".join(map(re.escape, next_labels)) + r")|$)"
        )
        m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        return _s(m.group(1)) if m else ""

    labels = [
        "TOPIC_NUCLEO:",
        "SUBHABILIDAD:",
        "SEÑAL_OBSERVABLE:",
        "EDAD:",
        "HIPOTESIS_FUNCIONAL:",
        "MICROOBJETIVO:",
        "PASOS:",
        "FRECUENCIA:",
        "DURACION:",
        "INDICADOR_DE_AVANCE:",
        "ESCALAMIENTO:",
    ]

    topic = grab("TOPIC_NUCLEO:", labels[1:])
    subskill = grab("SUBHABILIDAD:", labels[2:])
    signal = grab("SEÑAL_OBSERVABLE:", labels[3:])
    hypothesis = grab("HIPOTESIS_FUNCIONAL:", labels[5:])  # hasta MICROOBJETIVO
    micro = grab("MICROOBJETIVO:", labels[6:])
    steps_raw = grab("PASOS:", labels[7:])
    frequency = grab("FRECUENCIA:", labels[8:])
    duration = grab("DURACION:", labels[9:])
    progress = grab("INDICADOR_DE_AVANCE:", labels[10:])
    escalation = grab("ESCALAMIENTO:", labels[11:])

    # Steps: acepta "- ..." o "1) ..." o líneas
    steps: List[str] = []
    if steps_raw:
        s = steps_raw.strip()
        s = s.replace("\\n", "\n")
        # intenta bullets
        bullet_split = re.split(r"\n\s*-\s*", "\n" + s)
        if len(bullet_split) > 1:
            steps = [x.strip(" -\n\t") for x in bullet_split if x.strip()]
        else:
            # intenta numerados
            num_split = re.split(r"\n?\s*\d+\s*[.)]\s*", s)
            if len(num_split) > 1:
                steps = [x.strip(" -\n\t") for x in num_split if x.strip()]
            else:
                # líneas
                lines = [ln.strip() for ln in s.split("\n") if ln.strip()]
                steps = lines if lines else [s]

    steps = _dedupe_keep_order(steps)

    return {
        "topic_nucleo": topic,
        "subskill": subskill,
        "signal_observable": signal,
        "functional_hypothesis": hypothesis,
        "micro_objective": micro,
        "steps": steps,
        "frequency": frequency,
        "duration": duration,
        "progress_indicator": progress,
        "escalation": escalation,
    }


def _recommendations_from_playbook_fields(
    pb: Dict[str, Any], mode: str
) -> List[Dict[str, Any]]:
    """
    Convierte un playbook en 1 recomendación fuerte (o 2 si quieres partir pasos).
    mode: "teacher"|"parent"
    """
    steps: List[str] = pb.get("steps") or []
    if not steps:
        return []

    micro = _s(pb.get("micro_objective"))
    freq = _s(pb.get("frequency"))
    dur = _s(pb.get("duration"))
    indicator = _s(pb.get("progress_indicator"))
    escalation = _s(pb.get("escalation"))

    when = []
    if freq:
        when.append(f"Frecuencia: {freq}")
    if dur:
        when.append(f"Duración: {dur}")
    if indicator:
        when.append(f"Indicador: {indicator}")
    if escalation:
        when.append(f"Escalamiento: {escalation}")
    when_to_use = (
        " | ".join(when)
        if when
        else (
            "Durante la rutina diaria"
            if mode == "parent"
            else "Durante actividades en aula"
        )
    )

    title_bits = []
    if micro:
        title_bits.append(micro)
    # fallback por subskill
    if not title_bits and pb.get("subskill"):
        title_bits.append(str(pb["subskill"]))
    title = "JCJ: " + (" – ".join(title_bits) if title_bits else "Intervención")

    # Limitar a 8 pasos (regla IHUI)
    steps = steps[:8]

    return [
        {
            "title": title[:120],
            "steps": steps,
            "when_to_use": when_to_use[:200],
        }
    ]


# -------------------------------------------------------------------

FALLBACK_NOTE = (
    "⚠️ Nota: No se encontraron estrategias específicas en el Playbook JCJ para este caso. "
    "Las sugerencias siguientes son generales y deben ser validadas/ajustadas por el equipo profesional."
)


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

    CODEBLOCK_JSON_RE = re.compile(
        r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE
    )

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

    def parse_playbook_doc_v2(doc: str) -> Optional[Dict[str, Any]]:
        if not doc or not isinstance(doc, str):
            return None

        text = doc.strip()

        inline = {}
        for m in re.finditer(
            r"^(FRECUENCIA|DURACION)\s*:\s*(.+?)\s*$", text, re.MULTILINE
        ):
            inline[m.group(1)] = (m.group(2) or "").strip()

        out: Dict[str, Any] = {
            "topic_nucleo": _line_value(text, "TOPIC_NUCLEO"),
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
        }

        out["estrategias_paso_a_paso"] = _dedupe_keep_order(
            [s for s in (out.get("estrategias_paso_a_paso") or []) if s and s.strip()]
        )[:8]

        if (
            not out["topic_nucleo"]
            and not out["senal_observable"]
            and not out["estrategias_paso_a_paso"]
        ):
            return None

        return out

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

    # ✅ NUEVO: query_text limpio para retrieval/rerank
    def build_query_text(report_text: str) -> str:
        if not report_text:
            return ""
        lines: List[str] = []
        for ln in report_text.splitlines():
            s = ln.strip()
            if not s:
                continue
            low = s.lower()

            # quitar headers típicos
            if low.startswith("señales observables") or low.startswith(
                "senales observables"
            ):
                continue
            if low.startswith("notas") or low.startswith("nota"):
                continue
            if low.startswith("crear nuevo reporte"):
                continue

            # quitar bullets
            s = re.sub(r"^[-•*]\s*", "", s).strip()
            if s:
                lines.append(s)

        txt = " ".join(lines).strip()
        return txt[:800]

    # ✅ NUEVO: gate de evidencia (comparar reporte vs partes clave del playbook)
    def evidence_overlap_ratio(query_text: str, pb_doc: str) -> float:
        q = set(_tokenize_local(query_text))
        if not q:
            return 0.0

        sig = _extract_block(pb_doc, "SEÑAL_OBSERVABLE")
        micro = _extract_block(pb_doc, "MICROOBJETIVO")
        sub = _line_value(pb_doc, "SUBHABILIDAD")
        text = f"{sig} {micro} {sub}".strip()

        d = set(_tokenize_local(text))
        if not d:
            return 0.0

        return len(q & d) / len(q)

    def _micro_from_pb(pb: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        def _s(x: Any) -> str:
            return (x or "").strip()

        mi = {
            "topic_nucleo": _s(pb.get("topic_nucleo")),
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
        }

        # Validación mínima local para evitar romper Pydantic:
        if len(mi["topic_nucleo"]) < 3:
            return None
        if len(mi["subhabilidad"]) < 2:
            return None
        if len(mi["senal_observable"]) < 5:
            return None
        if len(mi["hipotesis_funcional"]) < 5:
            return None
        if len(mi["microobjetivo"]) < 3:
            return None
        if not mi["estrategias_paso_a_paso"] or len(mi["estrategias_paso_a_paso"]) < 1:
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

    def _dedupe_micro(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        seen = set()
        for it in items or []:
            key = (
                (
                    (it.get("topic_nucleo") or "")
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

    # ----------------------------
    # 0) Model info
    # ----------------------------
    model_info = get_model_info()

    # ----------------------------
    # ✅ NUEVO: query_text limpio para retrieval/rerank
    # ----------------------------
    query_text_for_rag = build_query_text(report_text)
    if not query_text_for_rag:
        query_text_for_rag = (report_text or "").strip()[:800]

    # ----------------------------
    # 1) Retrieve pool (SIN cambiar retrieve_playbooks)
    # ----------------------------
    store = ChromaPlaybookStore(
        host="chroma", port=8000, collection_name="jcj_playbooks_v1"
    )
    pool_playbooks: List[str] = (
        retrieve_playbooks(store, report_text=query_text_for_rag, age=age, n_results=40)
        or []
    )

    rag_pool_count = len(pool_playbooks)
    print("DEBUG RAG: age=", age, "rag_pool_count=", rag_pool_count)

    # ----------------------------
    # 2) Rerank + fallback decision
    # ----------------------------
    fallback_used = False
    fallback_reason: Optional[str] = None

    playbooks: List[str] = []
    best_score = 0.0
    second_score = 0.0
    gap = 0.0
    anchor_coverage = 0.0
    anchor_evidence = 0.0  # ✅ NUEVO
    bucket_docs: List[str] = []
    reranked_pool: List[str] = []
    min_ratio_used = None

    if pool_playbooks:
        ranked = bm25_rank(query_text_for_rag, pool_playbooks, top_k=None)
        best_score = ranked[0][1] if ranked else 0.0
        second_score = ranked[1][1] if ranked and len(ranked) > 1 else 0.0
        gap = best_score - second_score

        TOP_RERANK = 10
        top_pairs = ranked[: min(TOP_RERANK, len(ranked))]
        reranked_pool = [pool_playbooks[i] for (i, _s) in top_pairs]

        # ✅ NUEVO: elegimos anchor válido por evidencia (probamos topN)
        anchor_doc = ""
        anchor_score = 0.0
        anchor_cov = 0.0
        anchor_ev = 0.0

        EVIDENCE_MIN = 0.05  # 5% overlap de tokens útiles
        for idx, sc in top_pairs:
            cand = pool_playbooks[idx]
            ev = evidence_overlap_ratio(query_text_for_rag, cand)
            cov = bm25_coverage(query_text_for_rag, cand)
            if ev >= EVIDENCE_MIN and cov >= 0.02:
                anchor_doc = cand
                anchor_score = sc
                anchor_cov = cov
                anchor_ev = ev
                break

        # si ninguno pasó, usamos el top1 para decisión (normalmente caerá a fallback por low_evidence)
        if not anchor_doc and ranked:
            anchor_doc = pool_playbooks[ranked[0][0]]
            anchor_score = best_score
            anchor_cov = bm25_coverage(query_text_for_rag, anchor_doc)
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

        # ✅ regla de fallback + evidencia
        MIN_BEST_SCORE = 4.0
        MIN_COVERAGE_STRONG = 0.06
        MIN_COVERAGE_MIN = 0.03
        MIN_EVIDENCE = 0.05

        if best_score <= 0.0:
            fallback_used = True
            fallback_reason = "bm25_zero"
        elif anchor_evidence < MIN_EVIDENCE:
            fallback_used = True
            fallback_reason = "low_evidence"
        elif anchor_coverage < MIN_COVERAGE_MIN:
            fallback_used = True
            fallback_reason = "low_coverage"
        elif best_score < MIN_BEST_SCORE and anchor_coverage < MIN_COVERAGE_STRONG:
            fallback_used = True
            fallback_reason = "low_best_and_coverage"
        else:
            fallback_used = False
            fallback_reason = None

        print("DEBUG fallback_used=", fallback_used, "reason=", fallback_reason)

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

            # ✅ asegurar anchor incluido
            if anchor_doc and anchor_doc not in bucket_docs:
                bucket_docs = [anchor_doc] + [d for d in bucket_docs if d != anchor_doc]

            rest_docs = [d for d in bucket_docs if d != anchor_doc]
            picked_rest = _pick_subset_from_pool(
                rest_docs, job_id_seed=job_id, min_k=1, max_k=2
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
    # 3) Build output
    # ----------------------------
    if not fallback_used and playbooks:
        # ✅ STRICT: solo playbook
        parsed_pbs: List[Dict[str, Any]] = []
        for pb_text in playbooks:
            obj = parse_playbook_doc_v2(pb_text)
            if obj:
                parsed_pbs.append(obj)

        pb_micro = _dedupe_micro(
            [mi for pb in parsed_pbs for mi in [_micro_from_pb(pb)] if mi]
        )[:10]

        signals_detected = _dedupe_keep_order(
            [
                (pb.get("senal_observable") or "").strip()
                for pb in parsed_pbs
                if (pb.get("senal_observable") or "").strip()
            ]
        )[:10]

        # ✅ Summary: incluye resumen del problema desde el reporte del maestro (sin LLM)
        problem_lines = _dedupe_keep_order(
            [
                re.sub(r"^[-•*]\s*", "", ln.strip()).strip()
                for ln in (report_text or "").splitlines()
                if ln.strip()
            ]
        )
        problem_preview = " ".join(problem_lines)[:420]

        teacher_summary = (
            f"Resumen del reporte del maestro: {problem_preview}\n"
            f"Estrategias seleccionadas del Playbook JCJ para este caso."
        )[:800]

        parent_summary = (
            f"Resumen del reporte del maestro: {problem_preview}\n"
            f"Sugerencias basadas en el Playbook JCJ para este caso."
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
        # ✅ FALLBACK: LLM general + nota
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
    # 4) META worker/UI
    # ----------------------------
    query_full = (report_text or "").strip()
    query_text = query_full[:4000] if len(query_full) > 4000 else query_full

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
        "rerank_anchor_evidence": anchor_evidence,  # ✅ NUEVO
        "rerank_top_n": 10 if pool_playbooks else 0,
        "rerank_bucket_size": len(bucket_docs) if bucket_docs else 0,
        "rerank_min_ratio": min_ratio_used,
        "rag_query_text": query_text_for_rag,  # ✅ NUEVO para debug
    }

    return parsed, model_info.name, meta
