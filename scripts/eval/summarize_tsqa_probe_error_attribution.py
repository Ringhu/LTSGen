#!/usr/bin/env python3
"""Summarize data-only TSQA probe errors for benchmark seed triage."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROBE = (
    ROOT
    / ".research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/"
    / "data_only_probe_full60/self_contained_reasoning_tsqa_gpt_data_only_probe.json"
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def normalize(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def classify_error(pred: dict[str, Any]) -> str:
    reason = normalize(pred.get("reason", ""))
    gold = normalize(pred.get("gold_answer_label", ""))
    predicted = normalize(pred.get("pred_answer_label", ""))
    if gold and gold in reason and (not predicted or predicted not in reason or reason.rfind(gold) > reason.rfind(predicted)):
        return "reason_supports_gold_output_field_wrong"
    if gold and gold in reason:
        return "reason_mentions_gold_but_output_wrong"
    return "reason_does_not_recover_gold"


def summarize(probe: dict[str, Any]) -> dict[str, Any]:
    wrong = probe.get("summary", {}).get("semantic_wrong", [])
    classes: Counter[str] = Counter()
    by_domain: dict[str, Counter[str]] = defaultdict(Counter)
    by_task: dict[str, Counter[str]] = defaultdict(Counter)
    rows = []
    for pred in wrong:
        klass = classify_error(pred)
        classes[klass] += 1
        by_domain[str(pred.get("source", ""))][klass] += 1
        by_task[str(pred.get("task_family", ""))][klass] += 1
        rows.append(
            {
                "id": pred.get("id"),
                "source": pred.get("source"),
                "task_family": pred.get("task_family"),
                "gold_answer": pred.get("gold_answer"),
                "gold_answer_label": pred.get("gold_answer_label"),
                "pred_answer": pred.get("pred_answer"),
                "pred_answer_label": pred.get("pred_answer_label"),
                "attribution_class": klass,
                "reason": pred.get("reason", ""),
            }
        )
    return {
        "wrong_n": len(wrong),
        "classes": dict(classes),
        "by_domain": {key: dict(value) for key, value in sorted(by_domain.items())},
        "by_task_family": {key: dict(value) for key, value in sorted(by_task.items())},
        "rows": rows,
    }


def render_md(summary: dict[str, Any], probe_path: Path) -> str:
    lines = [
        "# Self-contained Reasoning TSQA v3 Data-only Error Attribution（2026-05-21）",
        "",
        "本报告只分析 data-only probe 的 semantic wrong 样本。它不是人工最终判定，而是扩增前的错误归因队列。",
        "",
        "## 总览",
        "",
        f"- probe: `{rel(probe_path)}`",
        f"- semantic wrong: `{summary['wrong_n']}`",
        f"- classes: `{json.dumps(summary['classes'], ensure_ascii=False)}`",
        "",
        "## 类别解释",
        "",
        "- `reason_supports_gold_output_field_wrong`：模型 reason 中已经算出或陈述了 gold label，但 JSON `answer/answer_label` 字段填成了别的选项。",
        "- `reason_mentions_gold_but_output_wrong`：reason 提到 gold，但文本中也混有错误判断，需要人工看是否为输出一致性问题。",
        "- `reason_does_not_recover_gold`：reason 没有恢复 gold，优先检查题面、规则阈值、变量定义或样本边界。",
        "",
        "## By Domain",
        "",
        "| domain | attribution counts |",
        "| --- | --- |",
    ]
    for domain, counts in summary["by_domain"].items():
        lines.append(f"| `{domain}` | `{json.dumps(counts, ensure_ascii=False)}` |")
    lines.extend(
        [
            "",
            "## 错例队列",
            "",
            "| domain | task | gold | pred | class | reason excerpt |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in summary["rows"]:
        reason = str(row["reason"]).replace("|", "／")[:220]
        lines.append(
            f"| `{row['source']}` | `{row['task_family']}` | "
            f"{row['gold_answer']} / {row['gold_answer_label']} | "
            f"{row['pred_answer']} / {row['pred_answer_label']} | "
            f"`{row['attribution_class']}` | {reason} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--out_dir", type=Path, default=None)
    args = parser.parse_args()

    probe = json.loads(args.probe.read_text(encoding="utf-8"))
    summary = summarize(probe)
    out_dir = args.out_dir or args.probe.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "self_contained_reasoning_tsqa_gpt_data_only_error_attribution.json"
    out_md = out_dir / "SELF_CONTAINED_REASONING_TSQA_GPT_DATA_ONLY_ERROR_ATTRIBUTION_20260521_ZH.md"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_md(summary, args.probe), encoding="utf-8")
    print(json.dumps({"out_json": rel(out_json), "out_md": rel(out_md), "summary": {k: v for k, v in summary.items() if k != "rows"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
