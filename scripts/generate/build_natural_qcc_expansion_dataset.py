#!/usr/bin/env python3
"""Build reviewed Natural-QCC expansion data and SFT assets.

This consumes natural rewrites plus GPT reviewer output. It preserves raw
time-series values from the candidate JSONL, replaces user-facing QA fields with
the reviewed natural wording, and writes positive rows plus split-specific SFT
files for downstream baseline and caption training.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515"
DEFAULT_NATURAL = BASE / "natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites.jsonl"
DEFAULT_REVIEW = BASE / "natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites_review.json"
DEFAULT_RAW = BASE / "natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates.jsonl"
DEFAULT_OUT_DIR = BASE / "natural_qcc_expansion_dataset_20260519"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


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
    return str(
        row.get("merge_source_name")
        or meta.get("merge_source_name")
        or row.get("source")
        or row.get("multisim_source_domain")
        or row.get("domain")
        or "unknown"
    )


def value_dim(row: dict[str, Any]) -> int:
    values = row.get("values") or []
    if not values:
        return 0
    first = values[0]
    return len(first) if isinstance(first, list) else 1


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
    label = str(case["gold_answer_label"])
    if "answer label:" in caption.lower():
        return caption
    return f"{caption} Answer label: {label}."


def build_prompt(case: dict[str, Any]) -> str:
    return (
        "You are a question-conditioned time-series evidence captioner. "
        "Given the time series, scene, variables, and question, write one or two "
        "concise natural-language sentences containing only the evidence needed "
        "to answer the question. Do not choose an option letter and do not output JSON.\n\n"
        f"Scene: {case['scene_en']}\n"
        f"Variables: {'; '.join(case.get('variables_en') or [])}\n"
        f"Question: {case['question_en']}"
    )


def build_row(raw: dict[str, Any], case: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    row = dict(raw)
    source = case.get("source") or source_name(row)
    row["merge_source_name"] = source
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
    row["prompt"] = build_prompt(case)
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
            "natural_qcc_expansion": True,
            "merge_source_name": source,
            "task_family": row.get("task_family", ""),
            "natural_question_en": case["question_en"],
            "natural_question_zh": case["question_zh"],
            "natural_evidence_en": case["evidence_en"],
            "natural_evidence_zh": case["evidence_zh"],
            "review_decision": review["decision"],
            "review_naturalness_score": review["naturalness_score"],
            "review_answerability_score": review["answerability_score"],
            "review_accuracy_risk": review["accuracy_risk"],
        }
    )
    row["meta"] = meta
    return row


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    meta = dict(row.get("meta") or {})
    meta.update(
        {
            "natural_qcc_expansion_sft": True,
            "merge_source_name": source_name(row),
            "task_family": row.get("task_family", ""),
            "answer": row.get("answer", ""),
            "answer_label": row.get("answer_label", ""),
            "question_zh": row.get("question_zh", ""),
            "natural_evidence_zh": row.get("natural_evidence_zh", ""),
        }
    )
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row.get("target_caption", row.get("output", "")),
        "meta": meta,
    }


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_split: dict[str, Counter[str]] = defaultdict(Counter)
    answer_counts = Counter(str(row.get("answer", "")) for row in rows)
    for row in rows:
        source_split[source_name(row)][str(row.get("split", ""))] += 1
    return {
        "n": len(rows),
        "by_source": dict(Counter(source_name(row) for row in rows)),
        "by_split": dict(Counter(str(row.get("split", "")) for row in rows)),
        "by_source_split": {source: dict(counts) for source, counts in sorted(source_split.items())},
        "by_task_family": dict(Counter(str(row.get("task_family", "")) for row in rows)),
        "by_value_dim": dict(Counter(str(value_dim(row)) for row in rows)),
        "answer_distribution": dict(answer_counts),
        "max_answer_share": round(max(answer_counts.values()) / len(rows), 4) if rows else 1.0,
        "missing_required_count": sum(
            1
            for row in rows
            if not all(
                key in row and row[key] not in ("", [], None)
                for key in ("id", "values", "prompt", "output", "target_caption", "question", "options", "answer")
            )
        ),
    }


def split_outputs(rows: list[dict[str, Any]], out_dir: Path, run_name: str) -> dict[str, Any]:
    split_dir = out_dir / "sft"
    files: dict[str, dict[str, str]] = {}
    split_names = sorted({str(row.get("split", "")) for row in rows if row.get("split")})
    for split in split_names:
        split_rows = [row for row in rows if str(row.get("split", "")) == split]
        raw_path = split_dir / f"{run_name}_{split}_raw.jsonl"
        sft_path = split_dir / f"{run_name}_{split}_sft.jsonl"
        write_jsonl(raw_path, split_rows)
        write_jsonl(sft_path, [sft_row(row) for row in split_rows])
        files[split] = {"raw": rel(raw_path), "sft": rel(sft_path), "n": len(split_rows)}
    return files


def markdown(report: dict[str, Any]) -> str:
    positive = report["positive"]
    lines = [
        "# Natural QCC Expansion Dataset（2026-05-19）",
        "",
        "本目录把 GPT-5.5 reviewer gate 通过的扩展 natural TS-QA 样本转成 MultiSim/QCC 兼容数据和 split-specific SFT 资产。",
        "",
        "## 输入输出",
        "",
        f"- natural rewrites: `{report['inputs']['natural_jsonl']}`",
        f"- reviewer JSON: `{report['inputs']['review_json']}`",
        f"- raw candidate JSONL: `{report['inputs']['raw_jsonl']}`",
        f"- positive JSONL: `{report['outputs']['positive_jsonl']}`",
        f"- excluded JSONL: `{report['outputs']['excluded_jsonl']}`",
        f"- schema report: `{report['outputs']['schema_report']}`",
        "",
        "## Positive Summary",
        "",
        f"- positive rows: `{positive['n']}`",
        f"- excluded rows: `{report['excluded']['n']}`",
        f"- by source: `{positive['by_source']}`",
        f"- by split: `{positive['by_split']}`",
        f"- by value dim: `{positive['by_value_dim']}`",
        f"- answer distribution: `{positive['answer_distribution']}`",
        f"- max answer share: `{positive['max_answer_share']}`",
        f"- schema gate pass: `{report['schema_gate_pass']}`",
        "",
        "## SFT Files",
        "",
        "| split | rows | raw | sft |",
        "| --- | ---: | --- | --- |",
    ]
    for split, item in sorted(report["sft_files"].items()):
        lines.append(f"| `{split}` | {item['n']} | `{item['raw']}` | `{item['sft']}` |")
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "1. 对 positive JSONL 跑 `scripts/eval/run_natural_qcc_probe.py --data ...`，重做 `question_only/generic/statistical/natural_oracle` baseline。",
            "2. 用 `sft/*_sft.jsonl` 在 A100/3090 上跑 TS-RLM/Qwen caption SFT。",
            "3. 对 trained captioner 的 generated captions 跑 `scripts/eval/evaluate_natural_qcc_predictions.py`，再判断 QA 是否相比旧流程提升。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--natural_jsonl", type=Path, default=DEFAULT_NATURAL)
    parser.add_argument("--review_json", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--raw_jsonl", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run_name", default="natural_qcc_expansion")
    parser.add_argument("--allow_partial_review", action="store_true")
    args = parser.parse_args()

    natural_rows = load_jsonl(args.natural_jsonl)
    raw_by_id = {row["id"]: row for row in load_jsonl(args.raw_jsonl)}
    review_payload = json.loads(args.review_json.read_text(encoding="utf-8"))
    review_by_id = {row["id"]: row for row in review_payload.get("reviews", [])}

    missing_reviews = [row["id"] for row in natural_rows if row["id"] not in review_by_id]
    missing_raw = [row["id"] for row in natural_rows if row["id"] not in raw_by_id]
    if missing_raw:
        raise RuntimeError(f"Missing raw candidate rows for {len(missing_raw)} ids, first={missing_raw[0]}")
    if missing_reviews and not args.allow_partial_review:
        raise RuntimeError(
            f"Reviewer output is incomplete: missing {len(missing_reviews)} reviews; "
            "rerun reviewer or pass --allow_partial_review for debugging only"
        )

    positive: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for case in natural_rows:
        review = review_by_id.get(case["id"])
        if review is None:
            excluded.append({**case, "exclude_reason": "missing_review"})
            continue
        if review_pass(review):
            positive.append(build_row(raw_by_id[case["id"]], case, review))
        else:
            excluded.append({**case, "review": review, "exclude_reason": review.get("reason_zh", "")})

    args.out_dir.mkdir(parents=True, exist_ok=True)
    positive_jsonl = args.out_dir / f"{args.run_name}_positive.jsonl"
    excluded_jsonl = args.out_dir / f"{args.run_name}_excluded.jsonl"
    schema_json = args.out_dir / f"{args.run_name}_dataset_summary.json"
    report_md = args.out_dir / "NATURAL_QCC_EXPANSION_DATASET_20260519_ZH.md"
    write_jsonl(positive_jsonl, positive)
    write_jsonl(excluded_jsonl, excluded)

    sft_files = split_outputs(positive, args.out_dir, args.run_name)
    report = {
        "inputs": {
            "natural_jsonl": rel(args.natural_jsonl),
            "review_json": rel(args.review_json),
            "raw_jsonl": rel(args.raw_jsonl),
        },
        "outputs": {
            "positive_jsonl": rel(positive_jsonl),
            "excluded_jsonl": rel(excluded_jsonl),
            "schema_report": rel(schema_json),
            "report_md": rel(report_md),
        },
        "review_complete": not missing_reviews,
        "missing_review_count": len(missing_reviews),
        "positive": summarize_rows(positive),
        "excluded": summarize_rows(excluded),
        "sft_files": sft_files,
    }
    report["schema_gate_pass"] = (
        report["review_complete"]
        and report["positive"]["n"] > 0
        and report["positive"]["missing_required_count"] == 0
        and all(item["n"] > 0 for item in sft_files.values())
        and set(report["positive"]["by_value_dim"]).issubset({"1", "2", "3", "4"})
    )
    schema_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
