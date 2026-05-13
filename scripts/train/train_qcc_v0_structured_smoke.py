#!/usr/bin/env python3
"""CPU training smoke for QCC-v0 structured evidence generation.

This is not a final LLM captioner. It is a deliberately small supervised
pipeline that verifies the end-to-end training loop:

dataset -> train learned structured predictor -> generate QCC fields/captions
-> parse/evaluate with the same evaluator used by larger models.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from joblib import dump
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.pipeline import Pipeline

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/generate"))
from build_qcc_v0_dataset import _fmt, target_caption  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts/eval"))
from run_qcc_v0_learned_planner import TASK_TO_OPERATOR  # noqa: E402


SELECTOR_KEYS = ("slot_local_t", "slot_line", "slot_load", "slot_generator", "slot_building", "slot_quarter")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def feature_text(row: dict[str, Any], *, no_question: bool = False) -> str:
    base = f"domain={row['domain']} source={row['source']} horizon={row['horizon']} task={row['task_family']}"
    if no_question:
        return base
    return f"{base} question={row['question']}"


def numeric_keys(rows: list[dict[str, Any]]) -> list[str]:
    keys: set[str] = set()
    for row in rows:
        for key, value in row["target_fields"].items():
            if key.startswith("slot_") and isinstance(value, float):
                keys.add(key)
    return sorted(keys)


def selector_training_rows(rows: list[dict[str, Any]], *, no_question: bool) -> tuple[list[dict[str, Any]], dict[str, Pipeline]]:
    models: dict[str, Pipeline] = {}
    for key in SELECTOR_KEYS:
        examples = [row for row in rows if key in row["target_fields"]]
        if not examples:
            continue
        x = [feature_text(row, no_question=no_question) for row in examples]
        y = [str(row["target_fields"][key]) for row in examples]
        model = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=0)),
        ])
        model.fit(x, y)
        models[key] = model
    return rows, models


class NumericRegressor:
    def __init__(self, key: str, *, no_question: bool) -> None:
        self.key = key
        self.no_question = no_question
        self.vec = DictVectorizer(sparse=True)
        self.model = Ridge(alpha=1.0)

    def _features(self, row: dict[str, Any], pred_fields: dict[str, Any] | None = None) -> dict[str, Any]:
        fields = pred_fields if pred_fields is not None else row["target_fields"]
        feats: dict[str, Any] = {
            "bias": 1.0,
            f"domain={row['domain']}": 1.0,
            f"task={row['task_family']}": 1.0,
            f"source={row['source']}": 1.0,
            "horizon": float(row["horizon"]),
        }
        if not self.no_question:
            feats[f"question={row['question']}"] = 1.0
        for selector in SELECTOR_KEYS:
            if selector in fields:
                value = fields[selector]
                feats[selector] = float(value)
                feats[f"{selector}={value}"] = 1.0
        return feats

    def fit(self, rows: list[dict[str, Any]]) -> None:
        x = [self._features(row) for row in rows if self.key in row["target_fields"]]
        y = [float(row["target_fields"][self.key]) for row in rows if self.key in row["target_fields"]]
        if not x:
            raise ValueError(f"No training rows for numeric key {self.key}")
        self.model.fit(self.vec.fit_transform(x), y)

    def predict(self, row: dict[str, Any], pred_fields: dict[str, Any]) -> float:
        return float(self.model.predict(self.vec.transform([self._features(row, pred_fields)]))[0])


def train_operator(rows: list[dict[str, Any]], *, no_question: bool) -> Pipeline:
    x = [feature_text(row, no_question=no_question) for row in rows]
    y = [TASK_TO_OPERATOR[row["task_family"]] for row in rows]
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=0)),
    ])
    model.fit(x, y)
    return model


def option_letter_for_value(options: list[str], value: str) -> str:
    for opt in options:
        if ". " not in opt:
            continue
        letter, text = opt.split(". ", 1)
        if text == value:
            return letter
    return ""


def train_models(rows: list[dict[str, Any]], *, no_question: bool) -> dict[str, Any]:
    op_model = train_operator(rows, no_question=no_question)
    _, selector_models = selector_training_rows(rows, no_question=no_question)
    num_models: dict[str, NumericRegressor] = {}
    for key in numeric_keys(rows):
        model = NumericRegressor(key, no_question=no_question)
        model.fit(rows)
        num_models[key] = model
    return {"operator": op_model, "selectors": selector_models, "numeric": num_models}


def predict_row(row: dict[str, Any], models: dict[str, Any], *, no_question: bool) -> dict[str, Any]:
    text = feature_text(row, no_question=no_question)
    pred_fields: dict[str, Any] = {}
    for key, model in models["selectors"].items():
        if key in row["target_fields"]:
            value = model.predict([text])[0]
            pred_fields[key] = int(value)
    for key, model in models["numeric"].items():
        if key in row["target_fields"]:
            pred_fields[key] = model.predict(row, pred_fields)
    try:
        caption = target_caption(row, pred_fields)
    except Exception:
        caption = ""
    value_keys = [k for k, v in pred_fields.items() if k.startswith("slot_") and isinstance(v, float)]
    answer_label = _fmt(pred_fields[value_keys[-1]]) if value_keys else ""
    answer = option_letter_for_value(row["options"], answer_label)
    pred_operator = models["operator"].predict([text])[0]
    return {
        "id": row["id"],
        "condition": "qcc_v0_structured_smoke_no_question" if no_question else "qcc_v0_structured_smoke",
        "gold_operator": TASK_TO_OPERATOR[row["task_family"]],
        "pred_operator": pred_operator,
        "pred_target_fields": pred_fields,
        "pred_target_caption": caption,
        "pred_answer_label": answer_label,
        "pred_answer": answer,
    }


def evaluate_internal(rows: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {p["id"]: p for p in predictions}
    op_gold = []
    op_pred = []
    numeric_abs_errors: dict[str, list[float]] = {}
    for row in rows:
        pred = by_id[row["id"]]
        op_gold.append(TASK_TO_OPERATOR[row["task_family"]])
        op_pred.append(pred["pred_operator"])
        for key, value in row["target_fields"].items():
            if isinstance(value, float) and key in pred["pred_target_fields"]:
                numeric_abs_errors.setdefault(key, []).append(abs(float(value) - float(pred["pred_target_fields"][key])))
    return {
        "operator_accuracy": round(float(accuracy_score(op_gold, op_pred)) if rows else 0.0, 4),
        "numeric_mae": {
            key: round(float(mean_absolute_error([0.0] * len(vals), vals)), 6)
            for key, vals in sorted(numeric_abs_errors.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--train_split", default="tiny_overfit")
    parser.add_argument("--eval_splits", nargs="+", default=["tiny_overfit", "dev"])
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--no_question", action="store_true")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.data))
    train_rows = [row for row in rows if row["split"] == args.train_split]
    if not train_rows:
        raise ValueError(f"No rows for split {args.train_split}")
    models = train_models(train_rows, no_question=args.no_question)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dump(models, out_dir / "structured_smoke.joblib")

    summary: dict[str, Any] = {
        "train_split": args.train_split,
        "n_train": len(train_rows),
        "no_question": args.no_question,
        "eval_splits": {},
    }
    all_predictions: list[dict[str, Any]] = []
    for split in args.eval_splits:
        eval_rows = [row for row in rows if row["split"] == split]
        preds = [predict_row(row, models, no_question=args.no_question) for row in eval_rows]
        write_jsonl(out_dir / f"predictions_{split}.jsonl", preds)
        all_predictions.extend(preds)
        summary["eval_splits"][split] = {"n_items": len(eval_rows), **evaluate_internal(eval_rows, preds)}
    write_jsonl(out_dir / "predictions_all_eval_splits.jsonl", all_predictions)
    summary["n_predictions_all_eval_splits"] = len(all_predictions)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
