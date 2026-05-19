#!/usr/bin/env python3
"""Train a small dependency-free local caption ranker for Natural-QCC.

This script is deliberately not a replacement for TS-RLM/Qwen QCC training. It
is a local diagnostic for machines without GPU or torch: train a row-conditioned
option ranker on the reviewed natural-QCC train split, then emit short generated
captions containing the predicted answer label so the same rule-QA evaluator can
measure whether a supervised caption interface has any signal.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any

from run_natural_qcc_probe import (
    TOKEN_RE,
    answer_from_caption,
    load_jsonl,
    numeric_features,
    option_pairs,
    rel,
    summarize_predictions,
    write_jsonl,
)


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
DEFAULT_DATA = BASE / "natural_qcc_crossdomain_positive.jsonl"
DEFAULT_OUT_DIR = BASE / "local_caption_ranker"


def safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(out):
        return 0.0
    return out


def scaled_numeric(value: float) -> float:
    value = safe_float(value)
    if value == 0.0:
        return 0.0
    return math.copysign(min(math.log1p(abs(value)), 8.0), value)


def source_name(row: dict[str, Any]) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(row.get("merge_source_name") or meta.get("merge_source_name") or "unknown")


def prompt_text(row: dict[str, Any], *, no_question: bool) -> str:
    if no_question:
        return f"{row.get('scene_en', '')} {'; '.join(row.get('variables_en') or [])}"
    return (
        f"{row.get('scene_en', '')} "
        f"{'; '.join(row.get('variables_en') or [])} "
        f"{row.get('question', '')}"
    )


def build_features(
    row: dict[str, Any],
    option_label: str,
    *,
    no_question: bool,
    use_task_feature: bool,
) -> dict[str, float]:
    feats: dict[str, float] = {"bias": 1.0}
    source = source_name(row)
    feats[f"source={source}"] = 1.0
    if use_task_feature:
        feats[f"task={row.get('task_family', '')}"] = 1.0

    prompt_tokens = Counter(TOKEN_RE.findall(prompt_text(row, no_question=no_question).lower()))
    option_tokens = Counter(TOKEN_RE.findall(option_label.lower()))
    for token, count in prompt_tokens.items():
        feats[f"p:{token}"] = min(float(count), 3.0)
    for token, count in option_tokens.items():
        feats[f"o:{token}"] = min(float(count), 3.0)
        feats[f"src:{source}|o:{token}"] = 1.0
        if use_task_feature:
            feats[f"task:{row.get('task_family', '')}|o:{token}"] = 1.0
    for p_token in prompt_tokens:
        for o_token in option_tokens:
            if p_token == o_token:
                feats[f"match:{p_token}"] = 1.0

    for key, value in numeric_features(row).items():
        scaled = scaled_numeric(value)
        feats[f"n:{key}"] = scaled
        if scaled > 0:
            feats[f"n_sign:{key}=pos"] = 1.0
        elif scaled < 0:
            feats[f"n_sign:{key}=neg"] = 1.0
        else:
            feats[f"n_sign:{key}=zero"] = 1.0
        for o_token in option_tokens:
            feats[f"nopt:{key}:{o_token}"] = scaled
    return feats


def dot(weights: dict[str, float], feats: dict[str, float]) -> float:
    return sum(weights.get(key, 0.0) * value for key, value in feats.items())


def add_scaled(weights: dict[str, float], feats: dict[str, float], scale: float) -> None:
    for key, value in feats.items():
        weights[key] = weights.get(key, 0.0) + scale * value
        if abs(weights[key]) < 1e-12:
            weights.pop(key, None)


def candidate_labels(row: dict[str, Any]) -> list[tuple[str, str]]:
    labels = option_pairs(row)
    if not labels:
        raise ValueError(f"Row has no parseable options: {row.get('id')}")
    return labels


def predict_label(
    row: dict[str, Any],
    weights: dict[str, float],
    *,
    no_question: bool,
    use_task_feature: bool,
) -> tuple[str, str, float]:
    scored = []
    for letter, label in candidate_labels(row):
        feats = build_features(row, label, no_question=no_question, use_task_feature=use_task_feature)
        scored.append((dot(weights, feats), letter, label))
    score, letter, label = max(scored, key=lambda item: (item[0], item[1]))
    return letter, label, round(score, 4)


def train_ranker(
    rows: list[dict[str, Any]],
    *,
    epochs: int,
    seed: int,
    no_question: bool,
    use_task_feature: bool,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    weights: dict[str, float] = {}
    rng = random.Random(seed)
    history: list[dict[str, Any]] = []
    for epoch in range(1, epochs + 1):
        order = list(rows)
        rng.shuffle(order)
        mistakes = 0
        for row in order:
            gold_letter = str(row.get("answer", ""))
            gold_labels = {letter: label for letter, label in candidate_labels(row)}
            if gold_letter not in gold_labels:
                continue
            pred_letter, pred_label, _ = predict_label(
                row,
                weights,
                no_question=no_question,
                use_task_feature=use_task_feature,
            )
            if pred_letter == gold_letter:
                continue
            mistakes += 1
            gold_label = gold_labels[gold_letter]
            add_scaled(
                weights,
                build_features(row, gold_label, no_question=no_question, use_task_feature=use_task_feature),
                1.0,
            )
            add_scaled(
                weights,
                build_features(row, pred_label, no_question=no_question, use_task_feature=use_task_feature),
                -1.0,
            )
        history.append({"epoch": epoch, "mistakes": mistakes, "n_train": len(rows), "weights": len(weights)})
    return weights, history


def caption_for_prediction(label: str) -> str:
    return (
        "A locally trained question-conditioned caption ranker selected this answer label "
        f"from the time-series window and question. Answer label: {label}."
    )


def predict_rows(
    rows: list[dict[str, Any]],
    weights: dict[str, float],
    *,
    split_name: str,
    no_question: bool,
    use_task_feature: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    preds = []
    for row in rows:
        letter, label, score = predict_label(
            row,
            weights,
            no_question=no_question,
            use_task_feature=use_task_feature,
        )
        caption = caption_for_prediction(label)
        pred_answer, pred_label, reason = answer_from_caption(row, caption)
        preds.append(
            {
                "id": row["id"],
                "split": str(row.get("split", "")),
                "source": source_name(row),
                "merge_source_name": source_name(row),
                "task_family": str(row.get("task_family", "")),
                "condition": split_name,
                "caption": caption,
                "pred_caption": caption,
                "ranker_score": score,
                "pred_answer": pred_answer,
                "pred_answer_label": pred_label,
                "gold_answer": str(row.get("answer", "")),
                "gold_answer_label": str(row.get("answer_label", "")),
                "correct": pred_answer == str(row.get("answer", "")),
                "qa_reason": reason,
            }
        )
    return preds, summarize_predictions(preds)


def markdown(report: dict[str, Any]) -> str:
    test = report["eval_metrics"]
    train = report["train_metrics"]
    baseline = report.get("baseline_accuracy") or {}
    lines = [
        "# Natural QCC Local Caption Ranker（2026-05-20）",
        "",
        "本诊断在无 GPU / 无 torch 环境下训练一个轻量 option-ranker，并把预测选项写成 generated caption 后用同一 rule-QA 评估。它不是 TS-RLM/Qwen SFT，也不验证 evidence factuality，只用于判断 reviewed natural QCC 数据是否存在可训练的弱监督信号。",
        "",
        "## Setup",
        "",
        f"- data: `{report['data']}`",
        f"- train split: `{report['train_split']}` (`{report['n_train']}` rows)",
        f"- eval split: `{report['eval_split']}` (`{report['n_eval']}` rows)",
        f"- epochs: `{report['epochs']}`",
        f"- no_question: `{report['no_question']}`",
        f"- use_task_feature: `{report['use_task_feature']}`",
        "",
        "## QA Metrics",
        "",
        "| condition | rows | accuracy | empty |",
        "| --- | ---: | ---: | ---: |",
        f"| `local_ranker_train` | {train['n']} | {train['accuracy']:.4f} | {train['empty_answer_rate']:.4f} |",
        f"| `local_ranker_eval` | {test['n']} | {test['accuracy']:.4f} | {test['empty_answer_rate']:.4f} |",
        "",
        "## Baseline Comparison",
        "",
        "| baseline | accuracy |",
        "| --- | ---: |",
    ]
    for key in ("natural_oracle", "generic_caption", "statistical_caption", "question_only", "nearest_caption_question_conditioned", "nearest_caption_no_question"):
        if key in baseline:
            lines.append(f"| `{key}` | `{baseline[key]}` |")
    lines.append(f"| `local_ranker_eval` | `{test['accuracy']}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- local ranker vs question-only: `{test['accuracy']}` vs `{baseline.get('question_only')}`.",
            "- 该结果只能作为本地弱训练诊断；正式结论仍需要 GPU 上的 TS-RLM/Qwen caption SFT、generated captions 和审计通过。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--train_split", default="train")
    parser.add_argument("--eval_split", default="test")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--no_question", action="store_true")
    parser.add_argument("--use_task_feature", action="store_true")
    parser.add_argument("--probe_results", type=Path, default=BASE / "probe_eval/natural_qcc_probe_results.json")
    args = parser.parse_args()

    rows = load_jsonl(args.data)
    train_rows = [row for row in rows if row.get("split") == args.train_split]
    eval_rows = [row for row in rows if row.get("split") == args.eval_split]
    if not train_rows or not eval_rows:
        raise ValueError(f"Need non-empty train/eval rows, got {len(train_rows)}/{len(eval_rows)}")

    weights, history = train_ranker(
        train_rows,
        epochs=args.epochs,
        seed=args.seed,
        no_question=args.no_question,
        use_task_feature=args.use_task_feature,
    )
    train_preds, train_metrics = predict_rows(
        train_rows,
        weights,
        split_name="local_ranker_train",
        no_question=args.no_question,
        use_task_feature=args.use_task_feature,
    )
    eval_preds, eval_metrics = predict_rows(
        eval_rows,
        weights,
        split_name="local_ranker_eval",
        no_question=args.no_question,
        use_task_feature=args.use_task_feature,
    )

    baseline_accuracy: dict[str, Any] = {}
    if args.probe_results.exists():
        probe = json.loads(args.probe_results.read_text(encoding="utf-8"))
        for key in ("natural_oracle", "generic_caption", "statistical_caption", "question_only"):
            baseline_accuracy[key] = probe.get("baselines", {}).get(key, {}).get("accuracy")
        for key in ("nearest_caption_question_conditioned", "nearest_caption_no_question"):
            baseline_accuracy[key] = probe.get("trainable", {}).get(key, {}).get("accuracy")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "train_predictions.jsonl", train_preds)
    write_jsonl(args.out_dir / "predictions.jsonl", eval_preds)
    report = {
        "data": rel(args.data),
        "train_split": args.train_split,
        "eval_split": args.eval_split,
        "n_train": len(train_rows),
        "n_eval": len(eval_rows),
        "epochs": args.epochs,
        "seed": args.seed,
        "no_question": args.no_question,
        "use_task_feature": args.use_task_feature,
        "history": history,
        "n_weights": len(weights),
        "train_metrics": train_metrics,
        "eval_metrics": eval_metrics,
        "baseline_accuracy": baseline_accuracy,
        "claim_scope": "local_dependency_free_training_diagnostic_not_tsrlm_qcc",
    }
    (args.out_dir / "local_caption_ranker_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.out_dir / "NATURAL_QCC_LOCAL_CAPTION_RANKER_20260520_ZH.md").write_text(
        markdown(report),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
