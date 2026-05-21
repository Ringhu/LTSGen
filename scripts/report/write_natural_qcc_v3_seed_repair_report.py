#!/usr/bin/env python3
"""Write an illustrated report for the Natural-QCC seed repair round."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515"
OUT_DIR = BASE / "natural_qcc_v3_seed_repair_report_20260521"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def svg_bar_chart(path: Path, title: str, groups: list[tuple[str, list[tuple[str, int, str]]]], ymax: int) -> None:
    width = 860
    height = 360
    left = 72
    top = 58
    plot_h = 220
    group_w = 190
    bar_w = 42
    gap = 14
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="30" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">{title}</text>',
    ]
    for i in range(5):
        y = top + plot_h * i / 4
        value = ymax * (1 - i / 4)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - 30}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
        parts.append(f'<text x="22" y="{y + 4:.1f}" font-family="Arial, sans-serif" font-size="11" fill="#6b7280">{value:.0f}</text>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#374151" stroke-width="1.2"/>')
    parts.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{width - 30}" y2="{top + plot_h}" stroke="#374151" stroke-width="1.2"/>')
    for gi, (label, bars) in enumerate(groups):
        start = left + 42 + gi * group_w
        for bi, (_, value, color) in enumerate(bars):
            x = start + bi * (bar_w + gap)
            h = plot_h * value / ymax
            y = top + plot_h - h
            parts.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" fill="{color}" rx="3"/>')
            parts.append(f'<text x="{x + bar_w / 2}" y="{y - 6:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#111827">{value}</text>')
        parts.append(f'<text x="{start + 54}" y="{top + plot_h + 26}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#111827">{label}</text>')
    legend_x = left
    legend_y = height - 38
    legend_items = groups[0][1]
    for i, (name, _, color) in enumerate(legend_items):
        x = legend_x + i * 180
        parts.append(f'<rect x="{x}" y="{legend_y - 11}" width="14" height="14" fill="{color}" rx="2"/>')
        parts.append(f'<text x="{x + 20}" y="{legend_y}" font-family="Arial, sans-serif" font-size="12" fill="#374151">{name}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def svg_horizontal_bars(path: Path, title: str, rows: list[tuple[str, int, str]], xmax: int) -> None:
    width = 860
    height = 90 + len(rows) * 42
    left = 240
    top = 54
    bar_h = 22
    plot_w = width - left - 70
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="32" y="30" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">{title}</text>',
    ]
    for i, (label, value, color) in enumerate(rows):
        y = top + i * 42
        w = plot_w * value / xmax if xmax else 0
        parts.append(f'<text x="32" y="{y + 16}" font-family="Arial, sans-serif" font-size="12" fill="#111827">{label}</text>')
        parts.append(f'<rect x="{left}" y="{y}" width="{plot_w}" height="{bar_h}" fill="#f3f4f6" rx="3"/>')
        parts.append(f'<rect x="{left}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="{color}" rx="3"/>')
        parts.append(f'<text x="{left + w + 8:.1f}" y="{y + 16}" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#111827">{value}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def svg_flow(path: Path) -> None:
    width, height = 980, 430
    boxes = [
        (40, 70, 175, 82, "Simulator / trace", "Grid2Op, CityLearn,\nTraffic, Water,\nAIOps, FinRL"),
        (260, 70, 180, 82, "Scenario + rule", "scene, variables,\ndecision rule,\nquestion/options"),
        (485, 70, 185, 82, "Deterministic verifier", "support slots,\ngold answer,\ncaption checks"),
        (715, 70, 195, 82, "Natural evidence", "answer-focused\ncaption target"),
        (260, 250, 180, 82, "GPT data-only probe", "diagnostic only,\nnot an answer oracle"),
        (485, 250, 185, 82, "Reviewer gate", "QA ready vs\ncaption-train ready"),
        (715, 250, 195, 82, "Smoke training", "qcond/no-question\ncaption model test"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="40" y="34" font-family="Arial, sans-serif" font-size="20" font-weight="700" fill="#111827">Natural-QCC seed repair architecture</text>',
    ]
    for x1, y1, x2, y2 in [(215, 111, 260, 111), (440, 111, 485, 111), (670, 111, 715, 111), (575, 152, 575, 250), (440, 291, 485, 291), (670, 291, 715, 291)]:
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#6b7280" stroke-width="2" marker-end="url(#arrow)"/>')
    parts.insert(2, '<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#6b7280"/></marker></defs>')
    for x, y, w, h, title, body in boxes:
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#f9fafb" stroke="#d1d5db" stroke-width="1.4" rx="6"/>')
        parts.append(f'<text x="{x + 14}" y="{y + 24}" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#111827">{title}</text>')
        for j, line in enumerate(body.split("\\n")):
            parts.append(f'<text x="{x + 14}" y="{y + 46 + j * 15}" font-family="Arial, sans-serif" font-size="12" fill="#4b5563">{line}</text>')
    parts.append('<text x="40" y="394" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">Key policy: LLM review/probe can criticize naturalness and diagnose failures, but deterministic support slots keep the gold answer fixed.</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def write_report() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig_dir = OUT_DIR / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    old = load_json(BASE / "seed_quality_review_v1_20260521/natural_qcc_seed_quality_review_v1_summary.json")
    policy = load_json(BASE / "seed_quality_review_v1_policy_recheck_20260521/natural_qcc_seed_quality_review_v1_policy_recheck_summary.json")
    new = load_json(BASE / "seed_quality_review_v2_20260521/natural_qcc_seed_quality_review_v2_summary.json")
    attr = load_json(BASE / "self_contained_error_attribution_v1_20260521/self_contained_data_only_error_attribution_v1_summary.json")

    svg_bar_chart(
        fig_dir / "reviewer_gate_before_after.svg",
        "Reviewer gate before/after",
        [
            ("old v1", [("QA ready", old["qa_seed_ready_count"], "#2563eb"), ("caption ready", old["caption_train_ready_count"], "#16a34a")]),
            ("policy only", [("QA ready", policy["qa_seed_ready_count"], "#2563eb"), ("caption ready", policy["caption_train_ready_count"], "#16a34a")]),
            ("v2/v3", [("QA ready", new["qa_seed_ready_count"], "#2563eb"), ("caption ready", new["caption_train_ready_count"], "#16a34a")]),
        ],
        72,
    )
    svg_horizontal_bars(
        fig_dir / "error_attribution_distribution.svg",
        "GPT data-only wrong attribution",
        [
            ("reason correct, answer field wrong", attr["attribution_counts"].get("model_reason_answer_inconsistency", 0), "#2563eb"),
            ("Water rule application + wording risk", attr["attribution_counts"].get("model_rule_application_error_with_water_clause_clarity_risk", 0), "#f97316"),
            ("model rule application error", attr["attribution_counts"].get("model_rule_application_error", 0), "#7c3aed"),
            ("data/gold defect", attr["data_defect_count"], "#dc2626"),
        ],
        max(1, max(attr["attribution_counts"].values())),
    )
    domain_rows = []
    colors = ["#2563eb", "#16a34a", "#7c3aed", "#f97316", "#0891b2", "#dc2626"]
    for i, (domain, stats) in enumerate(sorted(new["by_domain"].items())):
        domain_rows.append((f"{domain} caption-ready", stats["caption_train_ready_count"], colors[i % len(colors)]))
    svg_horizontal_bars(fig_dir / "domain_caption_ready_v2.svg", "Caption-ready by domain after repair", domain_rows, 12)
    svg_flow(fig_dir / "natural_qcc_repair_architecture.svg")

    case_dir = BASE / "natural_qcc_case_quality_v2_20260521"
    case_figs = sorted((case_dir / "figures").glob("*.svg"))
    lines = [
        "# Natural-QCC Seed Repair Round Report（2026-05-21）",
        "",
        "## 一句话结论",
        "",
        "这轮做的不是继续堆数据，而是把小规模 seed 从“看起来像规则槽位拼接”修成可以进入下一步 smoke test 的自然 QA/caption seed。",
        "修完后，72 条 seed 全部通过 QA-ready 和 caption-train-ready gate；但 15 条 GPT data-only 错误仍保留为诊断项，用于后续扩增时重点复核。",
        "",
        "![Reviewer gate before/after](figures/reviewer_gate_before_after.svg)",
        "",
        "## 这轮具体做了什么",
        "",
        "### 1. 修 reviewer gate",
        "",
        "旧 gate 把 `gpt_data_only_wrong` 直接当成 QA 不可用，导致一些本来 deterministic gold 没问题的样本被误判。",
        "现在它只触发 `needs_manual_error_attribution`，不再单独阻塞 QA seed。",
        "",
        "### 2. 生成 self-contained reasoning QA v3",
        "",
        "保留 v2 的题面、规则、选项、gold 和 support slots，只清洗 caption 训练目标：删除 `Answer label`，删除 `the rule maps this to`，把 caption 改成“时序形态 + 关键数值 + 为什么支持判断”。",
        "",
        "- 样本数：60",
        "- 分域：Grid2Op、CityLearn、Traffic、Water、AIOpsLab、FinRL 每域 10 条",
        "- bad phrase 检查：`Answer label` / `the rule maps this to` / `supports the answer` 全部为 0",
        "",
        "### 3. 做 GPT data-only 错误归因",
        "",
        "15 条 GPT data-only 错误没有被直接删掉，而是逐条归因。",
        "",
        "![Error attribution](figures/error_attribution_distribution.svg)",
        "",
        "归因结果很关键：11 条是模型 reason 已经算到正确答案，但最终 JSON answer 填错；3 条是 Water 规则应用错误并提示规则措辞要更硬；1 条是普通规则应用错误。没有一条被判为确定性 data/gold defect。",
        "",
        "### 4. 修 12 条 case-study v2",
        "",
        "case-study v2 保留每域 2 条和原有时序图，但改了读者看到的文本：去 simulator 名称，补清变量含义，说明对照/基线，删掉英文 caption 的模板句，让中英文 caption 聚焦同一组证据。",
        "",
        "![Caption ready by domain](figures/domain_caption_ready_v2.svg)",
        "",
        "### 5. 复跑 reviewer gate",
        "",
        f"- 原始 v1 结论：QA ready {old['qa_seed_ready_count']}/72，caption ready {old['caption_train_ready_count']}/72。",
        f"- 只修 gate 策略后：QA ready {policy['qa_seed_ready_count']}/72，caption ready {policy['caption_train_ready_count']}/72。",
        f"- v2/v3 数据修复后：QA ready {new['qa_seed_ready_count']}/72，caption ready {new['caption_train_ready_count']}/72。",
        "",
        "这说明：QA-ready 的改善主要来自 reviewer gate 策略修正；caption-ready 的改善主要来自 v3 caption target 清洗和 v2 case 改写。",
        "",
        "## 当前架构",
        "",
        "![Natural-QCC repair architecture](figures/natural_qcc_repair_architecture.svg)",
        "",
        "这张图的核心是：simulator/trace 和 deterministic verifier 仍负责 gold 和 support slots；LLM probe/reviewer 只负责自然性、可答性和失败诊断，不决定正确答案。",
        "",
        "## 代表时序 case",
        "",
        "下面这些图来自 case-study v2，每个域 2 条。报告正文在 `natural_qcc_case_quality_v2_20260521` 里包含完整场景、问题、中文选项、答案、中文 caption 和 English target caption。",
        "",
    ]
    for fig in case_figs:
        lines.extend([
            f"### {fig.stem}",
            "",
            f"![{fig.stem}](../natural_qcc_case_quality_v2_20260521/figures/{fig.name})",
            "",
        ])
    lines.extend([
        "## 产物清单",
        "",
        "| 类型 | 路径 |",
        "| --- | --- |",
        "| reviewer script | `scripts/eval/review_natural_qcc_seed_quality.py` |",
        "| error attribution script | `scripts/eval/attribute_self_contained_data_only_errors.py` |",
        "| self-contained v3 generator | `scripts/generate/build_self_contained_reasoning_tsqa_v3.py` |",
        "| case-study v2 generator | `scripts/generate/build_natural_qcc_case_quality_v2.py` |",
        "| self-contained v3 data | `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/` |",
        "| case-study v2 data/report | `.research/general-qcc-captioner-20260515/natural_qcc_case_quality_v2_20260521/` |",
        "| error attribution report | `.research/general-qcc-captioner-20260515/self_contained_error_attribution_v1_20260521/` |",
        "| reviewer gate v2 | `.research/general-qcc-captioner-20260515/seed_quality_review_v2_20260521/` |",
        "| illustrated round report | `.research/general-qcc-captioner-20260515/natural_qcc_v3_seed_repair_report_20260521/` |",
        "",
        "## 下一步",
        "",
        "下一步不应该直接上大训练。更稳的是用这 72 条作为 smoke seed，做一个小扩增和 qcond/no-question 对照：先验证 caption model 能否生成非空、自然、可验证的 evidence caption，再决定是否扩大到每域更多真实 simulator/exporter adapter 样本。",
        "",
    ])
    (OUT_DIR / "NATURAL_QCC_V3_SEED_REPAIR_ROUND_REPORT_20260521_ZH.md").write_text("\n".join(lines), encoding="utf-8")
    print(OUT_DIR / "NATURAL_QCC_V3_SEED_REPAIR_ROUND_REPORT_20260521_ZH.md")


if __name__ == "__main__":
    write_report()
