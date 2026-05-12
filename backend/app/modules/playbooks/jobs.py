from __future__ import annotations

from rq import get_current_job

from app.db.session import get_db_session
from app.modules.playbooks.service import sync_playbooks
from app.modules.playbooks.sync_runs_service import (
    create_sync_run,
    get_sync_run_by_job_id,
    mark_sync_run_failed,
    mark_sync_run_finished,
    mark_sync_run_started,
)


def run_playbook_sync_job() -> dict:
    """
    RQ job entrypoint for playbook sync.
    Tracks status in playbook_sync_runs.
    """
    db = get_db_session()

    try:
        current_job = get_current_job()
        if current_job is None:
            raise RuntimeError("No current RQ job found")

        job_id = current_job.id

        run = get_sync_run_by_job_id(db, job_id)
        if run is None:
            # Fallback safety: ideally the queued row was created at enqueue time.
            run = create_sync_run(
                db,
                job_id=job_id,
                status="queued",
            )

        mark_sync_run_started(db, run)

        result = sync_playbooks()

        mark_sync_run_finished(db, run, result=result)

        return result

    except Exception as exc:
        current_job = get_current_job()
        job_id = current_job.id if current_job is not None else "unknown"

        run = get_sync_run_by_job_id(db, job_id)
        if run is None:
            run = create_sync_run(
                db,
                job_id=job_id,
                status="queued",
            )

        mark_sync_run_failed(db, run, error_message=str(exc))
        raise

    finally:
        db.close()
