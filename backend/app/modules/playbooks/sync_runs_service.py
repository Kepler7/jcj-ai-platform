from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.playbooks.models import PlaybookSyncRun


def create_sync_run(
    db: Session,
    *,
    job_id: str,
    status: str,
    input_source: Optional[str] = None,
    output_path: Optional[str] = None,
    trigger_type: Optional[str] = None,
) -> PlaybookSyncRun:
    run = PlaybookSyncRun(
        job_id=job_id,
        status=status,
        input_source=input_source,
        output_path=output_path,
        trigger_type=trigger_type,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_sync_run_by_job_id(db: Session, job_id: str) -> Optional[PlaybookSyncRun]:
    return (
        db.query(PlaybookSyncRun)
        .filter(PlaybookSyncRun.job_id == job_id)
        .order_by(PlaybookSyncRun.id.desc())
        .first()
    )


def mark_sync_run_started(db: Session, run: PlaybookSyncRun) -> PlaybookSyncRun:
    run.status = "started"
    run.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run


def mark_sync_run_finished(
    db: Session,
    run: PlaybookSyncRun,
    *,
    result: Optional[Any] = None,
) -> PlaybookSyncRun:
    run.status = "finished"
    run.finished_at = datetime.now(timezone.utc)
    run.error_message = None
    run.result_json = (
        json.dumps(result, ensure_ascii=False) if result is not None else None
    )
    db.commit()
    db.refresh(run)
    return run


def mark_sync_run_failed(
    db: Session,
    run: PlaybookSyncRun,
    *,
    error_message: str,
) -> PlaybookSyncRun:
    run.status = "failed"
    run.finished_at = datetime.now(timezone.utc)
    run.error_message = error_message
    db.commit()
    db.refresh(run)
    return run


def get_latest_sync_run(db: Session) -> Optional[PlaybookSyncRun]:
    return db.query(PlaybookSyncRun).order_by(PlaybookSyncRun.id.desc()).first()


def serialize_sync_run(run: PlaybookSyncRun) -> dict[str, Any]:
    result: Any = None
    if run.result_json:
        try:
            result = json.loads(run.result_json)
        except Exception:
            result = run.result_json

    return {
        "id": run.id,
        "job_id": run.job_id,
        "status": run.status,
        "input_source": run.input_source,
        "output_path": run.output_path,
        "trigger_type": run.trigger_type,
        "error_message": run.error_message,
        "result": result,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }
