#!/usr/bin/env python3
"""Naturalize the next Natural-QCC expansion candidate pool.

This is a thin wrapper around the balanced8 natural TS-QA rewrite rules. It
keeps the deterministic answer/support slots unchanged and prepares a larger
candidate set for the GPT reviewer gate.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from build_natural_tsqa_balanced8 import lint_case, rewrite_case


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/"
    / "natural_qcc_expansion_candidates.jsonl"
)
DEFAULT_OUT_DIR = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519"
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_source(row: dict[str, Any]) -> None:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    source = (
        row.get("merge_source_name")
        or meta.get("merge_source_name")
        or row.get("multisim_source_domain")
        or row.get("domain")
        or "unknown"
    )
    row["merge_source_name"] = str(source)


def naturalize_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    cases: list[dict[str, Any]] = []
    lint_by_id: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        normalize_source(row)
        case = rewrite_case(row)
        if "_scene_extra_en" in row:
            case["scene_en"] += row["_scene_extra_en"]
            case["scene_zh"] += row["_scene_extra_zh"]
        case["expansion_candidate"] = True
        case["candidate_split_group"] = row.get("split_group")
        case["candidate_abstract_primitive"] = row.get("abstract_primitive")
        case["candidate_abstract_answer_label"] = row.get("abstract_answer_label")
        issues = lint_case(case)
        case["lint_issues"] = issues
        cases.append(case)
        lint_by_id[case["id"]] = issues
    return cases, lint_by_id


def summarize_cases(cases: list[dict[str, Any]], lint_by_id: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {
        "n": len(cases),
        "by_source": dict(Counter(case["source"] for case in cases)),
        "by_split": dict(Counter(str(case.get("split", "")) for case in cases)),
        "by_status": dict(Counter(case["natural_status"] for case in cases)),
        "by_task_family": dict(Counter(case["task_family"] for case in cases)),
        "by_abstract_primitive": dict(
            Counter(str(case.get("candidate_abstract_primitive", "")) for case in cases)
        ),
        "by_answer": dict(Counter(case["gold_answer"] for case in cases)),
        "issue_counts": dict(
            Counter(issue["code"] for issues in lint_by_id.values() for issue in issues)
        ),
    }


def markdown(report: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    summary = report["summary"]
    examples = []
    for case in cases[:12]:
        examples.append(
            f"- `{case['source']}` / `{case['task_family']}` / `{case['natural_status']}`: {case['question_zh']}"
        )
    examples_text = "\n".join(examples) if examples else "- 无"
    lines = [
        "# Natural QCC Expansion Rewrites（2026-05-19）",
        "",
        "本目录把扩展候选池改写成自然语言 TS-QA 草案，用于后续 GPT-5.5 reviewer gate。改写只改变场景、问题、选项和证据表述；`gold_answer`、`gold_answer_label` 和 `support_slots` 继续来自原始 deterministic 数据。",
        "",
        "## 输入输出",
        "",
        f"- input: `{report['input_jsonl']}`",
        f"- output JSONL: `{report['output_jsonl']}`",
        f"- lint JSON: `{report['lint_json']}`",
        f"- rows: `{summary['n']}`",
        "",
        "## 分布",
        "",
        f"- by source: `{summary['by_source']}`",
        f"- by split: `{summary['by_split']}`",
        f"- by natural status: `{summary['by_status']}`",
        f"- by abstract primitive: `{summary['by_abstract_primitive']}`",
        f"- by answer: `{summary['by_answer']}`",
        f"- lint issue counts: `{summary['issue_counts']}`",
        "",
        "## 前 12 条样例",
        "",
        examples_text,
        "",
        "## 使用方式",
        "",
        "在本地 checkout 中只有 AIOpsLab source JSONL，因此当前输出只包含本地可物化的 AIOps 候选。到包含完整 MultiSim v5 source JSONL 的数据机器上，应先重新运行 candidate selector，再运行本脚本：",
        "",
        "```bash",
        "python3 scripts/generate/select_natural_qcc_expansion_candidates.py \\",
        "  --schema .research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/schema_report.json \\",
        "  --out_dir .research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519 \\",
        "  --per_source 100 \\",
        "  --seed 55",
        "",
        "python3 scripts/generate/build_natural_qcc_expansion_rewrites.py \\",
        "  --input_jsonl .research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates.jsonl \\",
        "  --out_dir .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519",
        "",
        "python3 scripts/generate/review_natural_qcc_expansion_rewrites.py \\",
        "  --input_jsonl .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites.jsonl \\",
        "  --review_json .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites_review.json \\",
        "  --review_md .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/NATURAL_QCC_EXPANSION_REVIEW_20260519_ZH.md \\",
        "  --model gpt-5.5",
        "```",
        "",
        "## 下一步",
        "",
        "对 `natural_qcc_expansion_rewrites.jsonl` 运行 GPT-5.5 reviewer gate；只保留 `decision=keep`、`naturalness_score>=4`、`answerability_score>=4`、`accuracy_risk=low` 的样本进入正式 natural QCC train/dev/test。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_jsonl", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run_name", default="natural_qcc_expansion_rewrites")
    args = parser.parse_args()

    rows = load_jsonl(args.input_jsonl)
    cases, lint_by_id = naturalize_rows(rows)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = args.out_dir / f"{args.run_name}.jsonl"
    lint_json = args.out_dir / f"{args.run_name}_lint.json"
    report_md = args.out_dir / "NATURAL_QCC_EXPANSION_REWRITES_20260519_ZH.md"

    write_jsonl(out_jsonl, cases)
    report = {
        "input_jsonl": rel(args.input_jsonl),
        "output_jsonl": rel(out_jsonl),
        "lint_json": rel(lint_json),
        "summary": summarize_cases(cases, lint_by_id),
        "by_id": lint_by_id,
    }
    lint_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md.write_text(markdown(report, cases), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
