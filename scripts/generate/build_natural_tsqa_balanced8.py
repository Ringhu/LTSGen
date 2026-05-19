#!/usr/bin/env python3
"""Generate natural-language QA rewrites for the 48-row MultiSim balanced8 set."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[2]
RAW = (
    ROOT
    / ".research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/"
    / "case_study_simulator_data_20260518/raw_samples/balanced_eval_per_source8.jsonl"
)
OUT_DIR = ROOT / ".research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519"
OUT_JSONL = OUT_DIR / "natural_multisim_v5_balanced8.jsonl"
OUT_LINT = OUT_DIR / "natural_multisim_v5_balanced8_lint.json"
OUT_MD = OUT_DIR / "NATURAL_QA_BALANCED8_LINT_20260519_ZH.md"


OPTION_ZH = {
    "early": "早期",
    "middle": "中期",
    "late": "后期",
    "no pronounced spike": "没有明显尖峰",
    "x1": "x1",
    "x2": "x2",
    "both similar": "二者相近",
    "both weak": "二者都弱",
    "larger downward dip": "更大的向下偏差",
    "no material change": "没有实质变化",
    "larger upward peak": "更大的向上峰值",
    "cannot determine": "无法判断",
    "first half higher": "前半段更高",
    "second half higher": "后半段更高",
    "similar halves": "前后两半相近",
    "similar thirds": "三段相近",
    "flat": "基本平稳",
    "upward": "上升",
    "downward": "下降",
    "volatile": "波动明显",
    "x0 leads x1": "x0 领先 x1",
    "x1 leads x0": "x1 领先 x0",
    "no clear lead": "没有清晰领先关系",
    "unclear relation": "关系不清楚",
    "short cycle": "短周期",
    "medium cycle": "中等周期",
    "long cycle": "长周期",
    "no clear cycle": "没有明显周期",
    "lower queue under adaptive signal": "自适应信号下队列更低",
    "higher queue under adaptive signal": "自适应信号下队列更高",
    "no material queue change": "没有实质队列变化",
    "mixed effect": "混合影响",
    "lower pressure under leak": "漏水下水压更低",
    "higher pressure under leak": "漏水下水压更高",
    "no material pressure change": "没有实质水压变化",
    "event has similar x0 to baseline": "事件窗口内 x0 与基线相近",
    "event raises x0 above baseline": "事件使 x0 高于基线",
    "event lowers x0 below baseline": "事件使 x0 低于基线",
    "pressure recovers": "水压恢复",
    "pressure overshoot": "水压过冲",
    "persistent pressure stress": "持续水压压力",
    "no event recovery": "没有事件恢复",
    "no clear extremum": "没有清晰极值",
    "mixed": "混合变化",
    "critical combined stress": "严重综合压力",
    "stable combined state": "稳定综合状态",
    "moderate combined stress": "中等综合压力",
    "unclear combined state": "综合状态不清楚",
    "leak-stressed network": "漏水压力下的网络",
    "low-pressure risk": "低水压风险",
    "unclear hydraulic state": "水力状态不清楚",
    "stable water service": "稳定供水服务",
    "high building demand pressure": "高建筑需求压力",
    "low building demand pressure": "低建筑需求压力",
    "moderate building demand pressure": "中等建筑需求压力",
    "unclear demand pressure": "需求压力不清楚",
    "bearish regime": "熊市/下行状态",
    "bullish regime": "牛市/上行状态",
    "volatile sideways regime": "高波动横盘状态",
    "quiet sideways regime": "低波动横盘状态",
    "moderate drawdown": "中等回撤",
    "mild drawdown": "轻微回撤",
    "severe drawdown": "严重回撤",
    "little drawdown": "回撤很小",
    "built-in AIOpsLab incident": "内置 AIOpsLab 事故",
    "synthetic fallback incident": "合成备用事故",
    "external log replay": "外部日志回放",
    "unknown provenance": "未知来源",
    "hotel-reservation application": "hotel-reservation 应用",
    "astronomy-shop application": "astronomy-shop 应用",
    "social-network application": "social-network 应用",
    "unknown application": "未知应用",
    "user/account service role": "用户/账号服务角色",
    "text/content service role": "文本/内容服务角色",
    "storage service role": "存储服务角色",
    "other service role": "其他服务角色",
    "frontend service role": "前端服务角色",
    "database service role": "数据库服务角色",
    "unknown service role": "未知服务角色",
    "scale-to-zero": "副本缩为零",
    "port misconfiguration": "端口配置错误",
    "authentication revocation": "认证撤销",
    "other incident type": "其他事故类型",
    "memory leak": "内存泄漏",
    "network delay": "网络延迟",
    "unknown fault family": "未知故障族",
    "authentication fault context": "认证故障上下文",
    "port misconfiguration context": "端口配置错误上下文",
    "scale-to-zero context": "副本缩为零上下文",
    "resource saturation context": "资源饱和上下文",
    "unclear incident context": "事故上下文不清楚",
    "unknown fault context": "未知故障上下文",
    "speed leads queue": "车速领先队列变化",
    "queue leads speed": "队列领先车速变化",
    "event creates lower x0 than baseline": "事件窗口水压低于基线",
    "event creates higher x0 than baseline": "事件窗口水压高于基线",
    "event effect is mixed": "事件影响混合",
}


METADATA_ONLY_TASKS = {
    "aiops_official_app_context",
    "aiops_official_case_provenance_context",
    "aiops_official_service_role_context",
    "aiops_official_fault_family_detail_context",
    "aiops_official_fault_context",
}


def load_rows() -> list[dict]:
    with RAW.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fnum(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "NA"
    if isinstance(value, int):
        return str(value)
    if not math.isfinite(float(value)):
        return str(value)
    if abs(float(value)) >= 10000:
        return f"{float(value):,.2f}"
    return f"{float(value):.{digits}f}"


def label_zh(label: str) -> str:
    return OPTION_ZH.get(label, label)


def phrase_en(label: str) -> str:
    mapping = {
        "early": "the early part of the window",
        "middle": "the middle part of the window",
        "late": "the late part of the window",
        "no pronounced spike": "no pronounced spike",
        "no clear extremum": "no clear extremum",
        "first half higher": "the first half is higher",
        "second half higher": "the second half is higher",
        "similar halves": "the two halves are similar",
        "similar thirds": "the three thirds are similar",
        "upward": "an upward trend",
        "downward": "a downward trend",
        "flat": "a flat trend",
        "mixed": "a mixed trend",
        "short cycle": "a short cycle",
        "medium cycle": "a medium cycle",
        "long cycle": "a long cycle",
        "no clear cycle": "no clear cycle",
        "no clear lead": "no clear lead-lag relationship",
        "unclear relation": "an unclear relation",
        "x1": "x1",
        "x2": "x2",
        "both similar": "both companion signals are similarly related",
        "both weak": "both companion signals are weakly related",
    }
    return mapping.get(label, natural_option_en(label))


def phrase_zh(label: str) -> str:
    mapping = {
        "early": "早期",
        "middle": "中期",
        "late": "后期",
        "no pronounced spike": "没有明显尖峰",
        "no clear extremum": "没有清晰极值",
        "first half higher": "前半段更高",
        "second half higher": "后半段更高",
        "similar halves": "前后两半相近",
        "similar thirds": "三段相近",
        "upward": "上升趋势",
        "downward": "下降趋势",
        "flat": "基本平稳",
        "mixed": "混合变化",
        "short cycle": "短周期",
        "medium cycle": "中等周期",
        "long cycle": "长周期",
        "no clear cycle": "没有明显周期",
        "no clear lead": "没有清晰领先关系",
        "unclear relation": "关系不清楚",
    }
    return mapping.get(label, label_zh(label))


def window_horizon(row: dict) -> int | None:
    slots = row.get("support_slots") or {}
    if slots.get("horizon"):
        return int(slots["horizon"])
    start = slots.get("window_start")
    end = slots.get("window_end")
    if isinstance(start, int) and isinstance(end, int) and end > start:
        return end - start
    return None


def ticker_from_id(row: dict) -> str:
    if "::finrl_broad::" not in row["id"]:
        return ""
    return row["id"].split("::finrl_broad::", 1)[1].split("::", 1)[0]


def date_range_zh(row: dict) -> str:
    slots = row.get("support_slots") or {}
    start = slots.get("date_start")
    end = slots.get("date_end")
    return f"{start} 至 {end}" if start and end else ""


def position_phrase_en(index: int | None, horizon: int | None) -> str:
    if index is None or horizon is None:
        return "the relevant part of the window"
    third = horizon / 3
    if index < third:
        return "the early third of the window"
    if index < 2 * third:
        return "the middle third of the window"
    return "the late third of the window"


def position_phrase_zh(index: int | None, horizon: int | None) -> str:
    if index is None or horizon is None:
        return "窗口中的相关位置"
    third = horizon / 3
    if index < third:
        return "窗口前段"
    if index < 2 * third:
        return "窗口中段"
    return "窗口后段"


def contextual_option_zh(row: dict, text: str) -> str | None:
    task = row["task_family"]
    source = row["merge_source_name"]
    if "grid_cross_variable" in task:
        return {"x1": "总需求", "x2": "发电裕度"}.get(text)
    if "grid_temporal_lead_lag" in task:
        mapping = {
            "x0 leads x1": "最大线路负载压力领先总需求",
            "x1 leads x0": "总需求领先最大线路负载压力",
            "no clear lead": "同步变化，没有稳定领先方",
            "unclear relation": "相关性太弱，无法判断先后",
        }
        return mapping.get(text)
    if "traffic_speed_queue_lead_lag" in task:
        mapping = {
            "speed leads queue": "车速变化领先排队变化",
            "queue leads speed": "排队变化领先车速变化",
            "no clear lead": "没有稳定的方向性领先",
            "unclear relation": "相关性低于可用阈值",
        }
        return mapping.get(text)
    if "grid_counterfactual_peak_stress" in task:
        mapping = {
            "larger upward peak": "断线后压力更高",
            "larger downward dip": "断线后压力更低",
            "no material change": "断线前后压力基本相同",
        }
        return mapping.get(text)
    if "leak_counterfactual_pressure" in task:
        mapping = {
            "mixed effect": "窗口内变化方向不一致",
            "no material pressure change": "平均水压基本相同",
        }
        return mapping.get(text)
    if "counterfactual_event_gap" in task:
        mapping = {
            "event has similar x0 to baseline": "事件窗口水压与基线相近",
            "event creates lower x0 than baseline": "事件窗口水压低于基线",
            "event creates higher x0 than baseline": "事件窗口水压高于基线",
        }
        return mapping.get(text)
    if source == "finrl_scaled" and text in {"x1", "x2"}:
        return {"x1": "市场背景指标", "x2": "交易量"}.get(text)
    return None


def option_dict(row: dict, option: str) -> dict:
    if "." in option:
        letter, text = option.split(".", 1)
        letter = letter.strip()
        text = text.strip()
    else:
        letter = ""
        text = option.strip()
    return {
        "letter": letter,
        "en": natural_option_en(text),
        "zh": contextual_option_zh(row, text) or label_zh(text),
        "raw": option,
    }


def natural_option_en(text: str) -> str:
    mapping = {
        "x1": "x1 is the stronger companion signal",
        "x2": "x2 is the stronger companion signal",
        "both similar": "both companion signals are similarly related",
        "both weak": "neither companion signal is strongly related",
        "x0 leads x1": "maximum line-loading stress leads total demand",
        "x1 leads x0": "total demand leads maximum line-loading stress",
        "speed leads queue": "speed changes lead queue changes",
        "queue leads speed": "queue changes lead speed changes",
        "no clear lead": "there is no stable timing lead",
        "unclear relation": "correlation is too weak to use",
        "larger upward peak": "the intervention raises the stress",
        "larger downward dip": "the intervention lowers the stress",
        "no material change": "there is no material change",
        "higher queue under adaptive signal": "adaptive signal has the higher mean queue",
        "lower queue under adaptive signal": "adaptive signal has the lower mean queue",
        "no material queue change": "both policies have about the same queue",
        "mixed effect": "the policy effect is mixed",
        "no material pressure change": "there is no material pressure change",
        "event has similar x0 to baseline": "event-window x0 is similar to baseline",
        "event creates lower x0 than baseline": "event-window pressure is lower than baseline",
        "event creates higher x0 than baseline": "event-window pressure is higher than baseline",
        "event effect is mixed": "the event effect is mixed",
    }
    return mapping.get(text, text)


def source_context(row: dict) -> tuple[str, str, list[str], list[str]]:
    source = row["merge_source_name"]
    if source == "grid2op":
        return (
            "A Grid2Op operator is reviewing a power-grid time-series window. x0 is maximum line-loading stress, x1 is total demand, and x2 is generation margin. Stress above 1.0 indicates overload risk.",
            "一名 Grid2Op 电网调度员正在查看电网时序窗口。x0 是最大线路负载压力，x1 是总需求，x2 是发电裕度。压力超过 1.0 表示过载风险。",
            ["x0 max line-loading stress", "x1 total demand", "x2 generation margin"],
            ["x0 最大线路负载压力", "x1 总需求", "x2 发电裕度"],
        )
    if source == "citylearn":
        horizon = window_horizon(row)
        horizon_text_en = f"{horizon}-step " if horizon else ""
        horizon_text_zh = f"{horizon} 步" if horizon else "固定长度"
        return (
            f"A building energy controller is reviewing a {horizon_text_en}CityLearn window. x0 is total building electricity demand. The window is divided into early, middle, and late thirds when a location option is used.",
            f"建筑能耗控制器正在查看一个 {horizon_text_zh}的 CityLearn 窗口。x0 是建筑总用电需求。若问题使用早期/中期/后期选项，则按时间顺序把窗口三等分。",
            ["x0 total building electricity demand", "x1 weather/demand context", "x2 solar/auxiliary context"],
            ["x0 建筑总用电需求", "x1 天气/需求上下文", "x2 太阳能/辅助上下文"],
        )
    if source == "finrl_scaled":
        ticker = ticker_from_id(row)
        range_zh = date_range_zh(row)
        range_en = date_range_en(row)
        return (
            f"A market analyst is reviewing a historical market window for {ticker}{range_en}. x0 is the historical price series for {ticker}; return questions use returns computed from that price series. x1 is a market background indicator, and x2 is trading volume. Location questions divide the window into early, middle, and late thirds.",
            f"市场分析师正在查看 {ticker}{(' 在 ' + range_zh + ' 期间') if range_zh else ''}的历史行情窗口。x0 是 {ticker} 的历史价格序列；收益率问题使用从该价格序列计算出的收益。x1 是市场背景指标，x2 是交易量。位置类问题按时间顺序把窗口分为早期、中期和后期三段。",
            [f"x0 {ticker} historical price series", "x1 market background indicator", "x2 trading volume"],
            [f"x0 {ticker} 历史价格序列", "x1 市场背景指标", "x2 交易量"],
        )
    if source == "water":
        return (
            "A water-network operator is reviewing a service window. x0 is water pressure, x1 is pipe flow, and x2 is tank storage. Low pressure can indicate service risk.",
            "供水网络运维人员正在查看服务窗口。x0 是水压，x1 是管道流量，x2 是水箱蓄水量。低水压可能表示供水风险。",
            ["x0 water pressure", "x1 pipe flow", "x2 tank storage"],
            ["x0 水压", "x1 管道流量", "x2 水箱蓄水量"],
        )
    if source == "traffic":
        return (
            "A traffic engineer is reviewing a traffic-system window with mean speed, queue length, and occupancy/control context recorded as aligned time-series signals. Lower queue and higher speed usually indicate better traffic flow.",
            "交通工程师正在查看一段交通系统窗口，其中平均车速、排队长度、占有率/控制上下文都作为对齐的时间序列记录。更低队列和更高速度通常表示交通流更好。",
            ["x0 mean speed", "x1 queue length", "x2 occupancy/control context"],
            ["x0 平均车速", "x1 队列长度", "x2 占有率或控制上下文"],
        )
    return (
        "An SRE is reviewing an AIOpsLab microservice telemetry window. x0 is service CPU load, x1 is memory working set, x2 is network receive rate, and x3 is network transmit rate.",
        "一名 SRE 正在查看 AIOpsLab 微服务遥测窗口。x0 是服务 CPU 负载，x1 是内存工作集，x2 是网络接收速率，x3 是网络发送速率。",
        ["x0 CPU load", "x1 memory working set", "x2 network receive", "x3 network transmit"],
        ["x0 CPU 负载", "x1 内存工作集", "x2 网络接收", "x3 网络发送"],
    )


def date_range(row: dict) -> str:
    slots = row.get("support_slots") or {}
    start = slots.get("date_start")
    end = slots.get("date_end")
    return f" during {start} to {end}" if start and end else ""


def date_range_en(row: dict) -> str:
    slots = row.get("support_slots") or {}
    start = slots.get("date_start")
    end = slots.get("date_end")
    return f" from {start} to {end}" if start and end else ""


def rewrite_case(row: dict) -> dict:
    slots = row.get("support_slots") or {}
    task = row["task_family"]
    base_scene_en, base_scene_zh, vars_en, vars_zh = source_context(row)
    scene_en = base_scene_en
    scene_zh = base_scene_zh
    status = "candidate"
    exclude_reason = None

    if task in METADATA_ONLY_TASKS:
        status = "exclude_metadata_only"
        exclude_reason = "This AIOpsLab row requires official metadata rather than numeric telemetry alone."
        scene_en += " This row asks for official case metadata, so it is not a pure time-series QA example unless metadata is provided."
        scene_zh += " 这一行询问官方 case 元数据；如果不提供 metadata，它不是纯时间序列 QA 样本。"

    question_en, question_zh, evidence_en, evidence_zh = generic_rewrite(row, scene_en, scene_zh)

    return {
        "id": row["id"],
        "split": row.get("split"),
        "source": row["merge_source_name"],
        "task_family": task,
        "natural_status": status,
        "exclude_reason": exclude_reason,
        "scene_en": scene_en,
        "scene_zh": scene_zh,
        "variables_en": vars_en,
        "variables_zh": vars_zh,
        "question_en": question_en,
        "question_zh": question_zh,
        "options": [option_dict(row, opt) for opt in row["options"]],
        "gold_answer": row["answer"],
        "gold_answer_label": row["answer_label"],
        "gold_answer_zh": label_zh(row["answer_label"]),
        "evidence_en": evidence_en,
        "evidence_zh": evidence_zh,
        "support_slots": slots,
        "original_question": row["question"],
        "original_options": row["options"],
        "original_oracle_evidence": row["oracle_evidence_caption"],
    }


def generic_rewrite(row: dict, scene_en: str, scene_zh: str) -> tuple[str, str, str, str]:
    task = row["task_family"]
    slots = row.get("support_slots") or {}
    source = row["merge_source_name"]
    label = row["answer_label"]
    label_cn = label_zh(label)

    if "counterfactual_peak_stress" in task:
        scene_extra_en = (
            f" The line disconnection occurred at global step {slots.get('intervention_step')}; "
            f"this local plot covers global steps {slots.get('segment_start')} to {slots.get('segment_end')}. "
            "In this counterfactual case, x0 is intervention-minus-factual maximum line-loading stress; positive values mean the disconnection raises stress."
        )
        scene_extra_zh = (
            f" 断线发生在全局第 {slots.get('intervention_step')} 步；这张局部图覆盖全局第 "
            f"{slots.get('segment_start')} 到 {slots.get('segment_end')} 步。在这个反事实样本中，x0 表示“干预后最大线路负载压力减去事实运行压力”；x0 为正表示断线后压力更高。"
        )
        row["_scene_extra_en"] = scene_extra_en
        row["_scene_extra_zh"] = scene_extra_zh
        return (
            "In this post-event window, what is the main effect of disconnecting the line on maximum line-loading stress?",
            "在这个事件后窗口里，断开线路对最大线路负载压力的主要影响是什么？",
            f"The intervention-minus-factual stress difference ranges from {fnum(slots.get('min_x0_diff'))} to {fnum(slots.get('max_x0_diff'))}, so the effect is {natural_option_en(label)}.",
            f"干预后与事实运行的压力差值范围为 {fnum(slots.get('min_x0_diff'))} 到 {fnum(slots.get('max_x0_diff'))}，因此判断为：{contextual_option_zh(row, label) or label_cn}。",
        )

    if "cross_variable" in task:
        return (
            "For a quick overload review, should the operator look more closely at total demand or generation margin?",
            "做快速过载复盘时，调度员更应该关注总需求还是发电裕度？",
            f"The correlation with line-loading stress is {fnum(slots.get('corr_x1'))} for total demand and {fnum(slots.get('corr_x2'))} for generation margin; the stronger companion is {phrase_en(label)}.",
            f"总需求与线路负载压力的相关系数为 {fnum(slots.get('corr_x1'))}，发电裕度与线路负载压力的相关系数为 {fnum(slots.get('corr_x2'))}；更强的伴随信号是 {label_cn}。",
        )

    if "temporal_lead_lag" in task or "lead_lag" in task:
        if source == "traffic":
            signal_pair_en = "speed changes and queue-length changes"
            signal_pair_zh = "车速变化和排队长度变化"
            extra_en = " For this timing review, negative lag means speed tends to move earlier, and positive lag means queue length tends to move earlier. Absolute correlation strength below 0.35 is treated as too weak to use; if the best lag improves on the synchronous absolute-correlation strength by less than 0.05, the timing order is treated as not stable."
            extra_zh = " 对这个先后关系复盘来说，负滞后表示车速更早变化，正滞后表示排队长度更早变化。绝对相关强度低于 0.35 时视为太弱；若最强滞后相对同步绝对相关强度的提升小于 0.05，则视为没有稳定的方向性领先。"
        else:
            signal_pair_en = "total demand and maximum line-loading stress"
            signal_pair_zh = "总需求和最大线路负载压力"
            extra_en = " This question compares only x1 total demand and x0 line-loading stress. Lag 0 means synchronous movement; if the strongest relation is at lag 0, choose the synchronous/no-stable-lead option rather than either signal leading."
            extra_zh = " 本题只比较 x1 总需求和 x0 最大线路负载压力。滞后 0 表示同步变化；如果最强关系出现在滞后 0，则选择同步/无稳定领先方，而不是判定某个信号领先。"
        row["_scene_extra_en"] = extra_en
        row["_scene_extra_zh"] = extra_zh
        zero_lag = slots.get("zero_lag_corr")
        if zero_lag is None:
            evidence_en = (
                f"The strongest tested lag is {slots.get('best_lag')} with correlation "
                f"{fnum(slots.get('best_lag_corr'))}; this supports {natural_option_en(label)}."
            )
            evidence_zh = (
                f"最强候选滞后为 {slots.get('best_lag')}，相关系数为 {fnum(slots.get('best_lag_corr'))}。"
                f"因此判断为：{contextual_option_zh(row, label) or phrase_zh(label)}。"
            )
        elif source == "traffic":
            improvement = abs(abs(float(slots.get("best_lag_corr", 0))) - abs(float(zero_lag)))
            evidence_en = (
                f"The strongest lag is {slots.get('best_lag')} with correlation {fnum(slots.get('best_lag_corr'))}, "
                f"while the synchronous correlation is {fnum(zero_lag)}. The absolute-correlation strength improves by only {fnum(improvement)}, "
                f"below the 0.05 stability margin, so the traffic review should choose {natural_option_en(label)}."
            )
            evidence_zh = (
                f"最强滞后为 {slots.get('best_lag')}，相关系数为 {fnum(slots.get('best_lag_corr'))}；"
                f"同步相关系数为 {fnum(zero_lag)}。绝对相关强度只提升了 {fnum(improvement)}，低于 0.05 的稳定性余量，"
                f"因此交通复盘应选择：{contextual_option_zh(row, label) or phrase_zh(label)}。"
            )
        else:
            evidence_en = (
                f"The strongest tested lag is {slots.get('best_lag')} with correlation "
                f"{fnum(slots.get('best_lag_corr'))}; zero-lag correlation is {fnum(zero_lag)}. "
                f"This supports {natural_option_en(label)}."
            )
            evidence_zh = (
                f"最强候选滞后为 {slots.get('best_lag')}，相关系数为 {fnum(slots.get('best_lag_corr'))}；"
                f"零滞后相关系数为 {fnum(zero_lag)}。因此判断为："
                f"{contextual_option_zh(row, label) or phrase_zh(label)}。"
            )
        return (
            f"Do {signal_pair_en} show a clear timing order in this window?",
            f"{signal_pair_zh}之间是否表现出清晰的先后关系？",
            evidence_en,
            evidence_zh,
        )

    if "trend" in task:
        if source == "grid2op":
            return (
                "Is line-loading stress rising, falling, or staying roughly stable over this grid window?",
                "这个电网窗口中的线路负载压力是在上升、下降，还是大致稳定？",
                f"Line-loading stress starts near {fnum(slots.get('start_value'))} and ends near {fnum(slots.get('end_value'))}; the net change is {fnum(slots.get('delta'))} versus variability {fnum(slots.get('std'))}, supporting {phrase_en(label)}.",
                f"线路负载压力起点约 {fnum(slots.get('start_value'))}，终点约 {fnum(slots.get('end_value'))}；净变化为 {fnum(slots.get('delta'))}，而波动尺度为 {fnum(slots.get('std'))}，因此判断为 {phrase_zh(label)}。",
            )
        if source == "traffic":
            return (
                "Is traffic speed improving, degrading, or staying roughly stable over this window?",
                "这个交通窗口中的车速是在改善、恶化，还是大致稳定？",
                f"Mean speed starts near {fnum(slots.get('start_value'))} and ends near {fnum(slots.get('end_value'))}, with variability {fnum(slots.get('std'))}; the trend is {phrase_en(label)}.",
                f"平均车速起点约 {fnum(slots.get('start_value'))}，终点约 {fnum(slots.get('end_value'))}，波动尺度为 {fnum(slots.get('std'))}；整体趋势是 {phrase_zh(label)}。",
            )
        return (
            "How does the main monitored signal behave over this window?",
            "这个窗口中主要监测信号整体如何变化？",
            row["oracle_evidence_caption"],
            row["oracle_evidence_caption"],
        )

    if "volatility" in task:
        signal = "the monitored signal"
        signal_cn = "监测信号"
        if source == "citylearn":
            signal = "building electricity demand"
            signal_cn = "建筑用电需求"
        elif source == "finrl_scaled":
            signal = "asset returns"
            signal_cn = "资产收益率"
        elif source == "grid2op":
            signal = "total demand"
            signal_cn = "总需求"
        elif source == "traffic":
            signal = "queue length"
            signal_cn = "排队长度"
        elif source == "water":
            signal = "pipe flow"
            signal_cn = "管道流量"
        elif source == "aiopslab_official_v3":
            signal = "network receive rate"
            signal_cn = "网络接收速率"
        if source == "finrl_scaled":
            role_en = "market analyst"
            role_zh = "市场分析师"
        else:
            role_en = "operator"
            role_zh = "运维人员"
        return (
            f"Which part of the window should the {role_en} treat as the most variable for {signal}?",
            f"{role_zh}应该把窗口的哪一段视为{signal_cn}波动最大的部分？",
            f"The window is split into three equal time sections, and the standard-deviation comparison across those sections selects {phrase_en(label)}.",
            f"窗口按时间三等分后比较标准差，结果选择{phrase_zh(label)}。",
        )

    if "window_total_load" in task or "window_return" in task or "window_speed" in task or "window_memory" in task:
        if source == "citylearn":
            return (
                "When should the controller plan for higher average electricity demand?",
                "控制器应该在哪一段为更高的平均用电需求做准备？",
                f"The first-half mean is {fnum(slots.get('first_mean'))}, and the second-half mean is {fnum(slots.get('second_mean'))}.",
                f"前半段均值为 {fnum(slots.get('first_mean'))}，后半段均值为 {fnum(slots.get('second_mean'))}。",
            )
        if source == "grid2op":
            return (
                "Which half of this grid window has the higher average demand?",
                "这个电网窗口中哪一半的平均总需求更高？",
                f"The first-half demand mean is {fnum(slots.get('first_mean'))}, and the second-half mean is {fnum(slots.get('second_mean'))}.",
                f"前半段总需求均值为 {fnum(slots.get('first_mean'))}，后半段均值为 {fnum(slots.get('second_mean'))}。",
            )
        if source == "finrl_scaled":
            return (
                "Which half of the market window performed better?",
                "这个市场窗口中哪一半表现更好？",
                f"The first-half return is {float(slots.get('first_half_return', 0)) * 100:.2f}%, and the second-half return is {float(slots.get('second_half_return', 0)) * 100:.2f}%.",
                f"前半段收益率为 {float(slots.get('first_half_return', 0)) * 100:.2f}%，后半段收益率为 {float(slots.get('second_half_return', 0)) * 100:.2f}%。",
            )
        if source == "traffic":
            return (
                "During which half of the window is traffic moving faster on average?",
                "这个窗口中哪一半的平均车速更高？",
                f"The first-half mean speed is {fnum(slots.get('first_mean'))}, and the second-half mean speed is {fnum(slots.get('second_mean'))}.",
                f"前半段平均车速为 {fnum(slots.get('first_mean'))}，后半段平均车速为 {fnum(slots.get('second_mean'))}。",
            )
        if source == "aiopslab_official_v3":
            return (
                "Using a 5% relative-difference rule, does the service memory footprint stay about the same, or is one half of the incident window heavier?",
                "按 5% 相对差异规则，这个事故窗口中的服务内存占用是前后相近，还是某一半更重？",
                f"Rule: if the two half-window means differ by less than 5% of the larger mean, treat them as similar. The first-half memory mean is {fnum(slots.get('first_mean'))}, and the second-half mean is {fnum(slots.get('second_mean'))}.",
                f"规则：前后两半均值差小于较大均值的 5% 时，视为前后相近。前半段内存均值为 {fnum(slots.get('first_mean'))}，后半段均值为 {fnum(slots.get('second_mean'))}。",
            )
        return (
            "Does the monitored pressure ease or build up over this incident window?",
            "这个事故窗口中，监测压力是在缓解还是在累积？",
            f"The first-half mean is {fnum(slots.get('first_mean'))}, and the second-half mean is {fnum(slots.get('second_mean'))}.",
            f"前半段均值为 {fnum(slots.get('first_mean'))}，后半段均值为 {fnum(slots.get('second_mean'))}。",
        )

    if "anomaly" in task or "extrema" in task or "speed_extrema" in task:
        noun = "event"
        noun_cn = "事件"
        if source == "finrl_scaled":
            noun = "price or volume move"
            noun_cn = "价格或成交量异动"
        elif source == "citylearn":
            noun = "demand spike"
            noun_cn = "用电需求尖峰"
        elif source == "traffic":
            noun = "speed minimum"
            noun_cn = "最低车速点"
        if source == "citylearn":
            if "event_abs_z" in slots:
                if label == "no pronounced spike":
                    question_en = "Does the building-demand detector find a pronounced isolated spike in this window, and if so where?"
                    question_zh = "尖峰检测器是否在这个窗口发现明显的建筑用电需求孤立尖峰；如果有，它大致位于哪一段？"
                else:
                    question_en = "Where does the strongest isolated building-demand spike occur after splitting this window into early, middle, and late thirds?"
                    question_zh = "把这个窗口按时间分成早期、中期和后期后，最明显的建筑用电需求孤立尖峰出现在什么位置？"
                return (
                    question_en,
                    question_zh,
                    f"The demand-spike detector uses absolute z-score 3 as the pronounced-spike cutoff. The strongest candidate has absolute z-score {fnum(slots.get('event_abs_z'))} at {position_phrase_en(slots.get('event_index'), slots.get('horizon'))}, supporting {phrase_en(label)}.",
                    f"尖峰检测器使用绝对 z 分数 3 作为明显尖峰阈值；最强候选尖峰的绝对 z 分数为 {fnum(slots.get('event_abs_z'))}，位置在{position_phrase_zh(slots.get('event_index'), slots.get('horizon'))}，因此判断为{phrase_zh(label)}。",
                )
            return (
                "Where is the highest building-demand point after splitting this window into early, middle, and late thirds?",
                "把这个窗口按时间分成早期、中期和后期后，最高的建筑用电需求点出现在什么位置？",
                f"The peak demand is about {fnum(slots.get('extrema_value'))} and falls in {position_phrase_en(slots.get('extrema_index'), slots.get('horizon'))}, supporting {phrase_en(label)}.",
                f"最高需求约为 {fnum(slots.get('extrema_value'))}，位置在{position_phrase_zh(slots.get('extrema_index'), slots.get('horizon'))}，因此判断为{phrase_zh(label)}。",
            )
        if source == "finrl_scaled":
            ticker = ticker_from_id(row)
            if "event_abs_z" in slots:
                return (
                    f"Where is the largest {ticker} volume spike after splitting this market window into early, middle, and late thirds?",
                    f"把这个市场窗口按时间分成早期、中期和后期后，{ticker} 最大的成交量尖峰出现在什么位置？",
                    f"The volume-spike detector places it in {position_phrase_en(slots.get('event_index'), slots.get('horizon'))} with robust z-score {fnum(slots.get('event_abs_z'))}{date_range(row)}, supporting {phrase_en(label)}.",
                    f"成交量尖峰检测器把它定位在{position_phrase_zh(slots.get('event_index'), slots.get('horizon'))}，稳健 z 分数为 {fnum(slots.get('event_abs_z'))}，因此判断为{phrase_zh(label)}。",
                )
            return (
                f"Where does {ticker}'s historical price series reach its highest point in this window?",
                f"{ticker} 的历史价格序列在这个窗口中最高点大致出现在什么位置？",
                f"The historical price series reaches its highest point in {position_phrase_en(slots.get('extrema_index'), slots.get('horizon'))} with value about {fnum(slots.get('extrema_value'))}{date_range(row)}, supporting {phrase_en(label)}.",
                f"历史价格序列最高点位于{position_phrase_zh(slots.get('extrema_index'), slots.get('horizon'))}，数值约 {fnum(slots.get('extrema_value'))}，因此判断为{phrase_zh(label)}。",
            )
        if source == "traffic":
            return (
                "Where does the lowest mean speed occur after splitting this traffic window into early, middle, and late thirds?",
                "把这个交通窗口按时间分成早期、中期和后期后，最低平均车速出现在什么位置？",
                f"The speed minimum is about {fnum(slots.get('extrema_value'))} and falls in {phrase_en(label)}.",
                f"最低平均车速约为 {fnum(slots.get('extrema_value'))}，位置在{phrase_zh(label)}。",
            )
        return (
            f"Where does the most important {noun} occur in this window?",
            f"这个窗口中最重要的{noun_cn}出现在什么位置？",
            row["oracle_evidence_caption"],
            row["oracle_evidence_caption"],
        )

    if "drawdown" in task:
        ticker = ticker_from_id(row)
        return (
            "Using the stated drawdown bands, how severe is this price drawdown?",
            f"按照回撤分档规则，{ticker} 在这个窗口中的价格回撤应归为哪一类？",
            f"Drawdown bands are: little below 5%, mild 5-15%, moderate 15-30%, severe above 30%. The maximum drawdown is {abs(float(slots.get('max_drawdown', 0))) * 100:.2f}%{date_range(row)}.",
            f"回撤分档规则为：小于 5% 为回撤很小，5% 到 15% 为轻微回撤，15% 到 30% 为中等回撤，超过 30% 为严重回撤。该窗口最大回撤为 {abs(float(slots.get('max_drawdown', 0))) * 100:.2f}%。",
        )

    if "market_regime" in task:
        ticker = ticker_from_id(row)
        return (
            "Using total return first and volatility as tie-breaker, what market regime best describes this asset window?",
            f"先看总收益、再用波动率辅助判断，{ticker} 在这段时间最符合哪种市场状态？",
            f"Regime rule: total return >= 5% is bullish, <= -5% is bearish; otherwise it is sideways, with return volatility >= 0.03 classified as volatile sideways and below 0.03 as quiet sideways. Total return is {float(slots.get('total_return', 0)) * 100:.2f}% and return volatility is {fnum(slots.get('return_std'), 3)}.",
            f"市场状态规则为：总收益率 >= 5% 归为牛市/上行，<= -5% 归为熊市/下行；介于其间视为横盘，其中收益波动率 >= 0.03 为高波动横盘，低于 0.03 为低波动横盘。该窗口总收益率为 {float(slots.get('total_return', 0)) * 100:.2f}%，收益波动率为 {fnum(slots.get('return_std'), 3)}。",
        )

    if "domain_demand_context" in task:
        return (
            "Using the stated demand-pressure bands, what state should the building controller assume for this window?",
            "按照需求压力分档规则，建筑控制器应把这个窗口视为什么需求压力状态？",
            f"Demand-pressure rule: high if mean load is at least 8 or peak load is at least 16, low if mean load is below 3 and peak load below 8, otherwise moderate. Mean load is {fnum(slots.get('x0_mean'))}, peak load is {fnum(slots.get('x0_peak'))}, and solar/context mean is {fnum(slots.get('x2_mean'))}.",
            f"需求压力规则为：平均负载至少 8 或峰值负载至少 16 时为高需求压力；平均负载低于 3 且峰值负载低于 8 时为低需求压力；否则为中等需求压力。本窗口平均负载为 {fnum(slots.get('x0_mean'))}，峰值负载为 {fnum(slots.get('x0_peak'))}，太阳能/上下文均值为 {fnum(slots.get('x2_mean'))}。",
        )

    if "periodicity" in task:
        if source == "traffic":
            signal_en = "traffic speed"
            signal_zh = "车速"
        elif source == "water":
            signal_en = "water pressure"
            signal_zh = "水压"
        else:
            signal_en = "the monitored signal"
            signal_zh = "监测信号"
        return (
            f"Using the stated autocorrelation bands, what operating-cycle pattern does {signal_en} show?",
            f"按照自相关分档规则，{signal_zh}显示出哪种运行周期模式？",
            f"Cycle rule: score below 0.30 means no clear cycle; otherwise lag 1-10 is short, 11-40 is medium, and above 40 is long. The strongest autocorrelation peak is at lag {slots.get('best_period')} with score {fnum(slots.get('period_score'), 3)}, supporting {phrase_en(label)}.",
            f"周期规则为：自相关分数低于 0.30 表示没有明显周期；否则滞后 1 到 10 为短周期，11 到 40 为中等周期，超过 40 为长周期。最强自相关峰在滞后 {slots.get('best_period')}，分数为 {fnum(slots.get('period_score'), 3)}，因此判断为{phrase_zh(label)}。",
        )

    if "signal_counterfactual_queue" in task:
        return (
            "Compared with the fixed-signal baseline, did the adaptive signal policy improve queueing?",
            "与固定信号基线相比，自适应信号策略是否改善了排队？",
            f"The adaptive-signal mean queue is {fnum(slots.get('factual_mean'))}, compared with fixed baseline {fnum(slots.get('counterfactual_mean'))}.",
            f"自适应信号平均队列为 {fnum(slots.get('factual_mean'))}，固定基线为 {fnum(slots.get('counterfactual_mean'))}。",
        )

    if "leak_counterfactual_pressure" in task:
        return (
            "Compared with the no-leak baseline, is average pressure lower, higher, or about the same?",
            "与无漏水基线相比，漏水场景下该窗口的平均水压是更低、更高，还是基本相同？",
            f"Leak-scenario mean pressure is {fnum(slots.get('factual_mean'))}, compared with no-leak baseline {fnum(slots.get('counterfactual_mean'))}.",
            f"漏水场景平均水压为 {fnum(slots.get('factual_mean'))}，无漏水基线为 {fnum(slots.get('counterfactual_mean'))}。",
        )

    if "counterfactual_event_gap" in task:
        return (
            "Inside the event window, is water pressure meaningfully different from the matched baseline?",
            "在事件窗口内，事实水压与匹配基线相比是否有明显差异？",
            f"Factual event-window pressure mean is {fnum(slots.get('event_factual_mean'))}, baseline mean is {fnum(slots.get('event_baseline_mean'))}, and the gap is {fnum(slots.get('event_gap'))}.",
            f"事实事件窗口水压均值为 {fnum(slots.get('event_factual_mean'))}，基线均值为 {fnum(slots.get('event_baseline_mean'))}，差值为 {fnum(slots.get('event_gap'))}。",
        )

    if "event_recovery" in task:
        return (
            "Using the stated phase-mean rule, what water-pressure state follows the event?",
            "按照事件前、中、后三阶段均值规则，事件后的水压状态最符合哪一种判断？",
            f"Recovery rule: any post-event mean above the pre-event mean is overshoot; equal-to or below-but-returning toward pre-event level is recovery; below pre-event while still stressed is persistent pressure stress. Pre-event mean is {fnum(slots.get('pre_mean'))}, event mean is {fnum(slots.get('event_mean'))}, and post-event mean is {fnum(slots.get('post_mean'))}.",
            f"恢复规则为：事件后均值只要高于事件前均值，就视为水压过冲；等于或低于但回到事件前水平附近时视为恢复；低于事件前且仍偏低视为持续承压。事件前均值为 {fnum(slots.get('pre_mean'))}，事件中均值为 {fnum(slots.get('event_mean'))}，事件后均值为 {fnum(slots.get('post_mean'))}。",
        )

    if "domain_resilience" in task:
        return (
            "Using the stated service-state rule, which water-network state best matches this window?",
            "按照供水服务状态规则，这个供水网络窗口最符合哪种服务状态？",
            f"Service-state rule: minimum pressure below 50 suggests low-pressure risk; stable pressure above that level with no leak-stress evidence suggests stable water service. Mean pressure is {fnum(slots.get('mean_pressure'))}, minimum pressure is {fnum(slots.get('min_pressure'))}, and mean flow is {fnum(slots.get('mean_flow'))}.",
            f"服务状态规则为：最低水压低于 50 表示低水压风险；最低水压高于该下限且没有漏水压力证据时，视为稳定供水服务。本窗口平均水压为 {fnum(slots.get('mean_pressure'))}，最低水压为 {fnum(slots.get('min_pressure'))}，平均流量为 {fnum(slots.get('mean_flow'))}。",
        )

    if "combined_stress" in task:
        severe_low = slots.get("x0_event_indicator")
        return (
            "Using the stated stress-score rule, what operating state is most plausible for this water-service window?",
            "按照综合压力评分规则，这个供水服务窗口最可能处于哪种运行状态？",
            f"Stress rule: scores below -50 with a mid-window event indicate moderate combined stress when the severe-low-pressure flag is false; if that flag is true, classify as critical combined stress. The combined stress score is {fnum(slots.get('combined_stress_score'))}, the event timing label is {slots.get('event_label')}, and the severe-low-pressure flag is {bool(severe_low)}.",
            f"综合压力规则为：评分低于 -50 且窗口中段出现事件时，如果严重低压标记为 false，则归为中等综合压力；如果严重低压标记为 true，则归为严重综合压力。本窗口综合压力分数为 {fnum(slots.get('combined_stress_score'))}，事件位于{phrase_zh(slots.get('event_label'))}，严重低压标记为 {str(bool(severe_low)).lower()}。",
        )

    if task in METADATA_ONLY_TASKS:
        meta_evidence = {
            "aiops_official_app_context": (
                f"The official case metadata ties this telemetry window to the {slots.get('app')} application.",
                f"官方 case metadata 将这个遥测窗口归到 {slots.get('app')} 应用。",
            ),
            "aiops_official_case_provenance_context": (
                f"The official case metadata records the provenance as {slots.get('provenance')}.",
                f"官方 case metadata 记录的来源是：{label_cn}。",
            ),
            "aiops_official_service_role_context": (
                f"The faulty-service label {slots.get('faulty_service')} implies {slots.get('service_role')}.",
                f"故障服务标签 {slots.get('faulty_service')} 对应的服务角色是：{label_cn}。",
            ),
            "aiops_official_fault_family_detail_context": (
                f"The simulator metadata records the fault family as {slots.get('fault_family_detail')}.",
                f"模拟器 metadata 记录的故障族是：{label_cn}。",
            ),
            "aiops_official_fault_context": (
                f"The official simulator label indicates {slots.get('fault_family')} for faulty service {slots.get('faulty_service')}.",
                f"官方模拟器标签显示故障族为 {slots.get('fault_family')}，故障服务为 {slots.get('faulty_service')}；对应上下文是：{label_cn}。",
            ),
        }
        evidence_en, evidence_zh = meta_evidence.get(
            task, (row["oracle_evidence_caption"], row["oracle_evidence_caption"])
        )
        return (
            "Which official metadata label applies to this AIOpsLab telemetry case?",
            "这个 AIOpsLab 遥测样本对应哪个官方 metadata 标签？",
            evidence_en,
            evidence_zh,
        )

    return row["question"], row["question"], row["oracle_evidence_caption"], row["oracle_evidence_caption"]


def lint_case(case: dict) -> list[dict]:
    issues = []
    text = " ".join([case["scene_en"], case["question_en"], case["evidence_en"]])
    reader_text = " ".join([case["scene_en"], case["question_en"]])
    for token in ["post769_1025", "segment_tag", "bucket", "w512", "w128", "w0_", "case000", "case005"]:
        if token in reader_text:
            issues.append({"code": "internal_id_in_reader_text", "detail": token})
    if case["natural_status"] == "exclude_metadata_only":
        issues.append({"code": "metadata_only_not_pure_ts", "detail": case["exclude_reason"]})
    if "global step" in case["original_question"] and "global step" not in case["scene_en"]:
        issues.append({"code": "unexplained_global_time", "detail": "original question used global step"})
    if re.search(r"\bx[0-9]\b", case["question_en"]) and not re.search(r"\bx[0-9]\b", case["scene_en"]):
        issues.append({"code": "unexplained_variable", "detail": case["question_en"]})
    if "lead-lag" in case["question_en"].lower() or "lead" in case["question_en"].lower():
        issues.append({"code": "lead_lag_needs_manual_review", "detail": "lead-lag can be visually weak"})
    if "material" in text.lower() and "threshold" not in text.lower() and "about the same" not in text.lower():
        issues.append({"code": "material_without_threshold", "detail": "material change may need a threshold"})
    return issues


def build_summary(cases: list[dict], lint: dict) -> str:
    by_source = Counter(case["source"] for case in cases)
    by_status = Counter(case["natural_status"] for case in cases)
    issue_counts = Counter(issue["code"] for issues in lint["by_id"].values() for issue in issues)
    examples = []
    for case in cases[:12]:
        examples.append(
            f"- `{case['source']}` / `{case['task_family']}` / `{case['natural_status']}`: {case['question_zh']}"
        )
    examples_text = "\n".join(examples)
    lines = [
        "# Natural QA Balanced8 Lint（2026-05-19）",
        "",
        "本产物把 48 条 `balanced_eval_per_source8` 全部改写成自然语言 QA 草案。gold answer 仍来自原始 support slots；LLM/reviewer 不能决定答案。",
        "",
        "## 数量",
        "",
        f"- rows: `{len(cases)}`",
        f"- by source: `{dict(by_source)}`",
        f"- by natural status: `{dict(by_status)}`",
        f"- lint issue counts: `{dict(issue_counts)}`",
        "",
        "## 解释",
        "",
        "- `candidate`：可作为自然 TS-QA 候选，仍需 GPT reviewer 或人工审核。",
        "- `exclude_metadata_only`：需要 metadata，不应作为纯时间序列 QA 正例。",
        "- lint issue 是保守提示，不等于错误；用于决定哪些样本要 reviewer 或人工改写。",
        "",
        "## 前 12 条样例",
        "",
        examples_text,
        "",
        "## 建议",
        "",
        "下一步只对 `candidate` 运行 GPT-5.5 reviewer，并把 reviewer gate 作为正例准入条件：`keep`、naturalness >= 4、answerability >= 4、risk low。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = []
    lint_by_id = {}
    for row in load_rows():
        case = rewrite_case(row)
        if "_scene_extra_en" in row:
            case["scene_en"] += row["_scene_extra_en"]
            case["scene_zh"] += row["_scene_extra_zh"]
        issues = lint_case(case)
        case["lint_issues"] = issues
        lint_by_id[case["id"]] = issues
        cases.append(case)

    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    lint = {
        "input": str(RAW.relative_to(ROOT)),
        "output": str(OUT_JSONL.relative_to(ROOT)),
        "n": len(cases),
        "by_status": dict(Counter(case["natural_status"] for case in cases)),
        "by_source": dict(Counter(case["source"] for case in cases)),
        "issue_counts": dict(Counter(issue["code"] for issues in lint_by_id.values() for issue in issues)),
        "by_id": lint_by_id,
    }
    OUT_LINT.write_text(json.dumps(lint, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(build_summary(cases, lint), encoding="utf-8")
    print(OUT_JSONL)
    print(OUT_LINT)
    print(OUT_MD)


if __name__ == "__main__":
    main()
