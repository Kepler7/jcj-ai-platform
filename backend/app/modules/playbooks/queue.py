from __future__ import annotations

import os

from redis import Redis
from rq import Queue
from rq.job import Job
from rq.exceptions import NoSuchJobError

from app.modules.playbooks.jobs import run_playbook_sync_job

from app.db.session import get_db_session
from app.modules.playbooks.service import (
    get_playbook_input_source,
    get_playbook_output_path,
)
from app.modules.playbooks.sync_runs_service import create_sync_run

DEFAULT_QUEUE_NAME = "jcj"
PLAYBOOK_SYNC_JOB_ID = "playbook-sync"
ACTIVE_JOB_STATUSES = {"queued", "started", "deferred"}


def get_redis_url() -> str:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is not configured")
    return redis_url


def get_queue_name() -> str:
    return os.getenv("PLAYBOOK_SYNC_QUEUE", DEFAULT_QUEUE_NAME)


def get_redis_connection() -> Redis:
    return Redis.from_url(get_redis_url())


def get_playbook_queue() -> Queue:
    return Queue(
        name=get_queue_name(),
        connection=get_redis_connection(),
    )


def enqueue_playbook_sync():
    queue = get_playbook_queue()

    existing_job = get_existing_playbook_sync_job()
    if existing_job and existing_job.get_status() in ACTIVE_JOB_STATUSES:
        return existing_job

    job = queue.enqueue(
        run_playbook_sync_job,
        job_id=PLAYBOOK_SYNC_JOB_ID,
    )

    db = get_db_session()
    try:
        create_sync_run(
            db,
            job_id=job.id,
            status="queued",
            input_source=get_playbook_input_source(),
            output_path=str(get_playbook_output_path()),
            trigger_type="manual",
        )
    finally:
        db.close()

    return job


def get_job_status(job_id: str) -> dict:
    connection = get_redis_connection()

    try:
        job = Job.fetch(job_id, connection=connection)
    except NoSuchJobError:
        raise RuntimeError(f"Job not found: {job_id}")

    return {
        "job_id": job.id,
        "status": job.get_status(),
        "result": job.result,
        "is_finished": job.is_finished,
        "is_failed": job.is_failed,
    }


def get_existing_playbook_sync_job():
    connection = get_redis_connection()

    try:
        job = Job.fetch(PLAYBOOK_SYNC_JOB_ID, connection=connection)
        return job
    except NoSuchJobError:
        return None
