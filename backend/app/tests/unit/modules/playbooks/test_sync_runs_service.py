import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.modules.playbooks.models import PlaybookSyncRun
from app.modules.playbooks.sync_runs_service import (
    create_sync_run,
    get_latest_sync_run,
    get_sync_run_by_job_id,
    mark_sync_run_failed,
    mark_sync_run_finished,
    mark_sync_run_started,
    serialize_sync_run,
)


def make_test_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_create_sync_run():
    db = make_test_db()

    run = create_sync_run(
        db,
        job_id="playbook-sync",
        status="queued",
        input_source="https://example.com/export.csv",
        output_path="/tmp/out.jsonl",
        trigger_type="manual",
    )

    assert run.id is not None
    assert run.job_id == "playbook-sync"
    assert run.status == "queued"
    assert run.input_source == "https://example.com/export.csv"
    assert run.output_path == "/tmp/out.jsonl"
    assert run.trigger_type == "manual"


def test_get_sync_run_by_job_id_returns_latest():
    db = make_test_db()

    create_sync_run(db, job_id="playbook-sync", status="queued")
    latest = create_sync_run(db, job_id="playbook-sync", status="started")

    result = get_sync_run_by_job_id(db, "playbook-sync")

    assert result is not None
    assert result.id == latest.id
    assert result.status == "started"


def test_mark_sync_run_started():
    db = make_test_db()

    run = create_sync_run(db, job_id="playbook-sync", status="queued")
    updated = mark_sync_run_started(db, run)

    assert updated.status == "started"
    assert updated.started_at is not None


def test_mark_sync_run_finished():
    db = make_test_db()

    run = create_sync_run(db, job_id="playbook-sync", status="started")
    updated = mark_sync_run_finished(db, run, result={"ok": True})

    assert updated.status == "finished"
    assert updated.finished_at is not None
    assert updated.error_message is None
    assert json.loads(updated.result_json) == {"ok": True}


def test_mark_sync_run_failed():
    db = make_test_db()

    run = create_sync_run(db, job_id="playbook-sync", status="started")
    updated = mark_sync_run_failed(db, run, error_message="boom")

    assert updated.status == "failed"
    assert updated.finished_at is not None
    assert updated.error_message == "boom"


def test_get_latest_sync_run_returns_latest():
    db = make_test_db()

    create_sync_run(db, job_id="job-1", status="queued")
    latest = create_sync_run(db, job_id="job-2", status="finished")

    result = get_latest_sync_run(db)

    assert result is not None
    assert result.id == latest.id
    assert result.job_id == "job-2"


def test_get_latest_sync_run_returns_none_when_empty():
    db = make_test_db()

    result = get_latest_sync_run(db)

    assert result is None


def test_serialize_sync_run():
    db = make_test_db()

    run = create_sync_run(
        db,
        job_id="playbook-sync",
        status="finished",
        input_source="https://example.com/export.csv",
        output_path="/tmp/out.jsonl",
        trigger_type="manual",
    )
    run = mark_sync_run_finished(db, run, result={"ok": True})

    payload = serialize_sync_run(run)

    assert payload["id"] == run.id
    assert payload["job_id"] == "playbook-sync"
    assert payload["status"] == "finished"
    assert payload["input_source"] == "https://example.com/export.csv"
    assert payload["output_path"] == "/tmp/out.jsonl"
    assert payload["trigger_type"] == "manual"
    assert payload["error_message"] is None
    assert payload["result"] == {"ok": True}
    assert payload["created_at"] is not None
    assert payload["finished_at"] is not None
