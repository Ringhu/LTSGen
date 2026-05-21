#!/usr/bin/env python3
"""Build public raw-series TSQA v4 from reviewed v3 seed rows.

The public v4 benchmark keeps one canonical raw time-series record and exports
two input views:

* LLM text view: raw series serialized as CSV inside a prompt.
* TS-LLM array view: raw numeric array plus the same text question/options.

Support slots and oracle evidence are audit-only artifacts and are not included
in the main model inputs.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    ROOT
    / ".research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/"
    / "self_contained_reasoning_tsqa_v3_ready.jsonl"
)
DEFAULT_OUT_DIR = ROOT / ".research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521"
LETTERS = ("A", "B", "C", "D")
MIN_PUBLIC_SERIES_LENGTH = 32
FORBIDDEN_PUBLIC_PATTERNS = (
    "压缩表",
    "compact table",
    "block feature",
    "support slot",
    "x0_mean",
    "frac_gt_pos_0_05",
    "Answer label",
    "rule maps this to",
    "无需了解任何特定",
    "scenario_first_pilot",
    "window_start",
)


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


def thirds(values: list[float]) -> tuple[list[float], list[float], list[float]]:
    n = len(values)
    return values[: n // 3], values[n // 3 : 2 * n // 3], values[2 * n // 3 :]


def halves(values: list[float]) -> tuple[list[float], list[float]]:
    n = len(values)
    return values[: n // 2], values[n // 2 :]


def max_drawdown(prices: list[float]) -> float:
    peak = prices[0]
    drawdown = 0.0
    for price in prices:
        peak = max(peak, price)
        drawdown = min(drawdown, price / peak - 1.0)
    return drawdown


def fmt(value: float) -> str:
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return str(value)
    return f"{value:.6g}"


def fmt_pct(value: float) -> str:
    return f"{100 * float(value):.1f}%"


def raw_series(row: dict[str, Any]) -> list[list[float]]:
    values = row.get("raw_compact_values") or row.get("values")
    return [[float(item) for item in record] for record in values]


def v4_id(source_index: int) -> str:
    return f"public_raw_tsqa_v4_{source_index:05d}"


def options_from_labels(labels: list[str], label_to_public_en: dict[str, str], label_to_public_zh: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    return (
        {letter: label_to_public_en[label] for letter, label in zip(LETTERS, labels)},
        {letter: label_to_public_zh[label] for letter, label in zip(LETTERS, labels)},
    )


def letter_for(labels: list[str], semantic_label: str) -> str:
    return LETTERS[labels.index(semantic_label)]


def public_text(context: str, variables: dict[str, str], rule: str, question: str, options: dict[str, str]) -> str:
    variables_text = "\n".join(f"- {name}: {desc}" for name, desc in variables.items())
    options_text = "\n".join(f"{letter}. {text}" for letter, text in options.items())
    return (
        f"Context:\n{context}\n\n"
        f"Variables:\n{variables_text}\n\n"
        f"Decision guide:\n{rule}\n\n"
        f"Question:\n{question}\n\n"
        f"Options:\n{options_text}"
    )


def csv_values(columns: list[str], values: list[list[float]]) -> str:
    lines = ["time," + ",".join(columns)]
    for idx, record in enumerate(values):
        lines.append(f"{idx}," + ",".join(fmt(value) for value in record))
    return "\n".join(lines)


def llm_prompt(record: dict[str, Any], *, lang: str = "en") -> str:
    suffix = "_zh" if lang == "zh" else "_en"
    base = public_text(
        record[f"context{suffix}"],
        record[f"variable_descriptions{suffix}"],
        record[f"decision_rule{suffix}"],
        record[f"question{suffix}"],
        record[f"options{suffix}"],
    )
    return (
        "You are answering a raw time-series multiple-choice question.\n"
        "Use only the context, variables, decision guide, question, options, and full raw time series shown below.\n\n"
        f"{base}\n\n"
        "Time series values:\n"
        f"{csv_values(record['time_series']['columns'], record['time_series']['values'])}\n\n"
        "Return JSON only: {\"answer\": \"A|B|C|D\", \"answer_label\": \"option text\", \"reason\": \"brief\"}"
    )


def grid_record(row: dict[str, Any], raw: list[list[float]]) -> dict[str, Any]:
    stress = [r[0] for r in raw]
    avg = mean(stress)
    frac_pos = sum(x > 0.05 for x in stress) / len(stress)
    frac_neg = sum(x < -0.05 for x in stress) / len(stress)
    max_abs = max(abs(x) for x in stress)
    if avg >= 0.05 and frac_pos >= 0.80:
        label = "risk increases"
    elif avg <= -0.05 and frac_neg >= 0.80:
        label = "risk decreases"
    elif abs(avg) <= 0.02 and max_abs <= 0.03:
        label = "risk is broadly unchanged"
    else:
        label = "manual review needed"
    labels = ["risk increases", "risk decreases", "risk is broadly unchanged", "manual review needed"]
    opts_en, opts_zh = options_from_labels(
        labels,
        {
            "risk increases": "The planned outage increases stress.",
            "risk decreases": "The planned outage decreases stress.",
            "risk is broadly unchanged": "The effect is broadly unchanged.",
            "manual review needed": "The case needs manual review.",
        },
        {
            "risk increases": "计划断线会增加压力",
            "risk decreases": "计划断线会降低压力",
            "risk is broadly unchanged": "整体影响基本不变",
            "manual review needed": "需要人工复核",
        },
    )
    return {
        "domain": "power_grid",
        "time_series": {
            "columns": ["stress_delta", "demand_context", "generation_margin_context"],
            "values": raw,
            "time_axis": "ordered post-event operating window",
        },
        "variable_descriptions_en": {
            "stress_delta": "planned-outage line stress minus normal-operation line stress",
            "demand_context": "system demand context signal",
            "generation_margin_context": "generation margin context signal",
        },
        "variable_descriptions_zh": {
            "stress_delta": "计划断线相对正常运行的线路压力差",
            "demand_context": "系统负荷背景信号",
            "generation_margin_context": "发电裕度背景信号",
        },
        "context_en": "A grid operator is assessing how a planned line outage changes line stress compared with normal operation.",
        "context_zh": "电网调度员正在评估一次计划断线相对正常运行会如何改变线路压力。",
        "decision_rule_en": "If the average stress difference is clearly positive and most readings are above +0.05, classify the outage as increasing stress. If the average is clearly negative and most readings are below -0.05, classify it as decreasing stress. If the series stays close to zero with only tiny deviations, classify it as broadly unchanged; otherwise request manual review.",
        "decision_rule_zh": "如果平均压力差明显为正，且大多数读数高于 +0.05，则判为压力上升；如果平均压力差明显为负，且大多数读数低于 -0.05，则判为压力下降；如果整体接近 0 且波动很小，则判为基本不变；否则需要人工复核。",
        "question_en": "Based on the full stress-delta series, what should the operator conclude about the planned outage?",
        "question_zh": "根据完整压力差序列，调度员应如何判断这次计划断线的影响？",
        "options_en": opts_en,
        "options_zh": opts_zh,
        "semantic_answer_label": label,
        "answer": letter_for(labels, label),
        "support_slots": {
            "stress_delta_mean": avg,
            "share_above_pos_threshold": frac_pos,
            "share_below_neg_threshold": frac_neg,
            "max_abs_stress_delta": max_abs,
            "verifier_answer_label": label,
        },
        "oracle_evidence_en": f"The mean stress difference is {fmt(avg)}; {fmt_pct(frac_pos)} of readings are above +0.05 and {fmt_pct(frac_neg)} are below -0.05. The largest absolute deviation is {fmt(max_abs)}.",
        "oracle_evidence_zh": f"压力差均值为 {fmt(avg)}；高于 +0.05 的读数占 {fmt_pct(frac_pos)}，低于 -0.05 的读数占 {fmt_pct(frac_neg)}，最大绝对偏差为 {fmt(max_abs)}。",
        "reasoning_skill_tags": ["counterfactual_effect", "threshold_reasoning", "aggregation"],
    }


def city_record(row: dict[str, Any], raw: list[list[float]]) -> dict[str, Any]:
    demand = [r[0] for r in raw]
    solar = [r[2] for r in raw]
    net = [d - 0.15 * s for d, s in zip(demand, solar)]
    seg_means = [mean(part) for part in thirds(net)]
    best_idx = max(range(3), key=lambda idx: seg_means[idx])
    ordered = sorted(seg_means, reverse=True)
    gap = ordered[0] - ordered[1]
    label = "balanced reserve" if gap < 0.30 else ["reserve early", "reserve middle", "reserve late"][best_idx]
    labels = ["reserve early", "reserve middle", "reserve late", "balanced reserve"]
    opts_en, opts_zh = options_from_labels(
        labels,
        {
            "reserve early": "Reserve more supply for the early part of the window.",
            "reserve middle": "Reserve more supply for the middle part of the window.",
            "reserve late": "Reserve more supply for the late part of the window.",
            "balanced reserve": "Use a balanced reserve strategy.",
        },
        {
            "reserve early": "优先为早段预留供能",
            "reserve middle": "优先为中段预留供能",
            "reserve late": "优先为晚段预留供能",
            "balanced reserve": "采用均衡供能策略",
        },
    )
    return {
        "domain": "building_energy",
        "time_series": {
            "columns": ["demand", "weather_context", "solar_support"],
            "values": raw,
            "time_axis": "ordered operating window",
        },
        "variable_descriptions_en": {
            "demand": "building electricity demand",
            "weather_context": "weather context signal",
            "solar_support": "local solar support",
        },
        "variable_descriptions_zh": {
            "demand": "建筑用电需求",
            "weather_context": "天气背景信号",
            "solar_support": "本地太阳能支持",
        },
        "context_en": "A building energy planner needs to decide whether supply should be reserved for the early, middle, late, or evenly across the operating window.",
        "context_zh": "建筑能源调度员需要决定应为运行窗口的早段、中段、晚段或整体均衡预留供能。",
        "decision_rule_en": "Compute net grid load as demand minus 0.15 times solar support. Compare the average net load in the early, middle, and late portions of the full sequence. If the highest portion exceeds the second-highest by at least 0.30, reserve more supply for that portion; otherwise use a balanced reserve strategy.",
        "decision_rule_zh": "将净电网负荷定义为需求减去 0.15 倍太阳能支持。比较完整序列早段、中段、晚段的平均净负荷；若最高段比第二高段至少高 0.30，则为该段优先预留供能，否则采用均衡策略。",
        "question_en": "From the full demand and solar-support series, which reserve strategy is most appropriate?",
        "question_zh": "根据完整需求和太阳能支持序列，哪种供能预留策略最合适？",
        "options_en": opts_en,
        "options_zh": opts_zh,
        "semantic_answer_label": label,
        "answer": letter_for(labels, label),
        "support_slots": {
            "early_net_load_mean": seg_means[0],
            "middle_net_load_mean": seg_means[1],
            "late_net_load_mean": seg_means[2],
            "top_second_gap": gap,
            "verifier_answer_label": label,
        },
        "oracle_evidence_en": f"The early, middle, and late net-load means are {fmt(seg_means[0])}, {fmt(seg_means[1])}, and {fmt(seg_means[2])}. The top-second gap is {fmt(gap)} against the 0.30 threshold.",
        "oracle_evidence_zh": f"早段、中段、晚段净负荷均值分别为 {fmt(seg_means[0])}、{fmt(seg_means[1])}、{fmt(seg_means[2])}；最高与第二高差距为 {fmt(gap)}，阈值为 0.30。",
        "reasoning_skill_tags": ["derived_variable", "window_comparison", "threshold_reasoning"],
    }


def traffic_record(row: dict[str, Any], raw: list[list[float]]) -> dict[str, Any]:
    speed = [r[0] for r in raw]
    queue = [r[1] for r in raw]
    occ = [r[2] for r in raw]
    score = [q + 8.0 * o - 0.05 * s for s, q, o in zip(speed, queue, occ)]
    pre, event, post = [mean(part) for part in thirds(score)]
    if event <= pre + 0.50:
        label = "no clear congestion shock"
    elif post <= pre + 0.30 and post <= event - 0.30:
        label = "congestion recovers"
    elif post >= event - 0.20:
        label = "congestion persists"
    else:
        label = "partial recovery"
    labels = ["no clear congestion shock", "congestion recovers", "partial recovery", "congestion persists"]
    opts_en, opts_zh = options_from_labels(
        labels,
        {
            "no clear congestion shock": "No clear congestion shock occurs.",
            "congestion recovers": "Congestion recovers after the event.",
            "partial recovery": "Congestion partially recovers.",
            "congestion persists": "Congestion persists after the event.",
        },
        {
            "no clear congestion shock": "没有清晰拥堵冲击",
            "congestion recovers": "事件后拥堵恢复",
            "partial recovery": "事件后部分恢复",
            "congestion persists": "事件后拥堵持续",
        },
    )
    return {
        "domain": "traffic",
        "time_series": {
            "columns": ["speed", "queue_length", "lane_occupancy"],
            "values": raw,
            "time_axis": "ordered before-during-after event window",
        },
        "variable_descriptions_en": {
            "speed": "mean speed",
            "queue_length": "queue length",
            "lane_occupancy": "lane occupancy",
        },
        "variable_descriptions_zh": {
            "speed": "平均车速",
            "queue_length": "排队长度",
            "lane_occupancy": "车道占有率",
        },
        "context_en": "A traffic analyst is reviewing road readings before, during, and after an event.",
        "context_zh": "交通分析员正在查看事件前、事件中、事件后一段道路的时序读数。",
        "decision_rule_en": "Use queue length, lane occupancy, and speed to form a congestion score: queue length plus 8 times occupancy minus 0.05 times speed. First check whether the event portion rises by more than 0.50 over the pre-event portion. If not, there is no clear congestion shock. Only when that shock exists, decide whether congestion recovers, partially recovers, or persists using the post-event portion.",
        "decision_rule_zh": "用排队长度、车道占有率和车速形成拥堵分数：排队长度加 8 倍占有率再减去 0.05 倍车速。先看事件中分数是否比事件前高出 0.50 以上；若没有，则没有清晰拥堵冲击。只有冲击存在时，才继续判断恢复、部分恢复或持续。",
        "question_en": "What happened to congestion after the event phase?",
        "question_zh": "事件阶段之后，拥堵状态如何变化？",
        "options_en": opts_en,
        "options_zh": opts_zh,
        "semantic_answer_label": label,
        "answer": letter_for(labels, label),
        "support_slots": {
            "pre_event_score_mean": pre,
            "event_score_mean": event,
            "post_event_score_mean": post,
            "event_minus_pre": event - pre,
            "post_minus_pre": post - pre,
            "event_minus_post": event - post,
            "verifier_answer_label": label,
        },
        "oracle_evidence_en": f"The pre-event, event, and post-event congestion-score means are {fmt(pre)}, {fmt(event)}, and {fmt(post)}. The event rise over pre-event is {fmt(event - pre)}.",
        "oracle_evidence_zh": f"事件前、事件中、事件后拥堵分数均值分别为 {fmt(pre)}、{fmt(event)}、{fmt(post)}；事件中相对事件前上升 {fmt(event - pre)}。",
        "reasoning_skill_tags": ["derived_variable", "temporal_relation", "event_recovery"],
    }


def water_record(row: dict[str, Any], raw: list[list[float]]) -> dict[str, Any]:
    pressure = [r[0] for r in raw]
    flow = [r[1] for r in raw]
    pre_p, event_p, post_p = [mean(part) for part in thirds(pressure)]
    pre_f, event_f, _ = [mean(part) for part in thirds(flow)]
    min_p = min(pressure)
    flow_change = event_f - pre_f
    if min_p < 55 and flow_change > 1.0 and post_p < pre_p - 2.0:
        label = "persistent leak pressure risk"
    elif event_p < pre_p - 2.0 and post_p >= pre_p - 1.0:
        label = "pressure recovers after disturbance"
    elif abs(post_p - pre_p) <= 2.0:
        label = "stable service"
    else:
        label = "manual review needed"
    labels = ["persistent leak pressure risk", "pressure recovers after disturbance", "stable service", "manual review needed"]
    opts_en, opts_zh = options_from_labels(
        labels,
        {
            "persistent leak pressure risk": "Persistent leak pressure risk.",
            "pressure recovers after disturbance": "Pressure recovers after the disturbance.",
            "stable service": "Service remains stable.",
            "manual review needed": "Manual review is needed.",
        },
        {
            "persistent leak pressure risk": "持续漏水压力风险",
            "pressure recovers after disturbance": "扰动后水压恢复",
            "stable service": "服务保持稳定",
            "manual review needed": "需要人工复核",
        },
    )
    return {
        "domain": "water_service",
        "time_series": {
            "columns": ["pressure", "flow", "storage_context"],
            "values": raw,
            "time_axis": "ordered before-during-after disturbance window",
        },
        "variable_descriptions_en": {
            "pressure": "service pressure",
            "flow": "pipe flow",
            "storage_context": "storage context signal",
        },
        "variable_descriptions_zh": {
            "pressure": "服务水压",
            "flow": "管道流量",
            "storage_context": "蓄水背景信号",
        },
        "context_en": "A water-service operator is reviewing pressure and flow readings around a disturbance event.",
        "context_zh": "供水运维人员正在查看一次扰动事件前后水压和流量读数。",
        "decision_rule_en": "If pressure falls very low, flow clearly increases during the event, and pressure remains depressed afterward, classify the window as persistent leak pressure risk. If pressure drops during the event but rebounds close to or above the pre-event level afterward, classify it as recovery after disturbance. If there is no earlier risk pattern and post-event pressure stays close to pre-event pressure, classify service as stable; otherwise request manual review.",
        "decision_rule_zh": "若水压降得很低、事件中流量明显升高、且事件后水压仍明显低于事件前，则判为持续漏水压力风险。若事件中水压下降但事件后恢复到接近或高于事件前水平，则判为扰动后恢复。若前面风险模式不满足且事件后水压接近事件前，则判为服务稳定；否则需要人工复核。",
        "question_en": "Which service state best describes this disturbance window?",
        "question_zh": "这段扰动窗口最符合哪种供水服务状态？",
        "options_en": opts_en,
        "options_zh": opts_zh,
        "semantic_answer_label": label,
        "answer": letter_for(labels, label),
        "support_slots": {
            "pre_pressure_mean": pre_p,
            "event_pressure_mean": event_p,
            "post_pressure_mean": post_p,
            "min_pressure": min_p,
            "event_flow_change": flow_change,
            "verifier_answer_label": label,
        },
        "oracle_evidence_en": f"Pressure moves from {fmt(pre_p)} before the event to {fmt(event_p)} during the event and {fmt(post_p)} afterward. Minimum pressure is {fmt(min_p)}, and event flow changes by {fmt(flow_change)}.",
        "oracle_evidence_zh": f"水压从事件前 {fmt(pre_p)} 变为事件中 {fmt(event_p)}，事件后为 {fmt(post_p)}；最低水压为 {fmt(min_p)}，事件中流量变化为 {fmt(flow_change)}。",
        "reasoning_skill_tags": ["event_recovery", "cross_variable_relation", "threshold_reasoning"],
    }


def aiops_record(row: dict[str, Any], raw: list[list[float]]) -> dict[str, Any]:
    cpu = [r[0] for r in raw]
    mem = [r[1] for r in raw]
    rx = [r[2] for r in raw]
    tx = [r[3] for r in raw]
    mem_first, mem_second = [mean(part) for part in halves(mem)]
    mem_growth = (mem_second - mem_first) / max(abs(mem_first), 1e-9)
    rx_ratio = max(rx) / max(median(rx), 1e-9)
    tx_ratio = max(tx) / max(median(tx), 1e-9)
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
    opts_en, opts_zh = options_from_labels(
        labels,
        {
            "memory leak pattern": "Prioritize a memory-leak pattern.",
            "network burst pattern": "Prioritize a network-burst pattern.",
            "cpu saturation pattern": "Prioritize CPU saturation.",
            "no dominant symptom": "No dominant symptom is present.",
        },
        {
            "memory leak pattern": "优先排查内存泄漏模式",
            "network burst pattern": "优先排查网络突发模式",
            "cpu saturation pattern": "优先排查 CPU 饱和",
            "no dominant symptom": "没有主导症状",
        },
    )
    return {
        "domain": "service_telemetry",
        "time_series": {
            "columns": ["cpu_load", "memory_working_set", "network_receive_rate", "network_transmit_rate"],
            "values": raw,
            "time_axis": "ordered service telemetry window",
        },
        "variable_descriptions_en": {
            "cpu_load": "CPU load",
            "memory_working_set": "memory working set",
            "network_receive_rate": "network receive rate",
            "network_transmit_rate": "network transmit rate",
        },
        "variable_descriptions_zh": {
            "cpu_load": "CPU 负载",
            "memory_working_set": "内存工作集",
            "network_receive_rate": "网络接收速率",
            "network_transmit_rate": "网络发送速率",
        },
        "context_en": "An SRE is triaging one service telemetry window.",
        "context_zh": "SRE 正在排查一个服务遥测窗口。",
        "decision_rule_en": "Prioritize memory leak only if memory grows by at least 15% from the first half to the second half. If not, prioritize a network burst only when receive or transmit has a peak-to-median ratio of at least 2.5. If neither applies, prioritize CPU saturation only when max CPU is at least 0.85. Otherwise report no dominant symptom.",
        "decision_rule_zh": "只有内存从前半段到后半段至少增长 15% 时才优先排查内存泄漏。否则，只有接收或发送速率的峰值/中位数比至少为 2.5 时才优先排查网络突发。若都不满足，只有 CPU 最大负载至少为 0.85 时才排查 CPU 饱和；否则报告没有主导症状。",
        "question_en": "Which symptom should the SRE prioritize?",
        "question_zh": "SRE 应优先关注哪种症状？",
        "options_en": opts_en,
        "options_zh": opts_zh,
        "semantic_answer_label": label,
        "answer": letter_for(labels, label),
        "support_slots": {
            "memory_first_half_mean": mem_first,
            "memory_second_half_mean": mem_second,
            "memory_growth_ratio": mem_growth,
            "rx_peak_median_ratio": rx_ratio,
            "tx_peak_median_ratio": tx_ratio,
            "cpu_max": cpu_max,
            "verifier_answer_label": label,
        },
        "oracle_evidence_en": f"Memory changes from {fmt(mem_first)} to {fmt(mem_second)} ({fmt_pct(mem_growth)}). Receive and transmit peak-to-median ratios are {fmt(rx_ratio)} and {fmt(tx_ratio)}, and max CPU is {fmt(cpu_max)}.",
        "oracle_evidence_zh": f"内存从 {fmt(mem_first)} 变为 {fmt(mem_second)}，变化 {fmt_pct(mem_growth)}；接收和发送峰值/中位数比分别为 {fmt(rx_ratio)}、{fmt(tx_ratio)}，CPU 最大值为 {fmt(cpu_max)}。",
        "reasoning_skill_tags": ["cross_variable_relation", "threshold_reasoning", "incident_triage"],
    }


def finrl_record(row: dict[str, Any], raw: list[list[float]]) -> dict[str, Any]:
    prices = [r[0] for r in raw]
    total_return = prices[-1] / prices[0] - 1.0
    drawdown = max_drawdown(prices)
    if drawdown <= -0.20:
        label = "severe drawdown risk"
    elif total_return >= 0.08:
        label = "bullish regime"
    elif total_return <= -0.08:
        label = "bearish regime"
    else:
        label = "sideways regime"
    labels = ["bullish regime", "bearish regime", "sideways regime", "severe drawdown risk"]
    opts_en, opts_zh = options_from_labels(
        labels,
        {
            "bullish regime": "Bullish regime.",
            "bearish regime": "Bearish regime.",
            "sideways regime": "Sideways regime.",
            "severe drawdown risk": "Severe drawdown risk.",
        },
        {
            "bullish regime": "上行状态",
            "bearish regime": "下行状态",
            "sideways regime": "横盘状态",
            "severe drawdown risk": "严重回撤风险",
        },
    )
    return {
        "domain": "market",
        "time_series": {
            "columns": ["asset_price", "market_context", "trading_volume"],
            "values": raw,
            "time_axis": "ordered market window",
        },
        "variable_descriptions_en": {
            "asset_price": "asset price",
            "market_context": "market context signal",
            "trading_volume": "trading volume",
        },
        "variable_descriptions_zh": {
            "asset_price": "资产价格",
            "market_context": "市场背景信号",
            "trading_volume": "交易量",
        },
        "context_en": "A market analyst is reviewing an asset price window.",
        "context_zh": "市场分析师正在查看一段资产价格窗口。",
        "decision_rule_en": "Compute total return from the first to the last price and maximum drawdown from the running peak. Severe drawdown has priority if maximum drawdown is at least 20%. If that does not apply, classify the window as bullish when return is at least +8%, bearish when return is at most -8%, and sideways otherwise.",
        "decision_rule_zh": "计算首尾价格的总收益率，以及相对历史峰值的最大回撤。若最大回撤达到 20% 或以上，优先判为严重回撤风险。若没有触发回撤风险，则总收益率至少 +8% 判为上行，至多 -8% 判为下行，其余判为横盘。",
        "question_en": "How should this price window be classified?",
        "question_zh": "这段价格窗口应如何分类？",
        "options_en": opts_en,
        "options_zh": opts_zh,
        "semantic_answer_label": label,
        "answer": letter_for(labels, label),
        "support_slots": {
            "total_return": total_return,
            "max_drawdown": drawdown,
            "verifier_answer_label": label,
        },
        "oracle_evidence_en": f"Total return is {fmt_pct(total_return)}, and maximum drawdown from the running peak is {fmt_pct(drawdown)}.",
        "oracle_evidence_zh": f"总收益率为 {fmt_pct(total_return)}，相对历史峰值的最大回撤为 {fmt_pct(drawdown)}。",
        "reasoning_skill_tags": ["financial_reasoning", "derived_variable", "threshold_reasoning"],
    }


BUILDERS = {
    "grid2op": grid_record,
    "citylearn": city_record,
    "traffic": traffic_record,
    "water": water_record,
    "aiopslab": aiops_record,
    "finrl": finrl_record,
}


def public_record(row: dict[str, Any], source_index: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    raw = raw_series(row)
    built = BUILDERS[row["merge_source_name"]](row, raw)
    answer = built["answer"]
    options_en = built["options_en"]
    answer_label = options_en[answer]
    record = {
        "id": v4_id(source_index),
        "dataset_name": "public_raw_tsqa_v4",
        "source_simulator": row["merge_source_name"],
        "domain": built["domain"],
        "task_family": row["task_family"].replace("self_contained_", "raw_"),
        "split": row.get("split", "test"),
        "time_series": built["time_series"],
        "context_en": built["context_en"],
        "context_zh": built["context_zh"],
        "variable_descriptions_en": built["variable_descriptions_en"],
        "variable_descriptions_zh": built["variable_descriptions_zh"],
        "decision_rule_en": built["decision_rule_en"],
        "decision_rule_zh": built["decision_rule_zh"],
        "question_en": built["question_en"],
        "question_zh": built["question_zh"],
        "options_en": built["options_en"],
        "options_zh": built["options_zh"],
        "answer": answer,
        "answer_label": answer_label,
        "answer_label_zh": built["options_zh"][answer],
        "semantic_answer_label": built["semantic_answer_label"],
        "reasoning_skill_tags": built["reasoning_skill_tags"],
    }
    audit = {
        "id": record["id"],
        "source_v3_id": row["id"],
        "source_row_id": row.get("source_row_id"),
        "source_simulator": row["merge_source_name"],
        "v3_answer": row.get("answer"),
        "v3_semantic_answer_label": row.get("answer_label"),
        "raw_answer": answer,
        "raw_semantic_answer_label": built["semantic_answer_label"],
        "raw_gold_matches_v3": built["semantic_answer_label"] == row.get("answer_label"),
        "support_slots": built["support_slots"],
        "deterministic_rule_id": f"public_raw_tsqa_v4::{row['task_family']}",
        "oracle_evidence_en": built["oracle_evidence_en"],
        "oracle_evidence_zh": built["oracle_evidence_zh"],
        "reviewer_gate": {
            "source": "seed_quality_review_v3_fullprobe_20260521",
            "v3_positive_seed_ready": row.get("v3_positive_seed_ready"),
            "v3_probe_status": row.get("v3_probe_status"),
        },
    }
    mismatch = None if audit["raw_gold_matches_v3"] else audit
    return record, audit, mismatch


def llm_view(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "dataset_name": "public_raw_tsqa_v4_llm_text_view",
        "domain": record["domain"],
        "task_family": record["task_family"],
        "prompt_en": llm_prompt(record, lang="en"),
        "prompt_zh": llm_prompt(record, lang="zh"),
        "answer": record["answer"],
        "answer_label": record["answer_label"],
        "source_canonical_id": record["id"],
    }


def tsllm_view(record: dict[str, Any]) -> dict[str, Any]:
    text_en = public_text(
        record["context_en"],
        record["variable_descriptions_en"],
        record["decision_rule_en"],
        record["question_en"],
        record["options_en"],
    )
    text_zh = public_text(
        record["context_zh"],
        record["variable_descriptions_zh"],
        record["decision_rule_zh"],
        record["question_zh"],
        record["options_zh"],
    )
    return {
        "id": record["id"],
        "dataset_name": "public_raw_tsqa_v4_tsllm_array_view",
        "domain": record["domain"],
        "task_family": record["task_family"],
        "timeseries": record["time_series"]["values"],
        "columns": record["time_series"]["columns"],
        "time_axis": record["time_series"]["time_axis"],
        "text_en": text_en,
        "text_zh": text_zh,
        "answer": record["answer"],
        "answer_label": record["answer_label"],
        "source_canonical_id": record["id"],
    }


def oracle_row(record: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "domain": record["domain"],
        "question_en": record["question_en"],
        "question_zh": record["question_zh"],
        "options_en": record["options_en"],
        "options_zh": record["options_zh"],
        "answer": record["answer"],
        "answer_label": record["answer_label"],
        "oracle_evidence_en": audit["oracle_evidence_en"],
        "oracle_evidence_zh": audit["oracle_evidence_zh"],
        "source_canonical_id": record["id"],
    }


def forbidden_hits(record: dict[str, Any]) -> list[str]:
    public_parts = [
        record.get("id", ""),
        record.get("context_en", ""),
        record.get("context_zh", ""),
        record.get("decision_rule_en", ""),
        record.get("decision_rule_zh", ""),
        record.get("question_en", ""),
        record.get("question_zh", ""),
        json.dumps(record.get("options_en", {}), ensure_ascii=False),
        json.dumps(record.get("options_zh", {}), ensure_ascii=False),
        llm_prompt(record, lang="en"),
        llm_prompt(record, lang="zh"),
    ]
    text = "\n".join(public_parts)
    hits = []
    for pattern in FORBIDDEN_PUBLIC_PATTERNS:
        if re.search(re.escape(pattern), text, flags=re.IGNORECASE):
            hits.append(pattern)
    return hits


def summarize(records: list[dict[str, Any]], mismatches: list[dict[str, Any]], public_issues: list[dict[str, Any]]) -> dict[str, Any]:
    prompt_lengths = []
    for record in records:
        prompt_lengths.append(len(llm_prompt(record).split()))
    return {
        "n": len(records),
        "n_mismatch_excluded": len(mismatches),
        "n_public_forbidden_issues": len(public_issues),
        "by_domain": dict(Counter(row["domain"] for row in records)),
        "by_source_simulator": dict(Counter(row["source_simulator"] for row in records)),
        "answer_distribution": dict(Counter(row["answer"] for row in records)),
        "semantic_answer_distribution": dict(Counter(row["semantic_answer_label"] for row in records)),
        "time_series_lengths": {
            "min": min(len(row["time_series"]["values"]) for row in records) if records else 0,
            "max": max(len(row["time_series"]["values"]) for row in records) if records else 0,
        },
        "llm_prompt_word_lengths": {
            "min": min(prompt_lengths) if prompt_lengths else 0,
            "max": max(prompt_lengths) if prompt_lengths else 0,
            "mean": round(mean(prompt_lengths), 2) if prompt_lengths else 0,
        },
        "public_forbidden_issues": public_issues[:50],
    }


def render_spec(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Public Raw TSQA v4 Generation Spec（2026-05-21）",
        "",
        "本目录实现 `RAW_TSQA_BENCHMARK_STANDARD_20260521_ZH.md`：一份 canonical raw time-series QA 数据，同时导出 LLM text view 和 TS-LLM array view。",
        "",
        "## 产物",
        "",
        "- `canonical_raw_tsqa_v4.jsonl`：公开 canonical raw-series QA。",
        "- `llm_text_view.jsonl`：普通 LLM 使用的完整时序文本 prompt。",
        "- `tsllm_array_view.jsonl`：TS-LLM / ChatTS-style 模型使用的原始数组 + 文本问题。",
        "- `oracle_evidence.jsonl`：oracle evidence baseline 使用。",
        "- `audit_support.jsonl`：内部审计证据字段、规则 ID、source 信息和 reviewer trace。",
        "- `mismatch_audit.jsonl`：raw verifier 与 v3 gold 不一致而未纳入 public v4 的样本。",
        "",
        "## 本批统计",
        "",
        f"- rows: `{summary['n']}`",
        f"- mismatch excluded: `{summary['n_mismatch_excluded']}`",
        f"- public forbidden issues: `{summary['n_public_forbidden_issues']}`",
        f"- by domain: `{json.dumps(summary['by_domain'], ensure_ascii=False)}`",
        f"- answer distribution: `{json.dumps(summary['answer_distribution'], ensure_ascii=False)}`",
        f"- time-series length: `{summary['time_series_lengths']}`",
        f"- LLM prompt word length: `{summary['llm_prompt_word_lengths']}`",
        "",
    ]
    (out_dir / "PUBLIC_RAW_TSQA_V4_GENERATION_SPEC_20260521_ZH.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_jsonl", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    source_rows = load_jsonl(args.input_jsonl)
    canonical: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    public_issues: list[dict[str, Any]] = []
    for source_index, row in enumerate(source_rows):
        record, audit, mismatch = public_record(row, source_index)
        if mismatch is not None:
            mismatches.append(mismatch)
            continue
        if len(record["time_series"]["values"]) < MIN_PUBLIC_SERIES_LENGTH:
            mismatches.append(
                {
                    **audit,
                    "raw_gold_matches_v3": False,
                    "exclude_reason": "raw_series_too_short_for_public_benchmark",
                    "series_length": len(record["time_series"]["values"]),
                    "min_public_series_length": MIN_PUBLIC_SERIES_LENGTH,
                }
            )
            continue
        hits = forbidden_hits(record)
        if hits:
            public_issues.append({"id": record["id"], "hits": hits})
        canonical.append(record)
        audits.append(audit)

    llm_rows = [llm_view(row) for row in canonical]
    tsllm_rows = [tsllm_view(row) for row in canonical]
    oracle_rows = [oracle_row(row, audit) for row, audit in zip(canonical, audits)]
    summary = summarize(canonical, mismatches, public_issues)
    summary["inputs"] = {"v3_ready": rel(args.input_jsonl)}
    summary["outputs"] = {
        "canonical": rel(args.out_dir / "canonical_raw_tsqa_v4.jsonl"),
        "llm_text_view": rel(args.out_dir / "llm_text_view.jsonl"),
        "tsllm_array_view": rel(args.out_dir / "tsllm_array_view.jsonl"),
        "oracle_evidence": rel(args.out_dir / "oracle_evidence.jsonl"),
        "audit_support": rel(args.out_dir / "audit_support.jsonl"),
        "mismatch_audit": rel(args.out_dir / "mismatch_audit.jsonl"),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "canonical_raw_tsqa_v4.jsonl", canonical)
    write_jsonl(args.out_dir / "llm_text_view.jsonl", llm_rows)
    write_jsonl(args.out_dir / "tsllm_array_view.jsonl", tsllm_rows)
    write_jsonl(args.out_dir / "oracle_evidence.jsonl", oracle_rows)
    write_jsonl(args.out_dir / "audit_support.jsonl", audits)
    write_jsonl(args.out_dir / "mismatch_audit.jsonl", mismatches)
    write_json(args.out_dir / "public_raw_tsqa_v4_summary.json", summary)
    render_spec(args.out_dir, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
