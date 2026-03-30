from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.playbooks import router
from app.api.v1 import playbooks as playbooks_api


def create_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_sync_playbooks_endpoint_returns_new_job_payload(monkeypatch):
    class FakeJob:
        id = "playbook-sync"

        def get_status(self):
            return "queued"

    monkeypatch.setattr(playbooks_api, "enqueue_playbook_sync", lambda: FakeJob())

    client = create_test_client()
    response = client.post("/v1/playbooks/sync")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "job_id": "playbook-sync",
        "status": "queued",
    }


def test_sync_playbooks_endpoint_returns_existing_job_payload(monkeypatch):
    class FakeJob:
        id = "playbook-sync"

        def get_status(self):
            return "started"

    monkeypatch.setattr(playbooks_api, "enqueue_playbook_sync", lambda: FakeJob())

    client = create_test_client()
    response = client.post("/v1/playbooks/sync")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "job_id": "playbook-sync",
        "status": "started",
    }


def test_get_sync_status_endpoint_returns_job_status(monkeypatch):
    monkeypatch.setattr(
        playbooks_api,
        "get_job_status",
        lambda job_id: {
            "job_id": job_id,
            "status": "finished",
            "result": {"ok": True},
            "is_finished": True,
            "is_failed": False,
        },
    )

    client = create_test_client()
    response = client.get("/v1/playbooks/sync/job-123")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-123",
        "status": "finished",
        "result": {"ok": True},
        "is_finished": True,
        "is_failed": False,
    }


def test_get_sync_status_endpoint_returns_404_when_missing(monkeypatch):
    def fake_get_job_status(job_id: str):
        raise RuntimeError(f"Job not found: {job_id}")

    monkeypatch.setattr(playbooks_api, "get_job_status", fake_get_job_status)

    client = create_test_client()
    response = client.get("/v1/playbooks/sync/missing-job")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found: missing-job"}


def test_get_latest_sync_endpoint_returns_latest_run(monkeypatch):
    class FakeDB:
        def close(self):
            pass

    fake_run = object()

    monkeypatch.setattr(playbooks_api, "get_db_session", lambda: FakeDB())
    monkeypatch.setattr(playbooks_api, "get_latest_sync_run", lambda db: fake_run)
    monkeypatch.setattr(
        playbooks_api,
        "serialize_sync_run",
        lambda run: {
            "id": 1,
            "job_id": "playbook-sync",
            "status": "finished",
            "result": {"ok": True},
        },
    )

    client = create_test_client()
    response = client.get("/v1/playbooks/sync/latest")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "job_id": "playbook-sync",
        "status": "finished",
        "result": {"ok": True},
    }


def test_get_latest_sync_endpoint_returns_404_when_empty(monkeypatch):
    class FakeDB:
        def close(self):
            pass

    monkeypatch.setattr(playbooks_api, "get_db_session", lambda: FakeDB())
    monkeypatch.setattr(playbooks_api, "get_latest_sync_run", lambda db: None)

    client = create_test_client()
    response = client.get("/v1/playbooks/sync/latest")

    assert response.status_code == 404
    assert response.json() == {"detail": "No sync runs found"}
