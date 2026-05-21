#!/usr/bin/env python3
"""Render SVG figures and a case-study report for public raw TSQA v4."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / ".research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521"
FIG_DIR = DATA_DIR / "figures"
REPORT = DATA_DIR / "PUBLIC_RAW_TSQA_V4_REPORT_WITH_CASE_STUDY_20260521_ZH.md"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def esc(text: Any) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def save_bar(counter: Counter[str], path: Path, title: str) -> None:
    labels = list(counter.keys())
    values = [counter[label] for label in labels]
    width, height = 900, 420
    margin_l, margin_b, margin_t, margin_r = 70, 110, 50, 30
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    max_v = max(values) if values else 1
    bar_w = plot_w / max(len(values), 1) * 0.62
    step = plot_w / max(len(values), 1)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="18" font-family="Arial">{esc(title)}</text>',
        f'<line x1="{margin_l}" y1="{height - margin_b}" x2="{width - margin_r}" y2="{height - margin_b}" stroke="#333"/>',
        f'<line x1="{margin_l}" y1="{margin_t}" x2="{margin_l}" y2="{height - margin_b}" stroke="#333"/>',
    ]
    for idx, (label, value) in enumerate(zip(labels, values)):
        x = margin_l + idx * step + (step - bar_w) / 2
        bar_h = plot_h * value / max_v
        y = height - margin_b - bar_h
        label_x = x + bar_w / 2
        label_y = height - margin_b + 18
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="#4c78a8"/>')
        parts.append(f'<text x="{label_x:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-size="12" font-family="Arial">{value}</text>')
        parts.append(
            f'<text x="{label_x:.1f}" y="{label_y}" text-anchor="end" transform="rotate(-25 {label_x:.1f} {label_y})" font-size="11" font-family="Arial">{esc(label)}</text>'
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def save_length_hist(rows: list[dict[str, Any]], path: Path) -> None:
    save_bar(Counter(str(len(row["time_series"]["values"])) for row in rows), path, "Raw Time-series Lengths")


def scale(values: list[float], lo: float, hi: float, out_top: float, out_bottom: float) -> list[float]:
    if hi == lo:
        return [(out_top + out_bottom) / 2 for _ in values]
    return [out_bottom - (value - lo) / (hi - lo) * (out_bottom - out_top) for value in values]


def save_case_plot(row: dict[str, Any], path: Path) -> None:
    values = row["time_series"]["values"]
    columns = row["time_series"]["columns"]
    width = 980
    panel_h = 150
    margin_l, margin_r, margin_t = 110, 35, 52
    height = margin_t + panel_h * len(columns) + 45
    plot_w = width - margin_l - margin_r
    xs = list(range(len(values)))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="17" font-family="Arial">{esc(row["domain"])} | answer {esc(row["answer"])}: {esc(row["answer_label"])}</text>',
    ]
    for idx, column in enumerate(columns):
        top = margin_t + idx * panel_h
        bottom = top + panel_h - 34
        series = [record[idx] for record in values]
        lo, hi = min(series), max(series)
        x_scaled = [margin_l + (x / max(len(xs) - 1, 1)) * plot_w for x in xs]
        y_scaled = scale(series, lo, hi, top + 10, bottom)
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(x_scaled, y_scaled))
        parts.append(f'<line x1="{margin_l}" y1="{bottom}" x2="{width - margin_r}" y2="{bottom}" stroke="#ddd"/>')
        parts.append(f'<line x1="{margin_l}" y1="{top + 10}" x2="{margin_l}" y2="{bottom}" stroke="#ddd"/>')
        parts.append(f'<polyline points="{points}" fill="none" stroke="#4c78a8" stroke-width="1.5"/>')
        parts.append(f'<text x="12" y="{top + 34}" font-size="12" font-family="Arial">{esc(column)}</text>')
        parts.append(f'<text x="{margin_l - 8}" y="{top + 16}" text-anchor="end" font-size="10" font-family="Arial">{lo:.4g}</text>')
        parts.append(f'<text x="{margin_l - 8}" y="{bottom}" text-anchor="end" font-size="10" font-family="Arial">{hi:.4g}</text>')
    parts.append(f'<text x="{width / 2}" y="{height - 10}" text-anchor="middle" font-size="12" font-family="Arial">time index</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def pick_cases(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered_domains = ["power_grid", "building_energy", "traffic", "water_service", "service_telemetry", "market"]
    cases = []
    for domain in ordered_domains:
        domain_rows = [row for row in rows if row["domain"] == domain]
        if not domain_rows:
            continue
        non_a = [row for row in domain_rows if row["answer"] != "A"]
        cases.append(sorted(non_a or domain_rows, key=lambda row: (row["answer"], row["id"]))[0])
    return cases


def option_lines(options: dict[str, str]) -> list[str]:
    return [f"- {letter}. {text}" for letter, text in options.items()]


def variable_lines(variables: dict[str, str]) -> list[str]:
    return [f"- `{name}`: {desc}" for name, desc in variables.items()]


def bilingual_case_lines(row: dict[str, Any], audit: dict[str, Any]) -> list[str]:
    return [
        "#### English Version",
        "",
        "**Context**",
        "",
        row["context_en"],
        "",
        "**Time Axis**",
        "",
        row["time_series"]["time_axis"],
        "",
        "**Variables**",
        "",
        *variable_lines(row["variable_descriptions_en"]),
        "",
        "**Decision Guide**",
        "",
        row["decision_rule_en"],
        "",
        "**Question**",
        "",
        row["question_en"],
        "",
        "**Options**",
        "",
        *option_lines(row["options_en"]),
        "",
        f"**Gold Answer**: `{row['answer']}` / `{row['answer_label']}`",
        "",
        "**Audit Evidence**",
        "",
        audit["oracle_evidence_en"],
        "",
        "#### 中文版本",
        "",
        "**场景**",
        "",
        row["context_zh"],
        "",
        "**时间轴**",
        "",
        row["time_series"]["time_axis_zh"],
        "",
        "**变量**",
        "",
        *variable_lines(row["variable_descriptions_zh"]),
        "",
        "**判定规则**",
        "",
        row["decision_rule_zh"],
        "",
        "**问题**",
        "",
        row["question_zh"],
        "",
        "**选项**",
        "",
        *option_lines(row["options_zh"]),
        "",
        f"**标准答案**: `{row['answer']}` / `{row['answer_label_zh']}`",
        "",
        "**审计证据**",
        "",
        audit["oracle_evidence_zh"],
        "",
    ]


def render_report(rows: list[dict[str, Any]], audit_by_id: dict[str, dict[str, Any]], case_rows: list[dict[str, Any]]) -> str:
    summary = json.loads((DATA_DIR / "public_raw_tsqa_v4_summary.json").read_text(encoding="utf-8"))
    sanity = json.loads((DATA_DIR / "public_raw_tsqa_v4_sanity_check.json").read_text(encoding="utf-8"))
    lines = [
        "# Public Raw TSQA v4 图文报告与 Case Study（2026-05-21）",
        "",
        "## 一句话结论",
        "",
        "本轮已把 benchmark 标准从 v3 的技术验证格式推进到 public raw time-series QA 格式：同一条 canonical raw-series 样本同时导出 LLM text view 和 TS-LLM array view，内部审计证据和 oracle evidence 不进入主评测 prompt。",
        "",
        "## 产物结构",
        "",
        "| 文件 | 用途 |",
        "| --- | --- |",
        "| `canonical_raw_tsqa_v4.jsonl` | 一份标准 raw time-series QA 数据 |",
        "| `llm_text_view.jsonl` | 普通 LLM 使用：完整时序转 CSV 文本并放入 prompt |",
        "| `tsllm_array_view.jsonl` | TS-LLM 使用：原始数组 + 同一问题文本 |",
        "| `oracle_evidence.jsonl` | oracle evidence / upper-bound 条件 |",
        "| `audit_support.jsonl` | 内部审计证据字段、verifier rule、source 和 reviewer trace |",
        "| `mismatch_audit.jsonl` | 被排除样本及原因 |",
        "",
        "## 规模与覆盖",
        "",
        f"- canonical rows: `{summary['n']}`",
        f"- raw/v3 gold mismatch or excluded: `{summary['n_mismatch_excluded']}`",
        f"- public forbidden issues: `{summary['n_public_forbidden_issues']}`",
        f"- sanity check pass: `{sanity['pass']}`",
        f"- bilingual completeness: `{summary['n']}` / `{summary['n']}` canonical rows contain English and Chinese context, variables, decision guide, question, options, answer label, and evidence",
        f"- raw series length: `{summary['time_series_lengths']}`",
        f"- answer distribution: `{json.dumps(summary['answer_distribution'], ensure_ascii=False)}`",
        "",
        "![Domain distribution](figures/domain_distribution.svg)",
        "",
        "![Answer distribution](figures/answer_distribution.svg)",
        "",
        "![Raw series lengths](figures/time_series_lengths.svg)",
        "",
        "## 为什么 LLM 和 TS-LLM 可以复用同一批数据",
        "",
        "同一个 canonical record 保存原始时序、变量解释、问题、选项和 gold answer。LLM view 只是把 `time_series.values` 序列化成 CSV 文本；TS-LLM view 则直接保留同一个数组。两者不改变问题、不改变选项、不改变答案。",
        "",
        "这保证了评测比较的是模型输入接口差异，而不是两套数据差异。",
        "",
        "## Case Study",
        "",
        "下面每个 case 都完整展示英文版本和中文版本。两种语言使用同一个 raw time-series、同一个选项字母、同一个 gold answer；差别只在题面语言。",
        "",
    ]
    for idx, row in enumerate(case_rows, start=1):
        audit = audit_by_id[row["id"]]
        fig_name = f"case_{idx}_{row['domain']}.svg"
        lines.extend(
            [
                f"### Case {idx}: `{row['domain']}`",
                "",
                f"![Case {idx} series](figures/{fig_name})",
                "",
                *bilingual_case_lines(row, audit),
                "**内部审计证据字段摘要**",
                "",
                f"`{json.dumps(audit['support_slots'], ensure_ascii=False)}`",
                "",
                "**LLM / TS-LLM view 对齐说明**",
                "",
                "```text",
                "LLM English prompt = English context + English variables + English decision guide + English question/options + raw series as CSV.",
                "LLM Chinese prompt = Chinese context + Chinese variables + Chinese decision guide + Chinese question/options + same raw series as CSV.",
                "TS-LLM view = same raw numeric array + English/Chinese text fields. The answer letter is shared.",
                "```",
                "",
                "**TS-LLM array shape**",
                "",
                "```json",
                json.dumps(
                    {
                        "columns": row["time_series"]["columns"],
                        "timeseries_shape": [len(row["time_series"]["values"]), len(row["time_series"]["columns"])],
                        "question_en": row["question_en"],
                        "question_zh": row["question_zh"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## 本轮剩余问题",
            "",
            "- 当前 v4 只有 39 条，是 schema/pipeline 样板，不是最终 benchmark 规模。",
            "- answer distribution 仍偏 A，需要扩增时做全局 answer balance。",
            "- building_energy / traffic 的 ready seed 数量偏少，需要优先补齐。",
            "- 下一步应在 v4 schema 上扩增，而不是继续扩 v3 compact-style 数据。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    rows = load_jsonl(DATA_DIR / "canonical_raw_tsqa_v4.jsonl")
    audits = load_jsonl(DATA_DIR / "audit_support.jsonl")
    audit_by_id = {row["id"]: row for row in audits}
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    save_bar(Counter(row["domain"] for row in rows), FIG_DIR / "domain_distribution.svg", "Domain Distribution")
    save_bar(Counter(row["answer"] for row in rows), FIG_DIR / "answer_distribution.svg", "Answer Distribution")
    save_length_hist(rows, FIG_DIR / "time_series_lengths.svg")
    case_rows = pick_cases(rows)
    for idx, row in enumerate(case_rows, start=1):
        save_case_plot(row, FIG_DIR / f"case_{idx}_{row['domain']}.svg")
    REPORT.write_text(render_report(rows, audit_by_id, case_rows), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(REPORT.relative_to(ROOT)),
                "figures": len(list(FIG_DIR.glob("*.svg"))),
                "cases": [row["id"] for row in case_rows],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
