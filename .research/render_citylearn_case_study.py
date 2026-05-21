#!/usr/bin/env python3
"""Generate a Chinese CityLearn case-study report with plots."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
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


OUT_DIR = ROOT / "docs/case-studies/20260513-citylearn"
FIG_DIR = OUT_DIR / "figures"
RESEARCH_DIR = ROOT / ".research/real-citylearn-20260513/citylearn_real_v2_slot"
QA_PATH = RESEARCH_DIR / "citylearn_real_v2_slot.jsonl"
PRED_PATH = RESEARCH_DIR / "core_sweep_context_v3/predictions.jsonl"
METRICS_PATH = RESEARCH_DIR / "core_sweep_context_v3/metrics.json"
SANITY_PATH = RESEARCH_DIR / "sanity_report.json"


METHOD_ORDER = [
    "meta_only",
    "generic_caption",
    "oracle_evidence_caption",
    "numbers_sampled_32",
    "numbers_sampled_64",
    "numbers_sampled_128",
]

METHOD_LABELS = {
    "meta_only": "仅元信息",
    "generic_caption": "generic caption（通用说明文本）",
    "oracle_evidence_caption": "oracle evidence caption（oracle 证据说明文本）",
    "numbers_sampled_32": "sampled numbers（采样数值）32 行",
    "numbers_sampled_64": "sampled numbers（采样数值）64 行",
    "numbers_sampled_128": "sampled numbers（采样数值）128 行",
}

TASK_LABELS = {
    "building_load_value_slot": "指定建筑负载数值",
    "quarter_net_electricity_mean_value_slot": "指定 quarter 平均净用电",
    "outdoor_temperature_value_slot": "指定时刻户外温度",
}

TASK_ANALYSIS = {
    "building_load_value_slot": (
        "这个问题考察 exact slot value（精确槽位数值）：必须定位到指定 building（建筑）和 "
        "local_t（局部时间步），读取 non_shiftable_load（不可转移负载）。背景卡片能解释变量含义，"
        "但不会告诉模型该时刻的具体数值。"
    ),
    "quarter_net_electricity_mean_value_slot": (
        "这个问题考察 aggregation（聚合）：要先在每个时间步计算或读取 "
        "net_electricity_without_storage（无储能净用电），再对指定 quarter（四分段）求均值。"
        "稀疏 sampled numbers（采样数值）如果没有覆盖足够多时间点，就很难稳定恢复窗口均值。"
    ),
    "outdoor_temperature_value_slot": (
        "这个问题看似简单，但仍要求从长窗口中定位指定 local_t 的 "
        "outdoor_dry_bulb_temperature（户外干球温度）。sampled numbers 能否答对取决于采样点是否"
        "接近查询时刻，而不是只取决于 prompt（提示文本）长度。"
    ),
}


@dataclass(frozen=True)
class Case:
    title: str
    record_id: str
    tag: str


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def slugify(text: str) -> str:
    text = text.replace("::", "_")
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "_", text)
    return text.strip("_").lower()


def index_predictions(path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for row in load_jsonl(path):
        out.setdefault(row["id"], {})[row["condition"]] = row
    return out


def choose_cases(records: list[dict[str, Any]], preds: dict[str, dict[str, dict[str, Any]]]) -> list[Case]:
    by_id = {r["id"]: r for r in records}

    def ok(record_id: str, cond: str) -> bool:
        return bool(preds.get(record_id, {}).get(cond, {}).get("correct"))

    def pick(task: str, horizon: int | None, predicate) -> str:
        candidates = [
            r for r in records
            if r["task_family"] == task
            and (horizon is None or int(r["horizon"]) == horizon)
            and ok(r["id"], "oracle_evidence_caption")
            and predicate(r["id"])
        ]
        if not candidates:
            raise RuntimeError(f"No case found for {task=} {horizon=}")
        candidates = sorted(candidates, key=lambda r: (int(r["horizon"]), r["id"]))
        return candidates[0]["id"]

    selected = [
        Case(
            "建筑负载单点读取：generic caption 和 sampled numbers 都可能错",
            pick(
                "building_load_value_slot",
                2048,
                lambda rid: (not ok(rid, "generic_caption")) and (not ok(rid, "numbers_sampled_128")),
            ),
            "失败样例",
        ),
        Case(
            "quarter 均值聚合：稀疏采样难以恢复窗口平均",
            pick(
                "quarter_net_electricity_mean_value_slot",
                1024,
                lambda rid: (not ok(rid, "generic_caption")) and (not ok(rid, "numbers_sampled_64")),
            ),
            "聚合失败",
        ),
        Case(
            "户外温度定位：采样数值有时能答对，但仍比 evidence 冗长",
            pick(
                "outdoor_temperature_value_slot",
                None,
                lambda rid: ok(rid, "numbers_sampled_128") and (not ok(rid, "generic_caption")),
            ),
            "对照样例",
        ),
        Case(
            "2048 步窗口：oracle evidence 保持短而稳定",
            pick(
                "outdoor_temperature_value_slot",
                2048,
                lambda rid: (not ok(rid, "generic_caption")) and (not ok(rid, "numbers_sampled_32")),
            ),
            "长窗口样例",
        ),
        Case(
            "控制样例：sampled numbers 可以答对，但成本显著更高",
            pick(
                "building_load_value_slot",
                None,
                lambda rid: ok(rid, "numbers_sampled_32") and ok(rid, "numbers_sampled_64") and ok(rid, "numbers_sampled_128"),
            ),
            "控制样例",
        ),
    ]

    # Defensive check for accidental duplicate IDs.
    counts = Counter(c.record_id for c in selected)
    duplicates = [rid for rid, n in counts.items() if n > 1]
    if duplicates:
        raise RuntimeError(f"Duplicate selected cases: {duplicates}; sample title={by_id[duplicates[0]]['question']}")
    return selected


def translate_question(text: str) -> str:
    m = re.match(r"At local_t=(\d+), what is non_shiftable_load for building (\d+)\?", text)
    if m:
        t, b = m.groups()
        return f"在 local_t={t} 时，building {b} 的 non_shiftable_load（不可转移负载）是多少？"
    m = re.match(r"What is the mean net_electricity_without_storage in quarter (\d+) of this trace window\?", text)
    if m:
        q = m.group(1)
        return f"这个轨迹窗口第 {q} 个 quarter（四分段）的 mean net_electricity_without_storage（平均无储能净用电）是多少？"
    m = re.match(r"At local_t=(\d+), what is outdoor_dry_bulb_temperature\?", text)
    if m:
        t = m.group(1)
        return f"在 local_t={t} 时，outdoor_dry_bulb_temperature（户外干球温度）是多少？"
    return text


def translate_caption(text: str) -> str:
    m = re.match(r"At local_t=(\d+), non_shiftable_load for building (\d+) is (-?[0-9.]+)\.", text)
    if m:
        t, b, v = m.groups()
        return f"在 local_t={t} 时，building {b} 的 non_shiftable_load 为 {v}。"
    m = re.match(r"The mean net_electricity_without_storage in quarter (\d+) is (-?[0-9.]+)\.", text)
    if m:
        q, v = m.groups()
        return f"第 {q} 个 quarter 的 mean net_electricity_without_storage 为 {v}。"
    m = re.match(r"At local_t=(\d+), outdoor_dry_bulb_temperature is (-?[0-9.]+)\.", text)
    if m:
        t, v = m.groups()
        return f"在 local_t={t} 时，outdoor_dry_bulb_temperature 为 {v}。"
    if text.startswith("This CityLearn building-energy trace window"):
        return (
            "这个 CityLearn 建筑能耗轨迹窗口包含 2048 个小时步，覆盖 5 栋建筑，"
            "变量包括建筑负载、太阳能发电、天气、电价和碳强度。"
        )
    return text


def translate_option(option: str) -> str:
    if ". " not in option:
        return option
    letter, value = option.split(". ", 1)
    return f"{letter}. {value}"


def read_trace_window(record: dict[str, Any]) -> list[dict[str, Any]]:
    trace_path = ROOT / record["trace_path"]
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    start = int(record["trace_window"]["start"])
    end = int(record["trace_window"]["end"])
    return data["trace"][start:end]


def save_fig(fig, name: str) -> str:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return f"figures/{path.name}"


def quarter_spans(ax, horizon: int) -> None:
    colors = ["#f4f4f4", "#ffffff", "#f4f4f4", "#ffffff"]
    labels = ["第一段", "第二段", "第三段", "第四段"]
    for i in range(4):
        lo = i * horizon / 4
        hi = (i + 1) * horizon / 4
        ax.axvspan(lo, hi, color=colors[i], zorder=0)
        ax.text((lo + hi) / 2, 0.98, labels[i], transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=8, color="#777777")


def plot_case(record: dict[str, Any], slug: str) -> str:
    rows = read_trace_window(record)
    t = np.arange(len(rows))
    task = record["task_family"]
    evidence = record.get("evidence", {})

    if task == "building_load_value_slot":
        building = int(evidence["slot_building"])
        slot_t = int(evidence["slot_local_t"])
        load = np.asarray([r["buildings"][building - 1]["non_shiftable_load"] for r in rows], dtype=float)
        solar = np.asarray([r["buildings"][building - 1]["solar_generation"] for r in rows], dtype=float)
        temp = np.asarray([r["weather"]["outdoor_dry_bulb_temperature"] for r in rows], dtype=float)

        fig, axes = plt.subplots(3, 1, figsize=(9, 6.2), sharex=True, gridspec_kw={"height_ratios": [3, 2, 2]})
        axes[0].plot(t, load, color="#1f77b4", lw=1.2, label=f"building {building} non_shiftable_load")
        axes[0].axvline(slot_t, color="#d62728", ls="--", lw=1.2, label=f"查询时刻 t={slot_t}")
        axes[0].scatter([slot_t], [load[slot_t]], color="#d62728", s=35, zorder=4)
        axes[0].set_ylabel("load")
        axes[0].set_title("指定建筑的 non_shiftable_load（不可转移负载）")
        axes[0].legend(frameon=False, ncol=2, fontsize=8, loc="upper right")
        axes[1].plot(t, solar, color="#ff7f0e", lw=1.0, label="solar_generation")
        axes[1].set_ylabel("solar")
        axes[1].legend(frameon=False, fontsize=8, loc="upper right")
        axes[2].plot(t, temp, color="#2ca02c", lw=1.0, label="outdoor temperature")
        axes[2].set_ylabel("temp")
        axes[2].set_xlabel("局部时间步")
        axes[2].legend(frameon=False, fontsize=8, loc="upper right")
        return save_fig(fig, slug)

    if task == "quarter_net_electricity_mean_value_slot":
        q = int(evidence["slot_quarter"])
        net = np.asarray([r["totals"]["net_electricity_without_storage"] for r in rows], dtype=float)
        temp = np.asarray([r["weather"]["outdoor_dry_bulb_temperature"] for r in rows], dtype=float)
        solar_total = np.asarray([sum(float(b["solar_generation"]) for b in r["buildings"]) for r in rows], dtype=float)
        quarter_len = max(1, len(rows) // 4)
        start = (q - 1) * quarter_len
        end = len(rows) if q == 4 else q * quarter_len
        mean_value = float(net[start:end].mean())

        fig, axes = plt.subplots(3, 1, figsize=(9, 6.2), sharex=True, gridspec_kw={"height_ratios": [3, 2, 2]})
        quarter_spans(axes[0], len(rows))
        axes[0].plot(t, net, color="#1f77b4", lw=1.2, label="net_electricity_without_storage")
        axes[0].axvspan(start, end, color="#fbe7c6", alpha=0.55, zorder=0)
        axes[0].hlines(mean_value, start, end - 1, colors="#d62728", linestyles="--", lw=1.4, label=f"第 {q} 段均值={mean_value:.3f}")
        axes[0].set_ylabel("net electricity")
        axes[0].set_title("指定 quarter 的 mean net_electricity_without_storage")
        axes[0].legend(frameon=False, ncol=2, fontsize=8, loc="lower right")
        axes[1].plot(t, solar_total, color="#ff7f0e", lw=1.0, label="total solar_generation")
        axes[1].set_ylabel("solar")
        axes[1].legend(frameon=False, fontsize=8, loc="upper right")
        axes[2].plot(t, temp, color="#2ca02c", lw=1.0, label="outdoor temperature")
        axes[2].set_ylabel("temp")
        axes[2].set_xlabel("局部时间步")
        axes[2].legend(frameon=False, fontsize=8, loc="upper right")
        return save_fig(fig, slug)

    if task == "outdoor_temperature_value_slot":
        slot_t = int(evidence["slot_local_t"])
        temp = np.asarray([r["weather"]["outdoor_dry_bulb_temperature"] for r in rows], dtype=float)
        direct = np.asarray([r["weather"]["direct_solar_irradiance"] for r in rows], dtype=float)
        net = np.asarray([r["totals"]["net_electricity_without_storage"] for r in rows], dtype=float)

        fig, axes = plt.subplots(3, 1, figsize=(9, 6.2), sharex=True, gridspec_kw={"height_ratios": [3, 2, 2]})
        axes[0].plot(t, temp, color="#2ca02c", lw=1.2, label="outdoor_dry_bulb_temperature")
        axes[0].axvline(slot_t, color="#d62728", ls="--", lw=1.2, label=f"查询时刻 t={slot_t}")
        axes[0].scatter([slot_t], [temp[slot_t]], color="#d62728", s=35, zorder=4)
        axes[0].set_ylabel("temp")
        axes[0].set_title("指定时刻的 outdoor_dry_bulb_temperature（户外干球温度）")
        axes[0].legend(frameon=False, ncol=2, fontsize=8, loc="upper right")
        axes[1].plot(t, direct, color="#ff7f0e", lw=1.0, label="direct_solar_irradiance")
        axes[1].set_ylabel("irradiance")
        axes[1].legend(frameon=False, fontsize=8, loc="upper right")
        axes[2].plot(t, net, color="#1f77b4", lw=1.0, label="net_electricity_without_storage")
        axes[2].set_ylabel("net electricity")
        axes[2].set_xlabel("局部时间步")
        axes[2].legend(frameon=False, fontsize=8, loc="upper right")
        return save_fig(fig, slug)

    raise ValueError(f"Unsupported task {task}")


def option_text(record: dict[str, Any], letter: str) -> str:
    prefix = f"{letter}."
    for option in record["options"]:
        if option.startswith(prefix):
            return translate_option(option)
    return ""


def prediction_table(record: dict[str, Any], preds: dict[str, dict[str, Any]]) -> str:
    rows = ["| 输入条件 | 原始条件名 | 预测 | 正确性 | Prompt 字符数 | 选项文本 |", "| --- | --- | --- | --- | ---: | --- |"]
    for cond in METHOD_ORDER:
        pred = preds.get(cond)
        if not pred:
            continue
        mark = "正确" if pred["correct"] else "错误"
        rows.append(
            f"| {METHOD_LABELS[cond]} | `{cond}` | `{pred['pred']}` | {mark} | "
            f"{int(pred['prompt_chars'])} | {option_text(record, pred['pred'])} |"
        )
    return "\n".join(rows)


def facts_table(record: dict[str, Any]) -> str:
    rows = ["| 验证字段 | 数值 |", "| --- | --- |"]
    for key, value in record.get("evidence", {}).items():
        if isinstance(value, float):
            value = f"{value:.4f}"
        rows.append(f"| `{key}` | `{value}` |")
    return "\n".join(rows)


def context_card_md(record: dict[str, Any]) -> str:
    card = build_context_card(record)
    translations = {
        "CityLearn context card:": "**CityLearn context card（背景卡片）**",
        "- CityLearn is a building-energy simulation benchmark. A trace is an hourly sequence of building, weather, electricity price, and carbon-intensity variables.":
            "- CityLearn 是 building-energy simulation benchmark（建筑能耗仿真基准）。trace（轨迹）是一段按小时排列的建筑、天气、电价和碳强度变量序列。",
        "- `building` indexes a building in a district or neighborhood.":
            "- `building` 表示 district/neighborhood（区域或社区）中的某栋建筑编号。",
        "- `non_shiftable_load` is a building's electricity demand that cannot be shifted by control actions.":
            "- `non_shiftable_load` 是建筑中不能被控制动作移动的 electricity demand（用电需求）。",
        "- `solar_generation` is local photovoltaic generation. Larger solar_generation can make net electricity lower or negative.":
            "- `solar_generation` 是本地 photovoltaic generation（光伏发电）。太阳能发电越大，net electricity（净用电）可能越低，甚至为负。",
        "- `net_electricity_without_storage` is total non-shiftable building load minus total solar generation in this exported trace.":
            "- `net_electricity_without_storage` 在这个导出轨迹中等于总 non_shiftable_load 减去总 solar_generation，不考虑储能。",
        "- `outdoor_dry_bulb_temperature` is outdoor air temperature.":
            "- `outdoor_dry_bulb_temperature` 是 outdoor air temperature（室外空气温度）。",
        "- Use the trace values to answer. Background definitions do not determine the answer.":
            "- 回答必须使用 trace values（轨迹数值）。背景定义本身不会决定答案。",
        "Trace setup:": "\n**Trace setup（轨迹设置）**",
        "- This is a packaged CityLearn dataset trace, exported as one factual observation window.":
            "- 这是 packaged CityLearn dataset trace（打包数据集轨迹），作为单条 factual observation window（事实观测窗口）导出。",
        "- `local_t` indexes time within the selected hourly window.":
            "- `local_t` 是所选小时窗口内部的局部时间索引。",
        "- For quarter-based questions, divide the local window into four equal contiguous quarters.":
            "- 对 quarter-based questions（四分段问题），把局部窗口划分为四个连续且长度相等的 quarter。",
    }
    task_translations = {
        "read `non_shiftable_load` for the exact building and `local_t` specified in the question.":
            "读取题目指定 building（建筑）和 `local_t` 上的 `non_shiftable_load`。",
        "average `net_electricity_without_storage` over the exact quarter specified in the question.":
            "对题目指定 quarter（四分段）中的 `net_electricity_without_storage` 求平均。",
        "read `outdoor_dry_bulb_temperature` at the exact `local_t` specified in the question.":
            "读取题目指定 `local_t` 上的 `outdoor_dry_bulb_temperature`。",
    }
    lines = []
    for line in card.splitlines():
        if line in translations:
            lines.append(translations[line])
        elif line.startswith("Task rule:"):
            lines.append("\n**Task rule（任务规则）**")
            rule = line.replace("Task rule:", "").strip()
            lines.append(task_translations.get(rule, rule))
        else:
            lines.append(line)
    return "\n".join(lines)


def case_markdown(index: int, case: Case, record: dict[str, Any], preds: dict[str, dict[str, Any]], fig_path: str) -> str:
    options = "\n".join(f"- {translate_option(opt)}" for opt in record["options"])
    task = record["task_family"]
    correct_text = option_text(record, record["answer"])
    return f"""<details>
<summary>Case {index:02d}：{case.title}</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| Case ID | `{record['id']}` |
| 数据源 | CityLearn packaged dataset（打包数据集） |
| 任务类型 | `{task}` / {TASK_LABELS.get(task, task)} |
| Horizon | {record['horizon']} 小时步 |
| 窗口 | start={record['trace_window']['start']}, end={record['trace_window']['end']} |
| 案例标签 | {case.tag} |

<details>
<summary>背景卡片</summary>

{context_card_md(record)}

</details>

<details>
<summary>时序图</summary>

![CityLearn case {index:02d}]({fig_path})

</details>

<details>
<summary>QA 问题</summary>

**问题（中文）**：{translate_question(record['question'])}

**原始问题**：`{record['question']}`

**选项**：

{options}

**正确答案**：`{record['answer']}`，{correct_text}

</details>

<details>
<summary>Caption（说明文本）</summary>

**generic caption（通用说明文本）**：

{translate_caption(record['generic_caption'])}

**oracle evidence caption（oracle 证据说明文本）**：

{translate_caption(record['oracle_evidence_caption'])}

</details>

<details>
<summary>各方法回答</summary>

{prediction_table(record, preds)}

</details>

<details>
<summary>可验证字段</summary>

{facts_table(record)}

</details>

<details>
<summary>案例分析</summary>

{TASK_ANALYSIS.get(task, '')}

这个案例的关键点是：oracle evidence caption（oracle 证据说明文本）只保留回答问题所需的证据槽位，
因此 prompt 很短且答案可核验；generic caption（通用说明文本）只描述变量范围，不包含问题所需数值。
sampled numbers（采样数值）如果答错，通常不是因为模型不知道变量含义，而是因为在长窗口里定位或聚合
指定证据不稳定；如果答对，也需要显著更长的 prompt。

</details>

</details>
"""


def metrics_table(metrics: dict[str, Any]) -> str:
    rows = ["| Condition | Accuracy | Mean prompt chars |", "| --- | ---: | ---: |"]
    for cond in METHOD_ORDER:
        row = metrics["overall"][cond]
        rows.append(f"| `{cond}` | {row['accuracy']:.4f} | {row['mean_prompt_chars']:,.1f} |")
    return "\n".join(rows)


def build_report() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    records = load_jsonl(QA_PATH)
    by_id = {r["id"]: r for r in records}
    preds = index_predictions(PRED_PATH)
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    sanity = json.loads(SANITY_PATH.read_text(encoding="utf-8"))
    cases = choose_cases(records, preds)

    case_blocks = []
    manifest_cases = []
    for idx, case in enumerate(cases, 1):
        record = by_id[case.record_id]
        slug = f"{idx:02d}_{record['task_family']}_{slugify(record['id'])[:90]}"
        fig_path = plot_case(record, slug)
        case_blocks.append(case_markdown(idx, case, record, preds[record["id"]], fig_path))
        manifest_cases.append({
            "index": idx,
            "title": case.title,
            "tag": case.tag,
            "id": record["id"],
            "task_family": record["task_family"],
            "horizon": record["horizon"],
            "figure": fig_path,
            "answer": record["answer"],
            "predictions": {k: {"pred": v["pred"], "correct": v["correct"], "prompt_chars": v["prompt_chars"]} for k, v in preds[record["id"]].items()},
        })

    report = f"""# CityLearn 中文 Case Study：第二个 simulator 的 evidence-caption gate

这个报告展示 CityLearn v2 feasibility gate 中的 5 个代表性案例。所有案例都带有背景卡片，避免“直接问变量名、没有领域背景”的问题；但背景卡片只解释变量和轨迹设置，不包含答案数值。

## 数据与总体结果

- 数据：`{QA_PATH.relative_to(ROOT)}`
- 预测：`{PRED_PATH.relative_to(ROOT)}`
- 样本数：{sanity['n_items']}
- 答案字母分布：{sanity['answer_counts']}
- 任务分布：{sanity['by_task_family']}
- Horizon：512 / 1024 / 2048 小时步

{metrics_table(metrics)}

## 读法

- `generic_caption`（通用说明文本）只说明这段轨迹包含哪些变量。
- `oracle_evidence_caption`（oracle 证据说明文本）是从程序 ground truth（真值）抽取出的最短证据。
- `sampled numbers`（采样数值）把轨迹按固定数量采样成文本表格，prompt 明显更长。
- 本报告不宣称 raw numbers（原始数值）一定失败；控制样例显示 sampled numbers 有时能答对。当前结论是 evidence caption 更短、更稳定、且可验证。

## 案例

{''.join(case_blocks)}
"""

    (OUT_DIR / "README.md").write_text(report, encoding="utf-8")
    (OUT_DIR / "citylearn_case_study.md").write_text(report, encoding="utf-8")
    manifest = {
        "qa_path": str(QA_PATH.relative_to(ROOT)),
        "prediction_path": str(PRED_PATH.relative_to(ROOT)),
        "metrics_path": str(METRICS_PATH.relative_to(ROOT)),
        "n_cases": len(manifest_cases),
        "cases": manifest_cases,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out_dir": str(OUT_DIR), "n_cases": len(manifest_cases)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build_report()
