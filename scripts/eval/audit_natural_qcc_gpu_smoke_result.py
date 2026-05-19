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


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_decision(*, audit_pass: bool, generated_acc: float | None, baseline: dict[str, Any]) -> dict[str, Any]:
    generic = as_float(baseline.get("generic_caption"))
    statistical = as_float(baseline.get("statistical_caption"))
    question_only = as_float(baseline.get("question_only"))
    natural_oracle = as_float(baseline.get("natural_oracle"))
    non_oracle_values = [value for value in (generic, statistical, question_only) if value is not None]
    max_non_oracle = max(non_oracle_values) if non_oracle_values else None
    beats_non_oracle = generated_acc is not None and max_non_oracle is not None and generated_acc > max_non_oracle
    if not audit_pass:
        status = "incomplete_or_blocked"
        summary_zh = "GPU smoke run 尚未完整完成，不能解释 generated-caption QA。"
        next_action_zh = "先完成远程 preflight、训练、生成和 rule-QA，再重新运行本审计。"
    elif beats_non_oracle:
        status = "smoke_improves_over_local_non_oracle_baselines"
        summary_zh = "generated caption 在当前 AIOps smoke 子集上超过所有本地非 oracle 基线。"
        next_action_zh = "把结果作为单源 smoke 证据记录；下一步扩到跨域 reviewer-positive 数据后复验。"
    else:
        status = "smoke_no_improvement_over_local_non_oracle_baselines"
        summary_zh = "generated caption 没有超过当前最强非 oracle 基线，不能作为 QCC 训练成功。"
        next_action_zh = "检查训练日志、caption 空答率和输出格式；必要时调整训练数据或目标格式。"
    return {
        "status": status,
        "summary_zh": summary_zh,
        "next_action_zh": next_action_zh,
        "baseline_max_non_oracle": max_non_oracle,
        "beats_generic_caption": generated_acc is not None and generic is not None and generated_acc > generic,
        "beats_statistical_caption": generated_acc is not None and statistical is not None and generated_acc > statistical,
        "beats_question_only": generated_acc is not None and question_only is not None and generated_acc > question_only,
        "beats_all_non_oracle_baselines": beats_non_oracle,
        "oracle_gap": natural_oracle - generated_acc if natural_oracle is not None and generated_acc is not None else None,
        "claim_scope": (
            "AIOps smoke only; not a cross-domain method claim."
            if audit_pass
            else "No training-result claim allowed."
        ),
    }


def markdown(report: dict[str, Any]) -> str:
    checks = report["checks"]
    metrics = report.get("generated_qa_metrics") or {}
    baseline = report.get("baseline_accuracy") or {}
    decision = report.get("decision") or {}
    lines = [
        "# Natural QCC GPU Smoke Result Audit（2026-05-20）",
        "",
        f"- run_dir: `{report['run_dir']}`",
        f"- audit_pass: `{report['audit_pass']}`",
        f"- status: `{decision.get('status')}`",
        f"- generated QA accuracy: `{metrics.get('accuracy')}`",
        f"- generated QA rows: `{metrics.get('n')}`",
        f"- summary: {decision.get('summary_zh')}",
        f"- next action: {decision.get('next_action_zh')}",
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
            "## Decision Fields",
            "",
            f"- baseline max non-oracle: `{decision.get('baseline_max_non_oracle')}`",
            f"- beats all non-oracle baselines: `{decision.get('beats_all_non_oracle_baselines')}`",
            f"- beats question-only: `{decision.get('beats_question_only')}`",
            f"- oracle gap: `{decision.get('oracle_gap')}`",
            f"- claim scope: `{decision.get('claim_scope')}`",
        ]
    )
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
    generated_acc = as_float(generated_metrics.get("accuracy"))
    decision = build_decision(audit_pass=audit_pass, generated_acc=generated_acc, baseline=baseline_accuracy)
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
        "decision": decision,
        "beats_question_only": decision["beats_question_only"],
    }
    out = args.out or (run_dir / "natural_qcc_gpu_smoke_result_audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    out.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if audit_pass else 1)


if __name__ == "__main__":
    main()
