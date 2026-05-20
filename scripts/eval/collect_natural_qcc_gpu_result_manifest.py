#!/usr/bin/env python3
"""Collect small natural-QCC GPU smoke result artifacts for GitHub sync.

This intentionally excludes model checkpoints and any `final_model` contents.
It emits a JSON manifest plus a shell pathspec file that can be passed to
`git add --pathspec-from-file`.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
DEFAULT_QCOND = BASE / "tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520"
DEFAULT_NOQ = BASE / "tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520"
DEFAULT_COMPARE = BASE / "tsrlm_natural_qcc_crossdomain_qcond_vs_noquestion_audit_20260520.json"
DEFAULT_OBJECTIVE = BASE / "natural_qcc_objective_completion_audit_20260520.json"
DEFAULT_OUT = BASE / "natural_qcc_gpu_result_manifest_20260520.json"

COMMON_SAFE_RELATIVE_FILES = (
    "preflight.json",
    "natural_qcc_smoke_pipeline_plan.json",
    "natural_qcc_smoke_pipeline_summary.json",
    "multisim_v5_train_smoke_report.json",
    "natural_qcc_gpu_smoke_result_audit.json",
    "natural_qcc_gpu_smoke_result_audit.md",
    "natural_qcc_caption_quality_audit.json",
    "natural_qcc_caption_quality_audit.md",
    "natural_qcc_caption_quality_audit.rows.jsonl",
    "generate_eval_test_clean/metrics.json",
    "generate_eval_test_clean/predictions.jsonl",
)
STRICT_QA_SAFE_RELATIVE_FILES = (
    "generate_eval_test_clean/rule_qa/qa_metrics.json",
    "generate_eval_test_clean/rule_qa/qa_predictions.jsonl",
    "generate_eval_test_clean/rule_qa/NATURAL_QCC_PREDICTION_QA_20260519_ZH.md",
)
SEMANTIC_QA_SAFE_RELATIVE_FILES = (
    "generate_eval_test_clean/rule_qa/semantic_qa_metrics.json",
    "generate_eval_test_clean/rule_qa/semantic_qa_predictions.jsonl",
    "generate_eval_test_clean/rule_qa/NATURAL_QCC_SEMANTIC_PREDICTION_QA_20260520_ZH.md",
)
SAFE_RELATIVE_FILES = COMMON_SAFE_RELATIVE_FILES + STRICT_QA_SAFE_RELATIVE_FILES + SEMANTIC_QA_SAFE_RELATIVE_FILES


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def file_item(path: Path, *, required: bool) -> dict[str, Any]:
    exists = path.exists()
    item: dict[str, Any] = {
        "path": rel(path),
        "exists": exists,
        "required": required,
        "bytes": path.stat().st_size if exists else 0,
    }
    if path.suffix == ".jsonl":
        item["rows"] = count_jsonl(path)
    return item


def run_items(run_dir: Path, *, qa_kind: str = "strict") -> list[dict[str, Any]]:
    qa_files = SEMANTIC_QA_SAFE_RELATIVE_FILES if qa_kind == "semantic" else STRICT_QA_SAFE_RELATIVE_FILES
    safe_files = COMMON_SAFE_RELATIVE_FILES + qa_files
    required = {
        "preflight.json",
        "natural_qcc_smoke_pipeline_summary.json",
        "natural_qcc_gpu_smoke_result_audit.json",
        "natural_qcc_gpu_smoke_result_audit.md",
        "natural_qcc_caption_quality_audit.json",
        "natural_qcc_caption_quality_audit.md",
        "natural_qcc_caption_quality_audit.rows.jsonl",
        "generate_eval_test_clean/predictions.jsonl",
        qa_files[0],
        qa_files[1],
    }
    return [file_item(run_dir / name, required=name in required) for name in safe_files]


def audit_items(compare_audit: Path, objective_audit: Path) -> list[dict[str, Any]]:
    return [
        file_item(compare_audit, required=True),
        file_item(compare_audit.with_suffix(".md"), required=True),
        file_item(objective_audit, required=True),
        file_item(objective_audit.with_suffix(".md"), required=True),
    ]


def has_unsafe_path(items: list[dict[str, Any]]) -> bool:
    unsafe_markers = ("/final_model/", "pytorch_model.bin", "adapter_model", ".safetensors", "/checkpoint-")
    return any(any(marker in item["path"] for marker in unsafe_markers) for item in items)


def audit_summary(run_dir: Path) -> dict[str, Any]:
    audit = load_json(run_dir / "natural_qcc_gpu_smoke_result_audit.json") or {}
    checks = audit.get("checks") if isinstance(audit.get("checks"), dict) else {}
    decision = audit.get("decision") if isinstance(audit.get("decision"), dict) else {}
    generated = audit.get("generated_qa_metrics") if isinstance(audit.get("generated_qa_metrics"), dict) else {}
    return {
        "audit_pass": bool(audit.get("audit_pass")),
        "decision_status": decision.get("status"),
        "generated_accuracy": generated.get("accuracy"),
        "generated_rows": generated.get("n"),
        "pipeline_complete": bool(checks.get("pipeline_complete")),
        "predictions_exist": bool(checks.get("predictions_exist")),
        "qa_metrics_exists": bool(checks.get("qa_metrics_exists")),
    }


def caption_quality_summary(run_dir: Path) -> dict[str, Any]:
    audit = load_json(run_dir / "natural_qcc_caption_quality_audit.json") or {}
    metrics = audit.get("metrics") if isinstance(audit.get("metrics"), dict) else {}
    return {
        "exists": bool(audit),
        "quality_gate_pass": bool(metrics.get("quality_gate_pass")),
        "rows": metrics.get("n"),
        "evidence_shape_rate": metrics.get("evidence_shape_rate"),
        "answer_label_only_rate": metrics.get("answer_label_only_rate"),
        "numeric_evidence_rate": metrics.get("numeric_evidence_rate"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qcond_run_dir", type=Path, default=DEFAULT_QCOND)
    parser.add_argument("--no_question_run_dir", type=Path, default=DEFAULT_NOQ)
    parser.add_argument("--compare_audit", type=Path, default=DEFAULT_COMPARE)
    parser.add_argument("--objective_audit", type=Path, default=DEFAULT_OBJECTIVE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pathspec_out", type=Path, default=None)
    parser.add_argument("--qa_kind", choices=["strict", "semantic"], default="strict")
    args = parser.parse_args()

    qcond_items = run_items(args.qcond_run_dir, qa_kind=args.qa_kind)
    noq_items = run_items(args.no_question_run_dir, qa_kind=args.qa_kind)
    compare_items = audit_items(args.compare_audit, args.objective_audit)
    all_items = qcond_items + noq_items + compare_items
    required_missing = [item["path"] for item in all_items if item["required"] and not item["exists"]]
    unsafe = has_unsafe_path(all_items)
    pathspec = [item["path"] for item in all_items if item["exists"]]

    compare_payload = load_json(args.compare_audit) or {}
    report = {
        "qcond_run_dir": rel(args.qcond_run_dir),
        "no_question_run_dir": rel(args.no_question_run_dir),
        "compare_audit": rel(args.compare_audit),
        "objective_audit": rel(args.objective_audit),
        "qcond": audit_summary(args.qcond_run_dir),
        "qcond_caption_quality": caption_quality_summary(args.qcond_run_dir),
        "no_question": audit_summary(args.no_question_run_dir),
        "no_question_caption_quality": caption_quality_summary(args.no_question_run_dir),
        "compare_decision": compare_payload.get("decision", {}),
        "files": all_items,
        "required_missing": required_missing,
        "unsafe_path_detected": unsafe,
        "pathspec": pathspec,
        "manifest_pass": not required_missing and not unsafe,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pathspec_out = args.pathspec_out or args.out.with_suffix(".pathspec")
    pathspec_out.write_text("\n".join(pathspec + [rel(args.out), rel(pathspec_out)]) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["manifest_pass"] else 1)


if __name__ == "__main__":
    main()
