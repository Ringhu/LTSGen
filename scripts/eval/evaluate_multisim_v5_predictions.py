#!/usr/bin/env python3
"""Evaluate generated captions for the mixed MultiSim-v5 artifact."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/eval"))

from evaluate_citylearn_broad_captions import answer_from_caption as city_answer  # noqa: E402
from evaluate_finrl_broad_captions import answer_from_caption as finrl_answer  # noqa: E402
from evaluate_grid2op_broad_captions import answer_from_caption as grid_answer  # noqa: E402
from evaluate_multisim_smoke_captions import answer_from_caption as multisim_answer  # noqa: E402


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def source_name(row: dict[str, Any]) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(row.get("merge_source_name") or meta.get("merge_source_name") or row.get("multisim_source_domain") or row.get("domain") or "unknown")


def answer_for_prediction(row: dict[str, Any], caption: str) -> tuple[str, str, str]:
    source = source_name(row)
    task = row["task_family"]
    options = row["options"]
    if source == "grid2op" or task.startswith("grid_"):
        return grid_answer(task, caption, options)
    if source == "citylearn" or task.startswith("city_"):
        return city_answer(task, caption, options)
    if source == "finrl_scaled" or task.startswith("fin_"):
        return finrl_answer(task, caption, options)
    return multisim_answer(row, caption, condition="model_caption")


def accuracy(rows: list[dict[str, Any]]) -> float:
    return round(sum(1 for row in rows if row["correct"]) / len(rows), 4) if rows else 0.0


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_source[row["merge_source_name"]].append(row)
        by_task[row["task_family"]].append(row)
        by_split[row["split"]].append(row)
    return {
        "n": len(rows),
        "accuracy": accuracy(rows),
        "empty_answer_rate": round(sum(1 for row in rows if not row["pred_answer"]) / len(rows), 4) if rows else 0.0,
        "mean_caption_chars": round(sum(len(row["caption"]) for row in rows) / len(rows), 1) if rows else 0.0,
        "by_source": {
            source: {"n": len(items), "accuracy": accuracy(items), "empty_answer_rate": round(sum(1 for row in items if not row["pred_answer"]) / len(items), 4)}
            for source, items in sorted(by_source.items())
        },
        "by_task_family": {
            task: {"n": len(items), "accuracy": accuracy(items)}
            for task, items in sorted(by_task.items())
        },
        "by_split": {
            split: {"n": len(items), "accuracy": accuracy(items)}
            for split, items in sorted(by_split.items())
        },
        "pred_answer_distribution": dict(Counter(row["pred_answer"] or "EMPTY" for row in rows)),
        "reason_distribution": dict(Counter(row["qa_reason"] for row in rows)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions_jsonl", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--splits", nargs="+", default=["dev", "test"])
    parser.add_argument("--caption_field", default="pred_caption")
    args = parser.parse_args()

    keep = set(args.splits)
    preds = [row for row in load_jsonl(Path(args.predictions_jsonl)) if row.get("split") in keep]
    rows: list[dict[str, Any]] = []
    for pred in preds:
        caption = pred.get(args.caption_field, "")
        gold_answer = pred.get("gold_answer", pred.get("answer", ""))
        gold_answer_label = pred.get("gold_answer_label", pred.get("answer_label", ""))
        pred_answer, pred_label, reason = answer_for_prediction(pred, caption)
        rows.append(
            {
                "id": pred["id"],
                "split": pred["split"],
                "merge_source_name": source_name(pred),
                "multisim_source_domain": pred.get("multisim_source_domain", ""),
                "task_family": pred["task_family"],
                "caption": caption,
                "pred_answer": pred_answer,
                "pred_answer_label": pred_label,
                "gold_answer": gold_answer,
                "gold_answer_label": gold_answer_label,
                "correct": pred_answer == gold_answer,
                "qa_reason": reason,
            }
        )

    out_dir = Path(args.out_dir)
    write_jsonl(out_dir / "qa_predictions.jsonl", rows)
    summary = {
        "predictions_jsonl": args.predictions_jsonl,
        "splits": args.splits,
        "caption_field": args.caption_field,
        "qa_mode": "mixed_multisim_v5_rule_from_generated_caption",
        "metrics": summarize(rows),
    }
    (out_dir / "qa_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
