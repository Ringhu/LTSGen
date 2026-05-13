#!/usr/bin/env python3
"""Render Grid2Op case-study figures and GitHub Markdown report."""
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
        title="Peak quarter localization: sampled numbers miss the late line-loading peak",
        case_id="simqa::grid2op_real::rte_case14_realistic_trace_2048_nooverflow::h1024::s0::peak_rho_quarter",
        source="observation",
        analysis=(
            "This is the cleanest localization failure. The true peak line loading is on line 4 "
            "at local t=806, in the fourth quarter. Generic caption lacks the event location, "
            "and all sampled-numbers budgets answer the wrong quarter despite much longer prompts."
        ),
    ),
    CaseSpec(
        title="Average load aggregation: seeing sampled rows is not enough for window-level averages",
        case_id="simqa::grid2op_real::rte_case14_realistic_trace_1024::h512::s0::max_avg_load",
        source="observation",
        analysis=(
            "This case stresses aggregation over the whole window. The correct evidence is the "
            "window-average active power of load 1. Generic caption and all sampled numeric prompts "
            "choose a distractor, showing that raw sampled rows do not reliably substitute for "
            "the requested statistic."
        ),
    ),
    CaseSpec(
        title="Trend control case: numeric samples can solve simple aggregate trend questions",
        case_id="simqa::grid2op_real::rte_case14_realistic_trace_2048_nooverflow::h1024::s0::total_load_trend",
        source="observation",
        analysis=(
            "This is a control case. Sampled numbers solve the trend question, while generic caption "
            "still fails. It prevents overclaiming: numeric prompting does not always fail; the "
            "observed weakness is concentrated in localization and aggregation-heavy evidence."
        ),
    ),
    CaseSpec(
        title="Counterfactual threshold: a small intervention crosses the overload boundary",
        case_id="simqa::grid2op_real_cf::h1024_t128_line0::cf_intervention_overload_severity",
        source="counterfactual",
        analysis=(
            "Disconnecting line 0 barely changes max-rho but pushes the post-intervention peak to "
            "1.024, just over the 1.00 overload threshold. Low-budget sampled numbers miss this "
            "boundary; the oracle evidence states the threshold-relevant fact directly."
        ),
    ),
    CaseSpec(
        title="Counterfactual direction: paired traces require comparing factual and intervention peaks",
        case_id="simqa::grid2op_real_cf::h1024_t128_line5::cf_peak_rho_direction",
        source="counterfactual",
        analysis=(
            "Line 5 is a mild intervention: the post-peak max-rho rises from 0.999 to 1.138. "
            "The question requires paired factual/counterfactual comparison with a stated tolerance. "
            "Generic caption fails because it never provides the paired outcome facts."
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


def read_trace_window(record: dict[str, Any]) -> list[dict[str, Any]]:
    data = json.loads((ROOT / record["trace_path"]).read_text(encoding="utf-8"))
    start = int(record["trace_window"]["start"])
    end = int(record["trace_window"]["end"])
    return data["trace"][start:end]


def read_pair(record: dict[str, Any]) -> dict[str, Any]:
    return json.loads((ROOT / record["pair_path"]).read_text(encoding="utf-8"))


def quarter_spans(ax, horizon: int) -> None:
    colors = ["#f4f4f4", "#ffffff", "#f4f4f4", "#ffffff"]
    labels = ["Q1", "Q2", "Q3", "Q4"]
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
        ax.plot(t, max_rho, label="max rho across lines", color="#1f77b4", lw=1.6)
        ax.plot(t, line_rho, label=f"rho line {line}", color="#ff7f0e", lw=1.1, alpha=0.85)
        ax.axvline(peak_t, color="#d62728", ls="--", lw=1.2, label=f"peak t={peak_t}")
        ax.scatter([peak_t], [float(evidence["peak_rho"])], color="#d62728", s=35, zorder=4)
        ax.set_ylabel("rho")
        ax.set_xlabel("local timestep")
        ax.set_title("Peak line loading occurs in the fourth quarter")
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
            ax.plot(t, y, lw=1.2, label=f"load {idx} (mean={y.mean():.2f})")
            ax.axhline(y.mean(), lw=0.8, ls="--", alpha=0.45)
        ax.set_ylabel("active power")
        ax.set_xlabel("local timestep")
        ax.set_title("Window-level average active power by candidate load")
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
        ax.plot(t, total, color="#1f77b4", lw=1.3, label="total load")
        ax.hlines(first, 0, q - 1, colors="#2ca02c", linestyles="--", lw=1.4, label=f"Q1 mean={first:.2f}")
        ax.hlines(last, len(rows) - q, len(rows) - 1, colors="#d62728", linestyles="--", lw=1.4, label=f"Q4 mean={last:.2f}")
        ax.set_ylabel("total active load")
        ax.set_xlabel("local timestep")
        ax.set_title("Mean total load increases from first to last quarter")
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
    ax.plot(t, f_max, color="#1f77b4", lw=1.3, label="factual max rho")
    ax.plot(t, i_max, color="#d62728", lw=1.3, label="intervention max rho")
    ax.axvline(step, color="#555555", ls="--", lw=1.1, label=f"disconnect line {line} at t={step}")
    ax.axhline(threshold, color="#9467bd", ls=":", lw=1.2, label="overload threshold 1.00")
    peak_t = int(np.argmax(i_max[step + 1:]) + step + 1)
    ax.scatter([peak_t], [i_max[peak_t]], color="#d62728", s=32, zorder=4)
    ax.set_ylabel("max rho")
    ax.set_title("Factual vs intervention post-event line loading")
    ax.legend(frameon=False, ncol=2, fontsize=8)
    status = np.asarray([r["line_status"][line] for r in intervention[:n]], dtype=float)
    axes[1].step(t, status, where="post", color="#2ca02c", lw=1.3)
    axes[1].axvline(step, color="#555555", ls="--", lw=1.0)
    axes[1].set_ylim(-0.1, 1.1)
    axes[1].set_ylabel(f"line {line}\nstatus")
    axes[1].set_xlabel("local timestep")
    return save_fig(fig, slug)


def option_text(record: dict[str, Any], letter: str) -> str:
    prefix = f"{letter}."
    for opt in record["options"]:
        if opt.startswith(prefix):
            return opt
    return ""


def pred_table(record: dict[str, Any], preds: dict[str, dict[str, Any]]) -> str:
    rows = ["| 输入条件 | 预测 | 正确性 | Prompt chars | 选项文本 |", "| --- | --- | --- | ---: | --- |"]
    for cond in METHOD_ORDER:
        if cond not in preds:
            continue
        p = preds[cond]
        mark = "✓" if p["correct"] else "✗"
        rows.append(
            f"| `{cond}` | `{p['pred']}` | {mark} | {int(p['prompt_chars'])} | {option_text(record, p['pred'])} |"
        )
    return "\n".join(rows)


def format_options(record: dict[str, Any]) -> str:
    return "\n".join(f"- {opt}" for opt in record["options"])


def facts_table(record: dict[str, Any]) -> str:
    facts = record.get("evidence", {})
    rows = ["| Fact | Value |", "| --- | --- |"]
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
<summary>Case {idx:02d}: {spec.title}</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| Case ID | `{record['id']}` |
| Source | `{spec.source}` |
| Horizon | `{record['horizon']}` |
| Task family | `{record['task_family']}` |
| Correct answer | `{correct}` |
| Answer label | `{record.get('answer_label', '')}` |
| GT source | `trace_array` |

关键结论：{spec.analysis}

<details>
<summary>时序图</summary>

![{record['id']}]({image})

</details>

<details>
<summary>QA 问题</summary>

**Question**

{record['question']}

**Options**

{format_options(record)}

**Correct answer**: `{correct}` - {option_text(record, correct)}

</details>

<details>
<summary>Captions / Evidence</summary>

**Generic caption**

{record['generic_caption']}

**Oracle evidence caption**

{record['oracle_evidence_caption']}

**Verification facts**

{facts_table(record)}

</details>

<details>
<summary>模型回答</summary>

{pred_table(record, preds)}

</details>

<details>
<summary>Case 分析</summary>

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
        selected_records.append({"spec": spec.__dict__, "record": record})

    report = f"""# Grid2Op Medium-Horizon Case Study

This report visualizes selected Grid2Op simulator-derived TS-QA cases. Ground truth is computed from trace arrays or paired factual/counterfactual traces. LLMs are only evaluated as answerers; they do not define the correct answer.

## Coverage

| Dimension | Value |
| --- | --- |
| Environment | `rte_case14_realistic` |
| Horizons | `512`, `1024`, `2048` in the benchmark; selected cases use `512/1024` |
| Observation cases | 3 |
| Counterfactual cases | 2 |
| Methods shown | `meta_only`, `generic_caption`, `oracle_evidence_caption`, sampled numeric prompts |

## Takeaways

- Observation/localization and aggregation cases show the largest gap: oracle evidence is short and correct, while sampled numeric prompts are long and often wrong.
- Counterfactual cases are useful for verifiability and threshold analysis, but current numeric prompts can solve many of them when the relevant facts are explicit in the sampled table.
- Case-level visualizations make the intended evidence clear: peak location, window average, first-vs-last quarter mean, and factual/counterfactual post-intervention max-rho.

## Cases

{chr(10).join(sections)}
"""

    (OUT_DIR / "grid2op_case_study.md").write_text(report, encoding="utf-8")
    (OUT_DIR / "selected_cases.json").write_text(json.dumps(selected_records, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "manifest.json").write_text(json.dumps({"cases": manifests}, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "README.md").write_text(
        "# Grid2Op Medium-Horizon Case Study\n\n"
        "This directory contains the GitHub-renderable case-study report for the "
        "current Grid2Op TS-QA pilot.\n\n"
        "- [grid2op_case_study.md](grid2op_case_study.md): collapsible report with "
        "time-series plots, QA prompts, captions/evidence, and method answers.\n"
        "- `figures/`: PNG time-series plots for 3 observation cases and 2 "
        "counterfactual cases.\n"
        "- `selected_cases.json`: selected QA records and case specs.\n"
        "- `manifest.json`: compact manifest for downstream scripts.\n\n"
        "The report is meant to support the paper framing that task-conditioned, "
        "verifiable evidence captions provide a short and reliable interface, "
        "while generic captions and sampled numeric prompts can fail on "
        "localization, aggregation, and paired-trace comparison tasks.\n",
        encoding="utf-8",
    )
    print(json.dumps({"out_dir": str(OUT_DIR), "n_cases": len(CASES), "figures": len(list(FIG_DIR.glob('*.png')))}, indent=2))


if __name__ == "__main__":
    main()
