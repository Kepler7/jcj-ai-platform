from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.db import models_imports  # noqa: F401

from sqlalchemy.orm import Session

from app.db.db import SessionLocal
from app.modules.ai_jobs.models import AIJob, JobStatus

from app.modules.ai_reports.service import generate_ai_report  # <-- ajusta si se llama distinto


def generate_ai_report_task(job_id: str) -> None:
    db: Session = SessionLocal()
    try:
        job = db.get(AIJob, UUID(job_id))
        if not job:
            return

        job.status = JobStatus.running
        job.started_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        db.commit()

        try:
            contexts = None
            if job.contexts and isinstance(job.contexts, dict):
                contexts = job.contexts.get("contexts")

            # Esta función debe:
            # - validar acceso school (o ya viene validado en el endpoint)
            # - generar con Agno + RAG
            # - guardar en ai_reports
            generate_ai_report(
                db=db,
                report_id=job.report_id,
                user_id=job.requested_by_user_id,
                contexts=contexts,
            )

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
