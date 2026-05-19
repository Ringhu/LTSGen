#!/usr/bin/env python3
"""Audit whether generated natural-QCC captions look like evidence captions.

This audit is intentionally separate from downstream QA accuracy. A caption can
score well in the rule-QA bridge by emitting only an answer label, but that does
not show that the QCC model learned to produce useful evidence. This script
checks simple deterministic quality signals: non-empty captions, numeric
evidence, answer-label-only outputs, option-letter leakage, and short captions.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
DEFAULT_GOLD = BASE / "natural_qcc_crossdomain_positive.jsonl"
DEFAULT_PREDICTIONS = (
    BASE
    / "tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/generate_eval_test_clean/predictions.jsonl"
)
DEFAULT_OUT = BASE / "tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/natural_qcc_caption_quality_audit.json"

NUM_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
ANSWER_LABEL_RE = re.compile(r"answer label:\s*[^.;\n]+", flags=re.IGNORECASE)
OPTION_LETTER_RE = re.compile(
    r"\b(?:answer|option|choice)\s*[:=]?\s*[ABCD]\b|\b[ABCD][.)]\s",
    flags=re.IGNORECASE,
)
RANKER_STUB_RE = re.compile(r"locally trained .*caption ranker selected this answer label", flags=re.IGNORECASE)
JSONISH_RE = re.compile(r"^\s*[{[]|\"(?:answer|label|caption)\"\s*:")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def option_labels(row: dict[str, Any]) -> list[str]:
    labels = []
    for option in row.get("options", []):
        if ". " in str(option):
            labels.append(str(option).split(". ", 1)[1].strip())
    return labels


def source_name(row: dict[str, Any]) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(row.get("merge_source_name") or meta.get("merge_source_name") or row.get("multisim_source_domain") or "unknown")


def caption_without_labels(caption: str, row: dict[str, Any]) -> str:
    text = ANSWER_LABEL_RE.sub(" ", caption)
    labels = [str(row.get("answer_label", "")), *option_labels(row)]
    for label in labels:
        label = str(label).strip()
        if label:
            text = re.sub(re.escape(label), " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def quality_for_row(
    pred: dict[str, Any],
    gold: dict[str, Any],
    *,
    caption_field: str,
    min_caption_chars: int,
) -> dict[str, Any]:
    caption = str(pred.get(caption_field, ""))
    if not caption and caption_field in gold:
        caption = str(gold.get(caption_field, ""))
    stripped = caption.strip()
    non_label = caption_without_labels(stripped, gold)
    non_label_tokens = TOKEN_RE.findall(non_label)
    numbers = NUM_RE.findall(stripped)
    answer_label_only = bool(
        stripped
        and (
            RANKER_STUB_RE.search(stripped)
            or (len(numbers) == 0 and len(non_label_tokens) <= 8)
            or normalize(non_label) in {"", "answer", "label", "selected answer"}
        )
    )
    has_numeric_evidence = len(numbers) > 0
    too_short = len(stripped) < min_caption_chars
    evidence_shaped = bool(stripped and has_numeric_evidence and not answer_label_only and not too_short)
    return {
        "id": pred.get("id") or gold.get("id"),
        "split": str(gold.get("split", "")),
        "merge_source_name": source_name(gold),
        "task_family": str(gold.get("task_family", "")),
        "caption": stripped,
        "caption_chars": len(stripped),
        "number_count": len(numbers),
        "non_label_token_count": len(non_label_tokens),
        "has_numeric_evidence": has_numeric_evidence,
        "answer_label_only": answer_label_only,
        "option_letter_leak": bool(OPTION_LETTER_RE.search(stripped)),
        "jsonish_output": bool(JSONISH_RE.search(stripped)),
        "too_short": too_short,
        "evidence_shaped": evidence_shaped,
    }


def rate(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(1 for row in rows if row.get(key)) / len(rows), 4) if rows else 0.0


def summarize(rows: list[dict[str, Any]], *, min_evidence_shape_rate: float, max_answer_label_only_rate: float) -> dict[str, Any]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_source[row["merge_source_name"]].append(row)
        by_task[row["task_family"]].append(row)
    metrics = {
        "n": len(rows),
        "mean_caption_chars": round(sum(row["caption_chars"] for row in rows) / len(rows), 1) if rows else 0.0,
        "numeric_evidence_rate": rate(rows, "has_numeric_evidence"),
        "evidence_shape_rate": rate(rows, "evidence_shaped"),
        "answer_label_only_rate": rate(rows, "answer_label_only"),
        "option_letter_leak_rate": rate(rows, "option_letter_leak"),
        "jsonish_output_rate": rate(rows, "jsonish_output"),
        "too_short_rate": rate(rows, "too_short"),
        "by_source": {
            key: {
                "n": len(items),
                "evidence_shape_rate": rate(items, "evidence_shaped"),
                "answer_label_only_rate": rate(items, "answer_label_only"),
                "numeric_evidence_rate": rate(items, "has_numeric_evidence"),
            }
            for key, items in sorted(by_source.items())
        },
        "by_task_family": {
            key: {
                "n": len(items),
                "evidence_shape_rate": rate(items, "evidence_shaped"),
                "answer_label_only_rate": rate(items, "answer_label_only"),
            }
            for key, items in sorted(by_task.items())
        },
        "failure_reasons": dict(
            Counter(
                reason
                for row in rows
                for reason, failed in (
                    ("answer_label_only", row["answer_label_only"]),
                    ("no_numeric_evidence", not row["has_numeric_evidence"]),
                    ("too_short", row["too_short"]),
                    ("option_letter_leak", row["option_letter_leak"]),
                    ("jsonish_output", row["jsonish_output"]),
                )
                if failed
            )
        ),
    }
    quality_gate_pass = bool(
        rows
        and metrics["evidence_shape_rate"] >= min_evidence_shape_rate
        and metrics["answer_label_only_rate"] <= max_answer_label_only_rate
    )
    return {
        **metrics,
        "min_evidence_shape_rate": min_evidence_shape_rate,
        "max_answer_label_only_rate": max_answer_label_only_rate,
        "quality_gate_pass": quality_gate_pass,
    }


def markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Natural QCC Caption Quality Audit（2026-05-20）",
        "",
        "本审计检查 generated caption 是否具有基本 evidence-caption 形态。它不替代 downstream QA accuracy；QA 答对但只输出答案标签时，本审计会把它标为低质量 caption。",
        "",
        f"- predictions: `{report['predictions_jsonl']}`",
        f"- gold: `{report['gold_jsonl']}`",
        f"- caption field: `{report['caption_field']}`",
        f"- rows: `{metrics['n']}`",
        f"- quality gate pass: `{metrics['quality_gate_pass']}`",
        f"- evidence shape rate: `{metrics['evidence_shape_rate']:.4f}`",
        f"- numeric evidence rate: `{metrics['numeric_evidence_rate']:.4f}`",
        f"- answer-label-only rate: `{metrics['answer_label_only_rate']:.4f}`",
        "",
        "## By Source",
        "",
        "| source | n | evidence shaped | answer-label-only | numeric evidence |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for source, item in metrics["by_source"].items():
        lines.append(
            f"| `{source}` | {item['n']} | {item['evidence_shape_rate']:.4f} | "
            f"{item['answer_label_only_rate']:.4f} | {item['numeric_evidence_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Failure Reasons",
            "",
            f"`{metrics['failure_reasons']}`",
            "",
            "## Guardrail",
            "",
            "只有该审计通过，才说明 generated captions 至少不像单纯答案标签投机；最终方法结论仍需同时看 QA accuracy、qcond-vs-no-question gap 和人工/LLM 细审。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions_jsonl", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--gold_jsonl", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--caption_field", default="pred_caption")
    parser.add_argument("--splits", nargs="+", default=["test"])
    parser.add_argument("--min_caption_chars", type=int, default=40)
    parser.add_argument("--min_evidence_shape_rate", type=float, default=0.8)
    parser.add_argument("--max_answer_label_only_rate", type=float, default=0.2)
    args = parser.parse_args()

    gold_by_id = {row["id"]: row for row in load_jsonl(args.gold_jsonl)}
    keep = set(args.splits)
    rows = []
    for pred in load_jsonl(args.predictions_jsonl):
        row_id = pred.get("id")
        if row_id not in gold_by_id:
            raise KeyError(f"Prediction id not found in gold rows: {row_id}")
        gold = gold_by_id[row_id]
        if gold.get("split") not in keep:
            continue
        rows.append(quality_for_row(pred, gold, caption_field=args.caption_field, min_caption_chars=args.min_caption_chars))

    summary = {
        "predictions_jsonl": rel(args.predictions_jsonl),
        "gold_jsonl": rel(args.gold_jsonl),
        "caption_field": args.caption_field,
        "splits": args.splits,
        "metrics": summarize(
            rows,
            min_evidence_shape_rate=args.min_evidence_shape_rate,
            max_answer_label_only_rate=args.max_answer_label_only_rate,
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out.with_suffix(".rows.jsonl"), rows)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    args.out.with_suffix(".md").write_text(markdown(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0 if rows else 1)


if __name__ == "__main__":
    main()
