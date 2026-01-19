from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.auth.deps import get_current_user
from app.api.v1.ai_reports import ensure_same_school 
from app.auth.deps import require_role

from app.jobs.queue import get_queue
from rq import Retry

from app.jobs.ai_tasks import generate_ai_report_task
from app.modules.ai_jobs.models import AIJob, JobStatus

# Para validar que el report existe y sacar school_id
from app.modules.reports.models import StudentReport


router = APIRouter(prefix="/v1/ai-jobs", tags=["ai-jobs"])


class CreateAIJobRequest(BaseModel):
    report_id: UUID
    contexts: Optional[List[str]] = Field(default=None)


class CreateAIJobResponse(BaseModel):
    job_id: UUID
    status: str


@router.post("", response_model=CreateAIJobResponse, status_code=status.HTTP_201_CREATED)
def create_ai_job(
    payload: CreateAIJobRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Roles permitidos para pedir job
    require_role(current_user, ["platform_admin", "school_admin", "teacher"])

    report = db.get(StudentReport, payload.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="StudentReport not found")

    # Seguridad por escuela (platform_admin puede todo)
    ensure_same_school(current_user, report.school_id)

    job = AIJob(
        id=uuid.uuid4(),
        report_id=report.id,
        school_id=report.school_id,
        requested_by_user_id=current_user.id,
        contexts={"contexts": payload.contexts} if payload.contexts else None,
        status=JobStatus.queued,
        attempts=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()

    q = get_queue()
    q.enqueue(
        generate_ai_report_task,
        str(job.id),
        retry=Retry(max=3, interval=[10, 30, 60]),
    )

    return CreateAIJobResponse(job_id=job.id, status=job.status.value)

class AIJobStatusResponse(BaseModel):
    id: UUID
    report_id: UUID
    status: str
    attempts: int
    last_error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


@router.get("/{job_id}", response_model=AIJobStatusResponse)
def get_ai_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = db.get(AIJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    ensure_same_school(current_user, job.school_id)

    return AIJobStatusResponse(
        id=job.id,
        report_id=job.report_id,
        status=job.status.value,
        attempts=job.attempts,
        last_error=job.last_error,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )

