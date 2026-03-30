import pytest

from app.modules.playbooks import jobs


def test_run_playbook_sync_job_marks_started_and_finished(monkeypatch):
    db_calls = {
        "closed": False,
    }

    class FakeDB:
        def close(self):
            db_calls["closed"] = True

    class FakeCurrentJob:
        id = "playbook-sync"

    fake_run = object()

    captured = {
        "started_called": False,
        "finished_called": False,
        "failed_called": False,
    }

    monkeypatch.setattr(jobs, "get_db_session", lambda: FakeDB())
    monkeypatch.setattr(jobs, "get_current_job", lambda: FakeCurrentJob())
    monkeypatch.setattr(jobs, "get_sync_run_by_job_id", lambda db, job_id: fake_run)
    monkeypatch.setattr(
        jobs,
        "mark_sync_run_started",
        lambda db, run: captured.__setitem__("started_called", True),
    )
    monkeypatch.setattr(
        jobs,
        "sync_playbooks",
        lambda: {"ok": True, "output_path": "/tmp/out.jsonl"},
    )

    def fake_mark_finished(db, run, result=None):
        captured["finished_called"] = True
        captured["finished_result"] = result

    monkeypatch.setattr(jobs, "mark_sync_run_finished", fake_mark_finished)
    monkeypatch.setattr(
        jobs,
        "mark_sync_run_failed",
        lambda db, run, error_message: captured.__setitem__("failed_called", True),
    )
    monkeypatch.setattr(jobs, "create_sync_run", lambda db, job_id, status: fake_run)

    result = jobs.run_playbook_sync_job()

    assert result == {"ok": True, "output_path": "/tmp/out.jsonl"}
    assert captured["started_called"] is True
    assert captured["finished_called"] is True
    assert captured["finished_result"] == {"ok": True, "output_path": "/tmp/out.jsonl"}
    assert captured["failed_called"] is False
    assert db_calls["closed"] is True


def test_run_playbook_sync_job_marks_failed_on_exception(monkeypatch):
    db_calls = {
        "closed": False,
    }

    class FakeDB:
        def close(self):
            db_calls["closed"] = True

    class FakeCurrentJob:
        id = "playbook-sync"

    fake_run = object()

    captured = {
        "started_called": False,
        "finished_called": False,
        "failed_called": False,
    }

    monkeypatch.setattr(jobs, "get_db_session", lambda: FakeDB())
    monkeypatch.setattr(jobs, "get_current_job", lambda: FakeCurrentJob())
    monkeypatch.setattr(jobs, "get_sync_run_by_job_id", lambda db, job_id: fake_run)
    monkeypatch.setattr(
        jobs,
        "mark_sync_run_started",
        lambda db, run: captured.__setitem__("started_called", True),
    )

    def fake_sync_playbooks():
        raise RuntimeError("boom")

    monkeypatch.setattr(jobs, "sync_playbooks", fake_sync_playbooks)
    monkeypatch.setattr(
        jobs,
        "mark_sync_run_finished",
        lambda db, run, result=None: captured.__setitem__("finished_called", True),
    )

    def fake_mark_failed(db, run, error_message):
        captured["failed_called"] = True
        captured["failed_message"] = error_message

    monkeypatch.setattr(jobs, "mark_sync_run_failed", fake_mark_failed)
    monkeypatch.setattr(jobs, "create_sync_run", lambda db, job_id, status: fake_run)

    with pytest.raises(RuntimeError, match="boom"):
        jobs.run_playbook_sync_job()

    assert captured["started_called"] is True
    assert captured["finished_called"] is False
    assert captured["failed_called"] is True
    assert captured["failed_message"] == "boom"
    assert db_calls["closed"] is True


def test_run_playbook_sync_job_creates_fallback_run_when_missing(monkeypatch):
    class FakeDB:
        def close(self):
            pass

    class FakeCurrentJob:
        id = "playbook-sync"

    fake_run = object()
    captured = {}

    monkeypatch.setattr(jobs, "get_db_session", lambda: FakeDB())
    monkeypatch.setattr(jobs, "get_current_job", lambda: FakeCurrentJob())
    monkeypatch.setattr(jobs, "get_sync_run_by_job_id", lambda db, job_id: None)

    def fake_create_sync_run(db, job_id, status):
        captured["job_id"] = job_id
        captured["status"] = status
        return fake_run

    monkeypatch.setattr(jobs, "create_sync_run", fake_create_sync_run)
    monkeypatch.setattr(jobs, "mark_sync_run_started", lambda db, run: None)
    monkeypatch.setattr(jobs, "sync_playbooks", lambda: {"ok": True})
    monkeypatch.setattr(
        jobs, "mark_sync_run_finished", lambda db, run, result=None: None
    )
    monkeypatch.setattr(
        jobs, "mark_sync_run_failed", lambda db, run, error_message: None
    )

    result = jobs.run_playbook_sync_job()

    assert result == {"ok": True}
    assert captured["job_id"] == "playbook-sync"
    assert captured["status"] == "queued"
