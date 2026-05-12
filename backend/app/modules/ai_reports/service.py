from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from app.settings import settings

from app.modules.reports.models import StudentReport
from app.modules.students.models import Student
from app.modules.ai_reports.models import AIReport

# from app.ai.orchestrator import generate_support
from app.ai.generate_support_v2 import generate_support_v2
from app.ai.utils.normalization import normalize_topic_nucleo

try:
    from app.modules.ihui_3.service import generate_support_ihui3
except ImportError:
    generate_support_ihui3 = None


def generate_ai_report(
    *,
    db: Session,
    report_id: UUID,
    user_id: UUID,
    contexts: Optional[List[str]] = None,
    job_id: str | None = None,
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

    engine_version = str(getattr(settings, "IHUI_ENGINE_VERSION", "2")).strip()

    print(
        "DEBUG REPORT STUDENT:",
        {
            "report_id": str(report.id),
            "student_id": str(student.id),
            "student_name": student.full_name,
            "student_age": student.age,
            "ihui_version": engine_version,
        },
    )

    # 3) Armar report_text según tus campos reales
    parts: List[str] = []

    signals = getattr(report, "signals_observed", None)
    if signals:
        parts.append(f"Señales observables: {signals}")

    notes = getattr(report, "notes", None)
    if notes:
        parts.append(f"Notas: {notes}")

    report_text = "\n".join(parts).strip() or "Sin observaciones."

    # 4) Generar con IA
    #
    # Compatibilidad:
    # - viejo: (support, model_name)
    # - nuevo: (support, model_name, meta)
    support: Any
    model_name: str
    meta: Dict[str, Any] = {}

    if engine_version == "3":
        if generate_support_ihui3 is None:
            raise RuntimeError(
                "IHUI_ENGINE_VERSION=3 pero app.modules.ihui_3.service.generate_support_ihui3 "
                "todavía no existe. Crea el módulo IHUI 3.0 o cambia IHUI_ENGINE_VERSION=2."
            )

        out = generate_support_ihui3(
            db=db,
            report_id=report.id,
            report_text=report_text,
            age=student.age,
            student_id=student.id,
            school_id=report.school_id,
            model_name="ihui-3-initial",
        )
    else:
        out = generate_support_v2(
            db=db,
            report_id=report.id,
            report_text=report_text,
            age=student.age,
            student_id=student.id,
            school_id=report.school_id,
            model_name="v2-initial",
        )

    support = out["support"]
    model_name = out["model_name"]
    meta = out["meta"] or {}

    # 5) Derivar fallback desde meta (worker tracking)
    fallback_used = bool(meta.get("fallback_used", False))
    fallback_reason = meta.get("fallback_reason") or (
        "no_match" if fallback_used else None
    )

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
        engine_version=meta.get("engine_version", engine_version),
        ai_metadata=meta,
        validation_status=meta.get("validation_status"),
    )

    db.add(ai_report)
    db.commit()
    db.refresh(ai_report)

    def _clip(s: str, n: int) -> str:
        s = (s or "").strip()
        if len(s) <= n:
            return s
        return s[:n].rstrip() + "..."

    MAX_FULL = 4000

    # FULL query (preferimos meta, si no usamos report_text completo)
    query_text_full = meta.get("query_text") or (report_text or "").strip()
    if len(query_text_full) > MAX_FULL:
        query_text_full = query_text_full[:MAX_FULL]

    # PREVIEW query
    query_preview = meta.get("query_preview") or _clip(query_text_full, 240)

    # FULL summary (preferimos meta; si no, summary de parent_version completo)
    model_output_full = meta.get("model_output_summary")
    if not model_output_full:
        try:
            model_output_full = str(
                getattr(support.parent_version, "summary", "") or ""
            ).strip()
        except Exception:
            model_output_full = ""

    if len(model_output_full) > MAX_FULL:
        model_output_full = model_output_full[:MAX_FULL]

    # PREVIEW summary
    model_output_preview = meta.get("model_output_preview") or _clip(
        model_output_full, 240
    )

    # Si fue fallback, crear evento pendiente para Deneb
    if fallback_used:
        from app.jobs.ai_tasks import create_fallback_event

        create_fallback_event(
            db=db,
            school_id=report.school_id,
            student_id=report.student_id,
            report_id=report.id,
            ai_report_id=ai_report.id,
            reason=fallback_reason or "no_match",
            topic_nucleo=normalize_topic_nucleo(meta.get("topic_nucleo")),
            context=contexts_used,
            query_text=query_text_full,
            model_output_summary=model_output_full,
            created_by_user_id=user_id,
        )
        db.commit()

    return ai_report
