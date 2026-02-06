from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.reports.models import StudentReport
from app.modules.students.models import Student
from app.modules.ai_reports.models import AIReport

from app.ai.orchestrator import generate_support


def generate_ai_report(
    *,
    db: Session,
    report_id: UUID,
    user_id: UUID,
    contexts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Genera un AIReport para un StudentReport existente y lo guarda en Postgres.

    Importante:
    - NO valida permisos aquí (eso lo hace el endpoint/worker con ensure_same_school).
    - Aquí solo hace: fetch data -> prompt -> LLM -> guardar AIReport.
    - ✅ Regresa metadata para que el worker pueda registrar "fallback" en Pendientes de Playbook.
    """

    # 1) Cargar StudentReport
    report = db.get(StudentReport, report_id)
    if not report:
        raise ValueError("StudentReport not found")

    # 2) Cargar Student (para nombre/edad/grupo)
    student = db.get(Student, report.student_id)
    if not student:
        raise ValueError("Student not found")

    # 3) Armar report_text según tus campos reales
    parts: List[str] = []
    if getattr(report, "strengths", None):
        parts.append(f"Fortalezas: {report.strengths}")
    if getattr(report, "challenges", None):
        parts.append(f"Retos: {report.challenges}")
    if getattr(report, "notes", None):
        parts.append(f"Notas: {report.notes}")

    report_text = "\n".join(parts).strip() or "Sin observaciones."

    # 4) Generar con IA
    #
    # Compatibilidad:
    # - viejo: (support, model_name)
    # - nuevo: (support, model_name, meta)
    support: Any
    model_name: str
    meta: Dict[str, Any] = {}

    out = generate_support(
        student_name=student.full_name,
        age=student.age,
        group=getattr(student, "group", "") or "",
        report_text=report_text,
        contexts=contexts,
    )

    if isinstance(out, tuple) and len(out) == 3:
        support, model_name, meta = out
        if meta is None:
            meta = {}
    elif isinstance(out, tuple) and len(out) == 2:
        support, model_name = out
        meta = {}
    else:
        support = out
        model_name = getattr(out, "model_name", "unknown")
        meta = {}

    # 5) Derivar fallback desde meta (worker tracking)
    fallback_used = bool(meta.get("fallback_used", False))
    fallback_reason = meta.get("fallback_reason") or ("no_match" if fallback_used else None)

    # contexts usados (lista)
    contexts_used = meta.get("context")
    if not isinstance(contexts_used, list):
        # si viene como string o None, normalizamos
        if contexts_used:
            contexts_used = [str(contexts_used)]
        else:
            contexts_used = contexts or ["aula", "casa"]

    # 6) Guardrails notes: si support trae meta.disclaimer, lo guardamos
    guardrails_notes = None
    try:
        # support.meta existe si ya agregaste SupportMeta al schema
        # y lo seteamos en orchestrator.
        smeta = getattr(support, "meta", None)
        if smeta and getattr(smeta, "source", None) == "fallback":
            disclaimer = getattr(smeta, "disclaimer", None)
            if disclaimer:
                guardrails_notes = str(disclaimer)
    except Exception:
        guardrails_notes = None

    # 7) Guardar en ai_reports
    ai_report = AIReport(
        school_id=report.school_id,
        student_id=report.student_id,
        report_id=report.id,
        generated_by_user_id=user_id,
        model_name=model_name,
        teacher_version=support.teacher_version.model_dump(),
        parent_version=support.parent_version.model_dump(),
        signals_detected=support.teacher_version.signals_detected,
        guardrails_passed=True,
        # ✅ si fallback, guardamos disclaimer aquí (te sirve en UI también)
        guardrails_notes=guardrails_notes,
    )

    db.add(ai_report)
    db.commit()
    db.refresh(ai_report)

    # 8) Preparar respuesta para el worker (Pendientes de Playbook)
    query_text = meta.get("query_text")
    if not query_text:
        query_text = report_text[:240] + ("..." if len(report_text) > 240 else "")

    model_output_summary = meta.get("model_output_summary")
    if not model_output_summary:
        try:
            model_output_summary = str(getattr(support.parent_version, "summary", "") or "")[:240]
        except Exception:
            model_output_summary = None

    return {
        "ai_report_id": str(ai_report.id),
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "topic_nucleo": meta.get("topic_nucleo"),
        # ✅ estandar: lista de contexts usados
        "contexts": contexts_used,
        # ✅ opcional: primer contexto “principal”
        "context_primary": (contexts_used[0] if contexts_used else None),
        "query_text": query_text,
        "model_output_summary": model_output_summary,
        "rag_items_count": meta.get("rag_items_count", None),
    }

