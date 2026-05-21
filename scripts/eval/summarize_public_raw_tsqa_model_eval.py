#!/usr/bin/env python3
"""Summarize Public Raw TSQA model-eval predictions."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRED = (
    ROOT
    / ".research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521/model_eval_20260521/"
    / "full_gpt54_public_raw_tsqa_v4_39items_bilingual/predictions.jsonl"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def acc(rows: list[dict[str, Any]]) -> float:
    return round(sum(1 for row in rows if row.get("correct")) / len(rows), 4) if rows else 0.0


def grouped(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    out = {}
    for value in sorted({str(row[field]) for row in rows}):
        subset = [row for row in rows if str(row[field]) == value]
        out[value] = {"n": len(subset), "accuracy": acc(subset)}
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions_jsonl", type=Path, default=DEFAULT_PRED)
    parser.add_argument("--out_json", type=Path, default=None)
    parser.add_argument("--max_wrong_examples", type=int, default=30)
    args = parser.parse_args()

    rows = load_jsonl(args.predictions_jsonl)
    wrong = [row for row in rows if not row.get("correct")]
    summary = {
        "predictions_jsonl": str(args.predictions_jsonl.resolve().relative_to(ROOT)),
        "n": len(rows),
        "accuracy": acc(rows),
        "wrong_n": len(wrong),
        "wrong_by_language": dict(Counter(row["language"] for row in wrong)),
        "wrong_by_domain": dict(Counter(row["domain"] for row in wrong)),
        "wrong_by_task_family": dict(Counter(row["task_family"] for row in wrong)),
        "by_language": grouped(rows, "language"),
        "by_domain": grouped(rows, "domain"),
        "by_task_family": grouped(rows, "task_family"),
        "wrong_examples": [
            {
                "id": row["id"],
                "language": row["language"],
                "domain": row["domain"],
                "task_family": row["task_family"],
                "gold_answer": row["gold_answer"],
                "pred_answer": row.get("pred_answer", ""),
                "gold_answer_label": row.get("gold_answer_label", ""),
                "pred_answer_label": row.get("pred_answer_label", ""),
                "reason": row.get("reason", ""),
            }
            for row in wrong[: args.max_wrong_examples]
        ],
    }
    out = args.out_json or (args.predictions_jsonl.parent / "error_summary.json")
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
