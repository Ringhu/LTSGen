#!/usr/bin/env python3
"""Evaluate QCC-v0 structured evidence predictions."""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _fmt(v: float) -> str:
    return f"{float(v):.3f}"


def _close(a: float, b: float, tol: float) -> bool:
    return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)


def option_letter_for_value(options: list[str], value: str) -> str:
    for opt in options:
        if ". " not in opt:
            continue
        letter, text = opt.split(". ", 1)
        if text == value:
            return letter
    return ""


def compare_fields(gold: dict[str, Any], pred: dict[str, Any], tol: float) -> tuple[bool, dict[str, bool]]:
    per_key = {}
    for key, gold_value in gold.items():
        if key not in pred:
            per_key[key] = False
            continue
        pred_value = pred[key]
        if isinstance(gold_value, float):
            try:
                per_key[key] = _close(gold_value, float(pred_value), tol)
            except (TypeError, ValueError):
                per_key[key] = False
        else:
            per_key[key] = gold_value == pred_value
    return all(per_key.values()) if per_key else False, per_key


def numeric_answer_from_fields(fields: dict[str, Any]) -> str:
    numeric = [(k, v) for k, v in fields.items() if k.startswith("slot_") and isinstance(v, (int, float)) and not k.endswith(("local_t", "line", "load", "generator", "building", "quarter"))]
    if not numeric:
        return ""
    return _fmt(float(numeric[-1][1]))


def evaluate(dataset: list[dict[str, Any]], predictions: dict[str, dict[str, Any]], tol: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    for gold in dataset:
        pred = predictions.get(gold["id"])
        if pred is None:
            pred_fields: dict[str, Any] = {}
            pred_caption = ""
        else:
            pred_fields = pred.get("pred_target_fields", pred.get("target_fields", {}))
            pred_caption = str(pred.get("pred_target_caption", pred.get("target_caption", "")))

        field_exact, per_key = compare_fields(gold["target_fields"], pred_fields, tol)
        pred_answer_label = str(pred.get("pred_answer_label", "")) if pred else ""
        if not pred_answer_label:
            pred_answer_label = numeric_answer_from_fields(pred_fields)
        pred_answer = str(pred.get("pred_answer", "")) if pred else ""
        if not pred_answer and pred_answer_label:
            pred_answer = option_letter_for_value(gold["options"], pred_answer_label)

        caption_exact = pred_caption == gold["target_caption"]
        answer_label_correct = pred_answer_label == str(gold["answer_label"])
        answer_letter_correct = pred_answer == str(gold["answer"])

        rows.append({
            "id": gold["id"],
            "domain": gold["domain"],
            "task_family": gold["task_family"],
            "split": gold["split"],
            "field_exact": field_exact,
            "caption_exact": caption_exact,
            "answer_label_correct": answer_label_correct,
            "answer_letter_correct": answer_letter_correct,
            "missing_prediction": pred is None,
            "per_key": per_key,
            "gold_answer": gold["answer"],
            "pred_answer": pred_answer,
            "gold_answer_label": gold["answer_label"],
            "pred_answer_label": pred_answer_label,
        })

    metrics = aggregate(rows)
    return rows, metrics


def _acc(rows: list[dict[str, Any]], key: str) -> float:
    return round(float(np.mean([bool(r[key]) for r in rows])) if rows else 0.0, 4)


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "overall": {},
        "by_split": {},
        "by_domain": {},
        "by_task_family": {},
        "missing_prediction_count": sum(bool(r["missing_prediction"]) for r in rows),
    }
    for key in ("field_exact", "caption_exact", "answer_label_correct", "answer_letter_correct"):
        metrics["overall"][key] = {"n": len(rows), "accuracy": _acc(rows, key)}

    for group_name, field in (("by_split", "split"), ("by_domain", "domain"), ("by_task_family", "task_family")):
        for value in sorted({r[field] for r in rows}, key=str):
            subset = [r for r in rows if r[field] == value]
            metrics[group_name][value] = {
                "n": len(subset),
                "field_exact": _acc(subset, "field_exact"),
                "caption_exact": _acc(subset, "caption_exact"),
                "answer_label_correct": _acc(subset, "answer_label_correct"),
                "answer_letter_correct": _acc(subset, "answer_letter_correct"),
            }

    field_key_counts: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        for key, ok in row["per_key"].items():
            field_key_counts[key]["n"] += 1
            field_key_counts[key]["correct"] += int(ok)
    metrics["by_target_key"] = {
        key: {"n": c["n"], "accuracy": round(c["correct"] / c["n"], 4) if c["n"] else 0.0}
        for key, c in sorted(field_key_counts.items())
    }
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--tol", type=float, default=5e-4)
    args = parser.parse_args()

    dataset = load_jsonl(Path(args.data))
    predictions = {row["id"]: row for row in load_jsonl(Path(args.predictions))}
    rows, metrics = evaluate(dataset, predictions, args.tol)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "per_item.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
