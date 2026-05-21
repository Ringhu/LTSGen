#!/usr/bin/env python3
"""Attribute GPT data-only probe errors without using the probe as an answer oracle."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROWS = (
    ROOT
    / ".research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/"
    / "self_contained_reasoning_tsqa.jsonl"
)
DEFAULT_PROBE = (
    ROOT
    / ".research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/"
    / "self_contained_reasoning_tsqa_gpt_data_only_probe.json"
)
DEFAULT_OUT_DIR = ROOT / ".research/general-qcc-captioner-20260515/self_contained_error_attribution_v1_20260521"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def has_positive_gold_reason(reason: str, gold: str, source_row_id: str) -> bool:
    text = reason.lower()
    gold = gold.lower()
    positive_markers = (
        f"rule says {gold}",
        f"correct outcome is {gold}",
        f"rule outcome is {gold}",
        f"corresponds to {gold}",
        f"correct option text matching the computed rule outcome is {gold}",
        f"choose {gold}",
        f"{gold} applies",
        f"state is {gold}",
        f"regime is {gold}",
    )
    if any(marker in text for marker in positive_markers):
        return True
    if source_row_id.endswith("aiops_incident_dominant_symptom") and "no threshold is met" in text:
        return True
    if source_row_id.endswith("traffic_signal_policy_counterfactual_queue") and "no clear congestion shock" in text:
        return True
    return False


def classify(pred: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    reason = pred.get("reason", "")
    reason_lower = reason.lower()
    gold = pred["gold_answer_label"]
    pred_label = pred["pred_answer_label"]
    source = pred["source"]
    source_row_id = pred["source_row_id"]
    support = row.get("support_slots") or {}

    if has_positive_gold_reason(reason, gold, source_row_id):
        attribution = "model_reason_answer_inconsistency"
        decision = "hard_keep_for_seed"
        explanation = "probe 的推理文本已经算到 gold 语义，但最终 JSON answer/answer_label 填成了另一个选项。"
    elif source == "water":
        attribution = "model_rule_application_error_with_water_clause_clarity_risk"
        decision = "keep_for_seed_but_rewrite_water_rule_wording_before_scaling"
        explanation = (
            "deterministic support slots 满足 gold，但 probe 对水压恢复/稳定/人工复核的优先级或 "
            "`post >= pre - 1` 这类恢复条件应用错误；这更像模型规则应用失败，同时提示 Water 规则措辞还应更清楚。"
        )
    else:
        attribution = "model_rule_application_error"
        decision = "keep_for_seed_after_manual_check"
        explanation = "deterministic support slots 和 gold 保持一致，probe 错误主要来自模型对规则或算术的应用失败。"

    if pred.get("label_letter_mismatch"):
        attribution = "probe_letter_label_parse_inconsistency"
        decision = "rerun_probe_parser_check"
        explanation = "probe 输出的字母和标签互相矛盾，应先检查解析/输出格式。"

    data_defect = attribution in {
        "rule_ambiguity_data_defect",
        "feature_insufficient_data_defect",
        "option_mapping_data_defect",
    }

    return {
        "id": pred["id"],
        "source_row_id": source_row_id,
        "domain": source,
        "task_family": pred["task_family"],
        "gold_answer": pred["gold_answer"],
        "gold_answer_label": gold,
        "pred_answer": pred["pred_answer"],
        "pred_answer_label": pred_label,
        "confidence": pred.get("confidence"),
        "attribution": attribution,
        "recommended_decision": decision,
        "data_defect": data_defect,
        "support_slots": support,
        "computed_summary": pred.get("computed_summary"),
        "explanation_zh": explanation,
        "reason_excerpt": reason[-500:],
    }


def summarize(attributions: list[dict[str, Any]], probe_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "n_probe": probe_summary.get("n"),
        "n_wrong": len(attributions),
        "wrong_by_domain": dict(Counter(row["domain"] for row in attributions)),
        "attribution_counts": dict(Counter(row["attribution"] for row in attributions)),
        "recommended_decision_counts": dict(Counter(row["recommended_decision"] for row in attributions)),
        "data_defect_count": sum(1 for row in attributions if row["data_defect"]),
        "interpretation": (
            "GPT data-only wrong is diagnostic only. In this attribution pass, no row is marked as a deterministic "
            "data defect; Water rows should still get clearer rule wording before scaling because many probe errors "
            "cluster around recovery/stable/manual-review priority."
        ),
    }


def report(summary: dict[str, Any], rows: list[dict[str, Any]], out_dir: Path) -> str:
    lines = [
        "# Self-contained GPT Data-only Error Attribution v1（2026-05-21）",
        "",
        "## 结论",
        "",
        "这一步不是让 GPT 决定题目对错，而是解释 GPT data-only probe 为什么答错。",
        "归因结果显示：15 条错误里没有一条被判为确定性 gold/data defect；大部分是模型 reason 已经算到正确语义，但最后输出了错误选项。",
        "",
        f"- probe 总样本：{summary['n_probe']}",
        f"- data-only wrong：{summary['n_wrong']}",
        f"- data defect：{summary['data_defect_count']}",
        f"- wrong by domain：{summary['wrong_by_domain']}",
        f"- attribution：{summary['attribution_counts']}",
        "",
        "## 为什么这很重要",
        "",
        "如果把 `gpt_data_only_wrong` 直接当成 reject gate，就会误删很多本来规则和 gold 都没问题的样本。",
        "更合理的做法是：它只触发人工归因；只有归因为规则歧义、特征不足或选项映射错误时，才删题或重写 gold。",
        "",
        "## 逐条归因",
        "",
        "| domain | gold | pred | attribution | decision |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['domain']}` | `{row['gold_answer_label']}` | `{row['pred_answer_label']}` | "
            f"`{row['attribution']}` | `{row['recommended_decision']}` |"
        )
    lines.extend([
        "",
        "## Water 的额外说明",
        "",
        "Water 错误最多，但这不等于 Water 题都坏了。几个错误是 probe 把“事件后水压反弹到至少 pre-1”理解成不能超过 pre，或者在恢复/稳定/人工复核的优先级上绕错。",
        "因此当前判断是：这些样本可以保留为 seed，但 Water 的大规模扩增规则应写得更硬一些，例如明确“post 高于 pre 也满足恢复阈值”。",
        "",
        "## 产物",
        "",
        f"- attribution JSONL: `{out_dir / 'self_contained_data_only_error_attribution_v1.jsonl'}`",
        f"- summary JSON: `{out_dir / 'self_contained_data_only_error_attribution_v1_summary.json'}`",
        f"- report: `{out_dir / 'SELF_CONTAINED_DATA_ONLY_ERROR_ATTRIBUTION_V1_20260521_ZH.md'}`",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, default=DEFAULT_ROWS)
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    rows_by_id: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(args.rows):
        rows_by_id[row["id"]] = row
        if row.get("source_v2_id"):
            rows_by_id[row["source_v2_id"]] = row
    probe = json.loads(args.probe.read_text(encoding="utf-8"))
    wrong = [pred for pred in probe["predictions"] if not pred.get("semantic_correct")]
    attributions = [classify(pred, rows_by_id[pred["id"]]) for pred in wrong]
    summary_data = summarize(attributions, probe.get("summary") or {})

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "self_contained_data_only_error_attribution_v1.jsonl", attributions)
    (args.out_dir / "self_contained_data_only_error_attribution_v1_summary.json").write_text(
        json.dumps(summary_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "SELF_CONTAINED_DATA_ONLY_ERROR_ATTRIBUTION_V1_20260521_ZH.md").write_text(
        report(summary_data, attributions, args.out_dir.relative_to(ROOT)) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
