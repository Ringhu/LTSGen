#!/usr/bin/env python3
"""Train/evaluate a lightweight learned planner for QCC-v0.

The learned component predicts the task/operator from question text. Selector
arguments are parsed from the question, and a deterministic executor reads the
trace to compute numeric evidence. This is a deliberately small QCC-v0 smoke:
it tests whether the question-conditioned planning layer is learnable before
training any large captioner.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from joblib import dump
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline

from run_qcc_v0_trace_rule_extractor import extract_fields, option_letter_for_value

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/generate"))
from build_qcc_v0_dataset import _fmt, target_caption  # noqa: E402


TASK_TO_OPERATOR = {
    "rho_value_slot": "read_grid2op_rho",
    "load_average_value_slot": "mean_grid2op_load",
    "generator_average_value_slot": "mean_grid2op_generator",
    "quarter_total_load_mean_value_slot": "mean_grid2op_total_load_quarter",
    "cf_delta_max_rho_value_slot": "delta_cf_max_rho",
    "cf_intervention_max_rho_value_slot": "read_cf_intervention_max_rho",
    "building_load_value_slot": "read_citylearn_building_load",
    "quarter_net_electricity_mean_value_slot": "mean_citylearn_net_electricity_quarter",
    "outdoor_temperature_value_slot": "read_citylearn_outdoor_temperature",
}
OPERATOR_TO_TASK = {v: k for k, v in TASK_TO_OPERATOR.items()}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def planner_text(row: dict[str, Any]) -> str:
    return (
        f"domain={row['domain']} source={row['source']} horizon={row['horizon']} "
        f"question={row['question']}"
    )


def train_classifier(rows: list[dict[str, Any]]) -> Pipeline:
    x = [planner_text(row) for row in rows]
    y = [TASK_TO_OPERATOR[row["task_family"]] for row in rows]
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=0)),
    ])
    pipe.fit(x, y)
    return pipe


def _selector_args(question: str) -> dict[str, int]:
    args: dict[str, int] = {}
    if m := re.search(r"local_t=(\d+)", question):
        args["local_t"] = int(m.group(1))
    if m := re.search(r"line (\d+)", question):
        args["line"] = int(m.group(1))
    if m := re.search(r"load (\d+)", question):
        args["load"] = int(m.group(1))
    if m := re.search(r"generator (\d+)", question):
        args["generator"] = int(m.group(1))
    if m := re.search(r"building (\d+)", question):
        args["building"] = int(m.group(1))
    if m := re.search(r"quarter (\d+)", question):
        args["quarter"] = int(m.group(1))
    return args


def predict_rows(model: Pipeline, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    x = [planner_text(row) for row in rows]
    pred_ops = list(model.predict(x))
    gold_ops = [TASK_TO_OPERATOR[row["task_family"]] for row in rows]
    predictions = []
    planner_errors = []
    for row, pred_op, gold_op in zip(rows, pred_ops, gold_ops):
        planned_task = OPERATOR_TO_TASK.get(pred_op, "")
        planned = dict(row)
        planned["task_family"] = planned_task
        try:
            fields = extract_fields(planned)
            caption = target_caption(planned, fields)
            value_keys = [k for k, v in fields.items() if k.startswith("slot_") and isinstance(v, float)]
            answer_label = _fmt(float(fields[value_keys[-1]])) if value_keys else ""
            answer = option_letter_for_value(row["options"], answer_label)
        except Exception as exc:  # keep evaluation explicit rather than crashing
            fields = {}
            caption = ""
            answer_label = ""
            answer = ""
            planner_errors.append({"id": row["id"], "pred_operator": pred_op, "error": str(exc)})

        predictions.append({
            "id": row["id"],
            "condition": "learned_planner_tfidf_logreg",
            "gold_operator": gold_op,
            "pred_operator": pred_op,
            "selector_args": _selector_args(row["question"]),
            "pred_target_fields": fields,
            "pred_target_caption": caption,
            "pred_answer_label": answer_label,
            "pred_answer": answer,
        })
    info = {
        "n_items": len(rows),
        "planner_operator_accuracy": round(float(accuracy_score(gold_ops, pred_ops)) if rows else 0.0, 4),
        "planner_error_count": len(planner_errors),
        "planner_errors": planner_errors[:20],
    }
    return predictions, info


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--eval_data", default=None)
    parser.add_argument("--train_split", default="tiny_overfit")
    parser.add_argument("--eval_splits", nargs="+", default=["tiny_overfit", "dev"])
    parser.add_argument("--out_dir", required=True)
    args = parser.parse_args()

    rows = load_jsonl(Path(args.data))
    eval_source_rows = load_jsonl(Path(args.eval_data)) if args.eval_data else rows
    train_rows = [row for row in rows if row["split"] == args.train_split]
    if not train_rows:
        raise ValueError(f"No rows for train split {args.train_split}")
    model = train_classifier(train_rows)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dump(model, out_dir / "planner.joblib")

    summary: dict[str, Any] = {
        "train_split": args.train_split,
        "n_train": len(train_rows),
        "eval_splits": {},
    }
    all_predictions = []
    for split in args.eval_splits:
        eval_rows = [row for row in eval_source_rows if row["split"] == split]
        preds, info = predict_rows(model, eval_rows)
        write_jsonl(out_dir / f"predictions_{split}.jsonl", preds)
        all_predictions.extend(preds)
        summary["eval_splits"][split] = info
    write_jsonl(out_dir / "predictions_all_eval_splits.jsonl", all_predictions)
    summary["n_predictions_all_eval_splits"] = len(all_predictions)

    (out_dir / "planner_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
