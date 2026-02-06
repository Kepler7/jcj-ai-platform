from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID
import uuid

from sqlalchemy.orm import Session

from app.db.db import SessionLocal
from app.db import models_imports  # noqa: F401  <-- IMPORTANT: registra todos los modelos

from app.modules.ai_jobs.models import AIJob, JobStatus
from app.modules.ai_fallback_events.models import AIFallbackEvent
from app.modules.ai_reports.service import generate_ai_report
from app.modules.reports.models import StudentReport

def create_fallback_event(
    *,
    db: Session,
    school_id: UUID,
    student_id: UUID,
    report_id: UUID,
    ai_report_id: Optional[UUID],
    reason: str,
    topic_nucleo: Optional[str] = None,
    context: Optional[List[str]] = None,   # 👈 ahora lista
    query_text: Optional[str] = None,
    model_output_summary: Optional[str] = None,
    created_by_user_id: Optional[UUID] = None,
) -> None:
    ev = AIFallbackEvent(
        id=uuid.uuid4(),
        school_id=school_id,
        student_id=student_id,
        report_id=report_id,
        ai_report_id=ai_report_id,
        topic_nucleo=topic_nucleo,
        context=context,                    # JSON / ARRAY
        reason=reason,
        query_text=query_text,
        model_output_summary=model_output_summary,
        created_by_user_id=created_by_user_id,
        created_at=datetime.utcnow(),
        resolved_at=None,
    )

    db.add(ev)

def generate_ai_report_task(job_id: str) -> None:
    db: Session = SessionLocal()
    try:
        job = db.get(AIJob, UUID(job_id))
        if not job:
            return

        # 0) cargar report (para student_id / school_id confiables)
        report = db.get(StudentReport, job.report_id)
        if not report:
            # si no existe el report, marcamos failed con error claro
            job.status = JobStatus.failed
            job.finished_at = datetime.utcnow()
            job.last_error = "StudentReport not found"
            job.attempts = (job.attempts or 0) + 1
            job.updated_at = datetime.utcnow()
            db.commit()
            return

        # 1) Marcar running
        job.status = JobStatus.running
        job.started_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        db.commit()

        try:
            # 2) Extraer contexts
            contexts = None
            if job.contexts and isinstance(job.contexts, dict):
                contexts = job.contexts.get("contexts")

            # 3) Ejecutar generación
            # Idealmente generate_ai_report regresa metadata dict:
            # {
            #   "ai_report_id": "...",
            #   "fallback_used": true/false,
            #   "fallback_reason": "...",
            #   "topic_nucleo": "...",
            #   "context": [...],
            #   "query_text": "...",
            #   "model_output_summary": "..."
            # }
            result: Any = generate_ai_report(
                db=db,
                report_id=job.report_id,
                user_id=job.requested_by_user_id,
                contexts=contexts,
            )

            # 4) Interpretar resultado sin romper si generate_ai_report retorna AIReport u otra cosa
            fallback_used = False
            fallback_reason: Optional[str] = None
            ai_report_id: Optional[UUID] = None

            topic_nucleo: Optional[str] = None
            context_value: Any = None  # puede ser list[str]
            query_text: Optional[str] = None
            model_output_summary: Optional[str] = None

            if isinstance(result, dict):
                fallback_used = bool(result.get("fallback_used", False))
                fallback_reason = result.get("fallback_reason")
                raw_ai_id = result.get("ai_report_id")

                if raw_ai_id:
                    try:
                        ai_report_id = UUID(str(raw_ai_id))
                    except Exception:
                        ai_report_id = None

                topic_nucleo = result.get("topic_nucleo")
                context_value = result.get("context_primary")
                query_text = result.get("query_text")
                model_output_summary = result.get("model_output_summary")

            else:
                # si retorna un modelo AIReport (o algo con .id)
                if hasattr(result, "id"):
                    try:
                        ai_report_id = UUID(str(getattr(result, "id")))
                    except Exception:
                        ai_report_id = None

                # sin metadata => asumimos no fallback
                fallback_used = False

            # 5) Si hubo fallback, crear evento para “Pendientes de Playbook”
            if fallback_used:
                reason = fallback_reason or "no_match"

                # ✅ school_id: usa job.school_id (not-null) y de respaldo report.school_id
                school_id = getattr(job, "school_id", None) or report.school_id

                create_fallback_event(
                    db=db,
                    school_id=school_id,
                    student_id=report.student_id,         # ✅ viene del StudentReport
                    report_id=job.report_id,              # ✅ el StudentReport id
                    ai_report_id=ai_report_id,            # puede ser None si no se pudo parsear
                    reason=reason,
                    topic_nucleo=topic_nucleo,
                    context=context_value,
                    query_text=query_text,
                    model_output_summary=model_output_summary,
                    created_by_user_id=job.requested_by_user_id,
                )

                # importante: asegurar insert antes del commit final
                db.flush()

            # 6) Marcar done
            job.status = JobStatus.done
            job.finished_at = datetime.utcnow()
            job.last_error = None
            job.updated_at = datetime.utcnow()
            db.commit()

        except Exception as e:
            job.status = JobStatus.failed
            job.finished_at = datetime.utcnow()
            job.last_error = str(e)
            job.attempts = (job.attempts or 0) + 1
            job.updated_at = datetime.utcnow()
            db.commit()
            raise

    finally:
        db.close()
