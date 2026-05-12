import json
import logging
import os
from typing import Any, Dict, List, Optional

from app.modules.ai_guardrails.audit import build_guardrail_audit_payload

from agno.agent import Agent
from sqlalchemy.orm import Session

from app.ai.orchestrator import parse_playbook_doc_v2, retrieve_playbooks
from app.ai.providers import get_ai_model
from app.ai.schemas import (
    AIGeneratedSupport,
    GuardrailsBlock,
    MicroIntervention,
    ParentVersion,
    TeacherVersion,
)
from app.modules.ai_feedback.schemas import AIPredictionCreate
from app.modules.ai_feedback.service import create_ai_prediction
from app.rag.chroma_client import ChromaPlaybookStore
from app.ai.orchestrator import (
    generate_support,
    _strip_code_fences,
    check_guardrails,
    extract_json_object_lenient,
)
from app.ai.utils.normalization import normalize_topic_nucleo
from app.modules.ai_guardrails.pipeline import run_input_guardrails

logger = logging.getLogger(__name__)

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "jcj_playbooks_v1")

# ----------------------------
# CONFIG
# ----------------------------
CONFIRMED_THRESHOLD = 0.85
PENDING_THRESHOLD = 0.60


def _coerce_topic_nucleo_in_support(data: dict) -> dict:
    for version_key in ("teacher_version", "parent_version"):
        version = data.get(version_key) or {}
        micros = version.get("microintervenciones") or []

        if not isinstance(micros, list):
            continue

        for micro in micros:
            if not isinstance(micro, dict):
                continue

            micro["topic_nucleo"] = normalize_topic_nucleo(micro.get("topic_nucleo"))

    return data


def build_general_fallback_response(
    report_text: str,
    age: int,
    prediction_id,
) -> AIGeneratedSupport:
    """
    Construye una respuesta general cuando:
    - no hubo match suficiente con playbooks
    - o el sistema necesita caer a fallback general

    ¿Por qué la movimos a nivel módulo?
    Porque así se puede:
    - testear mejor
    - mockear en unit tests
    - reutilizar sin depender del scope interno de generate_support_v2
    """
    disclaimer = (
        "⚠️ Nota: No se encontraron estrategias específicas en el Playbook JCJ "
        "para este caso. Las sugerencias siguientes son generales y deben ser "
        "validadas/ajustadas por el equipo profesional."
    )

    def _extract_raw_text(resp: Any) -> str:
        """
        Intenta sacar texto útil desde distintas formas de respuesta del agente.
        """
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

    def _force_note(summary: str) -> str:
        """
        Asegura que el summary empiece con la nota de fallback.
        """
        s = (summary or "").strip()
        if not s.startswith("⚠️ Nota:"):
            s = f"{disclaimer}\n\n{s}".strip()
        return s[:800]

    schema_hint = {
        "teacher_version": {
            "summary": "string",
            "signals_detected": ["string"],
            "microintervenciones": [
                {
                    "topic_nucleo": [
                        "string (1..10 elementos, cada uno corto y claro)"
                    ],
                    "subhabilidad": "string",
                    "senal_observable": "string",
                    "hipotesis_funcional": "string",
                    "microobjetivo": "string",
                    "estrategias_paso_a_paso": ["string"],
                    "frecuencia": "string",
                    "duracion": "string",
                    "indicador_de_avance": "string",
                    "escalamiento": "string",
                }
            ],
        },
        "parent_version": {
            "summary": "string",
            "signals_detected": ["string"],
            "microintervenciones": [
                {
                    "topic_nucleo": [
                        "string (1..10 elementos, cada uno corto y claro)"
                    ],
                    "subhabilidad": "string",
                    "senal_observable": "string",
                    "hipotesis_funcional": "string",
                    "microobjetivo": "string",
                    "estrategias_paso_a_paso": ["string"],
                    "frecuencia": "string",
                    "duracion": "string",
                    "indicador_de_avance": "string",
                    "escalamiento": "string",
                }
            ],
        },
        "guardrails": {
            "no_diagnosis_confirmed": True,
            "no_clinical_labels_confirmed": True,
        },
    }

    prompt = f"""
Genera una respuesta de apoyo GENERAL para un alumno de {age} años.

IMPORTANTE:
- Devuelve SOLO JSON válido.
- No uses markdown.
- No des diagnósticos.
- No uses etiquetas clínicas como si fueran confirmaciones.
- Debes seguir esta estructura:

{json.dumps(schema_hint, ensure_ascii=False, indent=2)}

Reporte:
{report_text}
""".strip()

    try:
        agent = Agent(model=get_ai_model(), tools=[])
        resp = agent.run(prompt)
        raw = _strip_code_fences(_extract_raw_text(resp))
        data = extract_json_object_lenient(raw)

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

        data = _coerce_topic_nucleo_in_support(data)
        return AIGeneratedSupport.model_validate(data)

    except Exception:
        teacher_msg = (
            f"{disclaimer}\n\n"
            "Como apoyo inicial en aula, se recomienda observar con mayor precisión "
            "en qué momentos aparece la dificultad, reducir demandas simultáneas, "
            "dar instrucciones breves y claras, ofrecer apoyo visual cuando sea útil "
            "y registrar qué estrategias ayudan más al alumno."
        )

        parent_msg = (
            f"{disclaimer}\n\n"
            "Como apoyo inicial en casa, se recomienda mantener rutinas claras, "
            "dar una instrucción a la vez, reforzar avances pequeños, anticipar cambios "
            "y observar si hay momentos, ambientes o estímulos que aumentan o disminuyen "
            "la dificultad."
        )

        return AIGeneratedSupport(
            teacher_version=TeacherVersion(
                summary=teacher_msg,
                signals_detected=[],
                microintervenciones=[],
            ),
            parent_version=ParentVersion(
                summary=parent_msg,
                signals_detected=[],
                microintervenciones=[],
            ),
            guardrails=GuardrailsBlock(
                no_diagnosis_confirmed=True,
                no_clinical_labels_confirmed=True,
            ),
        )


# ----------------------------
# MAIN
# ----------------------------
def generate_support_v2(
    db: Session,
    *,
    report_id,
    report_text: str,
    age: int,
    student_id=None,
    school_id=None,
    model_name: str = "v2-llm-rerank",
) -> Dict[str, Any]:

    # ----------------------------
    # 0) INPUT GUARDRAILS
    # ----------------------------
    # Aquí protegemos la entrada ANTES de pasarla al retrieval o al modelo.
    input_guardrails = run_input_guardrails(report_text)

    # Este es el texto que sí está permitido usar en el flujo.
    # Si había PII, aquí ya vendrá redactada.
    sanitized_report_text = input_guardrails.sanitized_text

    # Metadata estructurada de guardrails de entrada.
    # La armamos desde el inicio para reutilizarla en cualquier ruta:
    # normal, safeguarding_review o block.
    input_guardrails_meta = {
        "safe": input_guardrails.safe,
        "should_block": input_guardrails.should_block,
        "should_restrict": input_guardrails.should_restrict,
        "risk_level": input_guardrails.risk_level,
        "flags": input_guardrails.flags,
        "blocked_reason": input_guardrails.blocked_reason,
        "route": input_guardrails.route,
        "response_mode": input_guardrails.response_mode,
        "human_review_required": input_guardrails.human_review_required,
        "allow_rag": input_guardrails.allow_rag,
        "allow_llm_generation": input_guardrails.allow_llm_generation,
        "classification": input_guardrails.classification.model_dump(),
    }

    # Auditoría estructurada del router de entrada.
    # Esto nos ayuda a observar qué decidió IHUI antes de entrar
    # al flujo normal, safeguarding o bloqueo.
    audit_payload = build_guardrail_audit_payload(
        report_id=str(report_id) if report_id is not None else None,
        student_id=str(student_id) if student_id is not None else None,
        school_id=str(school_id) if school_id is not None else None,
        route=input_guardrails.route,
        risk_level=input_guardrails.risk_level,
        input_guardrails_meta=input_guardrails_meta,
        sanitized_report_text=sanitized_report_text,
    )

    logger.info(
        "AI guardrails/router decision: %s",
        json.dumps(audit_payload, ensure_ascii=False),
    )

    # Si el pipeline decide bloquear, salimos temprano.
    # En este primer paso NO guardamos prediction en DB para evitar
    # contaminar datos con entradas bloqueadas.
    if input_guardrails.should_block:
        return {
            "status": "guardrails_blocked",
            "prediction_id": None,
            "support": build_guardrails_blocked_response(
                input_guardrails.blocked_reason
            ),
            "model_name": model_name,
            "meta": {
                "prediction_status": "guardrails_blocked",
                "fallback_used": False,
                "input_guardrails": input_guardrails_meta,
            },
        }
    # Si el caso es sensible legítimo, NO seguimos al flujo normal.
    # Salimos temprano con una respuesta restringida.
    if input_guardrails.should_restrict:
        return {
            "status": "safeguarding_review",
            "prediction_id": None,
            "support": build_safeguarding_review_response(
                input_guardrails.classification
            ),
            "model_name": model_name,
            "meta": {
                "prediction_status": "safeguarding_review",
                "fallback_used": False,
                "input_guardrails": input_guardrails_meta,
            },
        }

    store = ChromaPlaybookStore(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
        collection_name=CHROMA_COLLECTION,
    )

    # Usamos el texto sanitizado para no mandar PII al retrieval.
    raw_docs: List[str] = retrieve_playbooks(
        store=store,
        report_text=sanitized_report_text,
        n_results=40,
    )

    parsed_playbooks: List[Dict[str, Any]] = []
    for d in raw_docs:
        pb = parse_playbook_doc_v2(d)
        if pb:
            parsed_playbooks.append(pb)

    parsed_playbooks = _dedupe_playbooks(parsed_playbooks)

    # ----------------------------
    # 2) RERANK
    # ----------------------------
    # El rerank también debe usar el texto sanitizado.
    scored = llm_rerank_playbooks(sanitized_report_text, parsed_playbooks)

    # fallback local si el LLM falla o no regresa nada útil
    if not scored:
        scored = local_rerank_playbooks(sanitized_report_text, parsed_playbooks)

    top1 = scored[0] if scored else None
    top2 = scored[1] if len(scored) > 1 else None

    top1_score = float(top1["score"]) if top1 else 0.0
    top2_score = float(top2["score"]) if top2 else 0.0
    gap = top1_score - top2_score

    # ----------------------------
    # 3) DECISION POLICY
    # ----------------------------
    if top1 and top1_score >= CONFIRMED_THRESHOLD:
        status = "confirmed_jcj"
    elif top1 and top1_score >= PENDING_THRESHOLD:
        status = "pending_human_review"
    else:
        status = "general_fallback"

    # ----------------------------
    # 4) SAVE PREDICTION
    # ----------------------------
    prediction = create_ai_prediction(
        db,
        AIPredictionCreate(
            school_id=school_id,
            student_id=student_id,
            report_id=report_id,
            predicted_playbook_id=extract_playbook_id(top1),
            predicted_playbook_base_row=extract_base_row(top1),
            status=status,
            confidence_score=top1_score,
            confidence_gap=gap,
            top_candidates_json=[extract_playbook_id(x) for x in scored[:3]],
            top_scores_json=[float(x["score"]) for x in scored[:3]],
            retrieval_version="v1",
            reranker_version="llm_rerank_with_local_fallback",
            used_hyde=False,
            model_name=model_name,
        ),
    )

    # ----------------------------
    # 5) BUILD RESPONSE
    # ----------------------------
    if status == "confirmed_jcj":
        return {
            "status": status,
            "prediction_id": str(prediction.id),
            "support": build_confirmed_response(top1["playbook"], age, prediction.id),
            "model_name": model_name,
            "meta": {
                "prediction_status": status,
                "prediction_id": str(prediction.id),
                "confidence_score": top1_score,
                "confidence_gap": gap,
                "top_candidates": [extract_playbook_id(x) for x in scored[:3]],
                "fallback_used": False,
                "input_guardrails": input_guardrails_meta,
            },
        }

    if status == "pending_human_review":
        return {
            "status": status,
            "prediction_id": str(prediction.id),
            "support": build_pending_response(prediction.id),
            "model_name": model_name,
            "meta": {
                "prediction_status": status,
                "prediction_id": str(prediction.id),
                "confidence_score": top1_score,
                "confidence_gap": gap,
                "top_candidates": [extract_playbook_id(x) for x in scored[:3]],
                "fallback_used": False,
                "input_guardrails": input_guardrails_meta,
            },
        }

    return {
        "status": status,
        "prediction_id": str(prediction.id),
        "support": build_general_fallback_response(
            sanitized_report_text,
            age,
            prediction.id,
        ),
        "model_name": model_name,
        "meta": {
            "prediction_status": status,
            "prediction_id": str(prediction.id),
            "confidence_score": top1_score,
            "confidence_gap": gap,
            "top_candidates": [extract_playbook_id(x) for x in scored[:3]],
            "fallback_used": True,
            "fallback_reason": "no_match",
            "input_guardrails": input_guardrails_meta,
        },
    }


# ----------------------------
# HELPERS
# ----------------------------
def _dedupe_playbooks(playbooks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()

    for pb in playbooks:
        topic_key = "|".join(normalize_topic_nucleo(pb.get("topic_nucleo")))

        key = (pb.get("id") or "").strip() or (
            (
                topic_key
                + "|"
                + str(pb.get("subhabilidad") or "").strip()
                + "|"
                + str(pb.get("senal_observable") or "").strip()
            )
            .strip()
            .lower()
        )

        if not key or key in seen:
            continue

        seen.add(key)
        out.append(pb)

    return out


def local_rerank_playbooks(
    report_text: str, playbooks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Fallback local sencillo si el LLM falla.
    """
    scored = []

    report_tokens = set(_normalize_tokens(report_text))

    for pb in playbooks:
        topic_text = " ".join(normalize_topic_nucleo(pb.get("topic_nucleo")))

        candidate_text = " ".join(
            [
                topic_text,
                str(pb.get("subhabilidad", "") or ""),
                str(pb.get("senal_observable", "") or ""),
                str(pb.get("microobjetivo", "") or ""),
                str(pb.get("hipotesis_funcional", "") or ""),
            ]
        )

        candidate_tokens = set(_normalize_tokens(candidate_text))
        if not report_tokens:
            score = 0.0
        else:
            score = len(report_tokens & candidate_tokens) / max(len(report_tokens), 1)

        scored.append({"playbook": pb, "score": float(score)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def _normalize_tokens(text: str) -> List[str]:
    if not text:
        return []
    text = text.lower()
    for ch in [
        ",",
        ".",
        ";",
        ":",
        "(",
        ")",
        '"',
        "'",
        "\n",
        "\t",
        "-",
        "/",
        "¿",
        "?",
        "¡",
        "!",
    ]:
        text = text.replace(ch, " ")
    return [t.strip() for t in text.split() if t.strip()]


def llm_rerank_playbooks(
    report_text: str, playbooks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Usa el LLM para elegir el mejor playbook entre los candidatos.
    Regresa una lista tipo:
    [
      {"playbook": pb, "score": 0.87},
      ...
    ]
    """
    if not playbooks:
        return []

    candidates = playbooks[:8]

    formatted = []
    for i, pb in enumerate(candidates):
        formatted.append(
            {
                "index": i,
                "id": pb.get("id"),
                "topic_nucleo": ", ".join(
                    normalize_topic_nucleo(pb.get("topic_nucleo"))
                ),
                "subhabilidad": pb.get("subhabilidad"),
                "senal_observable": pb.get("senal_observable"),
                "microobjetivo": pb.get("microobjetivo"),
                "hipotesis_funcional": pb.get("hipotesis_funcional"),
            }
        )

    prompt = f"""
Eres experto en desarrollo infantil y estrategias educativas JCJ.

Dado este reporte de maestro:

{report_text}

Y estos posibles playbooks candidatos:

{json.dumps(formatted, ensure_ascii=False, indent=2)}

Tu tarea:
1. Elige el playbook MÁS relevante.
2. Si hay un segundo candidato razonable, inclúyelo también.
3. Asigna una confianza entre 0 y 1.

Responde SOLO JSON válido con este formato:
{{
  "ranked": [
    {{"best_index": 0, "confidence": 0.88}},
    {{"best_index": 1, "confidence": 0.62}}
  ]
}}
"""

    try:
        agent = Agent(model=get_ai_model(), tools=[], instructions=[])
        resp = agent.run(prompt)

        raw = _extract_raw_text(resp)
        data = _extract_json(raw)

        ranked = data.get("ranked") or []
        out: List[Dict[str, Any]] = []

        for item in ranked:
            idx = int(item.get("best_index", -1))
            conf = float(item.get("confidence", 0.0))
            if 0 <= idx < len(candidates):
                out.append(
                    {
                        "playbook": candidates[idx],
                        "score": conf,
                    }
                )

        # dedupe por id
        deduped: List[Dict[str, Any]] = []
        seen = set()
        for x in out:
            pbid = x["playbook"].get("id") or id(x["playbook"])
            if pbid in seen:
                continue
            seen.add(pbid)
            deduped.append(x)

        deduped.sort(key=lambda x: x["score"], reverse=True)
        return deduped

    except Exception:
        return []


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


def _extract_json(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}

    s = raw.strip()

    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1 :]
        s = s.strip()
        if s.endswith("```"):
            s = s[:-3].strip()

    if not s.startswith("{"):
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            s = s[start : end + 1].strip()

    return json.loads(s)


def extract_playbook_id(item) -> Optional[str]:
    if not item:
        return None
    return item["playbook"].get("id")


def extract_base_row(item) -> Optional[str]:
    if not item:
        return None
    return item["playbook"].get("base_row")


def _to_int_or_none(v: Any) -> Optional[int]:
    try:
        if v is None or str(v).strip() == "":
            return None
        return int(str(v).strip())
    except Exception:
        return None


def _age_status_for_playbook(pb: Dict[str, Any], student_age: int) -> str:
    amin = _to_int_or_none(pb.get("age_min"))
    amax = _to_int_or_none(pb.get("age_max"))

    if amin is None or amax is None:
        return "unknown_range"
    if student_age < amin:
        return "below_range"
    if student_age > amax:
        return "above_range"
    return "in_range"


# ----------------------------
# RESPONSE BUILDERS
# ----------------------------


def build_safeguarding_review_response(
    classification,
) -> AIGeneratedSupport:
    """
    Construye una respuesta restringida para casos sensibles legítimos.

    ¿Cuándo se usa?
    - Cuando el clasificador decide route = safeguarding_review

    ¿Por qué existe esta función?
    - Para no mandar estos casos al flujo normal de playbooks
    - Para devolver una respuesta segura y consistente
    - Para dejar claro que se requiere revisión humana

    Nota:
    En esta primera versión NO generamos un plan completo.
    Solo devolvemos una respuesta restringida y segura.
    """
    teacher_msg = (
        "IHUI detectó que este caso incluye un tema sensible que requiere revisión humana. "
        "Por seguridad, no se generó un plan automático estándar. "
        "Se recomienda revisar el caso con el equipo responsable y seguir el protocolo interno de escalamiento."
    )

    parent_msg = (
        "IHUI detectó que este caso incluye un tema sensible que requiere revisión humana. "
        "Por seguridad, no se generó un plan automático estándar. "
        "Se recomienda dar seguimiento con el equipo responsable y continuar la atención según el protocolo correspondiente."
    )

    # Si el clasificador trae topics, los mandamos como señales detectadas
    # para que el frontend o logs tengan una pista estructurada.
    detected_topics = [
        topic for topic in (classification.topics or []) if topic != "none"
    ]

    return AIGeneratedSupport(
        teacher_version=TeacherVersion(
            summary=teacher_msg,
            signals_detected=detected_topics,
            microintervenciones=[],
        ),
        parent_version=ParentVersion(
            summary=parent_msg,
            signals_detected=detected_topics,
            microintervenciones=[],
        ),
        guardrails=GuardrailsBlock(
            no_diagnosis_confirmed=True,
            no_clinical_labels_confirmed=True,
        ),
    )


def build_guardrails_blocked_response(
    blocked_reason: Optional[str],
) -> AIGeneratedSupport:
    """
    Construye una respuesta segura cuando los guardrails de entrada
    detectan que NO debemos mandar el texto al retrieval ni al LLM.

    ¿Por qué existe esta función?
    - Para no pasar contenido peligroso al agente.
    - Para responder de forma controlada.
    - Para no romper el contrato del tipo AIGeneratedSupport.

    Nota:
    En este primer paso regresamos un mensaje seguro y simple.
    Más adelante podremos mejorar el copy para teacher/parent/UI.
    """
    teacher_msg = (
        "IHUI detectó que este caso necesita validación humana antes de generar apoyo automático. "
        "Por seguridad, este contenido no fue procesado automáticamente."
    )

    parent_msg = (
        "IHUI detectó que este caso necesita validación humana antes de generar apoyo automático. "
        "Por seguridad, este contenido no fue procesado automáticamente."
    )

    # Si tenemos motivo de bloqueo, lo agregamos como nota corta
    # para debug/control. No revelamos reglas internas ni detalles sensibles.
    if blocked_reason:
        teacher_msg = f"{teacher_msg}\n\nMotivo de seguridad: {blocked_reason}"
        parent_msg = f"{parent_msg}\n\nMotivo de seguridad: {blocked_reason}"

    return AIGeneratedSupport(
        teacher_version=TeacherVersion(
            summary=teacher_msg,
            signals_detected=[],
            microintervenciones=[],
        ),
        parent_version=ParentVersion(
            summary=parent_msg,
            signals_detected=[],
            microintervenciones=[],
        ),
        guardrails=GuardrailsBlock(
            no_diagnosis_confirmed=True,
            no_clinical_labels_confirmed=True,
        ),
    )


def build_confirmed_response(
    pb: Dict[str, Any], age: int, prediction_id
) -> AIGeneratedSupport:
    micro = _pb_to_micro(pb)
    signal = micro.senal_observable
    age_status = _age_status_for_playbook(pb, age)

    if age_status == "below_range":
        teacher_summary = (
            "No te preocupes, esta señal puede ser esperada para la edad. "
            "Aun así, te compartimos estrategias del Playbook JCJ que pueden apoyar su desarrollo."
        )
        parent_summary = (
            "No te preocupes, esta señal puede ser esperada para la edad. "
            "Aun así, te compartimos estrategias prácticas que pueden apoyar su desarrollo."
        )
    elif age_status == "above_range":
        escalation = micro.escalamiento.strip()
        teacher_summary = (
            "Por la edad del alumno, esta señal requiere mayor atención. "
            "Antes de aplicar las estrategias, considera lo siguiente:"
        )
        parent_summary = (
            "Por la edad del alumno, esta señal merece observarse con mayor atención. "
            "Antes de aplicar las estrategias, considera lo siguiente:"
        )

        if escalation:
            teacher_summary = f"{teacher_summary}\n{escalation}"
            parent_summary = f"{parent_summary}\n{escalation}"
    else:
        teacher_summary = "Estrategias seleccionadas del Playbook JCJ para este caso."
        parent_summary = "Sugerencias basadas en el Playbook JCJ para este caso."

    return AIGeneratedSupport(
        teacher_version=TeacherVersion(
            summary=teacher_summary,
            signals_detected=[signal] if signal else [],
            microintervenciones=[micro],
        ),
        parent_version=ParentVersion(
            summary=parent_summary,
            signals_detected=[signal] if signal else [],
            microintervenciones=[micro],
        ),
        guardrails=GuardrailsBlock(),
    )


def build_pending_response(prediction_id) -> AIGeneratedSupport:
    msg = (
        "IHUI detectó que este caso necesita validación humana y queremos "
        "asegurarnos de darte una estrategia clara, segura y útil.\n\n"
        "Escríbenos por WhatsApp y lo resolvemos contigo en un lapso máximo "
        "de 24 hrs:\n"
    )

    return AIGeneratedSupport(
        teacher_version=TeacherVersion(
            summary=msg,
            signals_detected=[],
            microintervenciones=[],
        ),
        parent_version=ParentVersion(
            summary=msg,
            signals_detected=[],
            microintervenciones=[],
        ),
        guardrails=GuardrailsBlock(),
    )


def build_fallback_response(
    report_text: str, age: int, prediction_id
) -> AIGeneratedSupport:
    disclaimer = (
        "⚠️ Nota: No se encontraron estrategias específicas en el Playbook JCJ "
        "para este caso. Las sugerencias siguientes son generales y deben ser "
        "validadas/ajustadas por el equipo profesional."
    )

    try:
        # Reusar el generador general anterior
        # Ajusta la firma si tu función generate_support recibe parámetros distintos.
        legacy_out = generate_support(
            report_text=report_text,
            age=age,
        )

        # Compatibilidad por si generate_support regresa:
        # 1) solo AIGeneratedSupport
        # 2) tuple (support, model_name)
        # 3) dict con {"support": ...}
        if isinstance(legacy_out, tuple):
            legacy_support = legacy_out[0]
        elif isinstance(legacy_out, dict):
            legacy_support = legacy_out.get("support")
        else:
            legacy_support = legacy_out

        if not legacy_support:
            raise ValueError("legacy generate_support returned empty support")

        teacher_summary = (legacy_support.teacher_version.summary or "").strip()
        parent_summary = (legacy_support.parent_version.summary or "").strip()

        if teacher_summary:
            teacher_summary = f"{disclaimer} {teacher_summary}"
        else:
            teacher_summary = disclaimer

        if parent_summary:
            parent_summary = f"{disclaimer} {parent_summary}"
        else:
            parent_summary = disclaimer

        return AIGeneratedSupport(
            teacher_version=TeacherVersion(
                summary=teacher_summary,
                signals_detected=getattr(
                    legacy_support.teacher_version, "signals_detected", []
                )
                or [],
                microintervenciones=getattr(
                    legacy_support.teacher_version, "microintervenciones", []
                )
                or [],
            ),
            parent_version=ParentVersion(
                summary=parent_summary,
                signals_detected=getattr(
                    legacy_support.parent_version, "signals_detected", []
                )
                or [],
                microintervenciones=getattr(
                    legacy_support.parent_version, "microintervenciones", []
                )
                or [],
            ),
            guardrails=GuardrailsBlock(notes=disclaimer),
        )

    except Exception:
        # fallback de seguridad si el generador general falla
        teacher_msg = (
            f"{disclaimer} "
            "Como apoyo inicial, se recomienda observar con mayor precisión en qué "
            "momentos aparece la dificultad, reducir demandas simultáneas, dar "
            "instrucciones breves y claras, y registrar qué apoyos parecen funcionar "
            "mejor dentro del aula."
        )

        parent_msg = (
            f"{disclaimer} "
            "Como apoyo inicial en casa, se recomienda mantener rutinas claras, dar "
            "una instrucción a la vez, reforzar avances pequeños y observar si hay "
            "momentos, ambientes o estímulos que aumentan o disminuyen la dificultad."
        )

        return AIGeneratedSupport(
            teacher_version=TeacherVersion(
                summary=teacher_msg,
                signals_detected=[],
                microintervenciones=[],
            ),
            parent_version=ParentVersion(
                summary=parent_msg,
                signals_detected=[],
                microintervenciones=[],
            ),
            guardrails=GuardrailsBlock(notes=disclaimer),
        )


def _pb_to_micro(pb: Dict[str, Any]) -> MicroIntervention:
    steps = pb.get("estrategias_paso_a_paso") or pb.get("steps") or []
    if isinstance(steps, str):
        steps = [steps]

    return MicroIntervention(
        topic_nucleo=normalize_topic_nucleo(pb.get("topic_nucleo")),
        subhabilidad=(pb.get("subhabilidad") or pb.get("subskill") or "").strip(),
        senal_observable=(
            pb.get("senal_observable") or pb.get("signal_observable") or ""
        ).strip(),
        hipotesis_funcional=(
            pb.get("hipotesis_funcional") or pb.get("functional_hypothesis") or ""
        ).strip(),
        microobjetivo=(
            pb.get("microobjetivo") or pb.get("micro_objective") or ""
        ).strip(),
        estrategias_paso_a_paso=[str(x).strip() for x in steps if str(x).strip()][:8],
        frecuencia=(pb.get("frecuencia") or pb.get("frequency") or "").strip(),
        duracion=(pb.get("duracion") or pb.get("duration") or "").strip(),
        indicador_de_avance=(
            pb.get("indicador_de_avance") or pb.get("progress_indicator") or ""
        ).strip(),
        escalamiento=(pb.get("escalamiento") or pb.get("escalation") or "").strip(),
    )
