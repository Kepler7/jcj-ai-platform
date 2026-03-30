import pytest

from app.modules.playbooks import queue


def test_get_redis_url_returns_env_value(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")

    result = queue.get_redis_url()

    assert result == "redis://redis:6379/0"


def test_get_redis_url_raises_when_missing(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)

    with pytest.raises(RuntimeError, match="REDIS_URL is not configured"):
        queue.get_redis_url()


def test_get_queue_name_returns_default(monkeypatch):
    monkeypatch.delenv("PLAYBOOK_SYNC_QUEUE", raising=False)

    result = queue.get_queue_name()

    assert result == "jcj"


def test_get_queue_name_returns_env_value(monkeypatch):
    monkeypatch.setenv("PLAYBOOK_SYNC_QUEUE", "playbooks")

    result = queue.get_queue_name()

    assert result == "playbooks"


def test_get_job_status_returns_expected_payload(monkeypatch):
    class FakeJob:
        id = "job-123"
        result = {"ok": True}
        is_finished = True
        is_failed = False

        def get_status(self):
            return "finished"

    class FakeJobClass:
        @staticmethod
        def fetch(job_id, connection):
            assert job_id == "job-123"
            assert connection == "fake-redis-conn"
            return FakeJob()

    monkeypatch.setattr(queue, "get_redis_connection", lambda: "fake-redis-conn")
    monkeypatch.setattr(queue, "Job", FakeJobClass)

    result = queue.get_job_status("job-123")

    assert result == {
        "job_id": "job-123",
        "status": "finished",
        "result": {"ok": True},
        "is_finished": True,
        "is_failed": False,
    }


def test_get_job_status_returns_expected_payload(monkeypatch):
    class FakeJob:
        id = "job-123"
        result = {"ok": True}
        is_finished = True
        is_failed = False

        def get_status(self):
            return "finished"

    class FakeJobClass:
        @staticmethod
        def fetch(job_id, connection):
            assert job_id == "job-123"
            assert connection == "fake-redis-conn"
            return FakeJob()

    monkeypatch.setattr(queue, "get_redis_connection", lambda: "fake-redis-conn")
    monkeypatch.setattr(queue, "Job", FakeJobClass)

    result = queue.get_job_status("job-123")

    assert result == {
        "job_id": "job-123",
        "status": "finished",
        "result": {"ok": True},
        "is_finished": True,
        "is_failed": False,
    }


def test_get_job_status_raises_when_job_not_found(monkeypatch):
    class FakeJobClass:
        @staticmethod
        def fetch(job_id, connection):
            raise queue.NoSuchJobError

    monkeypatch.setattr(queue, "get_redis_connection", lambda: "fake-redis-conn")
    monkeypatch.setattr(queue, "Job", FakeJobClass)

    with pytest.raises(RuntimeError, match="Job not found: missing-job"):
        queue.get_job_status("missing-job")


def test_get_existing_playbook_sync_job_returns_none_when_missing(monkeypatch):
    class FakeJobClass:
        @staticmethod
        def fetch(job_id, connection):
            assert job_id == queue.PLAYBOOK_SYNC_JOB_ID
            raise queue.NoSuchJobError

    monkeypatch.setattr(queue, "get_redis_connection", lambda: "fake-redis-conn")
    monkeypatch.setattr(queue, "Job", FakeJobClass)

    result = queue.get_existing_playbook_sync_job()

    assert result is None


def test_get_existing_playbook_sync_job_returns_job_when_found(monkeypatch):
    fake_job = object()

    class FakeJobClass:
        @staticmethod
        def fetch(job_id, connection):
            assert job_id == queue.PLAYBOOK_SYNC_JOB_ID
            assert connection == "fake-redis-conn"
            return fake_job

    monkeypatch.setattr(queue, "get_redis_connection", lambda: "fake-redis-conn")
    monkeypatch.setattr(queue, "Job", FakeJobClass)

    result = queue.get_existing_playbook_sync_job()

    assert result is fake_job


def test_enqueue_playbook_sync_returns_existing_active_job(monkeypatch):
    class FakeExistingJob:
        id = "playbook-sync"

        def get_status(self):
            return "queued"

    monkeypatch.setattr(
        queue,
        "get_existing_playbook_sync_job",
        lambda: FakeExistingJob(),
    )

    called = {"enqueue_called": False}
    created = {"called": False}

    class FakeQueue:
        def enqueue(self, *args, **kwargs):
            called["enqueue_called"] = True
            raise AssertionError("enqueue should not be called")

    monkeypatch.setattr(queue, "get_playbook_queue", lambda: FakeQueue())
    monkeypatch.setattr(
        queue,
        "create_sync_run",
        lambda *args, **kwargs: created.__setitem__("called", True),
    )

    result = queue.enqueue_playbook_sync()

    assert result.id == "playbook-sync"
    assert called["enqueue_called"] is False
    assert created["called"] is False


def test_enqueue_playbook_sync_enqueues_new_job_when_no_existing_job(monkeypatch):
    monkeypatch.setattr(queue, "get_existing_playbook_sync_job", lambda: None)

    captured = {}

    class FakeJob:
        id = "playbook-sync"

    class FakeQueue:
        def enqueue(self, fn, job_id=None):
            captured["fn"] = fn
            captured["job_id"] = job_id
            return FakeJob()

    class FakeDB:
        def close(self):
            captured["db_closed"] = True

    def fake_create_sync_run(
        db,
        *,
        job_id,
        status,
        input_source=None,
        output_path=None,
        trigger_type=None,
    ):
        captured["sync_run"] = {
            "job_id": job_id,
            "status": status,
            "input_source": input_source,
            "output_path": output_path,
            "trigger_type": trigger_type,
        }

    monkeypatch.setattr(queue, "get_playbook_queue", lambda: FakeQueue())
    monkeypatch.setattr(queue, "get_db_session", lambda: FakeDB())
    monkeypatch.setattr(queue, "create_sync_run", fake_create_sync_run)
    monkeypatch.setattr(
        queue, "get_playbook_input_source", lambda: "https://example.com/export.csv"
    )
    monkeypatch.setattr(
        queue, "get_playbook_output_path", lambda: "/tmp/playbooks.normalized.jsonl"
    )

    job = queue.enqueue_playbook_sync()

    assert job.id == "playbook-sync"
    assert captured["fn"] is queue.run_playbook_sync_job
    assert captured["job_id"] == queue.PLAYBOOK_SYNC_JOB_ID
    assert captured["sync_run"] == {
        "job_id": "playbook-sync",
        "status": "queued",
        "input_source": "https://example.com/export.csv",
        "output_path": "/tmp/playbooks.normalized.jsonl",
        "trigger_type": "manual",
    }
    assert captured["db_closed"] is True


def test_enqueue_playbook_sync_enqueues_new_job_when_existing_job_not_active(
    monkeypatch,
):
    class FakeExistingJob:
        def get_status(self):
            return "finished"

    monkeypatch.setattr(
        queue,
        "get_existing_playbook_sync_job",
        lambda: FakeExistingJob(),
    )

    captured = {}

    class FakeJob:
        id = "playbook-sync"

    class FakeQueue:
        def enqueue(self, fn, job_id=None):
            captured["fn"] = fn
            captured["job_id"] = job_id
            return FakeJob()

    class FakeDB:
        def close(self):
            captured["db_closed"] = True

    def fake_create_sync_run(
        db,
        *,
        job_id,
        status,
        input_source=None,
        output_path=None,
        trigger_type=None,
    ):
        captured["sync_run"] = {
            "job_id": job_id,
            "status": status,
            "input_source": input_source,
            "output_path": output_path,
            "trigger_type": trigger_type,
        }

    monkeypatch.setattr(queue, "get_playbook_queue", lambda: FakeQueue())
    monkeypatch.setattr(queue, "get_db_session", lambda: FakeDB())
    monkeypatch.setattr(queue, "create_sync_run", fake_create_sync_run)
    monkeypatch.setattr(
        queue, "get_playbook_input_source", lambda: "https://example.com/export.csv"
    )
    monkeypatch.setattr(
        queue, "get_playbook_output_path", lambda: "/tmp/playbooks.normalized.jsonl"
    )

    job = queue.enqueue_playbook_sync()

    assert job.id == "playbook-sync"
    assert captured["fn"] is queue.run_playbook_sync_job
    assert captured["job_id"] == queue.PLAYBOOK_SYNC_JOB_ID
    assert captured["sync_run"] == {
        "job_id": "playbook-sync",
        "status": "queued",
        "input_source": "https://example.com/export.csv",
        "output_path": "/tmp/playbooks.normalized.jsonl",
        "trigger_type": "manual",
    }
    assert captured["db_closed"] is True
