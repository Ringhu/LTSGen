#!/usr/bin/env python3
"""Merge reviewed Natural-QCC positive pools.

The Natural-QCC expansion flow intentionally keeps each reviewed batch separate
until it passes its own reviewer gate. This utility combines already-positive
JSONL files, checks duplicate ids and basic schema fields, and writes a compact
summary so downstream SFT builders can consume one reviewer-positive pool.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
DEFAULT_OUT_DIR = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/merged"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
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


def source_name(row: dict[str, Any]) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(
        row.get("merge_source_name")
        or row.get("source")
        or meta.get("merge_source_name")
        or row.get("multisim_source_domain")
        or row.get("domain")
        or "unknown"
    )


def value_dim(row: dict[str, Any]) -> int:
    values = row.get("values") or []
    if not values:
        return 0
    first = values[0]
    return len(first) if isinstance(first, list) else 1


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_split: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        source_split[source_name(row)][str(row.get("split", ""))] += 1
    ids = [str(row.get("id", "")) for row in rows]
    required = ("id", "values", "question", "options", "answer", "answer_label", "support_slots")
    return {
        "n": len(rows),
        "duplicate_id_count": len(ids) - len(set(ids)),
        "by_source": dict(Counter(source_name(row) for row in rows)),
        "by_split": dict(Counter(str(row.get("split", "")) for row in rows)),
        "by_source_split": {source: dict(counts) for source, counts in sorted(source_split.items())},
        "by_task_family": dict(Counter(str(row.get("task_family", "")) for row in rows)),
        "by_value_dim": dict(Counter(str(value_dim(row)) for row in rows)),
        "answer_distribution": dict(Counter(str(row.get("answer", "")) for row in rows)),
        "missing_required_count": sum(
            1
            for row in rows
            if not all(key in row and row[key] not in ("", [], None) for key in required)
        ),
    }


def markdown(report: dict[str, Any]) -> str:
    merged = report["merged"]
    lines = [
        "# Natural QCC Failure-Domain Expansion Merge（2026-05-20）",
        "",
        "本目录合并已经通过 reviewer gate 的 Natural-QCC positive pool。合并脚本不改写问题、不决定 gold answer，只做去重、schema 检查和分布汇总。",
        "",
        "## Inputs",
        "",
    ]
    for item in report["inputs"]:
        lines.append(f"- `{item['path']}`: `{item['summary']['n']}` rows, source `{item['summary']['by_source']}`")
    lines.extend(
        [
            "",
            "## Merged Summary",
            "",
            f"- output positive JSONL: `{report['outputs']['positive_jsonl']}`",
            f"- rows: `{merged['n']}`",
            f"- duplicate id count: `{merged['duplicate_id_count']}`",
            f"- missing required count: `{merged['missing_required_count']}`",
            f"- by source: `{merged['by_source']}`",
            f"- by split: `{merged['by_split']}`",
            f"- answer distribution: `{merged['answer_distribution']}`",
            f"- schema gate pass: `{report['schema_gate_pass']}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputs",
        nargs="+",
        type=Path,
        default=[
            BASE / "natural_qcc_crossdomain_positive.jsonl",
            ROOT
            / ".research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/dataset/natural_qcc_failure_domain_expansion_positive.jsonl",
        ],
    )
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run_name", default="natural_qcc_crossdomain_failure_expanded")
    args = parser.parse_args()

    all_rows: list[dict[str, Any]] = []
    input_reports = []
    seen: set[str] = set()
    duplicate_ids: list[str] = []
    for path in args.inputs:
        rows = load_jsonl(path)
        input_reports.append({"path": rel(path), "summary": summarize(rows)})
        for row in rows:
            row_id = str(row.get("id", ""))
            if row_id in seen:
                duplicate_ids.append(row_id)
                continue
            seen.add(row_id)
            all_rows.append(row)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    positive_jsonl = args.out_dir / f"{args.run_name}_positive.jsonl"
    summary_json = args.out_dir / f"{args.run_name}_merge_summary.json"
    report_md = args.out_dir / "NATURAL_QCC_FAILURE_DOMAIN_EXPANSION_MERGE_20260520_ZH.md"
    write_jsonl(positive_jsonl, all_rows)

    merged = summarize(all_rows)
    report = {
        "inputs": input_reports,
        "outputs": {
            "positive_jsonl": rel(positive_jsonl),
            "summary_json": rel(summary_json),
            "report_md": rel(report_md),
        },
        "dropped_duplicate_ids": duplicate_ids,
        "merged": merged,
        "schema_gate_pass": bool(
            all_rows
            and not duplicate_ids
            and merged["duplicate_id_count"] == 0
            and merged["missing_required_count"] == 0
        ),
    }
    summary_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["schema_gate_pass"] else 1)


if __name__ == "__main__":
    main()
