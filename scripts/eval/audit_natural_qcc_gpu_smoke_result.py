#!/usr/bin/env python3
"""Audit a completed natural-QCC GPU smoke run.

The audit is intentionally stricter than file-existence checks. It verifies
that the pipeline completed, generated test predictions exist, rule-QA metrics
exist, and the generated-caption QA is compared against the local natural-QCC
baselines.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519"
DEFAULT_RUN_DIR = BASE / "tsrlm_natural_qcc_expansion_smoke_qwen3_4b_20260520"
DEFAULT_PROBE = BASE / "probe_eval/natural_qcc_probe_results.json"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def metric(summary: dict[str, Any] | None, *keys: str) -> Any:
    cur: Any = summary
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def markdown(report: dict[str, Any]) -> str:
    checks = report["checks"]
    metrics = report.get("generated_qa_metrics") or {}
    baseline = report.get("baseline_accuracy") or {}
    lines = [
        "# Natural QCC GPU Smoke Result Audit（2026-05-20）",
        "",
        f"- run_dir: `{report['run_dir']}`",
        f"- audit_pass: `{report['audit_pass']}`",
        f"- generated QA accuracy: `{metrics.get('accuracy')}`",
        f"- generated QA rows: `{metrics.get('n')}`",
        "",
        "## Checks",
        "",
        "| check | pass |",
        "| --- | ---: |",
    ]
    for key, value in checks.items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Baseline Comparison",
            "",
            "| condition | accuracy |",
            "| --- | ---: |",
        ]
    )
    for key in ("natural_oracle", "generic_caption", "statistical_caption", "question_only"):
        lines.append(f"| `{key}` | `{baseline.get(key)}` |")
    lines.append(f"| `generated_caption` | `{metrics.get('accuracy')}` |")
    lines.extend(
        [
            "",
            "## Interpretation Guardrail",
            "",
            "只有 `audit_pass=true` 时，才能把该 run 当作 generated-caption QA 结果；否则只能作为失败/阻塞记录。",
            "若 generated-caption QA 未超过 `question_only`，应报告为 training/interface failure，而不是 QCC 成功。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--probe_results", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    run_dir = args.run_dir
    preflight = load_json(run_dir / "preflight.json")
    pipeline = load_json(run_dir / "natural_qcc_smoke_pipeline_summary.json")
    predictions = run_dir / "generate_eval_test_clean/predictions.jsonl"
    qa_metrics_path = run_dir / "generate_eval_test_clean/rule_qa/qa_metrics.json"
    qa_summary = load_json(qa_metrics_path)
    probe = load_json(args.probe_results)

    generated_metrics = metric(qa_summary, "metrics") or {}
    baseline_accuracy = {}
    if probe:
        for key in ("natural_oracle", "generic_caption", "statistical_caption", "question_only"):
            baseline_accuracy[key] = metric(probe, "baselines", key, "accuracy")

    checks = {
        "preflight_exists": preflight is not None,
        "preflight_pass": bool(preflight and preflight.get("preflight_pass")),
        "pipeline_summary_exists": pipeline is not None,
        "pipeline_complete": bool(pipeline and pipeline.get("complete")),
        "predictions_exist": predictions.exists(),
        "prediction_rows_positive": count_jsonl(predictions) > 0,
        "qa_metrics_exists": qa_summary is not None,
        "qa_rows_positive": int(generated_metrics.get("n") or 0) > 0,
        "baseline_probe_exists": probe is not None,
        "baseline_has_question_only": baseline_accuracy.get("question_only") is not None,
    }
    audit_pass = all(checks.values())
    question_only = baseline_accuracy.get("question_only")
    generated_acc = generated_metrics.get("accuracy")
    report = {
        "run_dir": rel(run_dir),
        "preflight_json": rel(run_dir / "preflight.json"),
        "pipeline_summary_json": rel(run_dir / "natural_qcc_smoke_pipeline_summary.json"),
        "predictions_jsonl": rel(predictions),
        "qa_metrics_json": rel(qa_metrics_path),
        "probe_results_json": rel(args.probe_results),
        "checks": checks,
        "audit_pass": audit_pass,
        "generated_qa_metrics": generated_metrics,
        "baseline_accuracy": baseline_accuracy,
        "beats_question_only": (
            generated_acc is not None and question_only is not None and float(generated_acc) > float(question_only)
        ),
    }
    out = args.out or (run_dir / "natural_qcc_gpu_smoke_result_audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    out.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if audit_pass else 1)


if __name__ == "__main__":
    main()

