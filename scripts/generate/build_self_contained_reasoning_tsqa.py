#!/usr/bin/env python3
"""Build self-contained reasoning TS-QA rows from scenario-first traces.

The generated rows intentionally avoid platform-specific prior knowledge in the
user-facing scene. Each row includes a domain rule that can be applied directly
to the provided physical-unit time series values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    ROOT
    / ".research/general-qcc-captioner-20260515/scenario_first_multidomain_smoke_v2_20260520/"
    / "scenario_first_multidomain_smoke_v2.jsonl"
)
DEFAULT_OUT = ROOT / ".research/general-qcc-captioner-20260515/self_contained_reasoning_qa_20260521"
DOMAINS = ("grid2op", "citylearn", "traffic", "water", "aiopslab", "finrl")
LETTERS = ("A", "B", "C", "D")
GENERATION_VARIANT = "v1"


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
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def stable_int(*parts: Any) -> int:
    text = "::".join(str(p) for p in parts)
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def fmt(value: float) -> str:
    return f"{float(value):.2f}"


def fmt_pct(value: float) -> str:
    return f"{100 * float(value):.1f}%"


def is_v2() -> bool:
    return GENERATION_VARIANT == "v2"


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def max_drawdown(prices: list[float]) -> float:
    peak = prices[0]
    drawdown = 0.0
    for price in prices:
        peak = max(peak, price)
        drawdown = min(drawdown, price / peak - 1.0)
    return drawdown


def thirds(values: list[float]) -> tuple[list[float], list[float], list[float]]:
    n = len(values)
    return values[: n // 3], values[n // 3 : 2 * n // 3], values[2 * n // 3 :]


def halves(values: list[float]) -> tuple[list[float], list[float]]:
    n = len(values)
    return values[: n // 2], values[n // 2 :]


def contiguous_blocks(raw: list[list[float]], n_blocks: int = 12) -> list[list[list[float]]]:
    blocks = []
    n = len(raw)
    for block_idx in range(n_blocks):
        start = round(block_idx * n / n_blocks)
        end = round((block_idx + 1) * n / n_blocks)
        blocks.append(raw[start:end])
    return [block for block in blocks if block]


def col(block: list[list[float]], idx: int) -> list[float]:
    return [record[idx] for record in block]


def compact_grid(raw: list[list[float]]) -> list[list[float]]:
    compact = []
    for block in contiguous_blocks(raw, 12):
        diff = col(block, 0)
        compact.append(
            [
                mean(diff),
                sum(x > 0.05 for x in diff) / len(diff),
                sum(x < -0.05 for x in diff) / len(diff),
                max(abs(x) for x in diff),
            ]
        )
    return compact


def compact_city(raw: list[list[float]]) -> list[list[float]]:
    compact = []
    for block in contiguous_blocks(raw, 12):
        demand = col(block, 0)
        weather = col(block, 1)
        solar = col(block, 2)
        net = [d - 0.15 * s for d, s in zip(demand, solar)]
        compact.append([mean(demand), mean(weather), mean(solar), mean(net)])
    return compact


def compact_traffic(raw: list[list[float]]) -> list[list[float]]:
    compact = []
    for block in contiguous_blocks(raw, 12):
        speed = col(block, 0)
        queue = col(block, 1)
        occ = col(block, 2)
        score = [q + 8.0 * o - 0.05 * s for s, q, o in zip(speed, queue, occ)]
        compact.append([mean(speed), mean(queue), mean(occ), mean(score)])
    return compact


def compact_water(raw: list[list[float]]) -> list[list[float]]:
    compact = []
    for block in contiguous_blocks(raw, 12):
        pressure = col(block, 0)
        flow = col(block, 1)
        compact.append([mean(pressure), mean(flow), min(pressure)])
    return compact


def compact_aiops(raw: list[list[float]]) -> list[list[float]]:
    compact = []
    for block in contiguous_blocks(raw, 12):
        cpu = col(block, 0)
        mem = col(block, 1)
        rx = col(block, 2)
        tx = col(block, 3)
        compact.append(
            [
                max(cpu),
                mean(mem),
                max(rx) / max(median(rx), 1e-9),
                max(tx) / max(median(tx), 1e-9),
            ]
        )
    return compact


def compact_finrl(raw: list[list[float]]) -> list[list[float]]:
    compact = []
    for block in contiguous_blocks(raw, 24):
        price = col(block, 0)
        context = col(block, 1)
        volume = col(block, 2)
        compact.append([price[-1], mean(context), mean(volume), min(price)])
    if compact:
        compact[0][0] = raw[0][0]
    return compact


def optionize(labels: list[str], correct: str, key: str) -> tuple[list[str], str]:
    del key
    if correct not in labels:
        raise ValueError(f"correct label not in labels: {correct}")
    mapping = {letter: label for letter, label in zip(LETTERS, labels)}
    answer = LETTERS[labels.index(correct)]
    return [f"{letter}. {mapping[letter]}" for letter in LETTERS], answer


def split_option_labels(options: list[str]) -> dict[str, str]:
    return {option.split(". ", 1)[0]: option.split(". ", 1)[1] for option in options}


def translate_options(options: list[str], zh_map: dict[str, str]) -> list[str]:
    out = []
    for option in options:
        letter, label = option.split(". ", 1)
        out.append(f"{letter}. {zh_map[label]}")
    return out


def get_raw(row: dict[str, Any]) -> list[list[float]]:
    raw = row.get("raw_compact_values") or row.get("values")
    if not raw:
        raise ValueError(f"missing raw values for {row.get('id')}")
    return [[float(x) for x in record] for record in raw]


def common_row(
    source: dict[str, Any],
    *,
    task_family: str,
    raw: list[list[float]],
    scene_en: str,
    scene_zh: str,
    variables_en: list[str],
    variables_zh: list[str],
    decision_rule_en: str,
    decision_rule_zh: str,
    question_en: str,
    question_zh: str,
    labels_en: list[str],
    labels_zh: dict[str, str],
    answer_label: str,
    evidence_en: str,
    evidence_zh: str,
    support_slots: dict[str, Any],
    reasoning_steps_en: list[str],
    reasoning_steps_zh: list[str],
    tags: list[str],
    raw_compact: list[list[float]] | None = None,
) -> dict[str, Any]:
    source_domain = str(source.get("merge_source_name"))
    id_prefix = "self_contained_reasoning_v2" if is_v2() else "self_contained_reasoning"
    domain_suffix = "self_contained_reasoning_v2" if is_v2() else "self_contained_reasoning"
    new_id = f"{id_prefix}::{source_domain}::{source.get('id')}::{task_family}"
    options, answer = optionize(labels_en, answer_label, new_id)
    options_zh = translate_options(options, labels_zh)
    prompt = (
        "You are a time-series evidence captioner. Given the self-contained scene, "
        "decision rule, variable definitions, and question, write concise evidence "
        "that supports the answer. Do not rely on platform-specific background.\n\n"
        f"Scene: {scene_en}\n"
        f"Decision rule: {decision_rule_en}\n"
        f"Variables: {'; '.join(variables_en)}\n"
        f"Question: {question_en}"
    )
    target = f"{evidence_en} Answer label: {answer_label}."
    meta = dict(source.get("meta") or {})
    meta.update(
        {
            "self_contained_reasoning_tsqa": True,
            "source_row_id": source.get("id"),
            "merge_source_name": source_domain,
            "task_family": task_family,
            "answer": answer,
            "answer_label": answer_label,
            "reasoning_skill_tags": tags,
            "data_given_to_solver": "compact_block_physical_features" if is_v2() else "physical_unit_values",
            "generation_variant": GENERATION_VARIANT,
        }
    )
    return {
        "id": new_id,
        "source_row_id": source.get("id"),
        "merge_source_name": source_domain,
        "domain": f"{source_domain}_{domain_suffix}",
        "split": source.get("split", "train"),
        "horizon": len(raw),
        "source_horizon": len(raw_compact or raw),
        "solver_values_kind": "compact_block_physical_features" if is_v2() else "physical_unit_values",
        "task_family": task_family,
        "scene_en": scene_en,
        "scene_zh": scene_zh,
        "variables_en": variables_en,
        "variables_zh": variables_zh,
        "decision_rule_en": decision_rule_en,
        "decision_rule_zh": decision_rule_zh,
        "question": question_en,
        "question_zh": question_zh,
        "options": options,
        "options_zh": options_zh,
        "option_label_by_letter": split_option_labels(options),
        "answer": answer,
        "answer_label": answer_label,
        "answer_zh": labels_zh[answer_label],
        "values": raw,
        "raw_compact_values": raw_compact or raw,
        "raw_compact_values_kind": "source_full_physical_values" if raw_compact else "solver_physical_values",
        "normalized_values_available_in_source": bool(source.get("values")),
        "natural_evidence_caption": evidence_en,
        "natural_evidence_zh": evidence_zh,
        "oracle_evidence_caption": target,
        "target_caption": target,
        "output": target,
        "prompt": prompt,
        "support_slots": support_slots,
        "reasoning_steps_en": reasoning_steps_en,
        "reasoning_steps_zh": reasoning_steps_zh,
        "reasoning_skill_tags": tags,
        "requires_reasoning": True,
        "background_self_contained": True,
        "simulator_prior_required": False,
        "review_scope": "deterministic_self_contained_gate",
        "generation_variant": GENERATION_VARIANT,
        "review_decision": "keep",
        "review_naturalness_score": 4,
        "review_answerability_score": 5,
        "review_accuracy_risk": "low",
        "natural_status": "self_contained_reasoning_candidate",
        "meta": meta,
    }


def transform_grid(row: dict[str, Any]) -> dict[str, Any]:
    raw_original = get_raw(row)
    raw = compact_grid(raw_original) if is_v2() else raw_original
    if is_v2():
        avg = mean([r[0] for r in raw])
        frac_pos = mean([r[1] for r in raw])
        frac_neg = mean([r[2] for r in raw])
        max_abs = max(r[3] for r in raw)
    else:
        diff = [r[0] for r in raw]
        avg = mean(diff)
        frac_pos = sum(x > 0.05 for x in diff) / len(diff)
        frac_neg = sum(x < -0.05 for x in diff) / len(diff)
        max_abs = max(abs(x) for x in diff)
    if avg >= 0.05 and frac_pos >= 0.80:
        label = "risk increases"
    elif avg <= -0.05 and frac_neg >= 0.80:
        label = "risk decreases"
    elif abs(avg) <= 0.02 and max_abs <= 0.03:
        label = "risk is broadly unchanged"
    else:
        label = "manual review needed"
    labels = ["risk increases", "risk decreases", "risk is broadly unchanged", "manual review needed"]
    labels_zh = {
        "risk increases": "风险上升",
        "risk decreases": "风险下降",
        "risk is broadly unchanged": "风险基本不变",
        "manual review needed": "需要人工复核",
    }
    return common_row(
        row,
        task_family="self_contained_grid_counterfactual_risk",
        raw=raw,
        scene_en=(
            "A power-grid operator is comparing a planned line-outage run with a matched normal run. "
            "No platform-specific prior knowledge is needed: x0 is the outage-minus-normal stress difference at each step, "
            "so positive x0 means the outage is more stressful and negative x0 means it is less stressful."
        ),
        scene_zh=(
            "电网调度员正在比较一次计划断线运行和匹配的正常运行。无需了解任何特定平台背景："
            "x0 是每个时间步的“断线运行减正常运行”的压力差，x0 为正表示断线更紧张，x0 为负表示断线更安全。"
        ),
        variables_en=(
            [
                "x0 block mean outage-minus-normal line stress difference",
                "x1 block share where the difference exceeds +0.05",
                "x2 block share where the difference is below -0.05",
                "x3 block maximum absolute stress difference",
            ]
            if is_v2()
            else [
                "x0 outage-minus-normal line stress difference",
                "x1 total demand context",
                "x2 generation margin context",
            ]
        ),
        variables_zh=(
            ["x0 分块平均断线减正常压力差", "x1 分块中差值大于 +0.05 的比例", "x2 分块中差值小于 -0.05 的比例", "x3 分块最大绝对压力差"]
            if is_v2()
            else ["x0 断线减正常压力差", "x1 总需求上下文", "x2 发电裕度上下文"]
        ),
        decision_rule_en=(
            "The compact table has one row per contiguous time block. Compute mean x0, mean x1, mean x2, and max x3 across rows. "
            "Choose risk increases if mean x0 >= +0.05 and mean x1 >= 0.80; risk decreases if mean x0 <= -0.05 and mean x2 >= 0.80; "
            "risk is broadly unchanged if absolute mean x0 is at most 0.02 and max x3 is at most 0.03; otherwise choose manual review needed. "
            "Do not choose manual review when one of the earlier rules is satisfied."
            if is_v2()
            else "Compute the mean of x0 and the share of steps where x0 exceeds +0.05 or is below -0.05. "
            "Choose risk increases if mean x0 >= +0.05 and at least 80% of steps exceed +0.05; "
            "risk decreases if mean x0 <= -0.05 and at least 80% of steps are below -0.05; "
            "risk is broadly unchanged if |mean x0| <= 0.02 and every |x0| <= 0.03; otherwise choose manual review needed."
        ),
        decision_rule_zh=(
            "压缩表每行对应一个连续时间块。跨行计算 x0 均值、x1 均值、x2 均值和 x3 最大值。"
            "若 x0 均值 >= +0.05 且 x1 均值 >= 0.80，选风险上升；若 x0 均值 <= -0.05 且 x2 均值 >= 0.80，选风险下降；"
            "若 |x0 均值| <= 0.02 且 x3 最大值 <= 0.03，选风险基本不变；否则选需要人工复核。"
            "只要前面的规则满足，就不要再选需要人工复核。"
            if is_v2()
            else "计算 x0 均值，以及 x0 大于 +0.05 或小于 -0.05 的时间步比例。"
            "若均值 >= +0.05 且至少 80% 时间步大于 +0.05，选风险上升；"
            "若均值 <= -0.05 且至少 80% 时间步小于 -0.05，选风险下降；"
            "若 |均值| <= 0.02 且所有 |x0| <= 0.03，选风险基本不变；否则选需要人工复核。"
        ),
        question_en="Using the rule and the x0 series, what should the operator conclude about the planned outage?",
        question_zh="根据规则和 x0 序列，调度员应如何判断这次计划断线的影响？",
        labels_en=labels,
        labels_zh=labels_zh,
        answer_label=label,
        evidence_en=(
            f"Mean x0 is {fmt(avg)}, with {fmt_pct(frac_pos)} of steps above +0.05 and "
            f"{fmt_pct(frac_neg)} below -0.05; the rule maps this to {label}."
        ),
        evidence_zh=(
            f"x0 均值为 {fmt(avg)}，大于 +0.05 的时间步占 {fmt_pct(frac_pos)}，"
            f"小于 -0.05 的时间步占 {fmt_pct(frac_neg)}；按规则判断为：{labels_zh[label]}。"
        ),
        support_slots={
            "x0_mean": avg,
            "frac_gt_pos_0_05": frac_pos,
            "frac_lt_neg_0_05": frac_neg,
            "max_abs_x0": max_abs,
            "answer_label": label,
        },
        reasoning_steps_en=["aggregate x0", "apply threshold and proportion rule", "map to operational conclusion"],
        reasoning_steps_zh=["汇总 x0", "应用阈值和比例规则", "映射为运行结论"],
        tags=["counterfactual_effect", "threshold_reasoning", "aggregation"],
        raw_compact=raw_original if is_v2() else None,
    )


def transform_city(row: dict[str, Any]) -> dict[str, Any]:
    raw_original = get_raw(row)
    raw = compact_city(raw_original) if is_v2() else raw_original
    demand = [r[0] for r in raw]
    solar = [r[2] for r in raw]
    net = [r[3] for r in raw] if is_v2() else [d - 0.15 * s for d, s in zip(demand, solar)]
    segs = thirds(net)
    seg_means = [mean(x) for x in segs]
    best_idx = max(range(3), key=lambda i: seg_means[i])
    ordered = sorted(seg_means, reverse=True)
    if ordered[0] - ordered[1] < 0.30:
        label = "balanced reserve"
    elif best_idx == 0:
        label = "reserve early"
    elif best_idx == 2:
        label = "reserve late"
    else:
        label = "reserve middle"
    labels = ["reserve early", "reserve middle", "reserve late", "balanced reserve"]
    labels_zh = {
        "reserve early": "优先为早段预留供能",
        "reserve middle": "优先为中段预留供能",
        "reserve late": "优先为后段预留供能",
        "balanced reserve": "按均衡供能准备",
    }
    return common_row(
        row,
        task_family="self_contained_building_net_load_reserve",
        raw=raw,
        scene_en=(
            "A building energy planner is deciding when to reserve supply for a 256-step operating window. "
            "No platform-specific prior knowledge is needed. x0 is building demand, x2 is local solar support, "
            "and net grid load is defined here as x0 - 0.15*x2."
        ),
        scene_zh=(
            "建筑能耗规划员需要为一个 256 步运行窗口安排供能预留。无需了解任何特定平台背景。"
            "x0 是建筑用电需求，x2 是本地太阳能支持；这里定义净电网负荷为 x0 - 0.15*x2。"
        ),
        variables_en=(
            ["x0 block mean building demand", "x1 block mean weather context", "x2 block mean local solar support", "x3 block mean net grid load"]
            if is_v2()
            else ["x0 building demand", "x1 weather context", "x2 local solar support"]
        ),
        variables_zh=(
            ["x0 分块平均建筑用电需求", "x1 分块平均天气上下文", "x2 分块平均本地太阳能支持", "x3 分块平均净电网负荷"]
            if is_v2()
            else ["x0 建筑用电需求", "x1 天气上下文", "x2 本地太阳能支持"]
        ),
        decision_rule_en=(
            "The compact table has one row per contiguous time block; x3 is already the block mean net grid load x0 - 0.15*x2. "
            "Split the compact rows into early, middle, and late thirds. If the largest third-mean x3 exceeds the second-largest by at least 0.30, "
            "reserve supply for that third; otherwise choose balanced reserve. If the gap is below 0.30, the final answer must be balanced reserve. "
            "After computing the gap, make the answer label exactly match the rule outcome."
            if is_v2()
            else "Compute net grid load = x0 - 0.15*x2 at each step. Split the window into early, middle, and late thirds. "
            "If the largest third-mean net load exceeds the second-largest by at least 0.30, reserve supply for that third; "
            "otherwise choose balanced reserve."
        ),
        decision_rule_zh=(
            "压缩表每行对应一个连续时间块；x3 已经是该块平均净电网负荷 x0 - 0.15*x2。"
            "把压缩行分成早段、中段、后段。若最高一段的 x3 均值比第二高至少高 0.30，就为该段优先预留供能；"
            "否则按均衡供能准备。若差距低于 0.30，最终答案必须是均衡供能。计算差距后，答案标签必须与规则输出完全一致。"
            if is_v2()
            else "每步计算净电网负荷 = x0 - 0.15*x2。把窗口按时间分成早段、中段、后段。"
            "如果最高一段的平均净负荷比第二高至少高 0.30，就为该段优先预留供能；否则按均衡供能准备。"
        ),
        question_en="Using the net-load rule, when should supply be reserved for this window?",
        question_zh="根据净负荷规则，这个窗口应在哪个时段优先预留供能？",
        labels_en=labels,
        labels_zh=labels_zh,
        answer_label=label,
        evidence_en=(
            f"Mean net loads for early, middle, and late thirds are {fmt(seg_means[0])}, "
            f"{fmt(seg_means[1])}, and {fmt(seg_means[2])}; the rule maps this to {label}."
        ),
        evidence_zh=(
            f"早段、中段、后段平均净负荷分别为 {fmt(seg_means[0])}、{fmt(seg_means[1])}、{fmt(seg_means[2])}；"
            f"按规则判断为：{labels_zh[label]}。"
        ),
        support_slots={
            "early_net_mean": seg_means[0],
            "middle_net_mean": seg_means[1],
            "late_net_mean": seg_means[2],
            "gap_top_second": ordered[0] - ordered[1],
            "answer_label": label,
        },
        reasoning_steps_en=["derive net load", "average by temporal thirds", "compare largest gap"],
        reasoning_steps_zh=["计算净负荷", "按三段求均值", "比较最高段和次高段差距"],
        tags=["derived_variable", "window_comparison", "threshold_reasoning"],
        raw_compact=raw_original if is_v2() else None,
    )


def transform_traffic(row: dict[str, Any]) -> dict[str, Any]:
    raw_original = get_raw(row)
    raw = compact_traffic(raw_original) if is_v2() else raw_original
    speed = [r[0] for r in raw]
    queue = [r[1] for r in raw]
    occ = [r[2] for r in raw]
    score = [r[3] for r in raw] if is_v2() else [q + 8.0 * o - 0.05 * s for s, q, o in zip(speed, queue, occ)]
    pre, event, post = [mean(x) for x in thirds(score)]
    if event <= pre + 0.50:
        label = "no clear congestion shock"
    elif post <= pre + 0.30 and post <= event - 0.30:
        label = "congestion recovers"
    elif post >= event - 0.20:
        label = "congestion persists"
    else:
        label = "partial recovery"
    labels = ["no clear congestion shock", "congestion recovers", "partial recovery", "congestion persists"]
    labels_zh = {
        "no clear congestion shock": "没有清晰拥堵冲击",
        "congestion recovers": "拥堵恢复",
        "partial recovery": "部分恢复",
        "congestion persists": "拥堵持续",
    }
    return common_row(
        row,
        task_family="self_contained_traffic_recovery_reasoning",
        raw=raw,
        scene_en=(
            "A traffic analyst is reviewing one road segment over time. No traffic-platform prior knowledge is needed. "
            "x0 is mean speed, x1 is queue length, and x2 is lane occupancy. Higher queue and occupancy are worse; higher speed is better."
        ),
        scene_zh=(
            "交通分析员正在查看一段道路的时间序列。无需了解任何特定交通平台背景。"
            "x0 是平均车速，x1 是排队长度，x2 是车道占有率。队列和占有率越高越差，车速越高越好。"
        ),
        variables_en=(
            ["x0 block mean speed", "x1 block mean queue length", "x2 block mean lane occupancy", "x3 block mean congestion score"]
            if is_v2()
            else ["x0 mean speed", "x1 queue length", "x2 lane occupancy"]
        ),
        variables_zh=(
            ["x0 分块平均车速", "x1 分块平均排队长度", "x2 分块平均车道占有率", "x3 分块平均拥堵分数"]
            if is_v2()
            else ["x0 平均车速", "x1 排队长度", "x2 车道占有率"]
        ),
        decision_rule_en=(
            "The compact table has one row per contiguous time block; x3 is already the block mean congestion score x1 + 8*x2 - 0.05*x0. "
            "Split compact rows into pre-event, event, and post-event thirds. This rule has precedence: first check whether event mean x3 is more than pre mean x3 by 0.50. "
            "If not, choose no clear congestion shock and do not evaluate recovery categories. Only if event rises by more than 0.50, choose congestion recovers when post mean is within 0.30 of pre and at least 0.30 below event. "
            "If post remains within 0.20 of event or higher, choose congestion persists; otherwise choose partial recovery."
            if is_v2()
            else "Define congestion score = x1 + 8*x2 - 0.05*x0. Split the window into pre-event, event, and post-event thirds. "
            "This rule has precedence: first check whether event mean is more than pre mean by 0.50. "
            "If not, choose no clear congestion shock and do not evaluate recovery categories. "
            "Only if event rises by more than 0.50, choose congestion recovers when post mean is within 0.30 of pre and at least 0.30 below event. "
            "If post remains within 0.20 of event or higher, choose congestion persists; otherwise choose partial recovery."
        ),
        decision_rule_zh=(
            "压缩表每行对应一个连续时间块；x3 已经是该块平均拥堵分数 x1 + 8*x2 - 0.05*x0。"
            "把压缩行分成事件前、事件中、事件后三段。该规则有优先级：先检查事件中 x3 均值是否比事件前高出 0.50 以上。"
            "若没有，直接选没有清晰拥堵冲击，不再判断恢复类别；只有事件中升高超过 0.50 时，才继续判断："
            "若事件后均值距离事件前不超过 0.30、并比事件中低至少 0.30，选拥堵恢复；若事件后仍接近事件中，选拥堵持续；否则选部分恢复。"
            if is_v2()
            else "定义拥堵分数 = x1 + 8*x2 - 0.05*x0。把窗口分成事件前、事件中、事件后三段。"
            "该规则有优先级：先检查事件中均值是否比事件前高出 0.50 以上。"
            "若没有，直接选没有清晰拥堵冲击，不再判断恢复类别；"
            "只有事件中升高超过 0.50 时，才继续判断：若事件后均值距离事件前不超过 0.30、并比事件中低至少 0.30，选拥堵恢复；"
            "若事件后仍接近事件中，选拥堵持续；否则选部分恢复。"
        ),
        question_en="Using the congestion-score rule, what happened after the event phase?",
        question_zh="根据拥堵分数规则，事件阶段之后交通状态如何变化？",
        labels_en=labels,
        labels_zh=labels_zh,
        answer_label=label,
        evidence_en=(
            f"Mean congestion scores for pre-event, event, and post-event thirds are {fmt(pre)}, {fmt(event)}, and {fmt(post)}; "
            f"the rule maps this to {label}."
        ),
        evidence_zh=(
            f"事件前、事件中、事件后平均拥堵分数分别为 {fmt(pre)}、{fmt(event)}、{fmt(post)}；"
            f"按规则判断为：{labels_zh[label]}。"
        ),
        support_slots={"pre_score_mean": pre, "event_score_mean": event, "post_score_mean": post, "answer_label": label},
        reasoning_steps_en=["derive congestion score", "average three phases", "apply recovery rule"],
        reasoning_steps_zh=["计算拥堵分数", "计算三阶段均值", "应用恢复规则"],
        tags=["derived_variable", "temporal_relation", "event_recovery"],
        raw_compact=raw_original if is_v2() else None,
    )


def transform_water(row: dict[str, Any]) -> dict[str, Any]:
    raw_original = get_raw(row)
    raw = compact_water(raw_original) if is_v2() else raw_original
    pressure = [r[0] for r in raw]
    flow = [r[1] for r in raw]
    pre_p, event_p, post_p = [mean(x) for x in thirds(pressure)]
    pre_f, event_f, post_f = [mean(x) for x in thirds(flow)]
    min_p = min(r[2] for r in raw) if is_v2() else min(pressure)
    flow_jump = event_f - pre_f
    if min_p < 55 and flow_jump > 1.0 and post_p < pre_p - 2.0:
        label = "persistent leak pressure risk"
    elif event_p < pre_p - 2.0 and post_p >= pre_p - 1.0:
        label = "pressure recovers after disturbance"
    elif (is_v2() or min_p >= 55) and abs(post_p - pre_p) <= 2.0:
        label = "stable service"
    else:
        label = "manual review needed"
    labels = ["persistent leak pressure risk", "pressure recovers after disturbance", "stable service", "manual review needed"]
    labels_zh = {
        "persistent leak pressure risk": "持续漏水压力风险",
        "pressure recovers after disturbance": "扰动后水压恢复",
        "stable service": "服务稳定",
        "manual review needed": "需要人工复核",
    }
    return common_row(
        row,
        task_family="self_contained_water_service_recovery",
        raw=raw,
        scene_en=(
            "A water-service operator is reviewing pressure and flow over one service window. "
            "No water-platform prior knowledge is needed. x0 is pressure and x1 is pipe flow. "
            "A leak-like event usually lowers pressure while increasing flow."
        ),
        scene_zh=(
            "供水服务运维人员正在查看一个服务窗口中的水压和流量。无需了解任何特定水网平台背景。"
            "x0 是水压，x1 是管道流量。类似漏水的事件通常会降低水压并提高流量。"
        ),
        variables_en=(
            ["x0 block mean service pressure", "x1 block mean pipe flow", "x2 block minimum pressure"]
            if is_v2()
            else ["x0 service pressure", "x1 pipe flow", "x2 tank storage context"]
        ),
        variables_zh=(
            ["x0 分块平均服务水压", "x1 分块平均管道流量", "x2 分块最低水压"]
            if is_v2()
            else ["x0 服务水压", "x1 管道流量", "x2 水箱蓄水量上下文"]
        ),
        decision_rule_en=(
            "The compact table has one row per contiguous time block. Use x0 for block mean pressure, x1 for block mean flow, and x2 for block minimum pressure. "
            "Split compact rows into pre-event, event, and post-event thirds. Choose persistent leak pressure risk if minimum x2 < 55, event mean x1 exceeds pre-event mean x1 by > 1.0, "
            "and post-event mean x0 remains more than 2.0 below pre-event mean x0. Choose pressure recovers after disturbance if event mean x0 is more than 2.0 below pre-event mean x0 and post-event mean x0 rebounds to at least pre-event mean x0 minus 1.0. "
            "Choose stable service if post-event mean x0 is within 2.0 of pre-event mean x0 and no earlier rule applies; otherwise choose manual review needed. Apply the rules in this exact order."
            if is_v2()
            else "Split the window into pre-event, event, and post-event thirds. "
            "Choose persistent leak pressure risk if minimum pressure < 55, event mean flow exceeds pre-event mean flow by > 1.0, "
            "and post-event mean pressure remains more than 2.0 below pre-event pressure. "
            "Choose pressure recovers after disturbance if event pressure is more than 2.0 below pre-event pressure and post-event pressure rebounds to at least pre-event pressure minus 1.0. "
            "Choose stable service if minimum pressure >= 55 and post-event pressure is within 2.0 of pre-event; otherwise choose manual review needed."
        ),
        decision_rule_zh=(
            "压缩表每行对应一个连续时间块。x0 是分块平均水压，x1 是分块平均流量，x2 是分块最低水压。"
            "把压缩行分成事件前、事件中、事件后三段。若最低 x2 < 55，事件中 x1 均值比事件前高出 > 1.0，且事件后 x0 均值仍比事件前低 2.0 以上，选持续漏水压力风险；"
            "若事件中 x0 均值比事件前低 2.0 以上，且事件后 x0 均值反弹到至少“事件前 x0 均值 - 1.0”，选扰动后水压恢复；"
            "若前面规则都不满足、且事件后 x0 均值距离事件前不超过 2.0，选服务稳定；否则选需要人工复核。严格按这个顺序应用规则。"
            if is_v2()
            else "把窗口分成事件前、事件中、事件后三段。"
            "若最低水压 < 55，事件中平均流量比事件前高出 > 1.0，且事件后平均水压仍比事件前低 2.0 以上，选持续漏水压力风险；"
            "若事件中水压比事件前低 2.0 以上，且事件后水压反弹到至少“事件前水压 - 1.0”，选扰动后水压恢复；"
            "若最低水压 >= 55 且事件后水压距离事件前不超过 2.0，选服务稳定；否则选需要人工复核。"
        ),
        question_en="Using the pressure-flow recovery rule, what service state should be reported?",
        question_zh="根据水压-流量恢复规则，应报告哪种供水服务状态？",
        labels_en=labels,
        labels_zh=labels_zh,
        answer_label=label,
        evidence_en=(
            f"Pre/event/post pressure means are {fmt(pre_p)}, {fmt(event_p)}, and {fmt(post_p)}; "
            f"minimum pressure is {fmt(min_p)} and event flow increase is {fmt(flow_jump)}; the rule maps this to {label}."
        ),
        evidence_zh=(
            f"事件前/中/后水压均值为 {fmt(pre_p)}、{fmt(event_p)}、{fmt(post_p)}；"
            f"最低水压为 {fmt(min_p)}，事件中流量增幅为 {fmt(flow_jump)}；按规则判断为：{labels_zh[label]}。"
        ),
        support_slots={
            "pre_pressure_mean": pre_p,
            "event_pressure_mean": event_p,
            "post_pressure_mean": post_p,
            "min_pressure": min_p,
            "event_flow_increase": flow_jump,
            "answer_label": label,
        },
        reasoning_steps_en=["average pressure and flow by phase", "check pressure drop and recovery", "check flow increase"],
        reasoning_steps_zh=["按阶段计算水压和流量均值", "检查水压下探与恢复", "检查流量增幅"],
        tags=["event_recovery", "cross_variable_relation", "threshold_reasoning"],
        raw_compact=raw_original if is_v2() else None,
    )


def transform_aiops(row: dict[str, Any]) -> dict[str, Any]:
    raw_original = get_raw(row)
    raw = compact_aiops(raw_original) if is_v2() else raw_original
    cpu = [r[0] for r in raw]
    mem = [r[1] for r in raw]
    rx = [r[2] for r in raw]
    tx = [r[3] for r in raw]
    mem_first, mem_second = [mean(x) for x in halves(mem)]
    mem_growth = (mem_second - mem_first) / max(abs(mem_first), 1e-9)
    rx_ratio = max(rx) if is_v2() else max(rx) / max(median(rx), 1e-9)
    tx_ratio = max(tx) if is_v2() else max(tx) / max(median(tx), 1e-9)
    cpu_max = max(cpu)
    if mem_growth >= 0.15:
        label = "memory leak pattern"
    elif rx_ratio >= 2.5 or tx_ratio >= 2.5:
        label = "network burst pattern"
    elif cpu_max >= 0.85:
        label = "cpu saturation pattern"
    else:
        label = "no dominant symptom"
    labels = ["memory leak pattern", "network burst pattern", "cpu saturation pattern", "no dominant symptom"]
    labels_zh = {
        "memory leak pattern": "内存泄漏模式",
        "network burst pattern": "网络突发模式",
        "cpu saturation pattern": "CPU 饱和模式",
        "no dominant symptom": "没有主导症状",
    }
    return common_row(
        row,
        task_family="self_contained_aiops_symptom_triage",
        raw=raw,
        scene_en=(
            "An SRE is triaging one service telemetry window. No platform-specific prior knowledge is needed. "
            "x0 is CPU load, x1 is memory working set, x2 is network receive rate, and x3 is network transmit rate."
        ),
        scene_zh=(
            "SRE 正在排查一个服务遥测窗口。无需了解任何特定平台背景。"
            "x0 是 CPU 负载，x1 是内存工作集，x2 是网络接收速率，x3 是网络发送速率。"
        ),
        variables_en=(
            ["x0 block max CPU load", "x1 block mean memory working set", "x2 block receive peak-to-median ratio", "x3 block transmit peak-to-median ratio"]
            if is_v2()
            else ["x0 CPU load", "x1 memory working set", "x2 network receive rate", "x3 network transmit rate"]
        ),
        variables_zh=(
            ["x0 分块 CPU 最大负载", "x1 分块平均内存工作集", "x2 分块接收速率峰值/中位数", "x3 分块发送速率峰值/中位数"]
            if is_v2()
            else ["x0 CPU 负载", "x1 内存工作集", "x2 网络接收速率", "x3 网络发送速率"]
        ),
        decision_rule_en=(
            "The compact table has one row per contiguous time block. Compute first-half and second-half mean x1, max x2, max x3, and max x0 across rows. "
            "Choose memory leak pattern only if x1 grows by at least 15%; network burst pattern only if max x2 or max x3 is at least 2.5; "
            "cpu saturation pattern only if max x0 is at least 0.85; otherwise choose no dominant symptom. The memory rule has priority: when x1 growth is at least 15%, the final answer must be memory leak pattern. "
            "Do not choose the closest positive symptom when none of these thresholds is met."
            if is_v2()
            else "Compute first-half and second-half memory means, network peak-to-median ratios, and max CPU. "
            "Choose memory leak pattern if memory grows by at least 15%; network burst pattern if receive or transmit peak/median ratio is at least 2.5; "
            "cpu saturation pattern if max CPU is at least 0.85; otherwise choose no dominant symptom."
        ),
        decision_rule_zh=(
            "压缩表每行对应一个连续时间块。跨行计算前半段/后半段 x1 均值、x2 最大值、x3 最大值和 x0 最大值。"
            "只有 x1 增长至少 15% 时才选内存泄漏模式；只有 x2 或 x3 最大值至少 2.5 时才选网络突发模式；"
            "只有 x0 最大值至少 0.85 时才选 CPU 饱和模式；否则选没有主导症状。内存规则优先：若 x1 增长至少 15%，最终答案必须是内存泄漏模式。"
            "若所有阈值都不满足，不要选择最接近的正类症状。"
            if is_v2()
            else "计算前半段/后半段内存均值、网络峰值/中位数比值，以及 CPU 最大值。"
            "若内存增长至少 15%，选内存泄漏模式；若接收或发送速率峰值/中位数比值至少 2.5，选网络突发模式；"
            "若 CPU 最大值至少 0.85，选 CPU 饱和模式；否则选没有主导症状。"
        ),
        question_en="Using the triage rule, which symptom should the SRE prioritize?",
        question_zh="根据排障规则，SRE 应优先关注哪种症状？",
        labels_en=labels,
        labels_zh=labels_zh,
        answer_label=label,
        evidence_en=(
            f"Memory changes from {fmt(mem_first)} to {fmt(mem_second)} ({fmt_pct(mem_growth)}), "
            f"receive peak/median is {fmt(rx_ratio)}, transmit peak/median is {fmt(tx_ratio)}, and max CPU is {fmt(cpu_max)}; "
            f"the rule maps this to {label}."
        ),
        evidence_zh=(
            f"内存均值从 {fmt(mem_first)} 变为 {fmt(mem_second)}（{fmt_pct(mem_growth)}），"
            f"接收峰值/中位数为 {fmt(rx_ratio)}，发送峰值/中位数为 {fmt(tx_ratio)}，CPU 最大值为 {fmt(cpu_max)}；"
            f"按规则判断为：{labels_zh[label]}。"
        ),
        support_slots={
            "memory_first_half_mean": mem_first,
            "memory_second_half_mean": mem_second,
            "memory_growth_ratio": mem_growth,
            "rx_peak_median_ratio": rx_ratio,
            "tx_peak_median_ratio": tx_ratio,
            "cpu_max": cpu_max,
            "answer_label": label,
        },
        reasoning_steps_en=["compare memory halves", "compute network peak ratios", "check CPU maximum", "apply priority rule"],
        reasoning_steps_zh=["比较前后半段内存", "计算网络峰值比", "检查 CPU 最大值", "应用优先级规则"],
        tags=["cross_variable_relation", "threshold_reasoning", "incident_triage"],
        raw_compact=raw_original if is_v2() else None,
    )


def transform_finrl(row: dict[str, Any]) -> dict[str, Any]:
    raw_original = get_raw(row)
    raw = compact_finrl(raw_original) if is_v2() else raw_original
    prices = [r[0] for r in raw]
    total_return = prices[-1] / prices[0] - 1.0
    dd = max_drawdown(prices)
    if dd <= -0.20:
        label = "severe drawdown risk"
    elif total_return >= 0.08:
        label = "bullish regime"
    elif total_return <= -0.08:
        label = "bearish regime"
    else:
        label = "sideways regime"
    labels = ["bullish regime", "bearish regime", "sideways regime", "severe drawdown risk"]
    labels_zh = {
        "bullish regime": "上行状态",
        "bearish regime": "下行状态",
        "sideways regime": "横盘状态",
        "severe drawdown risk": "严重回撤风险",
    }
    return common_row(
        row,
        task_family="self_contained_finrl_return_drawdown_regime",
        raw=raw,
        scene_en=(
            "A market analyst is reviewing one asset price window. No platform-specific prior knowledge is needed. "
            "x0 is asset price, x1 is a market context indicator, and x2 is trading volume."
        ),
        scene_zh=(
            "市场分析师正在查看一个资产价格窗口。无需了解任何特定平台背景。"
            "x0 是资产价格，x1 是市场背景指标，x2 是交易量。"
        ),
        variables_en=(
            ["x0 block closing asset price", "x1 block mean market context indicator", "x2 block mean trading volume", "x3 block minimum asset price"]
            if is_v2()
            else ["x0 asset price", "x1 market context indicator", "x2 trading volume"]
        ),
        variables_zh=(
            ["x0 分块收盘资产价格", "x1 分块平均市场背景指标", "x2 分块平均交易量", "x3 分块最低资产价格"]
            if is_v2()
            else ["x0 资产价格", "x1 市场背景指标", "x2 交易量"]
        ),
        decision_rule_en=(
            "The compact table has one row per contiguous time block. Compute total return = last x0 / first x0 - 1 and maximum drawdown from the running peak of x0. "
            "Choose severe drawdown risk first if maximum drawdown <= -20%; only if this condition is false, choose bullish regime if total return >= +8%, "
            "bearish regime if total return <= -8%, and sideways regime otherwise. Drawdown has priority over return. If severe drawdown is false and return is >= +8%, the final answer must be bullish regime."
            if is_v2()
            else "Compute total return = last x0 / first x0 - 1 and maximum drawdown from the running peak of x0. "
            "Choose severe drawdown risk if maximum drawdown <= -20%; otherwise bullish regime if total return >= +8%, "
            "bearish regime if total return <= -8%, and sideways regime otherwise."
        ),
        decision_rule_zh=(
            "压缩表每行对应一个连续时间块。计算总收益率 = 最后一个 x0 / 第一个 x0 - 1，并根据 x0 的历史峰值计算最大回撤。"
            "若最大回撤 <= -20%，必须优先选严重回撤风险；只有该条件不满足时，才根据总收益率选择："
            "总收益率 >= +8% 选上行状态，总收益率 <= -8% 选下行状态，其余选横盘状态。回撤优先于收益率。若严重回撤不成立且收益率 >= +8%，最终答案必须是上行状态。"
            if is_v2()
            else "计算总收益率 = 最后一个 x0 / 第一个 x0 - 1，并根据 x0 的历史峰值计算最大回撤。"
            "若最大回撤 <= -20%，选严重回撤风险；否则若总收益率 >= +8%，选上行状态；"
            "若总收益率 <= -8%，选下行状态；其余选横盘状态。"
        ),
        question_en="Using return and maximum drawdown, how should this price window be classified?",
        question_zh="根据总收益率和最大回撤，这段价格窗口应如何分类？",
        labels_en=labels,
        labels_zh=labels_zh,
        answer_label=label,
        evidence_en=(
            f"Total return is {fmt_pct(total_return)} and maximum drawdown is {fmt_pct(dd)}; "
            f"the rule maps this to {label}."
        ),
        evidence_zh=(
            f"总收益率为 {fmt_pct(total_return)}，最大回撤为 {fmt_pct(dd)}；"
            f"按规则判断为：{labels_zh[label]}。"
        ),
        support_slots={"total_return": total_return, "max_drawdown": dd, "answer_label": label},
        reasoning_steps_en=["compute total return", "compute maximum drawdown", "apply precedence rule"],
        reasoning_steps_zh=["计算总收益率", "计算最大回撤", "应用优先级规则"],
        tags=["financial_reasoning", "derived_variable", "threshold_reasoning"],
        raw_compact=raw_original if is_v2() else None,
    )


TRANSFORMERS = {
    "grid2op": transform_grid,
    "citylearn": transform_city,
    "traffic": transform_traffic,
    "water": transform_water,
    "aiopslab": transform_aiops,
    "finrl": transform_finrl,
}


def select_rows(rows: list[dict[str, Any]], per_domain: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        domain = str(row.get("merge_source_name", ""))
        if domain in DOMAINS:
            grouped[domain].append(row)
    for domain in DOMAINS:
        candidates = sorted(
            grouped[domain],
            key=lambda r: (
                0 if r.get("smoke_source_tier") == "controlled_scenario_first_generator" else 1,
                str(r.get("id", "")),
            ),
        )
        if len(candidates) < per_domain:
            raise ValueError(f"{domain} has only {len(candidates)} rows, need {per_domain}")
        selected.extend(candidates[:per_domain])
    return selected


def validate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    for row in rows:
        for key in (
            "decision_rule_en",
            "decision_rule_zh",
            "scene_en",
            "scene_zh",
            "values",
            "question",
            "options",
            "answer",
            "support_slots",
            "reasoning_steps_en",
        ):
            if row.get(key) in (None, "", []):
                issues.append({"id": row.get("id"), "issue": f"missing_{key}"})
        if "Grid2Op" in row["scene_en"] or "CityLearn" in row["scene_en"] or "AIOpsLab" in row["scene_en"] or "FinRL" in row["scene_en"]:
            issues.append({"id": row["id"], "issue": "scene_mentions_simulator_name"})
        if row.get("answer_label") != row.get("support_slots", {}).get("answer_label"):
            issues.append({"id": row["id"], "issue": "answer_support_mismatch"})
        if len(row.get("options", [])) != 4 or row.get("answer") not in LETTERS:
            issues.append({"id": row["id"], "issue": "bad_options_or_answer"})
        if row.get("simulator_prior_required") is not False:
            issues.append({"id": row["id"], "issue": "simulator_prior_flag_not_false"})
    by_domain = Counter(row["merge_source_name"] for row in rows)
    answer_counts = Counter(row["answer"] for row in rows)
    return {
        "pass": not issues,
        "issue_count": len(issues),
        "issues": issues[:100],
        "n": len(rows),
        "by_domain": dict(by_domain),
        "by_task_family": dict(Counter(row["task_family"] for row in rows)),
        "answer_distribution": dict(answer_counts),
        "max_answer_share": round(max(answer_counts.values()) / len(rows), 4) if rows else 1.0,
        "all_domains_meet_target": all(by_domain.get(domain, 0) > 0 for domain in DOMAINS),
    }


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row["target_caption"],
        "meta": row["meta"],
    }


def render_spec(out_dir: Path, summary: dict[str, Any]) -> None:
    filename = (
        "SELF_CONTAINED_REASONING_TSQA_V2_GENERATION_SPEC_20260521_ZH.md"
        if is_v2()
        else "SELF_CONTAINED_REASONING_TSQA_GENERATION_SPEC_20260521_ZH.md"
    )
    lines = [
        f"# Self-contained Reasoning TSQA Generation Spec（2026-05-21, {GENERATION_VARIANT}）",
        "",
        "本规范针对上一批 review 中暴露的问题：题目太像直接读时序特征，背景依赖 simulator 名称，且部分答案不能只由问题和时序值复现。",
        "",
        "## 生成约束",
        "",
        "1. 每个样本必须给出自足背景：变量含义、单位或方向性、时间窗口划分、决策规则。",
        "2. 用户可见输入只需要 `scene + decision_rule + variables + question + options + physical-unit time series values`。",
        "3. 不允许要求答题者知道 Grid2Op、CityLearn、AIOpsLab、FinRL 等 simulator 背景。",
        "4. 问题必须需要至少一个派生量或聚合量：均值、分段均值、比例、差值、峰值/中位数比、最大回撤等。",
        "5. support slots 仍用于审计，但不能是唯一能推出答案的信息。",
        "6. 给 TS-LLM/LLM 的 `values` 使用物理量，不使用 z-score 后的归一化值。",
    ]
    if is_v2():
        lines.extend(
            [
                "7. v2 采用 review-driven compact values：给 solver 的 `values` 是连续时间块的物理量/派生量压缩表，原始长序列保留在 `raw_compact_values` 供审计。",
                "8. v2 题面显式写出负类和优先级：不要在阈值未满足时选择“最像的正类”。",
            ]
        )
    lines.extend(
        [
            "",
            "## 本批数据",
            "",
            f"- rows: `{summary['n']}`",
            f"- by domain: `{json.dumps(summary['by_domain'], ensure_ascii=False)}`",
            f"- answer distribution: `{json.dumps(summary['answer_distribution'], ensure_ascii=False)}`",
            f"- local gate pass: `{summary['pass']}`",
        ]
    )
    (out_dir / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_jsonl", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--per_domain", type=int, default=10)
    parser.add_argument("--variant", choices=["v1", "v2"], default="v1")
    args = parser.parse_args()

    global GENERATION_VARIANT
    GENERATION_VARIANT = args.variant

    source_rows = load_jsonl(args.input_jsonl)
    selected = select_rows(source_rows, args.per_domain)
    rows = [TRANSFORMERS[row["merge_source_name"]](row) for row in selected]
    summary = validate(rows)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "self_contained_reasoning_tsqa.jsonl", rows)
    write_jsonl(out_dir / "self_contained_reasoning_tsqa_sft.jsonl", [sft_row(row) for row in rows])
    (out_dir / "self_contained_reasoning_tsqa_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    render_spec(out_dir, summary)
    print(json.dumps({"out_dir": rel(out_dir), "summary": summary}, ensure_ascii=False, indent=2))
    if not summary["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
