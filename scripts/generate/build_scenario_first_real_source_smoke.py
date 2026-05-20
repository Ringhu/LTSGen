#!/usr/bin/env python3
"""Build a six-domain Natural-QCC smoke set from real/exported source rows.

This script is intentionally different from the controlled scenario-first
pilot. It does not synthesize replacement windows. It samples existing
Grid2Op, CityLearn, WNTR, SUMO, AIOpsLab, and historical-OHLCV source artifacts,
then attaches natural scene text, Chinese QA/options/evidence, provenance, and
figures for a small protocol smoke test.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / ".research/general-qcc-captioner-20260515/scenario_first_real_source_smoke_20260521"
DATASET_NAME = "real_source_natural_qcc_smoke"
DOMAINS = ("grid2op", "citylearn", "traffic", "water", "aiopslab", "finrl")
COLORS = ("#2563eb", "#dc2626", "#16a34a", "#9333ea", "#0891b2")


SOURCE_SPECS: dict[str, dict[str, Any]] = {
    "grid2op": {
        "path": ROOT
        / ".research/general-qcc-captioner-20260515/grid2op_broad_v5_semantic_anchor/grid2op_broad_v5_semantic_anchor.jsonl",
        "schema_report": ROOT
        / ".research/general-qcc-captioner-20260515/grid2op_broad_v5_semantic_anchor/schema_report.json",
        "source_kind": "real_trace_artifact",
        "source_tier": "real_grid2op_trace_export",
        "official_target_simulator": "Grid2Op",
        "domain_zh": "电网调度",
        "scene_en": (
            "A grid operator is reviewing a local Grid2Op trace window exported from the real simulator pipeline. "
            "x0 is maximum line-loading stress, x1 is total demand, and x2 is generation margin or an auxiliary grid signal."
        ),
        "scene_zh": (
            "一名电网调度员正在查看从 Grid2Op 真实仿真流程导出的局部 trace 窗口。"
            "x0 是最大线路负载压力，x1 是总需求，x2 是发电裕度或辅助电网信号。"
        ),
        "variables_en": ["x0 maximum line-loading stress", "x1 total demand", "x2 generation margin / grid context"],
        "variables_zh": ["x0 最大线路负载压力", "x1 总需求", "x2 发电裕度/电网上下文"],
        "provenance_note": "sampled from Grid2Op broad v5 semantic-anchor rows backed by local real Grid2Op traces",
    },
    "citylearn": {
        "path": ROOT
        / ".research/general-qcc-captioner-20260515/citylearn_broad_semantic_v3_qual/citylearn_broad_semantic_v3_qual.jsonl",
        "schema_report": ROOT
        / ".research/general-qcc-captioner-20260515/citylearn_broad_semantic_v3_qual/schema_report.json",
        "source_kind": "real_trace_artifact",
        "source_tier": "real_citylearn_trace_export",
        "official_target_simulator": "CityLearn",
        "domain_zh": "建筑能耗控制",
        "scene_en": (
            "A building energy controller is reviewing a CityLearn trace window exported from packaged CityLearn data. "
            "x0 is total building load, x1 is weather or outdoor context, and x2 is solar or another context signal."
        ),
        "scene_zh": (
            "建筑能耗控制器正在查看从 CityLearn 数据出口导出的 trace 窗口。"
            "x0 是建筑总负荷，x1 是天气/室外上下文，x2 是太阳能或其他上下文信号。"
        ),
        "variables_en": ["x0 total building load", "x1 weather/outdoor context", "x2 solar/context signal"],
        "variables_zh": ["x0 建筑总负荷", "x1 天气/室外上下文", "x2 太阳能/上下文信号"],
        "provenance_note": "sampled from CityLearn broad v3 qualitative rows backed by real CityLearn trace exports",
    },
    "traffic": {
        "path": ROOT
        / ".research/general-qcc-captioner-20260515/multisim_qcc_v3_stable_dataflow/traffic_broad_smoke_v1/traffic_broad_smoke_v1.jsonl",
        "schema_report": ROOT
        / ".research/general-qcc-captioner-20260515/multisim_qcc_v3_stable_dataflow/traffic_broad_smoke_v1/schema_report.json",
        "source_kind": "official_simulator_export",
        "source_tier": "official_sumo_export",
        "official_target_simulator": "SUMO",
        "domain_zh": "交通信号/拥堵管理",
        "scene_en": (
            "A traffic engineer is reviewing a road-network window from the SUMO export adapter. "
            "x0 is mean speed, x1 is queue length, and x2 is lane occupancy."
        ),
        "scene_zh": (
            "交通工程师正在查看来自 SUMO export adapter 的道路网络窗口。"
            "x0 是平均车速，x1 是排队长度，x2 是车道占有率。"
        ),
        "variables_en": ["x0 mean speed", "x1 queue length", "x2 lane occupancy"],
        "variables_zh": ["x0 平均车速", "x1 排队长度", "x2 车道占有率"],
        "provenance_note": "sampled from the SUMO official-simulator export smoke artifact",
    },
    "water": {
        "path": ROOT
        / ".research/general-qcc-captioner-20260515/multisim_qcc_v3_stable_dataflow/water_broad_smoke_v1/water_broad_smoke_v1.jsonl",
        "schema_report": ROOT
        / ".research/general-qcc-captioner-20260515/multisim_qcc_v3_stable_dataflow/water_broad_smoke_v1/schema_report.json",
        "source_kind": "official_simulator_export",
        "source_tier": "official_wntr_export",
        "official_target_simulator": "WNTR",
        "domain_zh": "供水网络运维",
        "scene_en": (
            "A water-network operator is reviewing a WNTR export window. "
            "x0 is service pressure, x1 is pipe flow, and x2 is tank storage."
        ),
        "scene_zh": (
            "供水网络运维人员正在查看 WNTR export 窗口。"
            "x0 是服务水压，x1 是管道流量，x2 是水箱蓄水量。"
        ),
        "variables_en": ["x0 service pressure", "x1 pipe flow", "x2 tank storage"],
        "variables_zh": ["x0 服务水压", "x1 管道流量", "x2 水箱蓄水量"],
        "provenance_note": "sampled from the WNTR official-simulator export smoke artifact",
    },
    "aiopslab": {
        "path": ROOT / ".research/general-qcc-captioner-20260515/aiopslab_official_v3/aiopslab_official_v3.jsonl",
        "schema_report": ROOT / ".research/general-qcc-captioner-20260515/aiopslab_official_v3/schema_report.json",
        "source_kind": "official_simulator_export",
        "source_tier": "official_aiopslab_prometheus_export",
        "official_target_simulator": "AIOpsLab",
        "domain_zh": "AIOps/SRE 事故排查",
        "scene_en": (
            "An SRE is reviewing an AIOpsLab Prometheus-metrics export window. "
            "x0 is CPU load, x1 is memory working set, x2 is network receive rate, and x3 is network transmit rate."
        ),
        "scene_zh": (
            "一名 SRE 正在查看 AIOpsLab Prometheus 指标 export 窗口。"
            "x0 是 CPU 负载，x1 是内存工作集，x2 是网络接收速率，x3 是网络发送速率。"
        ),
        "variables_en": ["x0 CPU load", "x1 memory working set", "x2 network receive rate", "x3 network transmit rate"],
        "variables_zh": ["x0 CPU 负载", "x1 内存工作集", "x2 网络接收速率", "x3 网络发送速率"],
        "provenance_note": "sampled from merged AIOpsLab Prometheus export rows; local runtime was not rerun in this script",
    },
    "finrl": {
        "path": ROOT
        / ".research/general-qcc-captioner-20260515/finrl_local_ohlcv_smoke_20260521/finrl_local_ohlcv_smoke_20260521.jsonl",
        "schema_report": ROOT
        / ".research/general-qcc-captioner-20260515/finrl_local_ohlcv_smoke_20260521/schema_report.json",
        "source_kind": "local_historical_ohlcv_smoke",
        "source_tier": "real_historical_market_export_smoke",
        "official_target_simulator": "FinRL-style historical OHLCV",
        "domain_zh": "金融交易/风险复盘",
        "scene_en": (
            "A market analyst is reviewing a real historical OHLCV window in the FinRL data format. "
            "x0 is target asset price, x1 is a market background price signal, and x2 is trading volume."
        ),
        "scene_zh": (
            "市场分析师正在查看 FinRL 数据格式下的真实历史 OHLCV 窗口。"
            "x0 是目标资产价格，x1 是市场背景价格信号，x2 是交易量。"
        ),
        "variables_en": ["x0 target asset price", "x1 market background signal", "x2 trading volume"],
        "variables_zh": ["x0 目标资产价格", "x1 市场背景价格信号", "x2 交易量"],
        "provenance_note": (
            "local smoke uses a real historical OHLCV sample because the scaled FinRL A100 artifact is not copied locally"
        ),
        "limitations": "FinRL rows are real historical OHLCV smoke rows, not the remote 1.1GB scaled FinRL artifact.",
    },
}


LABEL_ZH = {
    "upward": "上升",
    "downward": "下降",
    "flat": "基本持平",
    "mixed": "混合波动",
    "early": "早段",
    "middle": "中段",
    "late": "后段",
    "no clear extremum": "没有清晰极值",
    "no pronounced spike": "没有明显尖峰",
    "first half higher": "前半段更高",
    "second half higher": "后半段更高",
    "similar halves": "前后半段接近",
    "similar thirds": "三个阶段接近",
    "both similar": "两者接近",
    "both weak": "两者都弱",
    "cannot determine": "无法判断",
    "unclear relation": "关系不清晰",
    "no clear lead": "没有清晰领先/滞后",
    "x0 leads x1": "x0 领先 x1",
    "x1 leads x0": "x1 领先 x0",
    "x1": "x1 更相关",
    "x2": "x2 更相关",
    "high grid stress": "电网压力高",
    "moderate grid stress": "电网压力中等",
    "low grid stress": "电网压力低",
    "unclear stress": "电网压力不清晰",
    "higher after intervention": "干预后更高",
    "lower after intervention": "干预后更低",
    "no material change": "没有实质变化",
    "greater overload exposure": "过载暴露更高",
    "lower overload exposure": "过载暴露更低",
    "similar overload exposure": "过载暴露接近",
    "larger downward dip": "更大的向下低谷",
    "larger upward peak": "更大的向上峰值",
    "high building demand pressure": "建筑需求压力高",
    "moderate building demand pressure": "建筑需求压力中等",
    "low building demand pressure": "建筑需求压力低",
    "unclear demand pressure": "建筑需求压力不清晰",
    "long cycle": "长周期",
    "medium cycle": "中等周期",
    "short cycle": "短周期",
    "no clear cycle": "没有清晰周期",
    "low-pressure risk": "低水压风险",
    "leak-stressed network": "漏损压力下的网络",
    "stable water service": "供水服务稳定",
    "unclear hydraulic state": "水力状态不清晰",
    "higher pressure under leak": "漏损条件下水压更高",
    "lower pressure under leak": "漏损条件下水压更低",
    "no material pressure change": "水压没有实质变化",
    "flow leads pressure": "流量领先水压",
    "pressure leads flow": "水压领先流量",
    "pressure-flow coupling": "水压和流量耦合",
    "pressure-storage coupling": "水压和蓄水量耦合",
    "pressure recovers": "水压恢复",
    "no event recovery": "事件后没有恢复",
    "persistent pressure stress": "持续水压压力",
    "pressure overshoot": "水压过冲",
    "pressure-led disruption": "水压主导扰动",
    "flow-led disruption": "流量主导扰动",
    "both pressure and flow disrupted": "水压和流量都被扰动",
    "no clear event response": "事件响应不清晰",
    "event creates higher x0 than baseline": "事件使 x0 高于基线",
    "event creates lower x0 than baseline": "事件使 x0 低于基线",
    "event has similar x0 to baseline": "事件下 x0 与基线接近",
    "event effect is mixed": "事件影响混合",
    "critical combined stress": "综合压力严重",
    "moderate combined stress": "综合压力中等",
    "stable combined state": "综合状态稳定",
    "unclear combined state": "综合状态不清晰",
    "mixed effect": "影响混合",
    "free-flow traffic": "交通畅通",
    "moderate congestion": "中等拥堵",
    "severe congestion": "严重拥堵",
    "unclear traffic state": "交通状态不清晰",
    "higher queue under adaptive signal": "自适应信号下队列更长",
    "lower queue under adaptive signal": "自适应信号下队列更短",
    "no material queue change": "队列没有实质变化",
    "speed leads queue": "速度领先队列",
    "queue leads speed": "队列领先速度",
    "speed-queue coupling": "速度和队列耦合",
    "speed-occupancy coupling": "速度和占有率耦合",
    "speed recovers": "速度恢复",
    "persistent congestion": "持续拥堵",
    "speed overshoot": "速度过冲",
    "speed-led disruption": "速度主导扰动",
    "queue-led disruption": "队列主导扰动",
    "both speed and queue disrupted": "速度和队列都被扰动",
    "critical combined congestion": "综合拥堵严重",
    "moderate combined congestion": "综合拥堵中等",
    "stable combined traffic": "综合交通状态稳定",
    "bullish regime": "偏多行情",
    "bearish regime": "偏空行情",
    "volatile sideways regime": "高波动横盘",
    "quiet sideways regime": "低波动横盘",
    "little drawdown": "回撤很小",
    "mild drawdown": "轻微回撤",
    "moderate drawdown": "中等回撤",
    "severe drawdown": "严重回撤",
    "market co-movement": "与市场同向联动",
    "volume co-movement": "与成交量联动",
    "asset leads market": "资产领先市场",
    "market leads asset": "市场领先资产",
    "cpu-memory coupling": "CPU 和内存耦合",
    "network rx-tx coupling": "网络收发耦合",
    "port misconfiguration": "端口配置错误",
    "port misconfiguration context": "端口配置错误场景",
    "scale-to-zero": "副本缩到零",
    "scale-to-zero context": "副本缩到零场景",
    "authentication revocation": "认证撤销",
    "authentication fault context": "认证故障场景",
    "other incident type": "其他事故类型",
    "unclear incident context": "事故上下文不清晰",
    "user-service": "user-service",
    "post-storage-service": "post-storage-service",
    "text-service": "text-service",
    "other service": "其他服务",
    "astronomy-shop application": "astronomy-shop 应用",
    "hotel-reservation application": "hotel-reservation 应用",
    "social-network application": "social-network 应用",
    "unknown application": "未知应用",
    "database authentication layer": "数据库认证层",
    "replica scaling layer": "副本伸缩层",
    "service routing layer": "服务路由层",
    "unknown layer": "未知层",
    "user/account service role": "用户/账号服务角色",
    "text/content service role": "文本/内容服务角色",
    "storage service role": "存储服务角色",
    "other service role": "其他服务角色",
    "built-in AIOpsLab incident": "AIOpsLab 内置事故",
    "external log replay": "外部日志回放",
    "synthetic fallback incident": "合成兜底事故",
    "unknown provenance": "未知来源",
}


SLOT_ZH = {
    "start_value": "初始值",
    "end_value": "末值",
    "delta": "净变化",
    "std": "波动",
    "mean": "均值",
    "min_value": "最小值",
    "max_value": "最大值",
    "peak_value": "峰值",
    "peak_index": "峰值位置",
    "window_start": "窗口起点",
    "window_end": "窗口终点",
    "source_horizon": "源 trace 长度",
    "early_mean": "早段均值",
    "middle_mean": "中段均值",
    "late_mean": "后段均值",
    "first_half_mean": "前半段均值",
    "second_half_mean": "后半段均值",
    "corr_x0_x1": "x0-x1 相关",
    "corr_x0_x2": "x0-x2 相关",
    "best_lag": "最佳滞后",
    "max_corr": "最大相关",
    "mean_stress_diff": "压力差均值",
    "min_stress_diff": "压力差最小值",
    "max_stress_diff": "压力差最大值",
    "percent_change": "百分比变化",
    "max_drawdown": "最大回撤",
    "date_start": "开始日期",
    "date_end": "结束日期",
    "event_index": "事件位置",
    "event_label": "事件标签",
    "global_post_start": "全局事件后起点",
    "post_start": "事件后局部起点",
    "intervention_step": "干预步",
    "line_id": "线路编号",
    "segment_start": "片段起点",
    "segment_end": "片段终点",
    "mean_x0_diff": "x0 反事实差均值",
    "min_x0_diff": "x0 反事实差最小值",
    "max_x0_diff": "x0 反事实差最大值",
    "exposure_diff": "过载暴露差",
    "factual_overload_exposure": "事实过载暴露",
    "intervention_overload_exposure": "干预后过载暴露",
    "corr_x1": "x1 相关",
    "corr_x2": "x2 相关",
    "corr_market": "市场相关",
    "corr_volume_change": "成交量变化相关",
    "event_baseline_mean": "事件基线均值",
    "event_factual_mean": "事件事实均值",
    "event_gap": "事件差值",
    "combined_stress_score": "综合压力分数",
    "x0_event_indicator": "x0 事件指示",
    "x0_mean": "x0 均值",
    "x0_peak": "x0 峰值",
    "x1_mean": "x1 均值",
    "x2_mean": "x2 均值",
    "trace_bucket_group": "trace 分桶",
    "horizon": "窗口长度",
    "app": "应用",
    "app_context": "应用上下文",
    "provenance": "来源",
    "return_std": "收益波动",
    "total_return": "总收益",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def has_injected_control_signature(row: dict[str, Any]) -> bool:
    """Detect rows where a real trace was modified by a controlled anomaly hook."""
    support = row.get("support_slots") or (row.get("meta") or {}).get("support_slots") or {}
    probe = json.dumps(
        {
            "task_family": row.get("task_family"),
            "support_slots": support,
            "target_caption": row.get("target_caption") or row.get("oracle_evidence_caption"),
        },
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    bad_terms = (
        "controlled_v",
        "controlled_anomaly",
        "anomaly_injected",
        '"injected": true',
        '"injected": 1',
    )
    return any(term in probe for term in bad_terms)


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


def fmt(value: Any) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return str(value)
        if abs(value) >= 1000:
            return f"{value:.1f}"
        if abs(value) >= 10:
            return f"{value:.2f}"
        return f"{value:.3f}"
    return str(value)


def label_zh(label: str) -> str:
    return LABEL_ZH.get(label, label.replace("_", " "))


def options_zh(options: list[str]) -> list[str]:
    translated = []
    for option in options:
        if ". " in option:
            letter, label = option.split(". ", 1)
            translated.append(f"{letter}. {label_zh(label)}")
        else:
            translated.append(label_zh(option))
    return translated


def split_for_domain_index(index: int) -> str:
    if index < 6:
        return "train"
    if index < 8:
        return "dev"
    return "test"


def abstract_primitive(row: dict[str, Any]) -> str:
    value = row.get("abstract_primitive") or (row.get("meta") or {}).get("abstract_primitive")
    if value:
        return str(value)
    task = str(row.get("task_family", ""))
    if "counterfactual" in task:
        return "counterfactual_effect"
    if "lead_lag" in task:
        return "temporal_relation"
    if "cross" in task or "relation" in task:
        return "cross_variable_relation"
    if "window" in task:
        return "window_comparison"
    if "volatility" in task:
        return "volatility"
    if "anomaly" in task or "spike" in task:
        return "anomaly"
    if "extrema" in task:
        return "extrema"
    if "trend" in task:
        return "trend"
    if "context" in task or "regime" in task:
        return "domain_context_reasoning"
    if "periodicity" in task:
        return "periodicity"
    return "domain_decision"


def question_zh(row: dict[str, Any], spec: dict[str, Any]) -> str:
    domain_zh = spec["domain_zh"]
    primitive = abstract_primitive(row)
    q = str(row.get("question", "")).lower()
    if "app" in row.get("task_family", ""):
        return "从这个 AIOpsLab 指标窗口和事故元信息看，它属于哪个应用场景？"
    if "faulty_service" in row.get("task_family", ""):
        return "从这个 AIOpsLab 指标窗口和事故元信息看，最可能涉及哪个故障服务？"
    if "fault_family" in row.get("task_family", ""):
        return "从这个 AIOpsLab 指标窗口和事故元信息看，事故类型最接近哪一类？"
    if "service_role" in row.get("task_family", ""):
        return "从这个 AIOpsLab 指标窗口看，故障服务更像哪种业务角色？"
    if "case_provenance" in row.get("task_family", ""):
        return "从这个 AIOpsLab case 的来源信息看，它属于哪类事故来源？"
    if primitive == "trend":
        return f"在这个{domain_zh}时序窗口中，核心信号整体是上升、下降、持平还是混合波动？"
    if primitive == "extrema":
        return f"在这个{domain_zh}窗口中，核心信号最明显的极值主要出现在早段、中段还是后段？"
    if primitive == "volatility":
        return f"在这个{domain_zh}窗口中，波动强度最符合哪种判断？"
    if primitive == "anomaly":
        return f"在这个{domain_zh}窗口中，是否出现了明显异常尖峰，位置大致在哪里？"
    if primitive == "periodicity":
        return f"在这个{domain_zh}窗口中，周期性更像短周期、中周期、长周期，还是不清晰？"
    if primitive == "window_comparison":
        return f"把这个{domain_zh}窗口分成前后或三段比较，哪一段的压力/需求/风险更高？"
    if primitive == "cross_variable_relation":
        return f"在这个{domain_zh}窗口中，哪个伴随信号和核心信号的关系更强？"
    if primitive == "temporal_relation":
        return f"从这个{domain_zh}窗口看，两个关键信号之间是否存在清晰的领先或滞后关系？"
    if primitive == "counterfactual_effect":
        return f"与对照或反事实基线相比，这个{domain_zh}窗口中的干预主要带来什么影响？"
    if primitive == "domain_context_reasoning":
        return f"结合{domain_zh}背景和时序走势，这个窗口最符合哪种业务状态判断？"
    if "compared with" in q or "baseline" in q:
        return f"与匹配基线相比，这个{domain_zh}窗口中的主要变化是什么？"
    return f"结合这个{domain_zh}时序窗口，应选择哪一个最合理的业务判断？"


def scene_with_axis(row: dict[str, Any], spec: dict[str, Any]) -> tuple[str, str]:
    support = row.get("support_slots") or {}
    n = len(row.get("raw_compact_values") or row.get("values") or [])
    window_start = support.get("window_start")
    window_end = support.get("window_end")
    source_horizon = support.get("source_horizon")
    date_start = support.get("date_start")
    date_end = support.get("date_end")
    if date_start and date_end:
        axis_en = f" The local plot covers {n} observations from {date_start} to {date_end}."
        axis_zh = f" 图中的局部窗口包含 {n} 个观测点，时间从 {date_start} 到 {date_end}。"
    elif window_start is not None and window_end is not None:
        horizon_text = f" within a source trace of length {source_horizon}" if source_horizon is not None else ""
        axis_en = f" The local plot covers source steps {window_start}-{window_end}{horizon_text}."
        axis_zh = f" 图中的局部窗口覆盖源 trace 的第 {window_start}-{window_end} 步"
        if source_horizon is not None:
            axis_zh += f"，源 trace 长度为 {source_horizon}"
        axis_zh += "。"
    else:
        axis_en = f" The local plot contains {n} time steps."
        axis_zh = f" 图中的局部窗口包含 {n} 个时间步。"
    return spec["scene_en"] + axis_en, spec["scene_zh"] + axis_zh


def support_summary_zh(row: dict[str, Any]) -> str:
    support = row.get("support_slots") or {}
    skip = {"answer_label", "markers"}
    parts = []
    priority = [
        "start_value",
        "end_value",
        "delta",
        "std",
        "early_mean",
        "middle_mean",
        "late_mean",
        "first_half_mean",
        "second_half_mean",
        "mean_stress_diff",
        "min_stress_diff",
        "max_stress_diff",
        "percent_change",
        "max_drawdown",
        "corr_x0_x1",
        "corr_x0_x2",
        "best_lag",
        "max_corr",
        "window_start",
        "window_end",
        "date_start",
        "date_end",
    ]
    keys = [key for key in priority if key in support]
    keys.extend(key for key in sorted(support) if key not in set(keys) and key not in skip)
    for key in keys:
        if key in skip:
            continue
        value = support.get(key)
        if isinstance(value, (list, dict)):
            continue
        parts.append(f"{SLOT_ZH.get(key, key)}={fmt(value)}")
        if len(parts) >= 7:
            break
    return "，".join(parts) if parts else "源 artifact 中的确定性 support slots 与答案一致"


def evidence_zh(row: dict[str, Any]) -> str:
    answer_label = str(row.get("answer_label") or (row.get("support_slots") or {}).get("answer_label", ""))
    return f"确定性证据支持“{label_zh(answer_label)}”。关键数值：{support_summary_zh(row)}。"


def prompt_for(row: dict[str, Any], spec: dict[str, Any], scene_en: str) -> str:
    options_text = "\n".join(row.get("options") or [])
    return (
        "You are a question-conditioned time-series evidence captioner. "
        "Given the time series, scene, variables, and downstream multiple-choice question, "
        "write one or two concise natural-language sentences containing only the evidence needed to answer the question. "
        "Do not choose an option letter and do not output JSON.\n\n"
        f"Scene: {scene_en}\n"
        f"Variables: {'; '.join(spec['variables_en'])}\n"
        f"Question: {row.get('question', '')}\n"
        f"Options:\n{options_text}"
    )


def source_value(row: dict[str, Any], key: str, default: Any = None) -> Any:
    return row.get(key) if row.get(key) is not None else (row.get("meta") or {}).get(key, default)


def normalize_row(row: dict[str, Any], domain: str, domain_index: int) -> dict[str, Any]:
    spec = SOURCE_SPECS[domain]
    out = copy.deepcopy(row)
    source_row_id = str(out.get("id", ""))
    scene_en, scene_zh = scene_with_axis(out, spec)
    source_kind = str(source_value(out, "source_kind", spec["source_kind"]) or spec["source_kind"])
    official_target = str(
        source_value(out, "official_target_simulator", spec["official_target_simulator"])
        or spec["official_target_simulator"]
    )
    source_path = str(out.get("source_path") or source_value(out, "source_path", spec["path"]))
    support = copy.deepcopy(out.get("support_slots") or (out.get("meta") or {}).get("support_slots") or {})
    answer_label = str(out.get("answer_label") or support.get("answer_label") or "")
    if answer_label and not support.get("answer_label"):
        support["answer_label"] = answer_label
    target = str(out.get("target_caption") or out.get("oracle_evidence_caption") or (out.get("meta") or {}).get("target_caption") or "")
    if not target:
        target = f"Evidence supports {answer_label}."
    real_generation = {
        "source_adapter": spec["source_tier"],
        "source_path": source_path,
        "schema_report": rel(spec["schema_report"]),
        "official_target_simulator": official_target,
        "generation_order": [
            "load real/official source artifact from source_path",
            "extract source time-series window without synthesizing a controlled replacement",
            "compute or preserve deterministic support slots from trace/export values",
            "preserve source gold answer and evidence caption",
            "attach natural scene, Chinese QA/options/evidence, and smoke split",
        ],
    }
    smoke_id = f"real_source_smoke::{domain}::{domain_index:02d}::{out.get('task_family', 'task')}::{source_row_id}"
    smoke_id = smoke_id.replace("/", "_").replace(" ", "_")
    out.update(
        {
            "id": smoke_id,
            "source_row_id": source_row_id,
            "source_split": out.get("split"),
            "split": split_for_domain_index(domain_index),
            "smoke_split": split_for_domain_index(domain_index),
            "merge_source_name": domain,
            "multisim_source_domain": domain,
            "source_path": source_path,
            "source_kind": source_kind,
            "real_source_tier": spec["source_tier"],
            "official_target_simulator": official_target,
            "source_provenance_note": spec["provenance_note"],
            "real_source_limitations": spec.get("limitations", ""),
            "scene_en": scene_en,
            "scene_zh": scene_zh,
            "variables_en": spec["variables_en"],
            "variables_zh": spec["variables_zh"],
            "question_zh": out.get("question_zh") or question_zh(out, spec),
            "options_zh": out.get("options_zh") or options_zh(out.get("options") or []),
            "answer_label": answer_label,
            "answer_zh": label_zh(answer_label),
            "support_slots": support,
            "abstract_primitive": abstract_primitive(out),
            "natural_evidence_caption": target,
            "natural_evidence_zh": out.get("natural_evidence_zh") or evidence_zh({**out, "support_slots": support, "answer_label": answer_label}),
            "target_caption": target,
            "output": target,
            "prompt": prompt_for(out, spec, scene_en),
            "real_source_generation": real_generation,
            "scenario_first_generation": real_generation,
            "natural_status": "real_source_adapter_smoke",
            "review_scope": "deterministic_source_adapter_gate",
            "review_decision": "keep",
        }
    )
    meta = copy.deepcopy(out.get("meta") or {})
    meta.update(
        {
            "source_row_id": source_row_id,
            "source_split": out["source_split"],
            "smoke_split": out["smoke_split"],
            "merge_source_name": domain,
            "multisim_source_domain": domain,
            "source_kind": source_kind,
            "real_source_tier": spec["source_tier"],
            "official_target_simulator": official_target,
            "source_path": source_path,
            "question_zh": out["question_zh"],
            "options_zh": out["options_zh"],
            "answer_zh": out["answer_zh"],
            "natural_evidence_zh": out["natural_evidence_zh"],
            "real_source_generation": real_generation,
        }
    )
    out["meta"] = meta
    return out


def select_task_balanced(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[str(row.get("task_family", ""))].append(row)
    for task_rows in by_task.values():
        task_rows.sort(key=lambda r: (str(r.get("answer", "")), str(r.get("answer_label", "")), str(r.get("id", ""))))
    selected: list[dict[str, Any]] = []
    answer_counts: Counter[str] = Counter()
    tasks = sorted(by_task)
    while len(selected) < count and any(by_task.values()):
        for task in tasks:
            pool = by_task[task]
            if not pool:
                continue
            best_idx = min(
                range(len(pool)),
                key=lambda i: (answer_counts[str(pool[i].get("answer", ""))], str(pool[i].get("id", ""))),
            )
            row = pool.pop(best_idx)
            selected.append(row)
            answer_counts[str(row.get("answer", ""))] += 1
            if len(selected) >= count:
                break
    if len(selected) < count:
        raise ValueError(f"only selected {len(selected)} rows, need {count}")
    return selected


def build_rows(per_domain: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_summary: dict[str, Any] = {}
    for domain in DOMAINS:
        spec = SOURCE_SPECS[domain]
        source_rows = load_jsonl(spec["path"])
        filtered_rows = [row for row in source_rows if not has_injected_control_signature(row)]
        selected = select_task_balanced(filtered_rows, per_domain)
        source_summary[domain] = {
            "source_path": rel(spec["path"]),
            "schema_report": rel(spec["schema_report"]),
            "source_rows_available": len(source_rows),
            "source_rows_after_control_filter": len(filtered_rows),
            "filtered_control_signature_rows": len(source_rows) - len(filtered_rows),
            "source_kind": spec["source_kind"],
            "source_tier": spec["source_tier"],
            "official_target_simulator": spec["official_target_simulator"],
            "selected_rows": len(selected),
            "selected_task_families": sorted({str(row.get("task_family", "")) for row in selected}),
            "provenance_note": spec["provenance_note"],
            "limitations": spec.get("limitations", ""),
        }
        for idx, row in enumerate(selected):
            rows.append(normalize_row(row, domain, idx))
    return rows, source_summary


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row["target_caption"],
        "meta": row["meta"],
    }


def write_sft(out_dir: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    sft_dir = out_dir / "sft"
    sft_dir.mkdir(parents=True, exist_ok=True)
    sft_rows = [sft_row(row) for row in rows]
    combined = out_dir / f"{DATASET_NAME}_sft.jsonl"
    write_jsonl(combined, sft_rows)
    split_info: dict[str, Any] = {"all": {"path": rel(combined), "n": len(sft_rows)}}
    for split in ("train", "dev", "test"):
        raw = [row for row in rows if row.get("split") == split]
        raw_path = sft_dir / f"{DATASET_NAME}_{split}_raw.jsonl"
        sft_path = sft_dir / f"{DATASET_NAME}_{split}_sft.jsonl"
        write_jsonl(raw_path, raw)
        write_jsonl(sft_path, [sft_row(row) for row in raw])
        split_info[split] = {"raw": rel(raw_path), "sft": rel(sft_path), "n": len(raw)}
    return split_info


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_svg(row: dict[str, Any], out_path: Path, title: str) -> None:
    raw = row.get("raw_compact_values") or row.get("values") or []
    if not raw or not isinstance(raw[0], list):
        return
    width, height = 920, 360
    left, right, top, bottom = 72, 30, 60, 78
    plot_w = width - left - right
    plot_h = height - top - bottom
    n = len(raw)
    cols = [[float(r[i]) for r in raw if i < len(r)] for i in range(len(raw[0]))]
    labels = row.get("variables_zh") or [f"x{i}" for i in range(len(cols))]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="28" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">{escape(title)}</text>',
        f'<text x="{left}" y="49" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">source: {escape(row.get("source_kind", ""))}; per-variable min-max normalized for display</text>',
    ]
    for i in range(5):
        y = top + plot_h * i / 4
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#374151" stroke-width="1.2"/>')
    parts.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#374151" stroke-width="1.2"/>')
    markers = (row.get("support_slots") or {}).get("markers") or []
    for marker in markers:
        idx = marker.get("index")
        if isinstance(idx, int):
            x = left + plot_w * idx / max(1, n - 1)
            label = str(marker.get("label", "event"))
            parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}" stroke="#9ca3af" stroke-width="1" stroke-dasharray="5 4"/>')
            parts.append(f'<text x="{x + 4:.1f}" y="{top + 14}" font-family="Arial, sans-serif" font-size="11" fill="#6b7280">{escape(label)}</text>')
    for idx, col in enumerate(cols):
        if not col:
            continue
        ymin, ymax = min(col), max(col)
        span = ymax - ymin or 1.0
        pts = []
        for t, val in enumerate(col):
            x = left + plot_w * t / max(1, n - 1)
            y = top + plot_h * (1.0 - ((val - ymin) / span))
            pts.append(f"{x:.1f},{y:.1f}")
        color = COLORS[idx % len(COLORS)]
        parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        lx = left + (idx % 2) * 392
        ly = top + plot_h + 28 + (idx // 2) * 18
        parts.append(f'<line x1="{lx}" y1="{ly - 4}" x2="{lx + 24}" y2="{ly - 4}" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<text x="{lx + 31}" y="{ly}" font-family="Arial, sans-serif" font-size="12" fill="#111827">{escape(str(labels[idx]))}</text>')
    parts.append(f'<text x="{left}" y="{height - 14}" font-family="Arial, sans-serif" font-size="11" fill="#6b7280">row id: {escape(row["id"][:130])}</text>')
    parts.append("</svg>")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")


def render_figures(out_dir: Path, rows: list[dict[str, Any]]) -> dict[str, str]:
    fig_dir = out_dir / "figures"
    paths = {}
    for idx, row in enumerate(rows, start=1):
        domain = row["merge_source_name"]
        task = str(row.get("task_family", "task"))
        fig_path = fig_dir / f"{idx:02d}_{domain}_{task}.svg"
        title = f"{domain} / {task}"
        render_svg(row, fig_path, title)
        row["figure_path"] = rel(fig_path)
        paths[row["id"]] = rel(fig_path)
    return paths


def summarize(rows: list[dict[str, Any]], source_summary: dict[str, Any], sft_info: dict[str, Any]) -> dict[str, Any]:
    answer_counts = Counter(str(row.get("answer", "")) for row in rows)
    source_kind_by_domain: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        source_kind_by_domain[row["merge_source_name"]][row["source_kind"]] += 1
    return {
        "dataset": DATASET_NAME,
        "n": len(rows),
        "expected_domains": list(DOMAINS),
        "by_domain": dict(Counter(row["merge_source_name"] for row in rows)),
        "by_split": dict(Counter(row["split"] for row in rows)),
        "by_source_kind": dict(Counter(row["source_kind"] for row in rows)),
        "by_domain_source_kind": {k: dict(v) for k, v in sorted(source_kind_by_domain.items())},
        "by_task_family": dict(Counter(str(row.get("task_family", "")) for row in rows)),
        "answer_distribution": dict(answer_counts),
        "max_answer_share": round(max(answer_counts.values()) / len(rows), 4) if rows else 1.0,
        "caption_empty_count": sum(1 for row in rows if not row.get("target_caption")),
        "missing_chinese_count": sum(
            1 for row in rows if not row.get("question_zh") or len(row.get("options_zh") or []) != 4 or not row.get("natural_evidence_zh")
        ),
        "controlled_source_count": sum(1 for row in rows if "controlled" in str(row.get("source_kind", "")) or "controlled" in str(row.get("source_path", ""))),
        "injected_control_signature_count": sum(1 for row in rows if has_injected_control_signature(row)),
        "source_summary": source_summary,
        "sft_files": sft_info,
    }


def representative_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_domain = {}
    for row in rows:
        by_domain.setdefault(row["merge_source_name"], row)
    return [by_domain[domain] for domain in DOMAINS]


def render_report(out_dir: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> Path:
    report_path = out_dir / "REAL_SOURCE_NATURAL_QCC_SMOKE_REPORT_20260521_ZH.md"
    lines = [
        "# Real-source Natural-QCC 六域 Smoke 报告（2026-05-21）",
        "",
        "## 1. 先回答你的疑问",
        "",
        "不是所有上一轮样本都等价于“从每个域的真实 simulator/exporter adapter 里导出来”。上一轮六域 smoke 确实覆盖了 Grid2Op、CityLearn、Traffic、Water、AIOpsLab、FinRL 的领域外观，但大多数窗口来自 controlled scenario-first generator：它先设定一个领域场景，再按程序生成符合该场景的时序。这个流程适合检查题目协议和中文自然化，但它不能代表真实 simulator/exporter 的数据分布。",
        "",
        "support slots 的作用也不是“拿答案找问题”。更准确地说，它们是后台审计锚点：真实 trace/export 已经给出了时序窗口，程序再从窗口或 simulator 状态里计算趋势、峰值、相关、反事实差值、阈值判断等确定性证据，用来保证答案可验证。问题和 caption 应该自然地面向业务场景，而不是把这些 slot 名字拼出来。",
        "",
        "因此下一步不能只继续堆 controlled 数据。需要把同一套 Natural-QCC 协议接到每个域的真实数据出口上，原因有三个：",
        "",
        "1. 避免模型只学到 controlled generator 的规律，而不是各域真实 trace 的噪声、边界和分布。",
        "2. 避免题目越来越模板化；真实出口会暴露更多自然业务问题需要的上下文。",
        "3. 后续 smoke test 才能判断“协议能不能跨真实域运行”，而不是只判断“构造器能不能自洽”。",
        "",
        "## 2. 本轮做了什么",
        "",
        f"- 生成总数：`{summary['n']}` 条。",
        "- 每个域目标：`10` 条。",
        f"- 实际域覆盖：`{summary['by_domain']}`。",
        f"- source kind 分布：`{summary['by_source_kind']}`。",
        f"- controlled source count：`{summary['controlled_source_count']}`。",
        f"- injected/controlled anomaly signature count：`{summary['injected_control_signature_count']}`。",
        f"- caption empty count：`{summary['caption_empty_count']}`。",
        f"- 中文字段缺失数：`{summary['missing_chinese_count']}`。",
        "",
        "## 3. 数据来源表",
        "",
        "| domain | rows | source kind | source/export adapter | source artifact | 说明 |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for domain in DOMAINS:
        info = summary["source_summary"][domain]
        lines.append(
            f"| `{domain}` | `{summary['by_domain'].get(domain, 0)}` | `{info['source_kind']}` | "
            f"`{info['official_target_simulator']}` | `{info['source_path']}` | {info['provenance_note']} |"
        )
    lines.extend(
        [
            "",
            "FinRL 的限制需要单独说明：本地没有拷贝 A100 上约 1.1GB 的 scaled FinRL artifact，所以这轮本地 smoke 使用真实历史 OHLCV 小样本。它比 controlled generator 更接近真实数据出口，但还不是最终 FinRL 大规模 exporter benchmark。",
            "",
            "## 4. 生成协议",
            "",
            "本轮每条样本的顺序是：",
            "",
            "1. 读取已有真实/官方 source artifact。",
            "2. 抽取原始时序窗口，不用 controlled generator 替换窗口。",
            "3. 保留或计算 deterministic support slots，作为答案和 caption 的可审计证据。",
            "4. 保留原始 gold answer 和 evidence caption。",
            "5. 补齐自然场景、中文问题、中文选项、中文证据和 SFT prompt/output。",
            "",
            "## 5. 代表性 Case Study",
            "",
        ]
    )
    for idx, row in enumerate(representative_rows(rows), start=1):
        fig_path = Path(row["figure_path"]).name
        lines.extend(
            [
                f"### {idx}. `{row['merge_source_name']}` / `{row['task_family']}`",
                "",
                f"![](figures/{fig_path})",
                "",
                f"**source kind：** `{row['source_kind']}`",
                "",
                f"**source row：** `{row['source_row_id']}`",
                "",
                f"**场景中文：** {row['scene_zh']}",
                "",
                f"**问题中文：** {row['question_zh']}",
                "",
                "**选项中文：**",
                "",
            ]
        )
        lines.extend(f"- {option}" for option in row["options_zh"])
        lines.extend(
            [
                "",
                f"**答案：** `{row['answer']}` / {row['answer_zh']}",
                "",
                f"**证据中文：** {row['natural_evidence_zh']}",
                "",
                f"**英文 evidence caption：** {row['natural_evidence_caption']}",
                "",
            ]
        )
    lines.extend(
        [
            "## 6. 这轮结论",
            "",
            "这轮解决的是“每个域都接到真实/官方数据出口，并且每域有足够小样本用于 smoke test”的问题。它还不是最终训练集，也还没有经过 LLM reviewer 大规模自然性筛选；下一步应该在这些真实来源上扩大样本量，并对自然问题和 caption 做 reviewer gate。",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--per_domain", type=int, default=10)
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, source_summary = build_rows(args.per_domain)
    render_figures(out_dir, rows)
    rows_path = out_dir / f"{DATASET_NAME}.jsonl"
    write_jsonl(rows_path, rows)
    sft_info = write_sft(out_dir, rows)
    summary = summarize(rows, source_summary, sft_info)
    summary["artifacts"] = {
        "rows": rel(rows_path),
        "combined_sft": sft_info["all"]["path"],
        "report": rel(out_dir / "REAL_SOURCE_NATURAL_QCC_SMOKE_REPORT_20260521_ZH.md"),
    }
    summary_path = out_dir / f"{DATASET_NAME}_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = render_report(out_dir, rows, summary)
    print(json.dumps({"rows": rel(rows_path), "summary": rel(summary_path), "report": rel(report_path), "n": len(rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
