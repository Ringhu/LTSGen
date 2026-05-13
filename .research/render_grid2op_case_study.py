#!/usr/bin/env python3
"""生成 Grid2Op 中文案例分析图和 GitHub Markdown 报告。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = [
    "Noto Sans CJK SC",
    "Noto Sans CJK TC",
    "Noto Sans CJK JP",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs/case-studies/20260513-grid2op"
FIG_DIR = OUT_DIR / "figures"
RESEARCH_DIR = ROOT / ".research/real-grid2op-20260513"

OBS_QA = RESEARCH_DIR / "grid2op_real_v1_obs/grid2op_real_v1_obs.jsonl"
OBS_PRED = RESEARCH_DIR / "grid2op_real_v1_obs/full72_core_sweep/predictions.jsonl"
CF_QA = RESEARCH_DIR / "grid2op_real_cf_v3_compact_fixed/grid2op_real_cf_v3_compact_fixed.jsonl"
CF_PRED = RESEARCH_DIR / "grid2op_real_cf_v3_compact_fixed/sampling_sweep_18/predictions.jsonl"


@dataclass(frozen=True)
class CaseSpec:
    title: str
    case_id: str
    source: str
    analysis: str


CASES = [
    CaseSpec(
        title="峰值位置定位：sampled numbers（采样数值）错过后段线路负载峰值",
        case_id="simqa::grid2op_real::rte_case14_realistic_trace_2048_nooverflow::h1024::s0::peak_rho_quarter",
        source="observation",
        analysis=(
            "这是最清楚的定位失败样例。真实最大线路负载率出现在第 4 条线路、局部时间步 "
            "t=806，属于窗口第四段。generic caption（通用说明文本）没有给出事件位置，"
            "sampled numbers prompt（采样数值提示文本）虽然更长，但 32/64/128 三个采样预算"
            "都选错了窗口段。"
        ),
    ),
    CaseSpec(
        title="平均负载聚合：只看采样行不足以恢复窗口级均值",
        case_id="simqa::grid2op_real::rte_case14_realistic_trace_1024::h512::s0::max_avg_load",
        source="observation",
        analysis=(
            "这个样例考察整段窗口上的聚合统计。正确证据是负载 1 的窗口平均有功功率最高。"
            "generic caption（通用说明文本）和所有 sampled numbers（采样数值）条件都选择了干扰项，"
            "说明采样数值行不能稳定替代题目真正需要的窗口级统计量。"
        ),
    ),
    CaseSpec(
        title="趋势控制样例：简单聚合趋势下 sampled numbers（采样数值）可以答对",
        case_id="simqa::grid2op_real::rte_case14_realistic_trace_2048_nooverflow::h1024::s0::total_load_trend",
        source="observation",
        analysis=(
            "这是一个控制样例。sampled numbers（采样数值）能答对简单的前后段均值趋势问题，"
            "但 generic caption（通用说明文本）仍然失败。它提醒我们不要过度声称 raw numbers（原始数值）"
            "总是失败；当前观察到的弱点主要集中在定位、聚合和"
            "需要精确证据的任务上。"
        ),
    ),
    CaseSpec(
        title="反事实阈值：小幅干预刚好跨过过载边界",
        case_id="simqa::grid2op_real_cf::h1024_t128_line0::cf_intervention_overload_severity",
        source="counterfactual",
        analysis=(
            "断开第 0 条线路只带来很小的 max-rho 变化，但 intervention（干预）后的峰值达到 1.024，"
            "刚好超过 1.00 过载阈值。低采样预算的 sampled numbers（采样数值）漏掉了这个边界事实；"
            "oracle evidence caption（oracle 证据说明文本）直接给出"
            "与阈值判断相关的数值。"
        ),
    ),
    CaseSpec(
        title="反事实方向：必须比较事实轨迹和干预轨迹的峰值",
        case_id="simqa::grid2op_real_cf::h1024_t128_line5::cf_peak_rho_direction",
        source="counterfactual",
        analysis=(
            "断开第 5 条线路后，intervention（干预）后的峰值 max-rho 从 factual trace（事实轨迹）"
            "的 0.999 上升到 1.138。题目要求在 0.05 容忍阈值下比较 factual/counterfactual（事实/反事实）"
            "配对结果。generic caption（通用说明文本）失败的原因是它没有提供两条轨迹的配对结果事实。"
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
        for row in load_jsonl(path):
            by_id.setdefault(row["id"], {})[row["condition"]] = row
    return by_id


def translate_text(text: str) -> str:
    """Translate the fixed prompt/caption templates used by this benchmark."""
    exact = {
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

    if task == "peak_rho_quarter":
        rho = np.asarray([r["rho"] for r in rows], dtype=float)
        max_rho = rho.max(axis=1)
        line = int(evidence["peak_line"])
        line_rho = rho[:, line]
        peak_t = int(evidence["peak_local_t"])
        fig, ax = plt.subplots(figsize=(9, 3.2))
        quarter_spans(ax, len(rows))
        ax.plot(t, max_rho, label="所有线路的最大 rho", color="#1f77b4", lw=1.6)
        ax.plot(t, line_rho, label=f"第 {line} 条线路 rho", color="#ff7f0e", lw=1.1, alpha=0.85)
        ax.axvline(peak_t, color="#d62728", ls="--", lw=1.2, label=f"峰值 t={peak_t}")
        ax.scatter([peak_t], [float(evidence["peak_rho"])], color="#d62728", s=35, zorder=4)
        ax.set_ylabel("rho")
        ax.set_xlabel("局部时间步")
        ax.set_title("最大线路负载率出现在窗口第四段")
        ax.legend(frameon=False, ncol=3, fontsize=8)
        return save_fig(fig, slug)

    if task == "max_avg_load":
        load = np.asarray([r["load_p"] for r in rows], dtype=float)
        labels = [record["answer_label"]]
        for opt in record["options"]:
            m = re.search(r"load (\d+)", opt)
            if m:
                labels.append(f"load {m.group(1)}")
        load_ids = []
        for label in labels:
            idx = int(label.split()[-1])
            if idx not in load_ids:
                load_ids.append(idx)
        fig, ax = plt.subplots(figsize=(9, 3.2))
        for idx in load_ids:
            y = load[:, idx]
            ax.plot(t, y, lw=1.2, label=f"负载 {idx}（均值={y.mean():.2f}）")
            ax.axhline(y.mean(), lw=0.8, ls="--", alpha=0.45)
        ax.set_ylabel("有功功率")
        ax.set_xlabel("局部时间步")
        ax.set_title("候选负载的窗口级平均有功功率")
        ax.legend(frameon=False, ncol=2, fontsize=8)
        return save_fig(fig, slug)

    if task == "total_load_trend":
        load = np.asarray([r["load_p"] for r in rows], dtype=float)
        total = load.sum(axis=1)
        q = max(1, len(rows) // 4)
        first = float(total[:q].mean())
        last = float(total[-q:].mean())
        fig, ax = plt.subplots(figsize=(9, 3.2))
        quarter_spans(ax, len(rows))
        ax.plot(t, total, color="#1f77b4", lw=1.3, label="总负荷")
        ax.hlines(first, 0, q - 1, colors="#2ca02c", linestyles="--", lw=1.4, label=f"第一段均值={first:.2f}")
        ax.hlines(last, len(rows) - q, len(rows) - 1, colors="#d62728", linestyles="--", lw=1.4, label=f"第四段均值={last:.2f}")
        ax.set_ylabel("总有功负荷")
        ax.set_xlabel("局部时间步")
        ax.set_title("平均总负荷从第一段到第四段上升")
        ax.legend(frameon=False, ncol=3, fontsize=8)
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
    threshold = 1.0
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax = axes[0]
    ax.plot(t, f_max, color="#1f77b4", lw=1.3, label="事实轨迹 max rho")
    ax.plot(t, i_max, color="#d62728", lw=1.3, label="干预轨迹 max rho")
    ax.axvline(step, color="#555555", ls="--", lw=1.1, label=f"t={step} 断开第 {line} 条线路")
    ax.axhline(threshold, color="#9467bd", ls=":", lw=1.2, label="过载阈值 1.00")
    peak_t = int(np.argmax(i_max[step + 1:]) + step + 1)
    ax.scatter([peak_t], [i_max[peak_t]], color="#d62728", s=32, zorder=4)
    ax.set_ylabel("max rho")
    ax.set_title("事实轨迹与干预轨迹的事件后线路负载率对比")
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
| 单轨迹观测案例 | 3 |
| factual/counterfactual（事实/反事实）配对案例 | 2 |
| 展示方法 | `meta_only`、`generic_caption`、`oracle_evidence_caption`、sampled numbers prompt（采样数值提示文本） |

## 主要观察

- 单轨迹的定位题和聚合题差距最大：oracle evidence caption（oracle 证据说明文本）很短且答对，而 sampled numbers prompt（采样数值提示文本）更长却经常答错。
- counterfactual（反事实）案例更适合展示 verifiability（可验证性）和阈值判断；当采样表中刚好包含关键事实时，当前 sampled numbers prompt（采样数值提示文本）也可能答对。
- 逐案例可视化能清楚说明题目真正需要的 evidence（证据）：峰值位置、窗口平均值、第一段/最后一段均值，以及 factual/counterfactual（事实/反事实）干预后的 max-rho 对比。

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
        "- `figures/`：3 个单轨迹观测案例和 2 个 factual/counterfactual（事实/反事实）配对案例的 PNG 时序图。\n"
        "- `selected_cases.json`：被选中的 QA 记录和案例说明。\n"
        "- `manifest.json`：供后续脚本使用的紧凑 manifest。\n\n"
        "这组案例支持当前论文 framing：question-conditioned（问题条件化）、verifiable（可验证）的 evidence caption（证据说明文本）是更短且更可靠的接口；"
        "generic caption（通用说明文本）和 sampled numbers prompt（采样数值提示文本）在定位、聚合和配对轨迹比较任务上会出现明显失败。\n",
        encoding="utf-8",
    )
    print(json.dumps({"out_dir": str(OUT_DIR), "n_cases": len(CASES), "figures": len(list(FIG_DIR.glob('*.png')))}, indent=2))


if __name__ == "__main__":
    main()
