import json
from pathlib import Path

import pytest

from app.modules.playbooks.chroma_loader import (
    build_metadata,
    format_doc_from_row,
    load_jsonl_playbooks,
    read_jsonl,
    reload_playbooks_into_chroma,
)


def test_format_doc_from_row_includes_expected_sections():
    row = {
        "topic_nucleo": "Comunicación",
        "subskill": "Turnos",
        "signal_observable": "Interrumpe mucho",
        "age_min": 5,
        "age_max": 8,
        "functional_hypothesis": "Busca atención",
        "micro_objective": "Esperar turno",
        "steps": ["Modelar", "Reforzar"],
        "frequency": "Diaria",
        "duration": "2 semanas",
        "progress_indicator": "Menos interrupciones",
        "escalation": "Revisar con coordinación",
    }

    doc = format_doc_from_row(row)

    assert "TOPIC_NUCLEO: Comunicación" in doc
    assert "SUBHABILIDAD: Turnos" in doc
    assert "SEÑAL_OBSERVABLE:" in doc
    assert "EDAD: 5–8" in doc
    assert "- Modelar" in doc
    assert "- Reforzar" in doc


def test_build_metadata_returns_expected_fields():
    row = {
        "id": "abc123",
        "source": "sheet",
        "topic_nucleo": "Comunicación",
        "subskill": "Turnos",
        "age_min": 5,
        "age_max": 8,
        "frequency": "Diaria",
        "duration": "2 semanas",
    }

    metadata = build_metadata(row)

    assert metadata == {
        "id": "abc123",
        "source": "sheet",
        "topic_nucleo": "Comunicación",
        "subskill": "Turnos",
        "age_min": 5,
        "age_max": 8,
        "frequency": "Diaria",
        "duration": "2 semanas",
    }


def test_build_metadata_raises_when_id_missing():
    with pytest.raises(RuntimeError, match="Row missing 'id' field in JSONL"):
        build_metadata({"topic_nucleo": "Comunicación"})


def test_read_jsonl_reads_valid_rows(tmp_path: Path):
    path = tmp_path / "playbooks.jsonl"
    rows = [
        {"id": "1", "topic_nucleo": "A"},
        {"id": "2", "topic_nucleo": "B"},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    result = read_jsonl(path)

    assert len(result) == 2
    assert result[0]["id"] == "1"
    assert result[1]["topic_nucleo"] == "B"


def test_read_jsonl_raises_on_invalid_json(tmp_path: Path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"id":"1"}\n{bad json}\n', encoding="utf-8")

    with pytest.raises(RuntimeError, match="Invalid JSON on line 2"):
        read_jsonl(path)


def test_load_jsonl_playbooks_calls_store_add_document(tmp_path: Path):
    path = tmp_path / "playbooks.jsonl"
    rows = [
        {
            "id": "1",
            "source": "sheet",
            "topic_nucleo": "Comunicación",
            "subskill": "Turnos",
            "signal_observable": "Interrumpe",
            "age_min": 5,
            "age_max": 8,
            "functional_hypothesis": "Busca atención",
            "micro_objective": "Esperar turno",
            "steps": ["Modelar"],
            "frequency": "Diaria",
            "duration": "2 semanas",
            "progress_indicator": "Menos interrupciones",
            "escalation": "Coordinar",
        }
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    captured = {"calls": []}

    class FakeStore:
        def add_document(self, doc_id, text, metadata):
            captured["calls"].append(
                {"doc_id": doc_id, "text": text, "metadata": metadata}
            )

    count = load_jsonl_playbooks(FakeStore(), path)

    assert count == 1
    assert len(captured["calls"]) == 1
    assert captured["calls"][0]["doc_id"] == "1"
    assert "TOPIC_NUCLEO: Comunicación" in captured["calls"][0]["text"]
    assert captured["calls"][0]["metadata"]["topic_nucleo"] == "Comunicación"


def test_reload_playbooks_into_chroma_resets_and_loads(tmp_path: Path, monkeypatch):
    path = tmp_path / "playbooks.jsonl"
    rows = [
        {
            "id": "1",
            "source": "sheet",
            "topic_nucleo": "Comunicación",
            "subskill": "Turnos",
            "signal_observable": "Interrumpe",
            "age_min": 5,
            "age_max": 8,
            "functional_hypothesis": "Busca atención",
            "micro_objective": "Esperar turno",
            "steps": ["Modelar"],
            "frequency": "Diaria",
            "duration": "2 semanas",
            "progress_indicator": "Menos interrupciones",
            "escalation": "Coordinar",
        }
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    captured = {"reset_called": False, "documents": []}

    class FakeStore:
        def __init__(self, host, port, collection_name):
            captured["host"] = host
            captured["port"] = port
            captured["collection_name"] = collection_name

        def reset(self):
            captured["reset_called"] = True

        def add_document(self, doc_id, text, metadata):
            captured["documents"].append(
                {"doc_id": doc_id, "text": text, "metadata": metadata}
            )

    monkeypatch.setattr(
        "app.modules.playbooks.chroma_loader.ChromaPlaybookStore",
        FakeStore,
    )

    count = reload_playbooks_into_chroma(
        host="chroma",
        port=8000,
        collection_name="jcj_playbooks_v1",
        jsonl_path=path,
        reset=True,
    )

    assert count == 1
    assert captured["host"] == "chroma"
    assert captured["port"] == 8000
    assert captured["collection_name"] == "jcj_playbooks_v1"
    assert captured["reset_called"] is True
    assert len(captured["documents"]) == 1


def test_reload_playbooks_into_chroma_raises_when_jsonl_missing(tmp_path: Path):
    missing = tmp_path / "missing.jsonl"

    with pytest.raises(FileNotFoundError, match="JSONL not found"):
        reload_playbooks_into_chroma(
            host="chroma",
            port=8000,
            collection_name="jcj_playbooks_v1",
            jsonl_path=missing,
            reset=True,
        )
