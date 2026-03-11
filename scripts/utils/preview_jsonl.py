#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Preview one JSONL sample")
    parser.add_argument("file_path")
    parser.add_argument("--line", type=int, default=None, help="1-based line number to inspect")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_line = None

    with open(args.file_path, "r", encoding="utf-8") as f:
        if args.line is not None:
            for i, line in enumerate(f, start=1):
                if i == args.line:
                    selected_line = line
                    break
        else:
            for i, line in enumerate(f, start=1):
                if random.randint(1, i) == 1:
                    selected_line = line

    if selected_line is None:
        raise ValueError("No JSONL record was selected.")

    sample = json.loads(selected_line)
    print(json.dumps(sample, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
