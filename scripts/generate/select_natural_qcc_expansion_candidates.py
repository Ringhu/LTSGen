#!/usr/bin/env python3
"""Select the next natural-QCC expansion candidate pool.

The balanced8 pilot is too small for training claims. This selector prepares a
larger candidate manifest from the MultiSim-v5 source files, keeping source,
split, task-family, answer-letter, and primitive coverage visible before LLM
naturalization and reviewer gating.

It is safe to run locally when some large source JSONL files are absent: the
script writes a manifest that records missing sources instead of inventing data.
Run the same command on the A100/3090 data machine to materialize the full pool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = ROOT / ".research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/schema_report.json"
DEFAULT_OUT_DIR = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519"
DEFAULT_PILOT = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/natural_qcc_probe_positive.jsonl"

METADATA_ONLY_TASKS = {
    "aiops_official_app_context",
    "aiops_official_case_provenance_context",
    "aiops_official_service_role_context",
    "aiops_official_fault_family_detail_context",
    "aiops_official_fault_context",
    "aiops_official_faulty_service_context",
    "aiops_official_fault_layer_context",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def source_name(row: dict[str, Any], fallback: str = "") -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(row.get("merge_source_name") or meta.get("merge_source_name") or row.get("multisim_source_domain") or fallback or row.get("domain") or "unknown")


def stable_key(row: dict[str, Any], seed: int) -> str:
    return hashlib.sha256(f"{seed}::{row.get('id', '')}".encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row.get("output") or row.get("target_caption") or row.get("oracle_evidence_caption", ""),
        "target_caption": row.get("target_caption") or row.get("output") or row.get("oracle_evidence_caption", ""),
        "meta": row.get("meta", {}),
    }


def candidate_ok(row: dict[str, Any], *, include_metadata_only: bool) -> bool:
    required = ("id", "values", "question", "options", "answer", "answer_label", "support_slots")
    if any(key not in row or row[key] in ("", [], None) for key in required):
        return False
    if not include_metadata_only and row.get("task_family") in METADATA_ONLY_TASKS:
        return False
    return True


def source_paths(schema: dict[str, Any], source_filter: set[str], source_root: Path) -> list[tuple[str, str, Path]]:
    paths = []
    for report in schema.get("source_reports", []):
        source = report["source"]
        if source_filter and source not in source_filter:
            continue
        for split, info in sorted(report.get("splits", {}).items()):
            path = Path(info["path"])
            if not path.is_absolute():
                path = source_root / path
            paths.append((source, split, path))
    return paths


def load_available_rows(
    schema: dict[str, Any],
    source_filter: set[str],
    *,
    include_metadata_only: bool,
    source_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    missing = []
    for source, split, path in source_paths(schema, source_filter, source_root):
        if not path.exists():
            missing.append({"source": source, "split": split, "path": rel(path)})
            continue
        loaded = load_jsonl(path)
        for row in loaded:
            item = dict(row)
            item["merge_source_name"] = source
            if "split" not in item:
                item["split"] = split
            if candidate_ok(item, include_metadata_only=include_metadata_only):
                rows.append(item)
    return rows, missing


def load_pilot_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {row["id"] for row in load_jsonl(path)}


def select_rows(rows: list[dict[str, Any]], *, per_source: int, seed: int, exclude_ids: set[str]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["id"] not in exclude_ids:
            grouped[source_name(row)].append(row)

    selected: list[dict[str, Any]] = []
    for source, items in sorted(grouped.items()):
        task_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in items:
            task_groups[str(row.get("task_family", ""))].append(row)
        for task in task_groups:
            task_groups[task] = sorted(task_groups[task], key=lambda row: stable_key(row, seed))

        source_selected: list[dict[str, Any]] = []
        while len(source_selected) < per_source:
            progressed = False
            for task in sorted(task_groups):
                if len(source_selected) >= per_source:
                    break
                if task_groups[task]:
                    source_selected.append(task_groups[task].pop(0))
                    progressed = True
            if not progressed:
                break
        selected.extend(source_selected)
    return sorted(selected, key=lambda row: (source_name(row), row.get("split", ""), stable_key(row, seed)))


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_split: dict[str, Counter[str]] = defaultdict(Counter)
    source_task: dict[str, Counter[str]] = defaultdict(Counter)
    source_answer: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        source = source_name(row)
        source_split[source][str(row.get("split", ""))] += 1
        source_task[source][str(row.get("task_family", ""))] += 1
        source_answer[source][str(row.get("answer", ""))] += 1
    return {
        "n": len(rows),
        "by_source": dict(Counter(source_name(row) for row in rows)),
        "by_split": dict(Counter(str(row.get("split", "")) for row in rows)),
        "by_task_family": dict(Counter(str(row.get("task_family", "")) for row in rows)),
        "by_abstract_primitive": dict(Counter(str(row.get("abstract_primitive", "")) for row in rows)),
        "by_answer": dict(Counter(str(row.get("answer", "")) for row in rows)),
        "by_source_split": {source: dict(counts) for source, counts in sorted(source_split.items())},
        "by_source_answer": {source: dict(counts) for source, counts in sorted(source_answer.items())},
        "task_family_per_source": {source: dict(counts) for source, counts in sorted(source_task.items())},
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Natural QCC Expansion Candidates（2026-05-19）",
        "",
        "本目录用于准备 natural QCC 的下一批扩展候选。目标是在 reviewer gate 前先固定候选池，避免只围绕 balanced8 case study 手工扩展。",
        "",
        f"- schema: `{report['schema']}`",
        f"- output: `{report['output_jsonl']}`",
        f"- selected rows: `{report['selected']['n']}`",
        f"- missing source files: `{len(report['missing_files'])}`",
        f"- excluded pilot ids: `{report['excluded_pilot_ids']}`",
        "",
        "## Selected By Source",
        "",
        "| source | selected | split counts |",
        "| --- | ---: | --- |",
    ]
    selected = report["selected"]
    for source, n in sorted(selected["by_source"].items()):
        lines.append(f"| `{source}` | {n} | `{selected['by_source_split'].get(source, {})}` |")
    lines.extend(
        [
            "",
            "## Missing Files",
            "",
            "| source | split | path |",
            "| --- | --- | --- |",
        ]
    )
    for item in report["missing_files"]:
        lines.append(f"| `{item['source']}` | `{item['split']}` | `{item['path']}` |")
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "在包含完整 MultiSim v5 source JSONL 的 A100/3090 数据环境重新运行同一脚本；若 selected rows 达到每域目标，再对输出 JSONL 执行 natural rewrite 和 GPT-5.5 reviewer gate。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run_name", default="natural_qcc_expansion_candidates")
    parser.add_argument("--per_source", type=int, default=100)
    parser.add_argument("--seed", type=int, default=55)
    parser.add_argument("--sources", nargs="*", default=[])
    parser.add_argument("--pilot_jsonl", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--include_metadata_only", action="store_true")
    parser.add_argument(
        "--source_root",
        type=Path,
        default=ROOT,
        help="Root used to resolve relative source paths recorded in the schema report.",
    )
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    source_filter = set(args.sources)
    pilot_ids = load_pilot_ids(args.pilot_jsonl)
    available, missing = load_available_rows(
        schema,
        source_filter,
        include_metadata_only=args.include_metadata_only,
        source_root=args.source_root,
    )
    selected = select_rows(available, per_source=args.per_source, seed=args.seed, exclude_ids=pilot_ids)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = args.out_dir / f"{args.run_name}.jsonl"
    out_sft = args.out_dir / f"{args.run_name}_sft.jsonl"
    write_jsonl(out_jsonl, selected)
    write_jsonl(out_sft, [sft_row(row) for row in selected])
    report = {
        "schema": rel(args.schema),
        "output_jsonl": rel(out_jsonl),
        "output_sft_jsonl": rel(out_sft),
        "per_source": args.per_source,
        "seed": args.seed,
        "sources": args.sources or "all",
        "source_root": rel(args.source_root),
        "include_metadata_only": args.include_metadata_only,
        "available_rows_local": summarize(available),
        "selected": summarize(selected),
        "missing_files": missing,
        "excluded_pilot_ids": len(pilot_ids),
        "selection_complete_for_requested_sources": not missing and all(n >= args.per_source for n in summarize(selected)["by_source"].values()),
    }
    (args.out_dir / f"{args.run_name}_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.out_dir / "NATURAL_QCC_EXPANSION_CANDIDATES_20260519_ZH.md").write_text(
        markdown(report),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
