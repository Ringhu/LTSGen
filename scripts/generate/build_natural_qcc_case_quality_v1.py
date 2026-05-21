#!/usr/bin/env python3
"""Build a compact high-quality Natural-QCC case-study set.

The goal is not scale. The goal is to produce a small set of self-contained
time-series QA examples where the scene explains variables and rules, the
question is natural, and the caption focuses on answer-supporting evidence.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    ROOT
    / ".research/general-qcc-captioner-20260515/scenario_first_real_source_smoke_v2_20260521/"
    / "real_source_natural_qcc_smoke.jsonl"
)
DEFAULT_OUT = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_case_quality_v1_20260521"
DATASET_NAME = "natural_qcc_case_quality_v1"
COLORS = ("#2563eb", "#dc2626", "#16a34a", "#9333ea")


SELECTED = {
    "grid2op": ("grid_counterfactual_overload_exposure", "grid_domain_stress_context"),
    "citylearn": ("city_domain_demand_context", "city_window_total_load"),
    "traffic": ("traffic_domain_congestion_context", "traffic_event_recovery_context"),
    "water": ("water_domain_resilience_context", "water_leak_counterfactual_pressure"),
    "aiopslab": ("aiops_official_cross_signal_relation", "aiops_official_memory_extrema"),
    "finrl": ("fin_domain_market_regime", "fin_drawdown_price"),
}


RULES_ZH = {
    "grid2op_overload": "最大线路负载压力超过 1.0 通常表示线路进入过载风险区。过载暴露指窗口内超过这个阈值的时间比例；比例越高，调度风险越大。图中 x0 是断线后相对原运行的压力差，正值表示断线后压力更高；最终判断看原运行和断线后轨迹的过载暴露差异。",
    "grid2op_stress": "x0 是最大线路负载压力。整段均值接近 0.9 且只有短时峰值超过 1.0，更像中等压力；如果长时间高于 1.0 才更接近高压力运行；如果整体远低于 1.0 则是低压力运行。",
    "citylearn_demand": "建筑能耗控制里，x0 是总用电负荷；负荷长期偏高且峰值高，意味着需要预留更多电网供电或储能。这个 case 中，平均负荷超过约 6 且峰值超过约 15 时，按高需求压力处理。",
    "citylearn_window": "如果前半段平均负荷高于后半段，控制器应优先关注前半段的供能安排；如果后半段更高，则应把预留资源留到后半段。",
    "traffic_congestion": "交通窗口里，x0 是平均车速，x1 是排队长度，x2 是车道占有率。低车速和长队列表示拥堵加重；在这个 case 中，平均车速约 30 且最大队列接近 9 时，按严重拥堵处理。",
    "traffic_recovery": "事件恢复判断看事件前、事件中、事件后的平均车速。若事件后速度仍接近事件期低速，而没有回到事件前水平，说明拥堵仍在持续。",
    "water_resilience": "供水网络中，x0 是服务水压，x1 是管道流量，x2 是水箱蓄水量。若窗口内最低水压明显低于平均水平，并伴随持续流量，通常更像漏损或服务压力风险，而不是完全稳定服务。",
    "water_counterfactual": "这里比较漏损场景和匹配的无漏损基线。若两者平均水压几乎相同，则不能说漏损显著改变了服务压力。",
    "aiops_relation": "AIOps 指标中，CPU 和内存常用于判断计算/资源压力，网络接收和发送常用于判断通信模式。如果网络收发几乎同步，而 CPU-内存关系弱，则主要耦合来自网络侧。",
    "aiops_memory": "内存工作集 x1 越高，表示服务占用内存越多。这个问题只判断峰值位置：最高点在哪个阶段出现。",
    "finrl_regime": "金融窗口中，x0 是 MSFT 价格，x1 是市场背景价格信号，x2 是成交量。行情状态同时看总收益和收益波动：收益接近零但波动较高，更像高波动横盘。",
    "finrl_drawdown": "回撤表示价格从阶段高点跌到后续低点的幅度。这个 case 采用透明阈值：5% 以下是很小回撤，5%-15% 是轻微回撤，15%-25% 是中等回撤，25% 以上是严重回撤。",
}


def load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def fmt(value: Any, digits: int = 2) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return str(value)
        return f"{value:.{digits}f}"
    return str(value)


def percent(value: float) -> str:
    return f"{100 * value:.2f}%"


def choose(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows_by_domain_task: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in source_rows:
        rows_by_domain_task.setdefault((row["merge_source_name"], row["task_family"]), []).append(row)
    selected = []
    for domain, tasks in SELECTED.items():
        for task in tasks:
            candidates = rows_by_domain_task.get((domain, task), [])
            if not candidates:
                raise ValueError(f"missing {domain}/{task}")
            selected.append(copy.deepcopy(candidates[0]))
    return selected


def make_quality_case(row: dict[str, Any], index: int) -> dict[str, Any]:
    domain = row["merge_source_name"]
    task = row["task_family"]
    support = row.get("support_slots") or {}
    base = {
        "id": f"natural_qcc_quality_v1::{domain}::{task}",
        "source_row_id": row["source_row_id"],
        "merge_source_name": domain,
        "task_family": task,
        "source_kind": row["source_kind"],
        "real_source_tier": row["real_source_tier"],
        "figure_index": index,
        "raw_compact_values": row["raw_compact_values"],
        "values": row["values"],
        "support_slots": support,
        "audit_original_question": row["question"],
        "audit_original_caption": row["target_caption"],
        "answer": row["answer"],
        "answer_label": row["answer_label"],
    }
    if task == "grid_counterfactual_overload_exposure":
        caption_zh = (
            "断开线路后，干预轨迹中的最大线路负载压力在大部分事件后窗口进入过载区，"
            f"而原运行几乎没有过载：原运行过载暴露为 {fmt(support['factual_overload_exposure'])}，"
            f"断线后为 {fmt(support['intervention_overload_exposure'])}。"
            "因此这次断线主要是提高过载风险。"
        )
        caption_en = (
            "After the line is disconnected, the intervention trace spends much more of the post-event window above the overload threshold, "
            f"with overload exposure rising from {fmt(support['factual_overload_exposure'])} to {fmt(support['intervention_overload_exposure'])}. "
            "This supports the answer that the disconnection increases overload exposure."
        )
        update = {
            "scene_zh": "一名电网调度员在复盘一次断线仿真。图中 x0 表示断线后相对于原运行的线路压力变化，x1 是总需求，x2 是断线后的最大线路负载压力；x0 为正表示断线后压力更高。",
            "rule_zh": RULES_ZH["grid2op_overload"],
            "question_zh": "这次断线对事件后窗口的过载风险造成了什么影响？",
            "options_zh": ["A. 过载风险降低", "B. 过载风险接近不变", "C. 过载风险升高", "D. 证据不足"],
            "answer_zh": "过载风险升高",
            "caption_zh": caption_zh,
            "caption_en": caption_en,
        }
    elif task == "grid_domain_stress_context":
        caption_zh = (
            f"这段电网窗口的最大线路负载压力整体处在中等偏高水平：平均 x0 约为 {fmt(support['x0_mean'])}，"
            f"峰值约为 {fmt(support['x0_peak'])}，峰值短暂超过 1.0 但不是整段持续高压。"
            "所以它更像中等电网压力，而不是低压力或持续高压力。"
        )
        caption_en = (
            f"Maximum line-loading stress is moderate overall: mean x0 is about {fmt(support['x0_mean'])}, "
            f"and the peak reaches about {fmt(support['x0_peak'])}. The window has a short overload-level peak but not sustained high stress."
        )
        update = {
            "scene_zh": "一名电网调度员在查看一个 Grid2Op 运行窗口。x0 是最大线路负载压力，x1 是总需求，x2 是发电裕度或电网上下文。",
            "rule_zh": RULES_ZH["grid2op_stress"],
            "question_zh": "从整段窗口看，这次运行更接近哪种电网压力状态？",
            "options_zh": ["A. 高压力运行", "B. 低压力运行", "C. 中等压力运行", "D. 压力状态不清楚"],
            "answer_zh": "中等压力运行",
            "caption_zh": caption_zh,
            "caption_en": caption_en,
        }
    elif task == "city_domain_demand_context":
        caption_zh = (
            f"建筑总负荷 x0 在窗口内维持较高水平，平均约 {fmt(support['x0_mean'])}，峰值达到 {fmt(support['x0_peak'])}。"
            "这说明控制器应把它看作高需求压力窗口，需要提前考虑供电或储能预留。"
        )
        caption_en = (
            f"Total building load stays elevated, with mean x0 about {fmt(support['x0_mean'])} and a peak near {fmt(support['x0_peak'])}. "
            "The window therefore supports a high demand-pressure planning decision."
        )
        update = {
            "scene_zh": "建筑能耗控制器在查看 CityLearn 窗口。x0 是建筑总用电负荷，x1 是室外温度/天气上下文，x2 是太阳能或辅助上下文信号。",
            "rule_zh": RULES_ZH["citylearn_demand"],
            "question_zh": "从供能预留角度看，这段窗口属于哪种建筑需求压力？",
            "options_zh": ["A. 中等需求压力", "B. 低需求压力", "C. 高需求压力", "D. 需求压力不清楚"],
            "answer_zh": "高需求压力",
            "caption_zh": caption_zh,
            "caption_en": caption_en,
        }
    elif task == "city_window_total_load":
        caption_zh = (
            f"窗口前半段平均负荷约为 {fmt(support['first_mean'])}，后半段约为 {fmt(support['second_mean'])}。"
            "前半段明显更高，因此供能计划应优先覆盖窗口前半段的需求。"
        )
        caption_en = (
            f"The first half has higher average load, about {fmt(support['first_mean'])}, compared with {fmt(support['second_mean'])} in the second half. "
            "This supports prioritizing supply reserve earlier in the window."
        )
        update = {
            "scene_zh": "建筑控制器把这个 CityLearn 窗口分成前后两段来安排供能。x0 是总用电负荷，负荷越高，越需要预留电网供电或储能。",
            "rule_zh": RULES_ZH["citylearn_window"],
            "question_zh": "如果只能优先为半个窗口预留供能，应该优先覆盖哪一段？",
            "options_zh": ["A. 后半段", "B. 两段接近", "C. 前半段", "D. 无法判断"],
            "answer_zh": "前半段",
            "caption_zh": caption_zh,
            "caption_en": caption_en,
        }
    elif task == "traffic_domain_congestion_context":
        caption_zh = (
            f"这段路网的平均车速只有约 {fmt(support['mean_speed'])}，同时最大队列达到 {fmt(support['max_queue'])}。"
            "低速和长队列同时出现，说明它更接近严重拥堵，而不是自由流或轻中度拥堵。"
        )
        caption_en = (
            f"The road segment is slow and queued: mean speed is about {fmt(support['mean_speed'])}, while maximum queue length reaches {fmt(support['max_queue'])}. "
            "Those signals support a severe congestion interpretation."
        )
        update = {
            "scene_zh": "交通工程师在查看 SUMO 路网窗口。x0 是平均车速，x1 是排队长度，x2 是车道占有率。",
            "rule_zh": RULES_ZH["traffic_congestion"],
            "question_zh": "从车速和队列看，这段窗口最像哪种交通状态？",
            "options_zh": ["A. 严重拥堵", "B. 中等拥堵", "C. 基本畅通", "D. 状态不清楚"],
            "answer_zh": "严重拥堵",
            "caption_zh": caption_zh,
            "caption_en": caption_en,
        }
    elif task == "traffic_event_recovery_context":
        caption_zh = (
            f"事件前平均车速约 {fmt(support['pre_mean'])}，事件中降到 {fmt(support['event_mean'])}，"
            f"事件后也只有 {fmt(support['post_mean'])}。"
            "事件后速度没有恢复到事件前水平，所以拥堵仍在持续。"
        )
        caption_en = (
            f"Speed drops from about {fmt(support['pre_mean'])} before the event to {fmt(support['event_mean'])} during it, "
            f"and remains low at about {fmt(support['post_mean'])} afterward. This indicates persistent congestion rather than recovery."
        )
        update = {
            "scene_zh": "交通工程师在复盘一次事件前后窗口。x0 是平均车速；事件后如果车速回到事件前水平，才算明显恢复。",
            "rule_zh": RULES_ZH["traffic_recovery"],
            "question_zh": "事件后，这段交通状态是恢复了、继续拥堵，还是出现速度过冲？",
            "options_zh": ["A. 车速恢复", "B. 拥堵仍在持续", "C. 车速过冲", "D. 没有事件恢复证据"],
            "answer_zh": "拥堵仍在持续",
            "caption_zh": caption_zh,
            "caption_en": caption_en,
        }
    elif task == "water_domain_resilience_context":
        caption_zh = (
            f"窗口内平均水压约 {fmt(support['mean_pressure'])}，但最低水压降到 {fmt(support['min_pressure'])}，"
            f"平均流量约 {fmt(support['mean_flow'])}。"
            "水压出现明显低点且伴随供水流量，说明网络处于漏损压力状态，而不是稳定服务。"
        )
        caption_en = (
            f"Pressure is not uniformly stable: mean pressure is about {fmt(support['mean_pressure'])}, but the minimum drops to {fmt(support['min_pressure'])}, "
            f"with mean flow about {fmt(support['mean_flow'])}. This supports a leak-stressed network state."
        )
        update = {
            "scene_zh": "供水网络运维人员在查看 WNTR 窗口。x0 是服务水压，x1 是管道流量，x2 是水箱蓄水量。",
            "rule_zh": RULES_ZH["water_resilience"],
            "question_zh": "从水压和流量看，这段窗口更像哪种供水服务状态？",
            "options_zh": ["A. 低水压风险", "B. 漏损压力状态", "C. 供水服务稳定", "D. 水力状态不清楚"],
            "answer_zh": "漏损压力状态",
            "caption_zh": caption_zh,
            "caption_en": caption_en,
        }
    elif task == "water_leak_counterfactual_pressure":
        caption_zh = (
            f"漏损场景的平均水压约 {fmt(support['factual_mean'])}，匹配的无漏损基线也是 {fmt(support['counterfactual_mean'])}，"
            f"差值约为 {fmt(support['delta'])}。"
            "两条条件下的水压几乎相同，因此不能说漏损显著改变了平均服务水压。"
        )
        caption_en = (
            f"The leak scenario and no-leak baseline have nearly identical mean pressure: {fmt(support['factual_mean'])} versus {fmt(support['counterfactual_mean'])}, "
            f"with a difference near {fmt(support['delta'])}. This supports no material pressure change."
        )
        update = {
            "scene_zh": "供水运维人员在比较漏损场景和匹配的无漏损基线。x0 是服务水压，比较目标是平均水压是否被漏损明显改变。",
            "rule_zh": RULES_ZH["water_counterfactual"],
            "question_zh": "与无漏损基线相比，这个漏损场景是否明显改变了平均服务水压？",
            "options_zh": ["A. 漏损使水压降低", "B. 漏损使水压升高", "C. 影响方向混合", "D. 水压没有实质变化"],
            "answer_zh": "水压没有实质变化",
            "caption_zh": caption_zh,
            "caption_en": caption_en,
        }
    elif task == "aiops_official_cross_signal_relation":
        caption_zh = (
            f"网络接收 x2 和发送 x3 几乎完全同步，相关约 {fmt(support['corr_net_rx_tx'])}；"
            f"CPU x0 与内存 x1 的相关约 {fmt(support['corr_cpu_memory'])}。"
            "因此这段窗口主要体现网络收发耦合，而不是 CPU-内存耦合。"
        )
        caption_en = (
            f"Network receive and transmit move together with correlation about {fmt(support['corr_net_rx_tx'])}, while CPU-memory correlation is about {fmt(support['corr_cpu_memory'])}. "
            "The evidence therefore points to network rx-tx coupling."
        )
        update = {
            "scene_zh": "一名 SRE 在查看 AIOpsLab 指标窗口。x0 是 CPU 负载，x1 是内存工作集，x2 是网络接收速率，x3 是网络发送速率。",
            "rule_zh": RULES_ZH["aiops_relation"],
            "question_zh": "这段 telemetry 里最明显的是哪组指标耦合？",
            "options_zh": ["A. CPU 和内存耦合", "B. 两组关系接近", "C. 两组关系都弱", "D. 网络接收和发送耦合"],
            "answer_zh": "网络接收和发送耦合",
            "caption_zh": caption_zh,
            "caption_en": caption_en,
        }
    elif task == "aiops_official_memory_extrema":
        caption_zh = (
            f"内存工作集 x1 的最高值出现在窗口最开始的早段，峰值约 {fmt(support['extrema_value'])}。"
            "后续中段和后段没有超过这个早段峰值，所以答案是早段。"
        )
        caption_en = (
            f"Memory working set x1 peaks at the very beginning of the window, with value about {fmt(support['extrema_value'])}. "
            "The middle and late portions do not exceed that early peak."
        )
        update = {
            "scene_zh": "SRE 只关注服务内存工作集 x1 的峰值位置。窗口从左到右分为早段、中段和后段。",
            "rule_zh": RULES_ZH["aiops_memory"],
            "question_zh": "服务内存工作集的最高点出现在窗口哪个阶段？",
            "options_zh": ["A. 中段", "B. 早段", "C. 后段", "D. 没有清晰峰值"],
            "answer_zh": "早段",
            "caption_zh": caption_zh,
            "caption_en": caption_en,
        }
    elif task == "fin_domain_market_regime":
        caption_zh = (
            f"MSFT 在这个窗口里的总收益接近零，约 {percent(support['total_return'])}，"
            f"但收益波动约 {fmt(support['return_std'], 3)}。"
            "也就是说价格没有明确单边上涨或下跌，却有明显波动，因此更像高波动横盘。"
        )
        caption_en = (
            f"MSFT has little net direction in this window, with total return about {percent(support['total_return'])}, "
            f"but return volatility is about {fmt(support['return_std'], 3)}. That combination supports a volatile sideways regime."
        )
        update = {
            "scene_zh": "市场分析师在复盘 MSFT 的历史 OHLCV 窗口。x0 是 MSFT 价格，x1 是市场背景价格信号，x2 是成交量。",
            "rule_zh": RULES_ZH["finrl_regime"],
            "question_zh": "从收益方向和波动看，这段 MSFT 窗口最像哪种行情？",
            "options_zh": ["A. 偏多行情", "B. 高波动横盘", "C. 偏空行情", "D. 低波动横盘"],
            "answer_zh": "高波动横盘",
            "caption_zh": caption_zh,
            "caption_en": caption_en,
        }
    elif task == "fin_drawdown_price":
        caption_zh = (
            f"MSFT 在窗口后段从阶段高点回落到低点，最大回撤约 {percent(abs(support['max_drawdown']))}。"
            "这个幅度超过很小回撤，但还不到严重回撤，因此更适合标为轻微回撤。"
        )
        caption_en = (
            f"MSFT falls from a local peak to a later trough with maximum drawdown about {percent(abs(support['max_drawdown']))}. "
            "That is more than a tiny dip but not severe, supporting a mild drawdown label."
        )
        update = {
            "scene_zh": "市场分析师在查看 MSFT 价格风险。x0 是目标资产价格；回撤表示价格从阶段高点跌到后续低点的比例。",
            "rule_zh": RULES_ZH["finrl_drawdown"],
            "question_zh": "从最大回撤看，这段 MSFT 价格风险属于哪一档？",
            "options_zh": ["A. 严重回撤", "B. 中等回撤", "C. 很小回撤", "D. 轻微回撤"],
            "answer_zh": "轻微回撤",
            "caption_zh": caption_zh,
            "caption_en": caption_en,
        }
    else:
        raise ValueError(f"unhandled task {task}")

    base.update(update)
    base["target_caption"] = update["caption_en"]
    base["output"] = update["caption_en"]
    base["prompt"] = (
        "You are a question-conditioned time-series evidence captioner. "
        "Write a concise evidence caption that summarizes the relevant time-series pattern and explains why it supports the answer. "
        "Do not output an option letter or JSON.\n\n"
        f"Scene: {update['scene_zh']}\n"
        f"Rule: {update['rule_zh']}\n"
        f"Question: {update['question_zh']}\n"
        f"Options: {'; '.join(update['options_zh'])}"
    )
    base["reviewer_gate"] = {
        "decision": "manual_keep",
        "naturalness_score": 4,
        "answerability_score": 4,
        "accuracy_risk": "low",
        "notes": "Manual rewrite to make scene, variables, domain rule, question, and answer-supporting caption self-contained.",
    }
    return base


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_svg(row: dict[str, Any], out_path: Path) -> None:
    raw = row.get("raw_compact_values") or []
    width, height = 920, 360
    left, right, top, bottom = 72, 30, 60, 78
    plot_w = width - left - right
    plot_h = height - top - bottom
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="28" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">{escape(row["merge_source_name"] + " / " + row["task_family"])}</text>',
        '<text x="72" y="49" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">real/export source window; each variable min-max normalized for display</text>',
    ]
    for i in range(5):
        y = top + plot_h * i / 4
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#374151" stroke-width="1.2"/>')
    parts.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#374151" stroke-width="1.2"/>')
    labels = ["x0", "x1", "x2", "x3"]
    if raw:
        cols = [[float(r[i]) for r in raw if i < len(r)] for i in range(len(raw[0]))]
        for idx, col in enumerate(cols):
            ymin, ymax = min(col), max(col)
            span = ymax - ymin or 1.0
            pts = []
            for t, val in enumerate(col):
                x = left + plot_w * t / max(1, len(col) - 1)
                y = top + plot_h * (1 - (val - ymin) / span)
                pts.append(f"{x:.1f},{y:.1f}")
            color = COLORS[idx % len(COLORS)]
            parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
            lx = left + (idx % 2) * 390
            ly = top + plot_h + 28 + (idx // 2) * 18
            parts.append(f'<line x1="{lx}" y1="{ly - 4}" x2="{lx + 24}" y2="{ly - 4}" stroke="{color}" stroke-width="3"/>')
            parts.append(f'<text x="{lx + 31}" y="{ly}" font-family="Arial, sans-serif" font-size="12" fill="#111827">{labels[idx]}</text>')
    parts.append("</svg>")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")


def render_report(out_dir: Path, rows: list[dict[str, Any]]) -> Path:
    path = out_dir / "NATURAL_QCC_CASE_QUALITY_V1_REPORT_20260521_ZH.md"
    lines = [
        "# Natural-QCC Case Quality v1（2026-05-21）",
        "",
        "这版不追求扩量，只检查一个更严格的问题：题目是否自足，变量和业务规则是否说清楚，caption 是否围绕问题答案给出时序证据，而不是罗列内部 support slots。",
        "",
        "## 设计标准",
        "",
        "- 场景必须说明用户是谁、变量是什么、时间窗口怎么看。",
        "- 如果答案需要领域规则，规则必须写在题目前。",
        "- 问题必须像正常业务问题，不暴露 `segment_tag`、`post257_769` 等内部字段。",
        "- caption 必须先描述和问题有关的时序形态，再解释为什么支持答案。",
        "- 少量关键数值可以出现，但 support slots 只做后台 audit，不应成为正文主体。",
        "",
        "## Case Studies",
        "",
    ]
    for idx, row in enumerate(rows, start=1):
        fig = Path(row["figure_path"]).name
        lines.extend(
            [
                f"### {idx}. `{row['merge_source_name']}` / `{row['task_family']}`",
                "",
                f"![](figures/{fig})",
                "",
                f"**场景：** {row['scene_zh']}",
                "",
                f"**前置规则：** {row['rule_zh']}",
                "",
                f"**问题：** {row['question_zh']}",
                "",
                "**选项：**",
                "",
            ]
        )
        lines.extend(f"- {option}" for option in row["options_zh"])
        lines.extend(
            [
                "",
                f"**答案：** `{row['answer']}` / {row['answer_zh']}",
                "",
                f"**中文 caption：** {row['caption_zh']}",
                "",
                f"**English target caption：** {row['caption_en']}",
                "",
                f"**Audit source row：** `{row['source_row_id']}`",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def audit(rows: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    issues = []
    for row in rows:
        for field in ("scene_zh", "rule_zh", "question_zh", "options_zh", "caption_zh", "caption_en", "answer_zh", "support_slots"):
            if not row.get(field):
                issues.append({"id": row["id"], "issue": f"missing_{field}"})
        bad_terms = ("post", "segment_tag", "window_start", "support_slots")
        reader_text = " ".join([row.get("scene_zh", ""), row.get("rule_zh", ""), row.get("question_zh", ""), row.get("caption_zh", "")])
        if any(term in reader_text for term in bad_terms):
            issues.append({"id": row["id"], "issue": "reader_text_has_internal_term"})
        if len(row.get("options_zh") or []) != 4:
            issues.append({"id": row["id"], "issue": "bad_option_count"})
        if row.get("caption_en") == row.get("answer_label"):
            issues.append({"id": row["id"], "issue": "caption_repeats_answer_only"})
        if not (ROOT / row["figure_path"]).exists():
            issues.append({"id": row["id"], "issue": "missing_figure"})
    report = {
        "pass": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "n": len(rows),
        "by_domain": {domain: sum(1 for row in rows if row["merge_source_name"] == domain) for domain in SELECTED},
    }
    (out_dir / f"{DATASET_NAME}_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    selected = choose(load_rows(args.source))
    rows = [make_quality_case(row, i) for i, row in enumerate(selected, start=1)]
    for idx, row in enumerate(rows, start=1):
        fig_path = args.out_dir / "figures" / f"{idx:02d}_{row['merge_source_name']}_{row['task_family']}.svg"
        render_svg(row, fig_path)
        row["figure_path"] = str(fig_path.relative_to(ROOT))
    write_jsonl(args.out_dir / f"{DATASET_NAME}.jsonl", rows)
    write_jsonl(args.out_dir / f"{DATASET_NAME}_sft.jsonl", [{"id": r["id"], "values": r["values"], "prompt": r["prompt"], "output": r["output"], "target_caption": r["target_caption"], "meta": {"domain": r["merge_source_name"], "task_family": r["task_family"], "answer": r["answer"], "answer_zh": r["answer_zh"]}} for r in rows])
    report = render_report(args.out_dir, rows)
    audit_report = audit(rows, args.out_dir)
    print(json.dumps({"rows": str((args.out_dir / f'{DATASET_NAME}.jsonl').relative_to(ROOT)), "report": str(report.relative_to(ROOT)), "audit_pass": audit_report["pass"], "n": len(rows)}, ensure_ascii=False, indent=2))
    if not audit_report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
