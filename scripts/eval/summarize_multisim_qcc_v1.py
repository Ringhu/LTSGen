#!/usr/bin/env python3
"""Summarize MultiSim-QCC-v1 heldout QA metrics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DOMAINS = ("grid2op", "citylearn", "finrl")
SPLITS = ("dev", "test")
CF_MARKER = "counterfactual"
LEAD_MARKERS = ("lead_lag", "lead-lag")
AS047_GRID2OP_CF_TOTAL = 0.1852


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_domain_split(run_dir: Path, domain: str, split: str, qa_subdir: str) -> dict[str, Any]:
    path = run_dir / f"generate_{domain}_{split}_clean" / qa_subdir / "qa_metrics.json"
    payload = load_json(path)
    metrics = payload.get("metrics", {}) if isinstance(payload, dict) else {}
    return {
        "complete": path.exists(),
        "path": str(path),
        "n": int(metrics.get("n") or 0),
        "accuracy": metrics.get("accuracy"),
        "empty_answer_rate": metrics.get("empty_answer_rate"),
        "mean_caption_chars": metrics.get("mean_caption_chars"),
        "by_task_family": metrics.get("by_task_family", {}) if isinstance(metrics, dict) else {},
        "pred_answer_distribution": metrics.get("pred_answer_distribution", {}) if isinstance(metrics, dict) else {},
        "reason_distribution": metrics.get("reason_distribution", {}) if isinstance(metrics, dict) else {},
    }


def weighted_metric(items: list[dict[str, Any]], key: str) -> float | None:
    total_n = 0
    total = 0.0
    for item in items:
        n = int(item.get("n") or 0)
        value = item.get(key)
        if n and value is not None:
            total_n += n
            total += float(value) * n
    if not total_n:
        return None
    return round(total / total_n, 4)


def merge_task_metrics(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, float]] = {}
    for item in items:
        for task, task_metrics in item.get("by_task_family", {}).items():
            n = int(task_metrics.get("n") or 0)
            acc = task_metrics.get("accuracy")
            cur = merged.setdefault(task, {"n": 0.0, "correct": 0.0})
            cur["n"] += n
            if acc is not None:
                cur["correct"] += float(acc) * n
    out = {}
    for task, item in sorted(merged.items()):
        n = int(item["n"])
        out[task] = {"n": n, "accuracy": round(item["correct"] / n, 4) if n else None}
    return out


def weighted_task_accuracy(tasks: dict[str, dict[str, Any]], predicate) -> float | None:
    total_n = 0
    total = 0.0
    for task, metrics in tasks.items():
        if not predicate(task):
            continue
        n = int(metrics.get("n") or 0)
        acc = metrics.get("accuracy")
        if n and acc is not None:
            total_n += n
            total += float(acc) * n
    if not total_n:
        return None
    return round(total / total_n, 4)


def macro_task_accuracy(tasks: dict[str, dict[str, Any]], predicate) -> float | None:
    values = [
        float(metrics["accuracy"])
        for task, metrics in tasks.items()
        if predicate(task) and metrics.get("accuracy") is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def is_cf(task: str) -> bool:
    return CF_MARKER in task


def is_lead(task: str) -> bool:
    return any(marker in task for marker in LEAD_MARKERS)


def summarize_domain(run_dir: Path, domain: str, qa_subdir: str) -> dict[str, Any]:
    split_rows = {split: read_domain_split(run_dir, domain, split, qa_subdir) for split in SPLITS}
    split_values = list(split_rows.values())
    tasks = merge_task_metrics(split_values)
    combined = {
        "n": sum(int(row.get("n") or 0) for row in split_values),
        "accuracy": weighted_metric(split_values, "accuracy"),
        "empty_answer_rate": weighted_metric(split_values, "empty_answer_rate"),
        "mean_caption_chars": weighted_metric(split_values, "mean_caption_chars"),
        "by_task_family": tasks,
    }
    if domain == "grid2op":
        combined["cf_total"] = weighted_task_accuracy(tasks, is_cf)
        combined["lead_lag"] = weighted_task_accuracy(tasks, is_lead)
        combined["non_cf_macro"] = macro_task_accuracy(tasks, lambda task: not is_cf(task))
        combined["cf_by_task_family"] = {task: item for task, item in tasks.items() if is_cf(task)}
    return {
        "complete": all(row["complete"] for row in split_values),
        "splits": split_rows,
        "combined": combined,
    }


def make_decision(domains: dict[str, Any]) -> dict[str, Any]:
    if not all(row.get("complete") for row in domains.values()):
        return {
            "complete": False,
            "status": "incomplete",
            "failure_flags": ["missing_one_or_more_domain_split_metrics"],
        }

    domain_acc = {
        domain: row["combined"].get("accuracy")
        for domain, row in domains.items()
        if row["combined"].get("accuracy") is not None
    }
    domain_empty = {
        domain: row["combined"].get("empty_answer_rate")
        for domain, row in domains.items()
        if row["combined"].get("empty_answer_rate") is not None
    }
    worst_domain = min(domain_acc, key=domain_acc.get) if domain_acc else None
    worst_acc = domain_acc.get(worst_domain) if worst_domain else None
    grid_cf = domains.get("grid2op", {}).get("combined", {}).get("cf_total")
    non_grid_min = min(
        (value for domain, value in domain_acc.items() if domain != "grid2op"),
        default=None,
    )
    max_empty = max(domain_empty.values(), default=None)

    failure_flags = []
    if worst_acc is not None and worst_acc < 0.25:
        failure_flags.append("worst_domain_accuracy_below_0.25")
    if max_empty is not None and max_empty > 0.15:
        failure_flags.append("empty_answer_rate_above_0.15")
    if grid_cf is not None and grid_cf <= AS047_GRID2OP_CF_TOTAL:
        failure_flags.append("grid2op_cf_not_above_as047")

    scientific_success = (
        worst_acc is not None
        and worst_acc >= 0.35
        and max_empty is not None
        and max_empty < 0.05
        and grid_cf is not None
        and grid_cf > AS047_GRID2OP_CF_TOTAL
        and non_grid_min is not None
        and non_grid_min >= 0.35
    )
    if scientific_success:
        status = "scientific_success"
    elif failure_flags:
        status = "failure"
    elif worst_acc is not None and 0.25 <= worst_acc < 0.35:
        status = "ambiguous"
    else:
        status = "diagnostic"

    return {
        "complete": True,
        "status": status,
        "scientific_success": scientific_success,
        "worst_domain": worst_domain,
        "worst_domain_accuracy": worst_acc,
        "max_empty_answer_rate": max_empty,
        "grid2op_cf_total": grid_cf,
        "as047_grid2op_cf_total": AS047_GRID2OP_CF_TOTAL,
        "non_grid2op_min_accuracy": non_grid_min,
        "failure_flags": failure_flags,
    }


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# MultiSim-QCC-v1 Summary",
        "",
        f"Run dir: `{summary['run_dir']}`.",
        f"QA subdir: `{summary['qa_subdir']}`.",
        "",
        "## Domain Table",
        "",
        "| Domain | Complete | Dev acc | Test acc | Dev+test acc | Empty | Mean chars |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for domain in DOMAINS:
        row = summary["domains"][domain]
        splits = row["splits"]
        combined = row["combined"]
        lines.append(
            "| "
            + " | ".join(
                [
                    domain,
                    fmt(row["complete"]),
                    fmt(splits["dev"].get("accuracy")),
                    fmt(splits["test"].get("accuracy")),
                    fmt(combined.get("accuracy")),
                    fmt(combined.get("empty_answer_rate")),
                    fmt(combined.get("mean_caption_chars")),
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## Contract Check",
        "",
        "```json",
        json.dumps(summary["decision"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Grid2Op Diagnostics",
        "",
    ]
    grid = summary["domains"]["grid2op"]["combined"]
    lines += [
        f"- CF total: `{fmt(grid.get('cf_total'))}`",
        f"- Lead-lag: `{fmt(grid.get('lead_lag'))}`",
        f"- Non-CF macro: `{fmt(grid.get('non_cf_macro'))}`",
        "",
        "| Grid2Op task family | N | Accuracy |",
        "|---|---:|---:|",
    ]
    for task, item in grid.get("by_task_family", {}).items():
        lines.append(f"| {task} | {item['n']} | {fmt(item['accuracy'])} |")

    for domain in ("citylearn", "finrl"):
        lines += [
            "",
            f"## {domain} Task Families",
            "",
            "| Task family | N | Accuracy |",
            "|---|---:|---:|",
        ]
        for task, item in summary["domains"][domain]["combined"].get("by_task_family", {}).items():
            lines.append(f"| {task} | {item['n']} | {fmt(item['accuracy'])} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--qa_subdir", default="rule_qa")
    parser.add_argument("--out_json", default="")
    parser.add_argument("--out_md", default="")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    domains = {domain: summarize_domain(run_dir, domain, args.qa_subdir) for domain in DOMAINS}
    summary = {
        "run_dir": str(run_dir),
        "qa_subdir": args.qa_subdir,
        "domains": domains,
        "decision": make_decision(domains),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.out_json:
        Path(args.out_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.out_md:
        Path(args.out_md).write_text(markdown(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
