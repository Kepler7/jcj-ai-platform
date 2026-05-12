from __future__ import annotations

import os
from pathlib import Path

from app.modules.playbooks.chroma_loader import reload_playbooks_into_chroma
from app.modules.playbooks.normalizer import normalize_csv

DEFAULT_OUTPUT_PATH = "/app/data/playbooks/playbooks.normalized.jsonl"
DEFAULT_CHROMA_HOST = "chroma"
DEFAULT_CHROMA_PORT = 8000
DEFAULT_CHROMA_COLLECTION = "jcj_playbooks_v1"


def get_playbook_input_source() -> str:
    input_source = os.getenv("PLAYBOOK_SHEET_SOURCE")
    if not input_source:
        raise RuntimeError("PLAYBOOK_SHEET_SOURCE is not configured")
    return input_source


def get_playbook_output_path() -> Path:
    return Path(os.getenv("PLAYBOOK_NORMALIZED_OUTPUT", DEFAULT_OUTPUT_PATH))


def get_chroma_host() -> str:
    return os.getenv("CHROMA_HOST", DEFAULT_CHROMA_HOST)


def get_chroma_port() -> int:
    return int(os.getenv("CHROMA_PORT", str(DEFAULT_CHROMA_PORT)))


def get_chroma_collection() -> str:
    return os.getenv("CHROMA_COLLECTION", DEFAULT_CHROMA_COLLECTION)


def sync_playbooks() -> dict:
    input_source = get_playbook_input_source()
    output_path = get_playbook_output_path()

    normalize_csv(input_source=input_source, output_jsonl=output_path)

    loaded_count = reload_playbooks_into_chroma(
        host=get_chroma_host(),
        port=get_chroma_port(),
        collection_name=get_chroma_collection(),
        jsonl_path=output_path,
        reset=True,
    )

    return {
        "ok": True,
        "input_source": input_source,
        "output_path": str(output_path),
        "chroma_host": get_chroma_host(),
        "chroma_port": get_chroma_port(),
        "chroma_collection": get_chroma_collection(),
        "loaded_count": loaded_count,
    }
