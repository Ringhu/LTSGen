#!/usr/bin/env python3
"""Render the natural balanced8 QA case-study report with time-series figures."""
from __future__ import annotations

import html
import json
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CASE_DIR = ROOT / ".research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519"
NATURAL_JSONL = CASE_DIR / "natural_multisim_v5_balanced8.jsonl"
REVIEW_JSON = CASE_DIR / "natural_multisim_v5_balanced8_review.json"
RAW_JSONL = (
    ROOT
    / ".research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/"
    / "case_study_simulator_data_20260518/raw_samples/balanced_eval_per_source8.jsonl"
)
FIG_DIR = CASE_DIR / "figures"
OUT_MD = CASE_DIR / "NATURAL_QA_BALANCED8_CASE_STUDY_ANALYSIS_20260519_ZH.md"


SELECTED = [
    (
        "Grid2Op line-disconnection stress check",
        "Grid2Op 断线后的线路压力检查",
        "multisim_qcc_v5_aiops_v3::grid2op::grid2op_broad_cf::h2048_c-1_t512_line1::post769_1025::grid_counterfactual_peak_stress",
        "figures/01_grid2op_counterfactual_stress.svg",
        "把 global event 和 local window 的关系放进场景说明，问题本身只问调度员关心的反事实影响。",
    ),
    (
        "Grid2Op demand-stress timing review",
        "Grid2Op 总需求与线路压力先后关系复盘",
        "multisim_qcc_v5_aiops_v3::grid2op::grid2op_broad::rte_case14_realistic_chronic4_trace_2048_nooverflow::w512_1536::grid_temporal_lead_lag",
        "figures/02_grid2op_lead_lag.svg",
        "这是 lead-lag 边界样本：最强关系在 lag 0，因此答案不是某个变量领先，而是同步/无稳定领先方。",
    ),
    (
        "CityLearn demand-pressure planning",
        "CityLearn 建筑需求压力判断",
        "multisim_qcc_v5_aiops_v3::citylearn::citylearn_broad::citylearn_challenge_2022_phase_1_start2048_h2048_b5::w1792_2048::city_domain_demand_context",
        "figures/03_citylearn_demand_pressure.svg",
        "把负载均值和峰值转成建筑控制器可用的需求压力状态，而不是只问 x0 的统计量。",
    ),
    (
        "CityLearn isolated demand spike",
        "CityLearn 建筑用电孤立尖峰定位",
        "multisim_qcc_v5_aiops_v3::citylearn::citylearn_broad::citylearn_challenge_2022_phase_1_start6144_h2048_b5::w512_768::city_anomaly_total_load",
        "figures/04_citylearn_spike.svg",
        "尖峰题必须给出 z-score 阈值和时间三等分规则，避免“明显尖峰”成为主观判断。",
    ),
    (
        "FinRL GOOG market-regime review",
        "FinRL GOOG 市场状态复盘",
        "multisim_qcc_v5_aiops_v3::finrl_scaled::finrl_broad::GOOG::w2299_2555::fin_domain_market_regime",
        "figures/05_finrl_goog_regime.svg",
        "直接把 ticker 放进场景，并用总收益率与波动率规则形成金融分析判断。",
    ),
    (
        "FinRL MRK drawdown-risk review",
        "FinRL MRK 回撤风险复盘",
        "multisim_qcc_v5_aiops_v3::finrl_scaled::finrl_broad::MRK::w2043_2555::fin_drawdown_price",
        "figures/06_finrl_mrk_drawdown.svg",
        "回撤题比最高点位置更接近真实风险复盘，需要把 drawdown band 写清楚。",
    ),
    (
        "Traffic speed-queue timing review",
        "交通车速与排队先后关系复盘",
        "multisim_qcc_v5_aiops_v3::traffic::traffic_broad::traffic_scenario_020::traffic_speed_queue_lead_lag",
        "figures/07_traffic_lead_lag.svg",
        "该样本体现 reviewer 的价值：负相关时必须写成绝对相关强度，并说明稳定性余量。",
    ),
    (
        "Traffic signal-policy queue comparison",
        "交通信号策略的队列影响比较",
        "multisim_qcc_v5_aiops_v3::traffic::traffic_broad::traffic_scenario_025::traffic_signal_counterfactual_queue",
        "figures/08_traffic_signal_queue.svg",
        "把 factual-vs-baseline 均值比较改成交通工程师关心的策略是否改善排队。",
    ),
    (
        "Water combined-stress state",
        "供水系统综合压力状态判断",
        "multisim_qcc_v5_aiops_v3::water::water_broad::water_scenario_005::water_combined_stress_context",
        "figures/09_water_combined_stress.svg",
        "该题结合压力评分、事件时段和严重低压标记，比单变量 extrema 更接近运维判断。",
    ),
    (
        "Water event-recovery review",
        "供水事件后的水压恢复复盘",
        "multisim_qcc_v5_aiops_v3::water::water_broad::water_scenario_000::water_event_recovery_context",
        "figures/10_water_event_recovery.svg",
        "通过事件前、中、后三段均值判断恢复、持续承压或过冲，答案仍可由数值复核。",
    ),
    (
        "AIOpsLab memory-pressure triage",
        "AIOpsLab 内存压力排查",
        "multisim_qcc_v5_aiops_v3::aiopslab_official_v3::aiopslab_official::port_misconfig_seed0_user-service::case000::aiops_official_window_memory",
        "figures/11_aiops_memory.svg",
        "AIOps 正例必须由遥测窗口本身支持；这里用 5% 相对差异规则判断内存压力是否相近。",
    ),
    (
        "AIOpsLab network-volatility triage",
        "AIOpsLab 网络接收速率波动排查",
        "multisim_qcc_v5_aiops_v3::aiopslab_official_v3::aiopslab_official::port_misconfig_seed0_user-service::case000::aiops_official_network_volatility",
        "figures/12_aiops_network_volatility.svg",
        "该题保留为纯遥测正例；metadata/provenance/fault-context 类问题则单独排除。",
    ),
]


COLORS = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#d97706"]


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compact_value(value: object) -> str:
    if isinstance(value, float):
        if math.isfinite(value):
            return f"{value:.4g}"
        return str(value)
    if isinstance(value, dict):
        items = list(value.items())
        inner = ", ".join(f"{k}={compact_value(v)}" for k, v in items[:5])
        if len(items) > 5:
            inner += ", ..."
        return "{" + inner + "}"
    return str(value)


def support_text(slots: dict) -> str:
    parts = [f"`{key}={compact_value(value)}`" for key, value in slots.items()]
    return ", ".join(parts)


def options_text(case: dict) -> list[str]:
    lines = []
    for opt in case["options"]:
        lines.append(f"- {opt['letter']}. {opt['en']} / {opt['zh']}")
    return lines


def gold_text(case: dict) -> str:
    letter = case["gold_answer"]
    option = next((opt for opt in case["options"] if opt["letter"] == letter), None)
    if option:
        return f"`{letter}` / {option['en']} / {option['zh']}"
    return f"`{letter}` / {case['gold_answer_zh']}"


def finite_columns(values: list[list[float]]) -> list[list[float]]:
    if not values:
        return []
    width = max(len(row) for row in values)
    cols: list[list[float]] = [[] for _ in range(width)]
    for row in values:
        for idx in range(width):
            try:
                value = float(row[idx])
            except (IndexError, TypeError, ValueError):
                value = float("nan")
            cols[idx].append(value if math.isfinite(value) else float("nan"))
    return cols


def downsample(values: list[list[float]], max_points: int = 420) -> list[list[float]]:
    if len(values) <= max_points:
        return values
    step = math.ceil(len(values) / max_points)
    sampled = values[::step]
    if sampled[-1] is not values[-1]:
        sampled.append(values[-1])
    return sampled


def y_for(value: float, ymin: float, ymax: float, top: float, height: float) -> float:
    if not math.isfinite(value):
        return top + height / 2
    if ymax <= ymin:
        norm = 0.5
    else:
        norm = (value - ymin) / (ymax - ymin)
    return top + height * (1.0 - norm)


def marker_positions(case: dict, n_points: int) -> list[tuple[float, str]]:
    slots = case.get("support_slots") or {}
    positions: list[tuple[float, str]] = []
    task = case["task_family"]
    if any(key in task for key in ("volatility", "anomaly", "extrema")):
        positions.extend([(1 / 3, "1/3"), (2 / 3, "2/3")])
    if any(key in task for key in ("window", "memory")) and "first_mean" in slots:
        positions.append((0.5, "half"))
    for key, label in (
        ("event_index", "event"),
        ("drawdown_peak_index", "peak"),
        ("drawdown_trough_index", "trough"),
    ):
        value = slots.get(key)
        if isinstance(value, (int, float)) and n_points > 1:
            positions.append((max(0.0, min(1.0, float(value) / (n_points - 1))), label))
    return positions


def render_svg(raw: dict, case: dict, out_path: Path, title: str) -> None:
    values = raw.get("raw_compact_values") or raw.get("values") or []
    values = downsample(values)
    cols = finite_columns(values)
    labels = case.get("variables_zh") or [f"x{i}" for i in range(len(cols))]
    width, height = 920, 360
    left, right, top, bottom = 72, 28, 56, 72
    plot_w = width - left - right
    plot_h = height - top - bottom
    n = len(values)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="28" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">{html.escape(title)}</text>',
        f'<text x="{left}" y="48" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">per-variable min-max normalized raw compact values; x-axis is local time step</text>',
    ]
    for i in range(5):
        y = top + plot_h * i / 4
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#374151" stroke-width="1.2"/>')
    parts.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#374151" stroke-width="1.2"/>')

    for frac, label in marker_positions(case, n):
        x = left + plot_w * frac
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}" stroke="#9ca3af" stroke-width="1" stroke-dasharray="4 4"/>')
        parts.append(f'<text x="{x + 4:.1f}" y="{top + 14}" font-family="Arial, sans-serif" font-size="11" fill="#6b7280">{html.escape(label)}</text>')

    for idx, col in enumerate(cols[: len(COLORS)]):
        finite = [v for v in col if math.isfinite(v)]
        if not finite:
            continue
        ymin, ymax = min(finite), max(finite)
        pts = []
        for pos, value in enumerate(col):
            x = left + plot_w * (pos / max(1, len(col) - 1))
            y = y_for(value, ymin, ymax, top, plot_h)
            pts.append(f"{x:.1f},{y:.1f}")
        color = COLORS[idx % len(COLORS)]
        parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2.0" stroke-linejoin="round" stroke-linecap="round"/>')
        legend_y = top + plot_h + 28 + idx * 17
        label = labels[idx] if idx < len(labels) else f"x{idx}"
        parts.append(f'<line x1="{left + idx * 190}" y1="{legend_y - 4}" x2="{left + 24 + idx * 190}" y2="{legend_y - 4}" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<text x="{left + 30 + idx * 190}" y="{legend_y}" font-family="Arial, sans-serif" font-size="12" fill="#111827">{html.escape(label[:28])}</text>')

    parts.append(f'<text x="{left}" y="{height - 16}" font-family="Arial, sans-serif" font-size="11" fill="#6b7280">n={len(raw.get("raw_compact_values") or raw.get("values") or [])}; plotted n={n}</text>')
    parts.append("</svg>")
    out_path.write_text("\n".join(parts), encoding="utf-8")


def build_report(cases: dict[str, dict], raws: dict[str, dict], reviews: dict[str, dict]) -> str:
    review_values = list(reviews.values())
    by_scope = Counter(review["review_scope"] for review in review_values)
    by_decision = Counter(review["decision"] for review in review_values)
    by_risk = Counter(review["accuracy_risk"] for review in review_values)
    candidate = [r for r in review_values if r["review_scope"] == "gpt55_candidate"]
    positive = [
        r
        for r in candidate
        if r["decision"] == "keep"
        and r["naturalness_score"] >= 4
        and r["answerability_score"] >= 4
        and r["accuracy_risk"] == "low"
    ]
    lines = [
        "# Natural QA Balanced8 Case Study 分析报告（2026-05-19）",
        "",
        "目标：参考 `natural_qa_pilot_20260519/NATURAL_TSQA_CASE_PILOT_20260519_ZH.md` 的图文格式，把 `natural_multisim_v5_balanced8.jsonl` 中通过 reviewer gate 的自然 TS-QA 样本整理成可直接阅读的 case study。每个 case 都配有时序图、英文问题、中文翻译、双语选项和可验证证据。",
        "",
        "## 1. 总体结论",
        "",
        "| 指标 | 结果 |",
        "| --- | ---: |",
        f"| 总样本数 | `{len(review_values)}` |",
        f"| review scope | `{dict(by_scope)}` |",
        f"| decision | `{dict(by_decision)}` |",
        f"| risk | `{dict(by_risk)}` |",
        f"| candidate 正例通过 | `{len(positive)}/{len(candidate)}` |",
        "",
        "设计原则：",
        "",
        "- 场景说明负责交代 domain、变量含义、时间轴和必要规则。",
        "- 问题本身只问一个自然决策，不暴露内部 verifier 实现细节。",
        "- 选项是普通读者能理解的短答案，并保留原始 gold answer letter。",
        "- Evidence 只使用 deterministic support slots 或 raw trace 统计，LLM/reviewer 不决定答案。",
        "- 图中展示的是每个变量按自身 min-max 归一化后的 raw compact values；数值判定仍以 Evidence 和 Support slots 为准。",
        "",
        "## 2. 图文 Case Study",
        "",
    ]
    for idx, (title_en, title_zh, row_id, figure, design_note) in enumerate(SELECTED, start=1):
        case = cases[row_id]
        raw = raws[row_id]
        review = reviews[row_id]
        lines.extend(
            [
                f"### {idx}. {title_en}（{title_zh}）",
                "",
                f"![]({figure})",
                "",
                f"**Domain/source:** `{case['source']}`",
                "",
                f"**Task family:** `{case['task_family']}`",
                "",
                f"**Row ID:** `{case['id']}`",
                "",
                f"**Reviewer:** `decision={review['decision']}`, `naturalness={review['naturalness_score']}`, `answerability={review['answerability_score']}`, `risk={review['accuracy_risk']}`",
                "",
                f"**Scene EN:** {case['scene_en']}",
                "",
                f"**场景中文:** {case['scene_zh']}",
                "",
                f"**Question EN:** {case['question_en']}",
                "",
                f"**问题中文:** {case['question_zh']}",
                "",
                "**Options / 选项:**",
                "",
                *options_text(case),
                "",
                f"**Gold:** {gold_text(case)}",
                "",
                f"**Evidence EN:** {case['evidence_en']}",
                "",
                f"**证据中文:** {case['evidence_zh']}",
                "",
                f"**Support slots:** {support_text(case.get('support_slots') or {})}",
                "",
                f"**原始问题:** {case['original_question']}",
                "",
                f"**设计说明:** {design_note}",
                "",
                f"**Reviewer 说明:** {review['reason_zh']}",
                "",
            ]
        )

    lines.extend(
        [
            "## 3. 跨域观察",
            "",
            "- `Grid2Op` 的关键是把反事实差值方向、global/local 时间轴和 lead-lag 判定规则写清楚。",
            "- `CityLearn` 的高质量问题通常不是简单问均值，而是把负载统计转成控制器的需求压力或尖峰检测判断。",
            "- `FinRL` 必须明确 ticker、价格序列和金融规则，避免出现“股票代码由问题指定”这种不自然描述。",
            "- `Traffic` 的 lead-lag 问题需要特别谨慎；负相关时要写绝对相关强度，并说明同步相关与最佳滞后之间的差距。",
            "- `Water` 适合做供水状态、事件恢复和综合压力判断，这些题天然需要领域状态词和数值证据结合。",
            "- `AIOpsLab` 必须把纯遥测问题和 metadata-only 问题分开；metadata/provenance/fault-context 不应进入纯 TS-QA 正例池。",
            "",
            "## 4. 产物索引",
            "",
            "| 类型 | 路径 |",
            "| --- | --- |",
            "| 自然化 QA JSONL | `.research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/natural_multisim_v5_balanced8.jsonl` |",
            "| GPT-5.5 reviewer 报告 | `.research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/NATURAL_QA_BALANCED8_REVIEW_20260519_ZH.md` |",
            "| 本 case study 报告 | `.research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/NATURAL_QA_BALANCED8_CASE_STUDY_ANALYSIS_20260519_ZH.md` |",
            "| 时序图目录 | `.research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/figures/` |",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    cases = {row["id"]: row for row in load_jsonl(NATURAL_JSONL)}
    raws = {row["id"]: row for row in load_jsonl(RAW_JSONL)}
    review_payload = json.loads(REVIEW_JSON.read_text(encoding="utf-8"))
    reviews = {row["id"]: row for row in review_payload["reviews"]}

    for title_en, title_zh, row_id, figure, _ in SELECTED:
        if row_id not in cases:
            raise KeyError(f"missing natural case: {row_id}")
        if row_id not in raws:
            raise KeyError(f"missing raw case: {row_id}")
        if row_id not in reviews:
            raise KeyError(f"missing review: {row_id}")
        render_svg(raws[row_id], cases[row_id], CASE_DIR / figure, f"{title_en} / {title_zh}")

    OUT_MD.write_text(build_report(cases, raws, reviews), encoding="utf-8")
    print(OUT_MD)
    print(FIG_DIR)


if __name__ == "__main__":
    main()
