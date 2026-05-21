#!/usr/bin/env python3
"""Repair self-contained reasoning TSQA v2 into a v3 seed set.

v2 made the QA inputs self-contained, but its caption targets leaked the final
answer label. This script keeps the deterministic QA row structure, rewrites
caption targets as evidence-only text, and separates data-only-probe-pass rows
from rows that still need manual error attribution before expansion.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V2_DIR = ROOT / ".research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521"
DEFAULT_OUT_DIR = ROOT / ".research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521"
LETTERS = ("A", "B", "C", "D")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def fmt(value: Any) -> str:
    value = float(value)
    if abs(value) >= 100:
        return f"{value:.1f}"
    if abs(value) >= 10:
        return f"{value:.2f}"
    if abs(value) >= 1:
        return f"{value:.3f}"
    return f"{value:.4f}"


def pct(value: Any) -> str:
    return f"{float(value) * 100:.1f}%"


def met(flag: bool) -> str:
    return "met" if flag else "not met"


def met_zh(flag: bool) -> str:
    return "满足" if flag else "不满足"


def load_probe(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {row["id"]: row for row in payload.get("predictions", [])}


def domain_caption(row: dict[str, Any]) -> tuple[str, str]:
    slots = row["support_slots"]
    task = row["task_family"]
    if task == "self_contained_grid_counterfactual_risk":
        mean_x0 = float(slots["x0_mean"])
        frac_pos = float(slots["frac_gt_pos_0_05"])
        frac_neg = float(slots["frac_lt_neg_0_05"])
        max_abs = float(slots["max_abs_x0"])
        pos_gate = mean_x0 >= 0.05 and frac_pos >= 0.80
        neg_gate = mean_x0 <= -0.05 and frac_neg >= 0.80
        quiet_gate = abs(mean_x0) <= 0.02 and max_abs <= 0.03
        return (
            f"Across compact blocks, mean x0 is {fmt(mean_x0)}; the shares above +0.05 and below -0.05 are "
            f"{pct(frac_pos)} and {pct(frac_neg)}, and max absolute x0 is {fmt(max_abs)}. "
            f"The positive-stress gate is {met(pos_gate)}, the negative-stress gate is {met(neg_gate)}, "
            f"and the low-change gate is {met(quiet_gate)}.",
            f"跨压缩块看，x0 均值为 {fmt(mean_x0)}；高于 +0.05 和低于 -0.05 的比例分别为 {pct(frac_pos)}、{pct(frac_neg)}，"
            f"x0 最大绝对值为 {fmt(max_abs)}。正向压力门槛{met_zh(pos_gate)}，负向压力门槛{met_zh(neg_gate)}，"
            f"低变化门槛{met_zh(quiet_gate)}。",
        )

    if task == "self_contained_building_net_load_reserve":
        early = float(slots["early_net_mean"])
        middle = float(slots["middle_net_mean"])
        late = float(slots["late_net_mean"])
        gap = float(slots["gap_top_second"])
        means = {"early": early, "middle": middle, "late": late}
        top = max(means, key=means.get)
        second = sorted(means.values(), reverse=True)[1]
        separated = gap >= 0.30
        top_zh = {"early": "早段", "middle": "中段", "late": "后段"}[top]
        return (
            f"Early, middle, and late mean net loads are {fmt(early)}, {fmt(middle)}, and {fmt(late)}. "
            f"The largest third is {top}, the second-largest mean is {fmt(second)}, and the top-second gap is "
            f"{fmt(gap)} against the 0.30 separation threshold, so the separation gate is {met(separated)}.",
            f"早段、中段、后段平均净负荷分别为 {fmt(early)}、{fmt(middle)}、{fmt(late)}。"
            f"最高段是{top_zh}，第二高均值为 {fmt(second)}，最高与第二高差距为 {fmt(gap)}；"
            f"相对于 0.30 的分离阈值，该门槛{met_zh(separated)}。",
        )

    if task == "self_contained_traffic_recovery_reasoning":
        pre = float(slots["pre_score_mean"])
        event = float(slots["event_score_mean"])
        post = float(slots["post_score_mean"])
        event_rise = event - pre
        post_pre_gap = post - pre
        event_post_drop = event - post
        shock_gate = event_rise > 0.50
        recovery_gate = post <= pre + 0.30 and post <= event - 0.30
        persist_gate = post >= event - 0.20
        return (
            f"Pre-event, event, and post-event congestion-score means are {fmt(pre)}, {fmt(event)}, and {fmt(post)}. "
            f"The event rise over pre-event is {fmt(event_rise)} versus the 0.50 shock gate; post-event is "
            f"{fmt(post_pre_gap)} from pre-event and {fmt(event_post_drop)} below the event phase. "
            f"The shock, recovery, and persistence gates are {met(shock_gate)}, {met(recovery_gate)}, and {met(persist_gate)}.",
            f"事件前、事件中、事件后拥堵分数均值分别为 {fmt(pre)}、{fmt(event)}、{fmt(post)}。"
            f"事件中相对事件前上升 {fmt(event_rise)}，对应 0.50 的冲击门槛；事件后相对事件前为 {fmt(post_pre_gap)}，"
            f"并比事件中低 {fmt(event_post_drop)}。冲击、恢复、持续三个门槛分别{met_zh(shock_gate)}、{met_zh(recovery_gate)}、{met_zh(persist_gate)}。",
        )

    if task == "self_contained_water_service_recovery":
        pre = float(slots["pre_pressure_mean"])
        event = float(slots["event_pressure_mean"])
        post = float(slots["post_pressure_mean"])
        min_pressure = float(slots["min_pressure"])
        flow_jump = float(slots["event_flow_increase"])
        leak_gate = min_pressure < 55 and flow_jump > 1.0 and post < pre - 2.0
        recovery_gate = event < pre - 2.0 and post >= pre - 1.0
        stable_gate = abs(post - pre) <= 2.0
        return (
            f"Pre-event, event, and post-event pressure means are {fmt(pre)}, {fmt(event)}, and {fmt(post)}; "
            f"minimum pressure is {fmt(min_pressure)}, and event flow rises by {fmt(flow_jump)}. "
            f"Under the ordered checks, the leak-risk, recovery, and stable-pressure gates are "
            f"{met(leak_gate)}, {met(recovery_gate)}, and {met(stable_gate)}.",
            f"事件前、事件中、事件后水压均值分别为 {fmt(pre)}、{fmt(event)}、{fmt(post)}；"
            f"最低水压为 {fmt(min_pressure)}，事件中流量上升 {fmt(flow_jump)}。按顺序检查时，"
            f"漏损风险、恢复、稳定水压三个门槛分别{met_zh(leak_gate)}、{met_zh(recovery_gate)}、{met_zh(stable_gate)}。",
        )

    if task == "self_contained_aiops_symptom_triage":
        mem_first = float(slots["memory_first_half_mean"])
        mem_second = float(slots["memory_second_half_mean"])
        mem_growth = float(slots["memory_growth_ratio"])
        rx_ratio = float(slots["rx_peak_median_ratio"])
        tx_ratio = float(slots["tx_peak_median_ratio"])
        cpu_max = float(slots["cpu_max"])
        memory_gate = mem_growth >= 0.15
        network_gate = rx_ratio >= 2.5 or tx_ratio >= 2.5
        cpu_gate = cpu_max >= 0.85
        return (
            f"Mean memory changes from {fmt(mem_first)} in the first half to {fmt(mem_second)} in the second half "
            f"({pct(mem_growth)}). Receive and transmit peak ratios are {fmt(rx_ratio)} and {fmt(tx_ratio)}, "
            f"and max CPU is {fmt(cpu_max)}. In priority order, the memory, network, and CPU gates are "
            f"{met(memory_gate)}, {met(network_gate)}, and {met(cpu_gate)}.",
            f"内存均值从前半段 {fmt(mem_first)} 变为后半段 {fmt(mem_second)}，变化幅度为 {pct(mem_growth)}。"
            f"接收和发送峰值比为 {fmt(rx_ratio)}、{fmt(tx_ratio)}，CPU 最大值为 {fmt(cpu_max)}。按优先级看，"
            f"内存、网络、CPU 三个门槛分别{met_zh(memory_gate)}、{met_zh(network_gate)}、{met_zh(cpu_gate)}。",
        )

    if task == "self_contained_finrl_return_drawdown_regime":
        total_return = float(slots["total_return"])
        drawdown = float(slots["max_drawdown"])
        drawdown_gate = drawdown <= -0.20
        bullish_gate = total_return >= 0.08
        bearish_gate = total_return <= -0.08
        return (
            f"Total return is {pct(total_return)}, and maximum drawdown from the running peak is {pct(drawdown)}. "
            f"The drawdown priority gate at -20% is {met(drawdown_gate)}; if that gate is not active, "
            f"the +8% and -8% return gates are {met(bullish_gate)} and {met(bearish_gate)}.",
            f"总收益率为 {pct(total_return)}，相对历史峰值的最大回撤为 {pct(drawdown)}。"
            f"-20% 的回撤优先门槛{met_zh(drawdown_gate)}；若该门槛未触发，+8% 与 -8% 的收益率门槛分别"
            f"{met_zh(bullish_gate)}、{met_zh(bearish_gate)}。",
        )

    raise ValueError(f"unsupported task_family: {task}")


def clean_prompt(row: dict[str, Any]) -> str:
    variables = "; ".join(row.get("variables_en", []))
    return (
        "You are a time-series evidence captioner. Given the self-contained scene, decision rule, "
        "variable definitions, and question, write concise evidence that supports solving the question. "
        "Do not rely on platform-specific background, answer letters, or a standalone final option label.\n\n"
        f"Scene: {row['scene_en']}\n"
        f"Decision rule: {row['decision_rule_en']}\n"
        f"Variables: {variables}\n"
        f"Question: {row['question']}"
    )


def v3_id(v2_id: str) -> str:
    if "self_contained_reasoning_v2::" in v2_id:
        return v2_id.replace("self_contained_reasoning_v2::", "self_contained_reasoning_v3::", 1)
    return f"self_contained_reasoning_v3::{v2_id}"


def repair_row(row: dict[str, Any], probe_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out = deepcopy(row)
    source_v2_id = row["id"]
    new_id = v3_id(source_v2_id)
    probe = probe_by_id.get(source_v2_id) or probe_by_id.get(new_id)
    semantic_pass = bool(probe and probe.get("semantic_correct"))
    probe_status = "pass" if semantic_pass else "needs_error_attribution" if probe else "missing_probe"
    caption_en, caption_zh = domain_caption(row)

    out["id"] = new_id
    out["source_v2_id"] = source_v2_id
    out["domain"] = str(out.get("domain", "")).replace("_v2", "_v3")
    out["dataset_name"] = "self_contained_reasoning_qa_v3"
    out["seed_set"] = "self_contained_reasoning_qa_v3"
    out["generation_variant"] = "v3"
    out["natural_evidence_caption"] = caption_en
    out["natural_evidence_zh"] = caption_zh
    out["oracle_evidence_caption"] = caption_en
    out["target_caption"] = caption_en
    out["output"] = caption_en
    out["target_caption_zh"] = caption_zh
    out["prompt"] = clean_prompt(out)
    out["review_scope"] = "deterministic_self_contained_gate_v3_repair"
    out["review_decision"] = "keep" if semantic_pass else "revise"
    out["natural_status"] = "self_contained_reasoning_v3_positive_seed" if semantic_pass else "self_contained_reasoning_v3_needs_error_attribution"
    out["v3_probe_status"] = probe_status
    out["v3_probe_status_from_input"] = probe_status
    out["v3_positive_seed_ready"] = semantic_pass
    out["v3_repair_actions"] = [
        "removed_answer_label_sentence_from_target_caption",
        "rewrote_target_as_evidence_only_threshold_caption",
        "preserved_deterministic_support_slots_and_options",
    ]
    meta = deepcopy(out.get("meta", {}))
    meta.update(
        {
            "generation_variant": "v3",
            "source_generation_variant": "v2",
            "source_v2_id": source_v2_id,
            "v3_probe_status": probe_status,
            "v3_probe_status_from_input": probe_status,
            "v3_positive_seed_ready": semantic_pass,
            "v3_repair_actions": out["v3_repair_actions"],
        }
    )
    out["meta"] = meta
    return out


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "source_v2_id": row["source_v2_id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row["target_caption"],
        "target_caption_zh": row["target_caption_zh"],
        "meta": row["meta"],
    }


def balanced_subset(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_letter: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_letter[row["answer"]].append(row)
    if any(not by_letter.get(letter) for letter in LETTERS):
        return []
    per_letter = min(len(by_letter[letter]) for letter in LETTERS)
    selected: list[dict[str, Any]] = []
    for letter in LETTERS:
        selected.extend(sorted(by_letter[letter], key=lambda item: (item["merge_source_name"], item["id"]))[:per_letter])
    return sorted(selected, key=lambda item: item["id"])


def leakage_audit(rows: list[dict[str, Any]]) -> dict[str, int]:
    target_fields = ("target_caption", "output", "oracle_evidence_caption", "natural_evidence_caption")
    answer_label_regex = re.compile(r"\bAnswer label\b|答案是|supports the answer|therefore supports", re.I)
    rule_template_regex = re.compile(r"the rule maps this to|按规则判断为", re.I)
    return {
        "target_answer_label_phrase_hits": sum(
            1 for row in rows for field in target_fields if answer_label_regex.search(str(row.get(field, "")))
        ),
        "rule_maps_template_hits": sum(
            1 for row in rows for field in target_fields if rule_template_regex.search(str(row.get(field, "")))
        ),
        "target_exact_answer_label_hits": sum(
            1
            for row in rows
            if str(row.get("answer_label", "")).lower() in str(row.get("target_caption", "")).lower()
        ),
    }


def summarize(rows: list[dict[str, Any]], ready: list[dict[str, Any]], needs: list[dict[str, Any]], balanced: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n_all": len(rows),
        "n_positive_seed_ready": len(ready),
        "n_needs_error_attribution": len(needs),
        "n_balanced_positive_eval": len(balanced),
        "by_domain_all": dict(Counter(row["merge_source_name"] for row in rows)),
        "by_domain_positive_ready": dict(Counter(row["merge_source_name"] for row in ready)),
        "by_domain_needs_error_attribution": dict(Counter(row["merge_source_name"] for row in needs)),
        "answer_distribution_all": dict(Counter(row["answer"] for row in rows)),
        "answer_distribution_positive_ready": dict(Counter(row["answer"] for row in ready)),
        "answer_distribution_balanced_positive_eval": dict(Counter(row["answer"] for row in balanced)),
        "leakage_audit_all": leakage_audit(rows),
        "leakage_audit_positive_ready": leakage_audit(ready),
    }


def render_report(out_dir: Path, summary: dict[str, Any], inputs: dict[str, str]) -> None:
    lines = [
        "# Self-contained Reasoning TSQA v3 Repair Report（2026-05-21）",
        "",
        "## 结论",
        "",
        "v3 的目标不是重新发明 QA 规则，而是把 v2 中已经自包含的题面保留下来，修复 caption 训练目标泄漏，并把可扩增 seed 与需错误归因样本拆开。",
        "",
        f"- 全量 v3 rows：{summary['n_all']}",
        f"- positive seed ready：{summary['n_positive_seed_ready']}",
        f"- needs error attribution：{summary['n_needs_error_attribution']}",
        f"- answer-balanced positive eval：{summary['n_balanced_positive_eval']}",
        f"- target/caption `Answer label` 类泄漏命中：{summary['leakage_audit_all']['target_answer_label_phrase_hits']}",
        f"- target/caption `the rule maps this to` 类模板命中：{summary['leakage_audit_all']['rule_maps_template_hits']}",
        "",
        "## 输入",
        "",
        f"- v2 rows: `{inputs['v2_rows']}`",
        f"- data-only probe: `{inputs['data_only_probe']}`",
        "",
        "## 输出",
        "",
        f"- 全量 v3：`{rel(out_dir / 'self_contained_reasoning_tsqa.jsonl')}`",
        f"- positive ready：`{rel(out_dir / 'self_contained_reasoning_tsqa_v3_ready.jsonl')}`",
        f"- 需错误归因：`{rel(out_dir / 'self_contained_reasoning_tsqa_v3_needs_error_attribution.jsonl')}`",
        f"- answer-balanced eval 子集：`{rel(out_dir / 'self_contained_reasoning_tsqa_v3_balanced_positive_eval.jsonl')}`",
        f"- SFT caption rows：`{rel(out_dir / 'self_contained_reasoning_tsqa_sft.jsonl')}`",
        f"- summary: `{rel(out_dir / 'self_contained_reasoning_tsqa_v3_summary.json')}`",
        "",
        "## 分布",
        "",
        f"- all by domain: `{json.dumps(summary['by_domain_all'], ensure_ascii=False)}`",
        f"- ready by domain: `{json.dumps(summary['by_domain_positive_ready'], ensure_ascii=False)}`",
        f"- needs attribution by domain: `{json.dumps(summary['by_domain_needs_error_attribution'], ensure_ascii=False)}`",
        f"- all answer distribution: `{json.dumps(summary['answer_distribution_all'], ensure_ascii=False)}`",
        f"- ready answer distribution: `{json.dumps(summary['answer_distribution_positive_ready'], ensure_ascii=False)}`",
        f"- balanced eval answer distribution: `{json.dumps(summary['answer_distribution_balanced_positive_eval'], ensure_ascii=False)}`",
        "",
        "## 修复动作",
        "",
        "1. 删除 v2 `target_caption/output/oracle_evidence_caption` 中的答案标签句。",
        "2. 将 caption 改成 evidence-only：给出聚合量、阈值门槛是否满足、优先级检查结果，但不输出选项字母。",
        "3. 保留 `support_slots/options/answer`，gold answer 仍完全由 deterministic slots 决定。",
        "4. 使用输入 data-only probe 结果做初始分流：semantic pass 进入 positive seed；semantic wrong 进入 error attribution。",
        "",
        "## 解释",
        "",
        "positive seed ready 不是最终 benchmark，只是下一轮扩增的干净起点。需错误归因样本不能直接丢弃，因为 data-only wrong 可能是模型能力或输出解析问题；但在完成归因前，不应把这些样本混入正例扩增。",
        "",
    ]
    (out_dir / "SELF_CONTAINED_REASONING_TSQA_V3_REPAIR_REPORT_20260521_ZH.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_jsonl", type=Path, default=DEFAULT_V2_DIR / "self_contained_reasoning_tsqa.jsonl")
    parser.add_argument("--probe", type=Path, default=DEFAULT_V2_DIR / "self_contained_reasoning_tsqa_gpt_data_only_probe.json")
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    rows_v2 = load_jsonl(args.input_jsonl)
    probe_by_id = load_probe(args.probe)
    rows_v3 = [repair_row(row, probe_by_id) for row in rows_v2]
    ready = [row for row in rows_v3 if row["v3_positive_seed_ready"]]
    needs = [row for row in rows_v3 if not row["v3_positive_seed_ready"]]
    balanced = balanced_subset(ready)
    summary = summarize(rows_v3, ready, needs, balanced)
    summary["inputs"] = {"v2_rows": rel(args.input_jsonl), "data_only_probe": rel(args.probe)}
    summary["outputs"] = {
        "all": rel(args.out_dir / "self_contained_reasoning_tsqa.jsonl"),
        "ready": rel(args.out_dir / "self_contained_reasoning_tsqa_v3_ready.jsonl"),
        "needs_error_attribution": rel(args.out_dir / "self_contained_reasoning_tsqa_v3_needs_error_attribution.jsonl"),
        "balanced_positive_eval": rel(args.out_dir / "self_contained_reasoning_tsqa_v3_balanced_positive_eval.jsonl"),
        "sft": rel(args.out_dir / "self_contained_reasoning_tsqa_sft.jsonl"),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "self_contained_reasoning_tsqa.jsonl", rows_v3)
    write_jsonl(args.out_dir / "self_contained_reasoning_tsqa_v3_all.jsonl", rows_v3)
    write_jsonl(args.out_dir / "self_contained_reasoning_tsqa_v3_ready.jsonl", ready)
    write_jsonl(args.out_dir / "self_contained_reasoning_tsqa_v3_needs_error_attribution.jsonl", needs)
    write_jsonl(args.out_dir / "self_contained_reasoning_tsqa_v3_balanced_positive_eval.jsonl", balanced)
    write_jsonl(args.out_dir / "self_contained_reasoning_tsqa_sft.jsonl", [sft_row(row) for row in ready])
    write_json(args.out_dir / "self_contained_reasoning_tsqa_v3_summary.json", summary)
    render_report(args.out_dir, summary, summary["inputs"])
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
