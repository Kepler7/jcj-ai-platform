from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.modules.playbooks.queue import enqueue_playbook_sync, get_job_status
from app.db.session import get_db_session
from app.modules.playbooks.sync_runs_service import (
    get_latest_sync_run,
    serialize_sync_run,
)

router = APIRouter(prefix="/v1/playbooks", tags=["playbooks"])


@router.post("/sync")
def sync_playbooks_endpoint():
    try:
        job = enqueue_playbook_sync()
        return {
            "ok": True,
            "job_id": job.id,
            "status": job.get_status(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/sync/latest")
def get_latest_sync_endpoint():
    db = get_db_session()
    try:
        run = get_latest_sync_run(db)
        if run is None:
            raise HTTPException(status_code=404, detail="No sync runs found")

        return serialize_sync_run(run)
    finally:
        db.close()


@router.get("/sync/{job_id}")
def get_sync_status_endpoint(job_id: str):
    try:
        return get_job_status(job_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
