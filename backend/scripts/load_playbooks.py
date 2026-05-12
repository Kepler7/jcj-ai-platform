#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from app.modules.playbooks.chroma_loader import reload_playbooks_into_chroma

COLLECTION = "jcj_playbooks_v1"
DEFAULT_JSONL = Path("/app/data/playbooks/playbooks.normalized.jsonl")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--jsonl", default=str(DEFAULT_JSONL), help="Path to normalized JSONL"
    )
    ap.add_argument(
        "--reset",
        action="store_true",
        help="Reset (delete+recreate) the collection before loading",
    )
    args = ap.parse_args()

    count = reload_playbooks_into_chroma(
        host="chroma",
        port=8000,
        collection_name=COLLECTION,
        jsonl_path=Path(args.jsonl),
        reset=args.reset,
    )

    print(f"✅ Loaded {count} playbooks from sheet")


if __name__ == "__main__":
    main()
