from pathlib import Path

import pytest

from app.modules.playbooks import service


def test_get_playbook_input_source_returns_env_value(monkeypatch):
    monkeypatch.setenv("PLAYBOOK_SHEET_SOURCE", "https://example.com/test.csv")

    result = service.get_playbook_input_source()

    assert result == "https://example.com/test.csv"


def test_get_playbook_input_source_raises_when_missing(monkeypatch):
    monkeypatch.delenv("PLAYBOOK_SHEET_SOURCE", raising=False)

    with pytest.raises(RuntimeError, match="PLAYBOOK_SHEET_SOURCE is not configured"):
        service.get_playbook_input_source()


def test_get_playbook_output_path_returns_env_value(monkeypatch):
    monkeypatch.setenv("PLAYBOOK_NORMALIZED_OUTPUT", "/tmp/out.jsonl")

    result = service.get_playbook_output_path()

    assert result == Path("/tmp/out.jsonl")


def test_get_playbook_output_path_returns_default_when_missing(monkeypatch):
    monkeypatch.delenv("PLAYBOOK_NORMALIZED_OUTPUT", raising=False)

    result = service.get_playbook_output_path()

    assert result == Path("/app/data/playbooks/playbooks.normalized.jsonl")


def test_get_chroma_host_returns_default(monkeypatch):
    monkeypatch.delenv("CHROMA_HOST", raising=False)

    assert service.get_chroma_host() == "chroma"


def test_get_chroma_port_returns_default(monkeypatch):
    monkeypatch.delenv("CHROMA_PORT", raising=False)

    assert service.get_chroma_port() == 8000


def test_get_chroma_collection_returns_default(monkeypatch):
    monkeypatch.delenv("CHROMA_COLLECTION", raising=False)

    assert service.get_chroma_collection() == "jcj_playbooks_v1"


def test_sync_playbooks_normalizes_and_reloads_chroma(monkeypatch):
    monkeypatch.setenv("PLAYBOOK_SHEET_SOURCE", "https://example.com/export.csv")
    monkeypatch.setenv("PLAYBOOK_NORMALIZED_OUTPUT", "/tmp/playbooks.normalized.jsonl")
    monkeypatch.setenv("CHROMA_HOST", "chroma")
    monkeypatch.setenv("CHROMA_PORT", "8000")
    monkeypatch.setenv("CHROMA_COLLECTION", "jcj_playbooks_v1")

    captured = {}

    def fake_normalize_csv(input_source: str, output_jsonl: Path) -> None:
        captured["input_source"] = input_source
        captured["output_jsonl"] = output_jsonl

    def fake_reload_playbooks_into_chroma(
        *,
        host: str,
        port: int,
        collection_name: str,
        jsonl_path: Path,
        reset: bool = True,
    ) -> int:
        captured["host"] = host
        captured["port"] = port
        captured["collection_name"] = collection_name
        captured["jsonl_path"] = jsonl_path
        captured["reset"] = reset
        return 19

    monkeypatch.setattr(service, "normalize_csv", fake_normalize_csv)
    monkeypatch.setattr(
        service,
        "reload_playbooks_into_chroma",
        fake_reload_playbooks_into_chroma,
    )

    result = service.sync_playbooks()

    assert result == {
        "ok": True,
        "input_source": "https://example.com/export.csv",
        "output_path": "/tmp/playbooks.normalized.jsonl",
        "chroma_host": "chroma",
        "chroma_port": 8000,
        "chroma_collection": "jcj_playbooks_v1",
        "loaded_count": 19,
    }

    assert captured["input_source"] == "https://example.com/export.csv"
    assert captured["output_jsonl"] == Path("/tmp/playbooks.normalized.jsonl")
    assert captured["host"] == "chroma"
    assert captured["port"] == 8000
    assert captured["collection_name"] == "jcj_playbooks_v1"
    assert captured["jsonl_path"] == Path("/tmp/playbooks.normalized.jsonl")
    assert captured["reset"] is True
