#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from app.modules.playbooks.normalizer import normalize_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Local CSV path or CSV URL")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    args = parser.parse_args()

    normalize_csv(
        input_source=args.input,
        output_jsonl=Path(args.output),
    )


if __name__ == "__main__":
    main()
