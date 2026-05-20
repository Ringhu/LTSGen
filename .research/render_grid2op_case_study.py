#!/usr/bin/env python3
"""生成 Grid2Op 中文案例分析图和 GitHub Markdown 报告。"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from scripts.eval.eval_medium_horizon_simqa_pilot import build_context_card

plt.rcParams["font.sans-serif"] = [
    "Noto Sans CJK SC",
    "Noto Sans CJK TC",
    "Noto Sans CJK JP",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False


OUT_DIR = ROOT / "docs/case-studies/20260513-grid2op"
FIG_DIR = OUT_DIR / "figures"
RESEARCH_DIR = ROOT / ".research/real-grid2op-20260513"

OBS_QA = RESEARCH_DIR / "grid2op_real_v4_obs_slot/grid2op_real_v4_obs_slot.jsonl"
OBS_PRED = RESEARCH_DIR / "grid2op_real_v4_obs_slot/core_sweep_with_context_v2b/predictions.jsonl"
CF_QA = RESEARCH_DIR / "grid2op_real_cf_v6_slot/grid2op_real_cf_v6_slot.jsonl"
CF_PRED = RESEARCH_DIR / "grid2op_real_cf_v6_slot/core_sweep_with_context_v2b/predictions.jsonl"


@dataclass(frozen=True)
class CaseSpec:
    title: str
    case_id: str
    source: str
    analysis: str


CASES = [
    CaseSpec(
        title="单点线路负载率：背景充分后，仍需要定位到具体 line 和 local_t",
        case_id="simqa::grid2op_real::rte_case14_realistic_trace_512::h512::s0::peak_rho_quarter::slot_v4",
        source="observation",
        analysis=(
            "这个案例不是问“哪条线路最重要”，而是问指定时刻和指定线路上的 rho 数值。"
            "背景卡片解释了 Grid2Op、line（线路）和 rho（线路负载率）的含义，但不会泄漏答案。"
            "generic caption（通用说明文本）只说明有哪些变量，因此仍答错；oracle evidence caption"
            "（oracle 证据说明文本）给出可核验的 slot value（槽位数值）。"
        ),
    ),
    CaseSpec(
        title="平均负载聚合：只看采样行不足以恢复窗口级均值",
        case_id="simqa::grid2op_real::rte_case14_realistic_trace_512::h512::s0::max_avg_load::slot_v4",
        source="observation",
        analysis=(
            "这个样例考察整段窗口上的 aggregation（聚合）统计。问题指定 load 1，要求它在整个窗口"
            "上的平均 load_p，而不是让模型猜哪个负载最大。所有 sampled numbers（采样数值）条件"
            "都选错，说明稀疏采样行不能稳定替代窗口级统计。"
        ),
    ),
    CaseSpec(
        title="发电机窗口均值：长采样提示文本仍可能错过聚合答案",
        case_id="simqa::grid2op_real::rte_case14_realistic_trace_512::h512::s0::max_avg_generator::slot_v4",
        source="observation",
        analysis=(
            "这个案例和负载均值类似，但变量换成 generator（发电机）的 gen_p。题目指定 generator 0，"
            "要求窗口平均值。sampled numbers prompt（采样数值提示文本）长度达到数万字符仍答错，"
            "而 oracle evidence caption 只保留一个可验证数值。"
        ),
    ),
    CaseSpec(
        title="控制样例：quarter 均值问题中 sampled numbers（采样数值）可以答对",
        case_id="simqa::grid2op_real::rte_case14_realistic_trace_2048_nooverflow::h1024::s512::peak_total_load_quarter::slot_v4",
        source="observation",
        analysis=(
            "这是一个对照案例。问题要求第 3 个 quarter（四分段）中的 mean total_load（平均总负荷），"
            "三个 sampled numbers 条件都答对，说明我们不能简单宣称 raw numbers（原始数值）总是失败。"
            "当前更稳妥的结论是：oracle evidence caption 提供了更短且稳定的答案接口。"
        ),
    ),
    CaseSpec(
        title="反事实差值：必须比较同一时刻的事实轨迹和干预轨迹",
        case_id="simqa::grid2op_real_cf::h1024_c-1_t256_line1::cf_peak_rho_direction::slot_v4",
        source="counterfactual",
        analysis=(
            "这个反事实案例要求比较同一个 local_t 上 intervention_max_rho 和 factual_max_rho 的差值。"
            "背景卡片说明了 factual/counterfactual（事实/反事实）配对轨迹怎么读，但答案必须来自两条"
            "轨迹的逐时刻数值比较。generic caption 没有给出配对数值；高预算 sampled numbers 也不稳定。"
        ),
    ),
]


METHOD_ORDER = [
    "meta_only",
    "generic_caption",
    "oracle_evidence_caption",
    "numbers_sampled_32",
    "numbers_sampled_64",
    "numbers_sampled_128",
    "numbers_sampled_256",
    "numbers_sampled_512",
]

METHOD_LABELS = {
    "meta_only": "仅元信息",
    "generic_caption": "generic caption（通用说明文本）",
    "oracle_evidence_caption": "oracle evidence caption（oracle 证据说明文本）",
    "numbers_sampled_32": "sampled numbers（采样数值）32 行",
    "numbers_sampled_64": "sampled numbers（采样数值）64 行",
    "numbers_sampled_128": "sampled numbers（采样数值）128 行",
    "numbers_sampled_256": "sampled numbers（采样数值）256 行",
    "numbers_sampled_512": "sampled numbers（采样数值）512 行",
}

SOURCE_LABELS = {
    "observation": "单条观测轨迹",
    "counterfactual": "factual/counterfactual（事实/反事实）配对轨迹",
}

TASK_LABELS = {
    "peak_rho_quarter": "最大线路负载率所在窗口段",
    "max_avg_load": "窗口平均负载最大者",
    "total_load_trend": "前后窗口总负荷趋势",
    "cf_intervention_overload_severity": "断线干预后的过载严重度",
    "cf_peak_rho_direction": "断线干预后的峰值方向变化",
    "rho_value_slot": "指定时刻线路 rho 数值",
    "load_average_value_slot": "指定负载窗口平均 load_p",
    "generator_average_value_slot": "指定发电机窗口平均 gen_p",
    "quarter_total_load_mean_value_slot": "指定 quarter 平均 total_load",
    "cf_delta_max_rho_value_slot": "指定时刻反事实 max-rho 差值",
    "cf_intervention_max_rho_value_slot": "指定时刻干预轨迹 max-rho",
}

QUARTER_LABELS = {
    "first": "第一段（前 1/4）",
    "second": "第二段",
    "third": "第三段",
    "fourth": "第四段（后 1/4）",
}


def slugify(text: str) -> str:
    text = text.replace("::", "_")
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "_", text)
    return text.strip("_").lower()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def index_by_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {r["id"]: r for r in records}


def load_predictions(paths: list[Path]) -> dict[str, dict[str, dict[str, Any]]]:
    by_id: dict[str, dict[str, dict[str, Any]]] = {}
    for path in paths:
        if not path.exists():
            continue
        for row in load_jsonl(path):
            by_id.setdefault(row["id"], {})[row["condition"]] = row
    return by_id


def translate_text(text: str) -> str:
    """Translate the fixed prompt/caption templates used by this benchmark."""
    exact = {
        "At local_t=170, what is rho for line 3?":
            "在 local_t=170 时，第 3 条线路的 rho（线路负载率）是多少？",
        "What is the window-average load_p for load 1?":
            "load 1 在整个窗口中的平均 load_p（负载有功功率）是多少？",
        "What is the window-average gen_p for generator 0?":
            "generator 0 在整个窗口中的平均 gen_p（发电机有功出力）是多少？",
        "What is the mean total_load in quarter 3 of this trace window?":
            "这个轨迹窗口第 3 个 quarter（四分段）中的 mean total_load（平均总负荷）是多少？",
        "At local_t=623, what is intervention_max_rho minus factual_max_rho?":
            "在 local_t=623 时，intervention_max_rho 减去 factual_max_rho 是多少？",
        "Which quarter of this Grid2Op trace window contains the maximum line loading?":
            "这个 Grid2Op 轨迹窗口中，最大线路负载率出现在第几个窗口段？",
        "Which load has the highest average active power in this Grid2Op trace window?":
            "这个 Grid2Op 轨迹窗口中，哪个负载的平均有功功率最高？",
        "Compared with the first quarter, how does mean total load in the last quarter change?":
            "与第一段相比，最后一段的平均总负荷如何变化？",
        "After disconnecting line 0 at t=128, what is the worst overload severity later in the rollout?":
            "在 t=128 断开第 0 条线路后，后续 rollout 中最严重的过载程度是什么？",
        "Using a 0.05 max-rho tolerance, if line 5 is disconnected at t=128, how does the post-intervention peak maximum line loading compare with the factual rollout?":
            "以 0.05 的 max-rho 容忍阈值判断：如果在 t=128 断开第 5 条线路，干预后的峰值最大线路负载率相对事实 rollout 如何变化？",
        "This Grid2Op power-grid trace window contains line loading, load, generator, and power-flow variables over 1024 steps.":
            "这个 Grid2Op 电网轨迹窗口包含 1024 个时间步上的线路负载率、负载、发电机和潮流变量。",
        "This Grid2Op power-grid trace window contains line loading, load, generator, and power-flow variables over 512 steps.":
            "这个 Grid2Op 电网轨迹窗口包含 512 个时间步上的线路负载率、负载、发电机和潮流变量。",
        "This paired Grid2Op trace contains a factual rollout and a counterfactual rollout with one power line disconnected during the episode.":
            "这组 Grid2Op 配对轨迹包含一条事实 rollout，以及一条在 episode 中断开某条输电线路的反事实 rollout。",
        "not determinable from the trace window":
            "无法仅从该轨迹窗口判断",
        "not determinable from the paired traces":
            "无法仅从配对轨迹判断",
        "a severe overload above 1.20":
            "严重过载，超过 1.20",
        "an overload above 1.00 but not above 1.20":
            "发生过载，超过 1.00 但不超过 1.20",
        "no overload above 1.00":
            "没有超过 1.00 的过载",
        "first": "第一段",
        "second": "第二段",
        "third": "第三段",
        "fourth": "第四段",
        "higher": "更高",
        "lower": "更低",
        "unchanged": "基本不变",
        "overload": "过载",
        "increase": "上升",
        "decrease": "下降",
        "same": "基本不变",
    }
    if text in exact:
        return exact[text]

    replacements = [
        ("the fourth quarter of the trace window", "轨迹窗口第四段"),
        ("the third quarter of the trace window", "轨迹窗口第三段"),
        ("the second quarter of the trace window", "轨迹窗口第二段"),
        ("the first quarter of the trace window", "轨迹窗口第一段"),
        ("lower than the first quarter", "低于第一段"),
        ("higher than the first quarter", "高于第一段"),
        ("roughly unchanged from the first quarter", "与第一段大致不变"),
        ("load ", "负载 "),
        ("it decreases by at least 0.05 max-rho relative to the factual rollout", "相对事实 rollout 至少下降 0.05 max-rho"),
        ("it changes by less than 0.05 max-rho relative to the factual rollout", "相对事实 rollout 的变化小于 0.05 max-rho"),
        ("it increases by at least 0.05 max-rho relative to the factual rollout", "相对事实 rollout 至少上升 0.05 max-rho"),
        ("it cannot be determined from the paired traces", "无法仅从配对轨迹判断"),
    ]
    out = text
    for src, dst in replacements:
        out = out.replace(src, dst)

    m = re.match(
        r"The maximum line loading rho is ([0-9.]+) on line (\d+) at local t=(\d+) "
        r"\(global t=(\d+)\), which falls in the (\w+) quarter of the trace window\.",
        text,
    )
    if m:
        rho, line, local_t, global_t, quarter = m.groups()
        return (
            f"最大线路负载率 rho 为 {rho}，出现在第 {line} 条线路、局部时间步 "
            f"t={local_t}（全局 t={global_t}），属于{QUARTER_LABELS.get(quarter, quarter)}。"
        )

    m = re.match(r"Load (\d+) has the largest average active power over the window: ([0-9.]+)\.", text)
    if m:
        load_id, value = m.groups()
        return f"负载 {load_id} 在该窗口中的平均有功功率最高，为 {value}。"

    m = re.match(
        r"Mean total load is ([0-9.]+) in the first quarter and ([0-9.]+) in the last quarter, "
        r"so the last quarter is higher than the first quarter\.",
        text,
    )
    if m:
        first, last = m.groups()
        return f"第一段的平均总负荷为 {first}，最后一段为 {last}，因此最后一段高于第一段。"

    m = re.match(
        r"After the intervention, the largest post-intervention max-rho is ([0-9.]+)\. "
        r"That corresponds to an overload above 1\.00 but not above 1\.20\.",
        text,
    )
    if m:
        return f"干预后，后续最大 max-rho 为 {m.group(1)}，对应超过 1.00 但不超过 1.20 的过载。"

    m = re.match(
        r"In the factual rollout, the post-intervention peak max-rho is ([0-9.]+); "
        r"after disconnecting line (\d+) at t=(\d+), it is ([0-9.]+)\. "
        r"The difference is \+([0-9.]+); with a 0\.05 tolerance, it increases by at least 0\.05 max-rho relative to the factual rollout\.",
        text,
    )
    if m:
        factual, line, step, intervention, delta = m.groups()
        return (
            f"事实 rollout 中，干预后峰值 max-rho 为 {factual}；在 t={step} 断开第 {line} 条线路后，"
            f"该值变为 {intervention}。差值为 +{delta}；以 0.05 为容忍阈值，它相对事实 rollout "
            "至少上升 0.05 max-rho。"
        )

    m = re.match(r"At local_t=(\d+), rho for line (\d+) is ([0-9.]+)\.", text)
    if m:
        local_t, line, value = m.groups()
        return f"在 local_t={local_t} 时，第 {line} 条线路的 rho（线路负载率）为 {value}。"

    m = re.match(r"The window-average load_p for load (\d+) is ([0-9.]+)\.", text)
    if m:
        load_id, value = m.groups()
        return f"load {load_id} 在整个窗口中的平均 load_p（负载有功功率）为 {value}。"

    m = re.match(r"The window-average gen_p for generator (\d+) is ([0-9.]+)\.", text)
    if m:
        gen_id, value = m.groups()
        return f"generator {gen_id} 在整个窗口中的平均 gen_p（发电机有功出力）为 {value}。"

    m = re.match(r"The mean total_load in quarter (\d+) is ([0-9.]+)\.", text)
    if m:
        quarter, value = m.groups()
        return f"第 {quarter} 个 quarter（四分段）中的 mean total_load（平均总负荷）为 {value}。"

    m = re.match(
        r"At local_t=(\d+), intervention_max_rho - factual_max_rho is (-?[0-9.]+)\.",
        text,
    )
    if m:
        local_t, value = m.groups()
        return f"在 local_t={local_t} 时，intervention_max_rho - factual_max_rho 为 {value}。"

    m = re.match(r"At local_t=(\d+), intervention_max_rho is ([0-9.]+)\.", text)
    if m:
        local_t, value = m.groups()
        return f"在 local_t={local_t} 时，intervention_max_rho 为 {value}。"

    return out


def translate_option(option: str) -> str:
    if ". " not in option:
        return translate_text(option)
    letter, text = option.split(". ", 1)
    return f"{letter}. {translate_text(text)}"


def display_record(record: dict[str, Any], spec: CaseSpec) -> dict[str, Any]:
    return {
        "id": record["id"],
        "source": spec.source,
        "source_zh": SOURCE_LABELS.get(spec.source, spec.source),
        "task_family": record["task_family"],
        "task_family_zh": TASK_LABELS.get(record["task_family"], record["task_family"]),
        "horizon": record["horizon"],
        "question_zh": translate_text(record["question"]),
        "options_zh": [translate_option(opt) for opt in record["options"]],
        "answer": record["answer"],
        "answer_label_zh": translate_text(str(record.get("answer_label", ""))).replace("load ", "负载 "),
        "generic_caption_zh": translate_text(record["generic_caption"]),
        "oracle_evidence_caption_zh": translate_text(record["oracle_evidence_caption"]),
        "evidence": record.get("evidence", {}),
    }


def read_trace_window(record: dict[str, Any]) -> list[dict[str, Any]]:
    data = json.loads((ROOT / record["trace_path"]).read_text(encoding="utf-8"))
    start = int(record["trace_window"]["start"])
    end = int(record["trace_window"]["end"])
    return data["trace"][start:end]


def read_pair(record: dict[str, Any]) -> dict[str, Any]:
    return json.loads((ROOT / record["pair_path"]).read_text(encoding="utf-8"))


def quarter_spans(ax, horizon: int) -> None:
    colors = ["#f4f4f4", "#ffffff", "#f4f4f4", "#ffffff"]
    labels = ["第一段", "第二段", "第三段", "第四段"]
    for i in range(4):
        lo = i * horizon / 4
        hi = (i + 1) * horizon / 4
        ax.axvspan(lo, hi, color=colors[i], zorder=0)
        ax.text((lo + hi) / 2, 0.98, labels[i], transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=8, color="#777777")


def save_fig(fig, name: str) -> str:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return f"figures/{path.name}"


def plot_observation(record: dict[str, Any], slug: str) -> str:
    rows = read_trace_window(record)
    t = np.arange(len(rows))
    task = record["task_family"]
    evidence = record["evidence"]

    if task in {"peak_rho_quarter", "rho_value_slot"}:
        rho = np.asarray([r["rho"] for r in rows], dtype=float)
        line = int(evidence.get("slot_line", evidence.get("peak_line", 0)))
        line_rho = rho[:, line]
        slot_t = int(evidence.get("slot_local_t", evidence.get("peak_local_t", 0)))
        fig, ax = plt.subplots(figsize=(9, 3.2))
        ax.plot(t, line_rho, label=f"第 {line} 条线路 rho", color="#1f77b4", lw=1.2)
        ax.axvline(slot_t, color="#d62728", ls="--", lw=1.2, label=f"查询时刻 t={slot_t}")
        ax.scatter([slot_t], [float(line_rho[slot_t])], color="#d62728", s=35, zorder=4)
        ax.set_ylabel("rho")
        ax.set_xlabel("局部时间步")
        ax.set_title("指定线路在查询时刻的 rho（线路负载率）")
        ax.legend(frameon=False, ncol=2, fontsize=8)
        return save_fig(fig, slug)

    if task in {"max_avg_load", "load_average_value_slot"}:
        load = np.asarray([r["load_p"] for r in rows], dtype=float)
        load_ids = [int(evidence.get("slot_load", evidence.get("max_avg_load", 0)))]
        fig, ax = plt.subplots(figsize=(9, 3.2))
        for idx in load_ids:
            y = load[:, idx]
            ax.plot(t, y, lw=1.2, label=f"负载 {idx}（均值={y.mean():.2f}）")
            ax.axhline(y.mean(), lw=1.1, ls="--", color="#d62728", alpha=0.75, label="窗口均值")
        ax.set_ylabel("load_p")
        ax.set_xlabel("局部时间步")
        ax.set_title("指定负载的窗口级平均 load_p")
        ax.legend(frameon=False, ncol=3, fontsize=8)
        return save_fig(fig, slug)

    if task == "generator_average_value_slot":
        gen = np.asarray([r["gen_p"] for r in rows], dtype=float)
        gen_id = int(evidence.get("slot_generator", evidence.get("max_avg_generator", 0)))
        y = gen[:, gen_id]
        fig, ax = plt.subplots(figsize=(9, 3.2))
        ax.plot(t, y, color="#1f77b4", lw=1.2, label=f"发电机 {gen_id} gen_p")
        ax.axhline(y.mean(), lw=1.1, ls="--", color="#d62728", alpha=0.75, label=f"窗口均值={y.mean():.2f}")
        ax.set_ylabel("gen_p")
        ax.set_xlabel("局部时间步")
        ax.set_title("指定发电机的窗口级平均 gen_p")
        ax.legend(frameon=False, ncol=2, fontsize=8)
        return save_fig(fig, slug)

    if task in {"total_load_trend", "quarter_total_load_mean_value_slot"}:
        load = np.asarray([r["load_p"] for r in rows], dtype=float)
        total = load.sum(axis=1)
        q = max(1, len(rows) // 4)
        slot_quarter = int(evidence.get("slot_quarter", 4))
        start = (slot_quarter - 1) * q
        end = len(rows) if slot_quarter == 4 else slot_quarter * q
        mean_value = float(total[start:end].mean())
        fig, ax = plt.subplots(figsize=(9, 3.2))
        quarter_spans(ax, len(rows))
        ax.plot(t, total, color="#1f77b4", lw=1.3, label="总负荷")
        ax.axvspan(start, end, color="#fbe7c6", alpha=0.45, zorder=0)
        ax.hlines(mean_value, start, end - 1, colors="#d62728", linestyles="--", lw=1.4, label=f"第 {slot_quarter} 段均值={mean_value:.2f}")
        ax.set_ylabel("total_load")
        ax.set_xlabel("局部时间步")
        ax.set_title("指定 quarter（四分段）的 mean total_load")
        ax.legend(frameon=False, ncol=2, fontsize=8)
        return save_fig(fig, slug)

    raise ValueError(f"Unsupported observation task: {task}")


def plot_counterfactual(record: dict[str, Any], slug: str) -> str:
    data = read_pair(record)
    factual = data["factual_trace"]
    intervention = data["intervention_trace"]
    n = min(len(factual), len(intervention))
    t = np.arange(n)
    f_rho = np.asarray([r["rho"] for r in factual[:n]], dtype=float)
    i_rho = np.asarray([r["rho"] for r in intervention[:n]], dtype=float)
    f_max = f_rho.max(axis=1)
    i_max = i_rho.max(axis=1)
    step = int(record["intervention"]["step"])
    line = int(record["intervention"]["line_id"])
    slot_t = int(record.get("evidence", {}).get("slot_local_t", step + 1))
    threshold = 1.0
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax = axes[0]
    ax.plot(t, f_max, color="#1f77b4", lw=1.3, label="事实轨迹 max rho")
    ax.plot(t, i_max, color="#d62728", lw=1.3, label="干预轨迹 max rho")
    ax.axvline(step, color="#555555", ls="--", lw=1.1, label=f"t={step} 断开第 {line} 条线路")
    ax.axvline(slot_t, color="#2ca02c", ls="--", lw=1.1, label=f"查询时刻 t={slot_t}")
    ax.axhline(threshold, color="#9467bd", ls=":", lw=1.2, label="过载阈值 1.00")
    ax.scatter([slot_t], [i_max[slot_t]], color="#d62728", s=32, zorder=4)
    ax.scatter([slot_t], [f_max[slot_t]], color="#1f77b4", s=32, zorder=4)
    ax.set_ylabel("max rho")
    ax.set_title("同一 local_t 上事实轨迹与干预轨迹的 max-rho 对比")
    ax.legend(frameon=False, ncol=2, fontsize=8)
    status = np.asarray([r["line_status"][line] for r in intervention[:n]], dtype=float)
    axes[1].step(t, status, where="post", color="#2ca02c", lw=1.3)
    axes[1].axvline(step, color="#555555", ls="--", lw=1.0)
    axes[1].set_ylim(-0.1, 1.1)
    axes[1].set_ylabel(f"第 {line} 条线\n状态")
    axes[1].set_xlabel("局部时间步")
    return save_fig(fig, slug)


def option_text(record: dict[str, Any], letter: str) -> str:
    prefix = f"{letter}."
    for opt in record["options"]:
        if opt.startswith(prefix):
            return translate_option(opt)
    return ""


def pred_table(record: dict[str, Any], preds: dict[str, dict[str, Any]]) -> str:
    rows = ["| 输入条件 | 原始条件名 | 预测 | 正确性 | Prompt 字符数 | 选项文本 |", "| --- | --- | --- | --- | ---: | --- |"]
    for cond in METHOD_ORDER:
        if cond not in preds:
            continue
        p = preds[cond]
        mark = "正确" if p["correct"] else "错误"
        rows.append(
            f"| {METHOD_LABELS.get(cond, cond)} | `{cond}` | `{p['pred']}` | {mark} | {int(p['prompt_chars'])} | {option_text(record, p['pred'])} |"
        )
    return "\n".join(rows)


def format_options(record: dict[str, Any]) -> str:
    return "\n".join(f"- {translate_option(opt)}" for opt in record["options"])


def facts_table(record: dict[str, Any]) -> str:
    facts = record.get("evidence", {})
    rows = ["| 验证字段 | 数值 |", "| --- | --- |"]
    for key, value in facts.items():
        if isinstance(value, float):
            value = f"{value:.4f}"
        rows.append(f"| `{key}` | `{value}` |")
    return "\n".join(rows)


def context_card_md(record: dict[str, Any]) -> str:
    card = build_context_card(record)
    if not card:
        return "这个案例没有额外背景卡片。"
    translations = {
        "Grid2Op context card:": "**Grid2Op context card（背景卡片）**",
        "- Grid2Op is a power-grid simulation environment. A trace is a time-ordered rollout of grid state.":
            "- Grid2Op 是 power-grid simulation environment（电网仿真环境）。trace（轨迹）是一段按时间排序的电网状态 rollout。",
        "- A power line transports electricity between grid nodes. Disconnecting a line changes the grid topology and can redistribute flows across other lines.":
            "- power line（输电线路）负责在电网节点之间传输电力。disconnecting a line（断开线路）会改变 grid topology（电网拓扑），并可能让潮流重新分配到其他线路。",
        "- `rho[line]` is the loading ratio of each power line. A larger rho means a more heavily loaded line; rho >= 1.00 means overload, and rho > 1.20 means severe overload in these questions.":
            "- `rho[line]` 是每条线路的 loading ratio（负载率）。rho 越大表示线路越接近负载上限；在这些问题中，rho >= 1.00 表示 overload（过载），rho > 1.20 表示 severe overload（严重过载）。",
        "- `max_rho` means the largest rho across all lines at a timestep. `argmax rho line` is the line index with that largest rho.":
            "- `max_rho` 表示某个时间步所有线路中最大的 rho；`argmax rho line` 是达到该最大 rho 的线路编号。",
        "- `load_p[load]` is active power demand for each load. `gen_p[generator]` is active power output for each generator.":
            "- `load_p[load]` 是每个负载点的 active power demand（有功功率需求）；`gen_p[generator]` 是每个发电机的 active power output（有功出力）。",
        "- `line_status[line]` is 1 when a line is connected and 0 when disconnected.":
            "- `line_status[line]` 表示线路状态：1 为 connected（连接），0 为 disconnected（断开）。",
        "- Use the trace values to answer. Do not infer the effect of an intervention from domain intuition alone.":
            "- 回答必须使用 trace values（轨迹数值）。不要只凭领域直觉推断 intervention（干预）的影响。",
        "- Domain: Grid2Op is a power-grid simulator. Each time step is one simulated grid state.":
            "- Domain（领域）：Grid2Op 是 power-grid simulator（电网仿真器）。每个时间步代表一个仿真的电网状态。",
        "- line: a transmission line connecting grid nodes.":
            "- line（线路）：连接电网节点的输电线路。",
        "- load_p: active power demand at a load. Larger load_p means larger electricity demand.":
            "- load_p（负载有功功率）：某个负载点的有功用电需求，数值越大表示需求越大。",
        "- gen_p: active power output from a generator.":
            "- gen_p（发电机有功出力）：某个发电机的有功输出。",
        "- rho: line loading ratio. rho near or above 1.0 means the line is close to or above its thermal limit.":
            "- rho（线路负载率）：输电线路的负载比例，接近或超过 1.0 表示线路接近或超过热稳定限额。",
        "- max_rho: the maximum rho over all lines at a time step.":
            "- max_rho：某个时间步上所有线路 rho 的最大值。",
        "- line_status: 1 means connected, 0 means disconnected.":
            "- line_status（线路状态）：1 表示连接，0 表示断开。",
        "- total_load: sum of load_p over all loads at a time step.":
            "- total_load（总负荷）：某个时间步所有 load_p 的总和。",
        "Trace setup:":
            "\n**Trace setup（轨迹设置）**",
        "- This is a single factual trace window.":
            "- 这是单条 factual trace window（事实轨迹窗口）。",
        "- `local_t` indexes time within the selected window; `global_t` indexes the original exported trace.":
            "- `local_t` 是所选窗口内部的局部时间索引；`global_t` 是原始导出轨迹中的全局时间索引。",
        "- For quarter-based questions, divide the local window into four equal contiguous quarters.":
            "- 对 quarter-based questions（四分段问题），把局部窗口划分为四个连续且长度相等的 quarter。",
        "- This is a paired factual/counterfactual setting.":
            "- 这是 paired factual/counterfactual setting（事实/反事实配对设置）。",
        "- The factual trace is the original rollout.":
            "- factual trace（事实轨迹）是原始 rollout。",
        "- The intervention trace follows the same setup except that one specified power line is disconnected at the intervention time.":
            "- intervention trace（干预轨迹）与事实轨迹设置相同，区别是在 intervention time（干预时刻）断开指定输电线路。",
        "- For post-intervention questions, compare timesteps after the intervention time in the factual and intervention traces.":
            "- 对 post-intervention questions（干预后问题），比较事实轨迹和干预轨迹在干预时刻之后的时间步。",
        "- A trace window is a contiguous sequence of simulated grid states.":
            "- trace window（轨迹窗口）是一段连续的仿真电网状态序列。",
        "- Questions ask about facts inside the provided trace window only.":
            "- 问题只要求回答给定轨迹窗口内部的事实。",
        "- Background definitions do not determine the answer; the answer must come from the trace values.":
            "- 背景定义不会决定答案；答案必须来自轨迹数值。",
        "- factual trace: normal rollout.":
            "- factual trace（事实轨迹）：正常 rollout。",
        "- counterfactual/intervention trace: rollout after an action, here disconnecting one line at the stated step.":
            "- counterfactual/intervention trace（反事实/干预轨迹）：执行动作后的 rollout，这里是在指定时间步断开一条线路。",
        "- To answer counterfactual questions, compare the factual and intervention traces at the specified time/window.":
            "- 回答反事实问题时，要在指定时间或窗口上比较事实轨迹和干预轨迹。",
    }
    lines = []
    for line in card.splitlines():
        if line in translations:
            lines.append(translations[line])
        elif line.startswith("Task rule:"):
            lines.append("\n**Task rule（任务规则）**")
            task_rule = line.replace("Task rule:", "").strip()
            task_translations = {
                "read the `rho` value for the exact line and `local_t` specified in the question.":
                    "读取题目指定的 line（线路）和 `local_t` 上的 `rho` 数值。",
                "compute the average `load_p` over the whole window for the exact load specified in the question.":
                    "对题目指定的 load（负载），计算整个窗口上的平均 `load_p`。",
                "compute the average `gen_p` over the whole window for the exact generator specified in the question.":
                    "对题目指定的 generator（发电机），计算整个窗口上的平均 `gen_p`。",
                "compute total load at each timestep as the sum of all `load_p` values, then average it over the exact quarter specified in the question.":
                    "先把每个时间步所有 `load_p` 相加得到 total_load（总负荷），再对题目指定的 quarter（四分段）求平均。",
                "at the exact `local_t` specified in the question, subtract factual `max_rho` from intervention `max_rho`.":
                    "在题目指定的 `local_t` 上，用 intervention trace（干预轨迹）的 `max_rho` 减去 factual trace（事实轨迹）的 `max_rho`。",
                "at the exact `local_t` specified in the question, read `max_rho` from the intervention trace.":
                    "在题目指定的 `local_t` 上，从 intervention trace（干预轨迹）读取 `max_rho`。",
            }
            if task_rule in task_translations:
                lines.append(task_translations[task_rule])
            else:
                lines.append(task_rule)
        else:
            lines.append(line)
    return "\n".join(lines)


def render_case(idx: int, spec: CaseSpec, record: dict[str, Any], preds: dict[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    slug = f"{idx:02d}_{slugify(record['task_family'])}_{slugify(record['id'])[:80]}"
    image = plot_observation(record, slug) if spec.source == "observation" else plot_counterfactual(record, slug)
    correct = record["answer"]
    section = f"""<details>
<summary>案例 {idx:02d}：{spec.title}</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 案例 ID | `{record['id']}` |
| 数据来源 | {SOURCE_LABELS.get(spec.source, spec.source)} (`{spec.source}`) |
| 窗口长度 | `{record['horizon']}` |
| 任务类型 | {TASK_LABELS.get(record['task_family'], record['task_family'])} (`{record['task_family']}`) |
| 正确答案 | `{correct}` |
| 正确答案标签 | `{translate_text(str(record.get('answer_label', ''))).replace('load ', '负载 ')}` |
| ground truth（真值）来源 | `trace_array` / 仿真器轨迹 |

关键结论：{spec.analysis}

<details>
<summary>背景卡片</summary>

{context_card_md(record)}

</details>

<details>
<summary>时序图</summary>

![{record['id']}]({image})

</details>

<details>
<summary>QA 问题</summary>

**问题**

{translate_text(record['question'])}

**选项**

{format_options(record)}

**正确答案**：`{correct}` - {option_text(record, correct)}

</details>

<details>
<summary>caption（说明文本）与 evidence（证据）</summary>

**generic caption（通用说明文本）**

{translate_text(record['generic_caption'])}

**oracle evidence caption（oracle 证据说明文本）**

{translate_text(record['oracle_evidence_caption'])}

**可验证事实**

{facts_table(record)}

</details>

<details>
<summary>模型回答</summary>

{pred_table(record, preds)}

</details>

<details>
<summary>案例分析</summary>

{spec.analysis}

</details>

</details>
"""
    manifest = {
        "index": idx,
        "id": record["id"],
        "source": spec.source,
        "task_family": record["task_family"],
        "horizon": record["horizon"],
        "answer": record["answer"],
        "image": image,
        "predictions": {k: {"pred": v["pred"], "correct": v["correct"], "prompt_chars": v["prompt_chars"]} for k, v in preds.items()},
    }
    return section, manifest


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    obs = index_by_id(load_jsonl(OBS_QA))
    cf = index_by_id(load_jsonl(CF_QA))
    pred = load_predictions([OBS_PRED, CF_PRED])

    sections = []
    manifests = []
    selected_records = []
    for i, spec in enumerate(CASES, 1):
        record = obs.get(spec.case_id) if spec.source == "observation" else cf.get(spec.case_id)
        if record is None:
            raise KeyError(spec.case_id)
        if spec.case_id not in pred:
            raise KeyError(f"No predictions for {spec.case_id}")
        section, manifest = render_case(i, spec, record, pred[spec.case_id])
        sections.append(section)
        manifests.append(manifest)
        selected_records.append({
            "case_spec": {
                "title_zh": spec.title,
                "case_id": spec.case_id,
                "source": spec.source,
        "analysis_zh": spec.analysis,
            },
            "record_display_zh": display_record(record, spec),
        })

    report = f"""# Grid2Op 中等长度时序 QA 案例分析

这份报告展示当前 Grid2Op simulator-derived（仿真器派生）TS-QA pilot 中选出的代表性案例。所有 ground truth（真值）都来自轨迹数组或 factual/counterfactual（事实/反事实）配对轨迹，LLM 只作为答题模型参与评估，不参与定义正确答案。

## 覆盖范围

| 维度 | 内容 |
| --- | --- |
| 环境 | `rte_case14_realistic` |
| 窗口长度 | 评测集覆盖 `512`、`1024`、`2048`；本报告选取的案例使用 `512/1024` |
| 单轨迹观测案例 | 4 |
| factual/counterfactual（事实/反事实）配对案例 | 1 |
| 展示方法 | `meta_only`、`generic_caption`、`oracle_evidence_caption`、sampled numbers prompt（采样数值提示文本） |

## 主要观察

- 单轨迹的定位题和聚合题差距最大：oracle evidence caption（oracle 证据说明文本）很短且答对，而 sampled numbers prompt（采样数值提示文本）更长却经常答错。
- 这版问题包含显式背景卡片；它解释 Grid2Op、line（线路）、rho（线路负载率）和 factual/counterfactual（事实/反事实）轨迹，但不包含答案事实。
- 报告保留一个对照案例：当采样表覆盖到足够信息时，sampled numbers（采样数值）也能答对。因此当前结论不是“raw numbers（原始数值）必然失败”，而是“question-conditioned evidence（问题条件化证据）更短、更稳定”。
- 逐案例可视化能清楚说明题目真正需要的 evidence（证据）：指定时刻的线路数值、窗口平均值、quarter 均值，以及 factual/counterfactual（事实/反事实）同一时刻的 max-rho 对比。

## 案例

{chr(10).join(sections)}
"""

    (OUT_DIR / "grid2op_case_study.md").write_text(report, encoding="utf-8")
    (OUT_DIR / "selected_cases.json").write_text(json.dumps(selected_records, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "manifest.json").write_text(json.dumps({"cases": manifests}, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "README.md").write_text(
        "# Grid2Op 中等长度时序 QA 案例分析\n\n"
        "这个目录保存当前 Grid2Op TS-QA pilot 的 GitHub 可读中文案例分析报告。\n\n"
        "- [grid2op_case_study.md](grid2op_case_study.md)：带折叠面板的中文报告，包含时序图、QA 问题、caption（说明文本）与 evidence（证据）、各方法回答。\n"
        "- `figures/`：4 个单轨迹观测案例和 1 个 factual/counterfactual（事实/反事实）配对案例的 PNG 时序图。\n"
        "- `selected_cases.json`：被选中的 QA 记录和案例说明。\n"
        "- `manifest.json`：供后续脚本使用的紧凑 manifest。\n\n"
        "这组案例支持当前论文 framing：question-conditioned（问题条件化）、verifiable（可验证）的 evidence caption（证据说明文本）是更短且更可靠的接口；"
        "generic caption（通用说明文本）和 sampled numbers prompt（采样数值提示文本）在定位、聚合和配对轨迹比较任务上会出现明显失败。\n",
        encoding="utf-8",
    )
    print(json.dumps({"out_dir": str(OUT_DIR), "n_cases": len(CASES), "figures": len(list(FIG_DIR.glob('*.png')))}, indent=2))


if __name__ == "__main__":
    main()
