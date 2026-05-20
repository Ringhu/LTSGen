#!/usr/bin/env python3
"""Evaluate generated natural-QCC evidence captions with the pilot rule QA.

The natural QCC pilot deliberately keeps answer grounding deterministic: a
caption is scored by matching the predicted answer label against the row's
four human-readable options. This evaluator is the bridge from a trained
TS-RLM/Qwen captioner output (`pred_caption`) to downstream QA accuracy.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/"
    / "natural_qcc_probe_positive.jsonl"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def option_pairs(row: dict[str, Any]) -> list[tuple[str, str]]:
    pairs = []
    for option in row.get("options", []):
        if ". " not in option:
            continue
        letter, label = option.split(". ", 1)
        pairs.append((letter.strip(), label.strip()))
    return pairs


def source_name(row: dict[str, Any]) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(row.get("merge_source_name") or meta.get("merge_source_name") or row.get("multisim_source_domain") or row.get("domain") or "unknown")


def answer_from_caption(row: dict[str, Any], caption: str) -> tuple[str, str, str]:
    text = normalize(caption)
    answer_label_match = re.search(r"answer label:\s*([^.;]+)", caption, flags=re.IGNORECASE)
    if answer_label_match:
        label_text = answer_label_match.group(1).strip()
        for letter, label in option_pairs(row):
            if normalize(label) == normalize(label_text):
                return letter, label, "explicit_answer_label"
        if normalize(str(row.get("answer_label", ""))) == normalize(label_text):
            return str(row.get("answer", "")), str(row.get("answer_label", "")), "explicit_gold_answer_label"

    for letter, label in sorted(option_pairs(row), key=lambda item: len(item[1]), reverse=True):
        if normalize(label) in text:
            return letter, label, "option_label_text"

    gold = normalize(str(row.get("answer_label", "")))
    if gold and gold in text:
        return str(row.get("answer", "")), str(row.get("answer_label", "")), "gold_label_text"
    return "", "", "no_label_match"


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_source[row["merge_source_name"]].append(row)
        by_split[row["split"]].append(row)
        by_task[row["task_family"]].append(row)

    def acc(items: list[dict[str, Any]]) -> float:
        return round(sum(1 for item in items if item["correct"]) / len(items), 4) if items else 0.0

    def empty_rate(items: list[dict[str, Any]]) -> float:
        return round(sum(1 for item in items if not item["pred_answer"]) / len(items), 4) if items else 0.0

    return {
        "n": len(rows),
        "accuracy": acc(rows),
        "empty_answer_rate": empty_rate(rows),
        "mean_caption_chars": round(sum(len(item["caption"]) for item in rows) / len(rows), 1) if rows else 0.0,
        "by_source": {
            key: {"n": len(items), "accuracy": acc(items), "empty_answer_rate": empty_rate(items)}
            for key, items in sorted(by_source.items())
        },
        "by_split": {key: {"n": len(items), "accuracy": acc(items), "empty_answer_rate": empty_rate(items)} for key, items in sorted(by_split.items())},
        "by_task_family": {key: {"n": len(items), "accuracy": acc(items)} for key, items in sorted(by_task.items())},
        "pred_answer_distribution": dict(Counter(item["pred_answer"] or "EMPTY" for item in rows)),
        "reason_distribution": dict(Counter(item["qa_reason"] for item in rows)),
    }


def resolve_caption(pred: dict[str, Any], gold: dict[str, Any], field: str) -> str:
    if field in pred:
        return str(pred.get(field, ""))
    return str(gold.get(field, ""))


def markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# Natural QCC Prediction QA（2026-05-19）",
        "",
        "本报告把 generated evidence captions 转成下游 QA accuracy，用于训练后快速判断 natural QCC caption 是否真的支持答题。",
        "",
        f"- predictions: `{summary['predictions_jsonl']}`",
        f"- gold: `{summary['gold_jsonl']}`",
        f"- caption field: `{summary['caption_field']}`",
        f"- rows: `{metrics['n']}`",
        f"- accuracy: `{metrics['accuracy']:.4f}`",
        f"- empty answer rate: `{metrics['empty_answer_rate']:.4f}`",
        "",
        "## By Source",
        "",
        "| source | n | accuracy | empty |",
        "| --- | ---: | ---: | ---: |",
    ]
    for source, item in metrics["by_source"].items():
        lines.append(f"| `{source}` | {item['n']} | {item['accuracy']:.4f} | {item['empty_answer_rate']:.4f} |")
    lines.extend(
        [
            "",
            "## Reason Distribution",
            "",
            f"`{metrics['reason_distribution']}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions_jsonl", required=True)
    parser.add_argument("--gold_jsonl", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--caption_field", default="pred_caption")
    parser.add_argument("--splits", nargs="+", default=["dev", "test"])
    args = parser.parse_args()

    gold_by_id = {row["id"]: row for row in load_jsonl(args.gold_jsonl)}
    split_keep = set(args.splits)
    rows = []
    for pred in load_jsonl(Path(args.predictions_jsonl)):
        if pred["id"] not in gold_by_id:
            raise KeyError(f"Prediction id not found in gold rows: {pred['id']}")
        gold = gold_by_id[pred["id"]]
        if gold.get("split") not in split_keep:
            continue
        caption = resolve_caption(pred, gold, args.caption_field)
        pred_answer, pred_label, reason = answer_from_caption(gold, caption)
        rows.append(
            {
                "id": pred["id"],
                "split": str(gold.get("split", "")),
                "merge_source_name": source_name(gold),
                "task_family": str(gold.get("task_family", "")),
                "caption": caption,
                "pred_answer": pred_answer,
                "pred_answer_label": pred_label,
                "gold_answer": str(gold.get("answer", "")),
                "gold_answer_label": str(gold.get("answer_label", "")),
                "correct": pred_answer == str(gold.get("answer", "")),
                "qa_reason": reason,
            }
        )

    out_dir = Path(args.out_dir)
    write_jsonl(out_dir / "qa_predictions.jsonl", rows)
    summary = {
        "predictions_jsonl": args.predictions_jsonl,
        "gold_jsonl": str(args.gold_jsonl),
        "caption_field": args.caption_field,
        "splits": args.splits,
        "metrics": summarize(rows),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "qa_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "NATURAL_QCC_PREDICTION_QA_20260519_ZH.md").write_text(markdown(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
