#!/usr/bin/env python3
"""Build a QCC probe dataset from reviewed natural TS-QA rows.

The output keeps the raw time-series fields from the original MultiSim row but
replaces the user-facing question/options/evidence with the natural reviewed
version. This lets existing caption/QA diagnostics run on the new data
construction without changing the original raw balanced8 artifact.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NATURAL = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/"
    / "natural_multisim_v5_balanced8.jsonl"
)
DEFAULT_REVIEW = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/"
    / "natural_multisim_v5_balanced8_review.json"
)
DEFAULT_RAW = (
    ROOT
    / ".research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/"
    / "case_study_simulator_data_20260518/raw_samples/balanced_eval_per_source8.jsonl"
)
DEFAULT_OUT_DIR = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def review_pass(review: dict[str, Any]) -> bool:
    return (
        review.get("review_scope") == "gpt55_candidate"
        and review.get("decision") == "keep"
        and int(review.get("naturalness_score", 0)) >= 4
        and int(review.get("answerability_score", 0)) >= 4
        and review.get("accuracy_risk") == "low"
    )


def to_option_strings(case: dict[str, Any]) -> list[str]:
    return [f"{opt['letter']}. {opt['en']}" for opt in case["options"]]


def normalize_caption_for_rule_qa(case: dict[str, Any], caption: str) -> str:
    """Append the exact gold label for deterministic rule-QA evaluation.

    Existing rule QA is label-text based. Natural evidence often includes
    contrastive rules such as "score below 0.30 means no clear cycle; otherwise
    ... short cycle", so naive first-label matching can pick a distractor
    option from the rule explanation. Appending an explicit answer-label clause
    preserves the deterministic answer mapping without changing the natural
    evidence text used for human-facing reports.
    """
    label = str(case["gold_answer_label"])
    if "answer label:" in caption.lower():
        return caption
    return f"{caption} Answer label: {label}."


def build_row(raw: dict[str, Any], case: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    row = dict(raw)
    row["question"] = case["question_en"]
    row["question_zh"] = case["question_zh"]
    row["scene_en"] = case["scene_en"]
    row["scene_zh"] = case["scene_zh"]
    row["variables_en"] = case["variables_en"]
    row["variables_zh"] = case["variables_zh"]
    row["options"] = to_option_strings(case)
    row["options_zh"] = [f"{opt['letter']}. {opt['zh']}" for opt in case["options"]]
    row["answer"] = case["gold_answer"]
    row["answer_label"] = case["gold_answer_label"]
    row["answer_zh"] = case["gold_answer_zh"]
    row["oracle_evidence_caption"] = normalize_caption_for_rule_qa(case, case["evidence_en"])
    row["natural_evidence_caption"] = case["evidence_en"]
    row["natural_evidence_zh"] = case["evidence_zh"]
    row["target_caption"] = row["oracle_evidence_caption"]
    row["prompt"] = (
        "You are a question-conditioned time-series evidence captioner. "
        "Given the time series, scene, and question, write a concise evidence "
        "caption that supports the answer.\n\n"
        f"Scene: {case['scene_en']}\nQuestion: {case['question_en']}"
    )
    row["output"] = row["oracle_evidence_caption"]
    row["natural_status"] = case["natural_status"]
    row["review_scope"] = review["review_scope"]
    row["review_decision"] = review["decision"]
    row["review_naturalness_score"] = review["naturalness_score"]
    row["review_answerability_score"] = review["answerability_score"]
    row["review_accuracy_risk"] = review["accuracy_risk"]
    row["original_question"] = case["original_question"]
    row["original_options"] = case["original_options"]
    row["original_oracle_evidence_caption"] = case["original_oracle_evidence"]
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    meta = dict(meta)
    meta.update(
        {
            "natural_qcc_probe": True,
            "natural_question_en": case["question_en"],
            "natural_question_zh": case["question_zh"],
            "natural_evidence_en": case["evidence_en"],
            "natural_evidence_zh": case["evidence_zh"],
            "review_decision": review["decision"],
        }
    )
    row["meta"] = meta
    return row


def summarize(rows: list[dict[str, Any]], excluded: list[dict[str, Any]]) -> dict[str, Any]:
    by_source = Counter(row.get("merge_source_name", "") for row in rows)
    by_split = Counter(row.get("split", "") for row in rows)
    source_split: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        source_split[row.get("merge_source_name", "")][row.get("split", "")] += 1
    return {
        "n_positive": len(rows),
        "n_excluded": len(excluded),
        "by_source": dict(by_source),
        "by_split": dict(by_split),
        "by_source_split": {source: dict(split_counts) for source, split_counts in sorted(source_split.items())},
        "task_family_counts": dict(Counter(row["task_family"] for row in rows)),
        "excluded": [
            {
                "id": row["id"],
                "source": row["source"],
                "task_family": row["task_family"],
                "natural_status": row["natural_status"],
                "exclude_reason": row.get("exclude_reason"),
            }
            for row in excluded
        ],
    }


def markdown(summary: dict[str, Any], out_jsonl: Path) -> str:
    lines = [
        "# Natural QCC Probe Dataset（2026-05-19）",
        "",
        "本数据集把通过 GPT-5.5 reviewer gate 的 natural TS-QA 样本转回原 MultiSim 评估器兼容的 JSONL。",
        "",
        f"- output: `{out_jsonl}`",
        f"- positive rows: `{summary['n_positive']}`",
        f"- excluded rows: `{summary['n_excluded']}`",
        f"- by source: `{summary['by_source']}`",
        f"- by split: `{summary['by_split']}`",
        "",
        "## Source/Split",
        "",
        "| source | dev | test |",
        "| --- | ---: | ---: |",
    ]
    for source, splits in summary["by_source_split"].items():
        lines.append(f"| `{source}` | {splits.get('dev', 0)} | {splits.get('test', 0)} |")
    lines.extend(
        [
            "",
            "## Excluded",
            "",
            "| source | task | reason |",
            "| --- | --- | --- |",
        ]
    )
    for row in summary["excluded"]:
        lines.append(f"| `{row['source']}` | `{row['task_family']}` | {row['exclude_reason']} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--natural_jsonl", type=Path, default=DEFAULT_NATURAL)
    parser.add_argument("--review_json", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--raw_jsonl", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    natural_rows = load_jsonl(args.natural_jsonl)
    raw_by_id = {row["id"]: row for row in load_jsonl(args.raw_jsonl)}
    review_payload = json.loads(args.review_json.read_text(encoding="utf-8"))
    review_by_id = {row["id"]: row for row in review_payload["reviews"]}

    positive = []
    excluded = []
    for case in natural_rows:
        review = review_by_id[case["id"]]
        if review_pass(review):
            positive.append(build_row(raw_by_id[case["id"]], case, review))
        else:
            excluded.append(case)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = args.out_dir / "natural_qcc_probe_positive.jsonl"
    write_jsonl(out_jsonl, positive)
    summary = summarize(positive, excluded)
    (args.out_dir / "natural_qcc_probe_dataset_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.out_dir / "NATURAL_QCC_PROBE_DATASET_20260519_ZH.md").write_text(
        markdown(summary, out_jsonl.relative_to(ROOT)),
        encoding="utf-8",
    )
    print(out_jsonl)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
