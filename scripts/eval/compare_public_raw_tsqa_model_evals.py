#!/usr/bin/env python3
"""Build a comparison table for Public Raw TSQA v4 model evaluations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_DIR = (
    ROOT
    / ".research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521/model_eval_20260521"
)
DEFAULT_OUT_MD = DEFAULT_EVAL_DIR / "MODEL_EVAL_COMPARISON_20260521.md"
DEFAULT_OUT_JSONL = DEFAULT_EVAL_DIR / "MODEL_EVAL_COMPARISON_20260521.jsonl"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_row(metrics_path: Path) -> dict[str, Any]:
    metrics = load_json(metrics_path)
    run = metrics.get("run", {})
    overall = metrics.get("overall", {})
    by_language = metrics.get("by_language", {})
    by_domain = metrics.get("by_domain", {})
    return {
        "run_name": metrics_path.parent.name,
        "model": run.get("model", ""),
        "provider": run.get("provider", ""),
        "n_rows": run.get("n_rows", 0),
        "n_prompts": overall.get("n", 0),
        "accuracy": overall.get("accuracy", 0.0),
        "en_accuracy": by_language.get("en", {}).get("accuracy", None),
        "zh_accuracy": by_language.get("zh", {}).get("accuracy", None),
        "empty_answer_rate": overall.get("empty_answer_rate", 0.0),
        "mean_latency_sec": overall.get("mean_latency_sec", 0.0),
        "error_count": run.get("error_count", 0),
        "water_service_accuracy": by_domain.get("water_service", {}).get("accuracy", None),
        "metrics_path": rel(metrics_path),
        "predictions_path": rel(metrics_path.parent / "predictions.jsonl"),
        "error_summary_path": rel(metrics_path.parent / "error_summary.json"),
    }


def keep_row(row: dict[str, Any], *, full_only: bool) -> bool:
    if not full_only:
        return True
    return int(row.get("n_prompts") or 0) == 78 and int(row.get("n_rows") or 0) == 39


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_markdown(path: Path, rows: list[dict[str, Any]], *, eval_dir: Path, full_only: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Public Raw TSQA v4 Model Evaluation Comparison",
        "",
        f"- eval_dir: `{rel(eval_dir)}`",
        f"- full_only: `{str(full_only).lower()}`",
        f"- runs: `{len(rows)}`",
        "",
        "| Run | Provider | Model | Prompts | Acc. | EN | ZH | Water | Empty | Errors | Mean Latency |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            f"`{row['run_name']}` | "
            f"`{row['provider']}` | "
            f"`{row['model']}` | "
            f"{row['n_prompts']} | "
            f"{fmt(row['accuracy'])} | "
            f"{fmt(row['en_accuracy'])} | "
            f"{fmt(row['zh_accuracy'])} | "
            f"{fmt(row['water_service_accuracy'])} | "
            f"{fmt(row['empty_answer_rate'])} | "
            f"{row['error_count']} | "
            f"{fmt(row['mean_latency_sec'])} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval_dir", type=Path, default=DEFAULT_EVAL_DIR)
    parser.add_argument("--out_md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--out_jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    parser.add_argument("--include_pilots", action="store_true")
    args = parser.parse_args()

    rows = [
        run_row(path)
        for path in sorted(args.eval_dir.glob("*/metrics.json"))
    ]
    rows = [row for row in rows if keep_row(row, full_only=not args.include_pilots)]
    rows.sort(key=lambda row: (-float(row.get("accuracy") or 0.0), str(row.get("model")), str(row.get("run_name"))))
    write_jsonl(args.out_jsonl, rows)
    write_markdown(args.out_md, rows, eval_dir=args.eval_dir, full_only=not args.include_pilots)
    print(json.dumps({"runs": len(rows), "out_md": rel(args.out_md), "out_jsonl": rel(args.out_jsonl)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
