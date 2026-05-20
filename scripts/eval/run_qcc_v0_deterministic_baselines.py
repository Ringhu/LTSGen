#!/usr/bin/env python3
"""Run deterministic QCC-v0 sanity baselines."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def oracle_prediction(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "condition": "oracle_structured_target",
        "pred_target_fields": row["target_fields"],
        "pred_target_caption": row["target_caption"],
        "pred_answer_label": row["answer_label"],
        "pred_answer": row["answer"],
    }


def metadata_only_prediction(row: dict[str, Any]) -> dict[str, Any]:
    # A deliberate weak baseline: it knows the task schema but has no trace
    # values, so it predicts zeros / first slot defaults.
    pred_fields: dict[str, Any] = {}
    for key, value in row["target_fields"].items():
        if isinstance(value, int):
            pred_fields[key] = 0
        elif isinstance(value, float):
            pred_fields[key] = 0.0
        else:
            pred_fields[key] = ""
    return {
        "id": row["id"],
        "condition": "metadata_only_slot",
        "pred_target_fields": pred_fields,
        "pred_target_caption": "",
        "pred_answer_label": "0.000",
        "pred_answer": "A",
    }


def question_only_prediction(row: dict[str, Any]) -> dict[str, Any]:
    # Extract selectors that are explicitly present in the question. Numeric
    # evidence values are unavailable without the trace, so they stay at zero.
    question = row["question"]
    pred_fields: dict[str, Any] = {}
    for key, value in row["target_fields"].items():
        if key == "slot_local_t":
            m = re.search(r"local_t=(\d+)", question)
            pred_fields[key] = int(m.group(1)) if m else 0
        elif key == "slot_line":
            m = re.search(r"line (\d+)", question)
            pred_fields[key] = int(m.group(1)) if m else 0
        elif key == "slot_load":
            m = re.search(r"load (\d+)", question)
            pred_fields[key] = int(m.group(1)) if m else 0
        elif key == "slot_generator":
            m = re.search(r"generator (\d+)", question)
            pred_fields[key] = int(m.group(1)) if m else 0
        elif key == "slot_building":
            m = re.search(r"building (\d+)", question)
            pred_fields[key] = int(m.group(1)) if m else 1
        elif key == "slot_quarter":
            m = re.search(r"quarter (\d+)", question)
            pred_fields[key] = int(m.group(1)) if m else 1
        elif isinstance(value, float):
            pred_fields[key] = 0.0
        elif isinstance(value, int):
            pred_fields[key] = 0
        else:
            pred_fields[key] = ""
    return {
        "id": row["id"],
        "condition": "question_only_selectors",
        "pred_target_fields": pred_fields,
        "pred_target_caption": "",
        "pred_answer_label": "0.000",
        "pred_answer": "A",
    }


BASELINES = {
    "oracle_structured_target": oracle_prediction,
    "metadata_only_slot": metadata_only_prediction,
    "question_only_selectors": question_only_prediction,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--conditions", nargs="+", default=list(BASELINES))
    args = parser.parse_args()

    rows = load_jsonl(Path(args.data))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for cond in args.conditions:
        if cond not in BASELINES:
            raise ValueError(cond)
        predictions = [BASELINES[cond](row) for row in rows]
        write_jsonl(out_dir / f"{cond}.jsonl", predictions)
    print(json.dumps({"n_items": len(rows), "conditions": args.conditions}, indent=2))


if __name__ == "__main__":
    main()
