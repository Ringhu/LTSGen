#!/usr/bin/env python3
"""Audit whether the natural-QCC cross-domain objective is complete.

This is an objective-level gate, not a method-success gate. A completed run can
still be a negative result if generated captions fail to beat baselines or the
no-question control. The objective is complete only when the data assets,
q-conditioned training, no-question training, generated-caption QA, paired
comparison, and safe result manifest are all present and auditable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
DEFAULT_OUT = BASE / "natural_qcc_objective_completion_audit_20260520.json"

PATHS = {
    "dataset_summary": BASE / "natural_qcc_crossdomain_dataset_summary.json",
    "no_question_summary": BASE / "sft_no_question/natural_qcc_crossdomain_no_question_summary.json",
    "probe_results": BASE / "probe_eval/natural_qcc_probe_results.json",
    "qcond_audit": BASE / "tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/natural_qcc_gpu_smoke_result_audit.json",
    "no_question_audit": BASE
    / "tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520/natural_qcc_gpu_smoke_result_audit.json",
    "compare_audit": BASE / "tsrlm_natural_qcc_crossdomain_qcond_vs_noquestion_audit_20260520.json",
    "manifest": BASE / "natural_qcc_gpu_result_manifest_20260520.json",
    "remote_access": BASE / "natural_qcc_remote_gpu_access_check_20260520.json",
}


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


def nested(obj: Any, *keys: str) -> Any:
    cur = obj
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


def artifact_exists(path_text: str | None) -> bool:
    if not path_text:
        return False
    path = Path(path_text)
    if path.is_absolute():
        return path.exists()
    return (ROOT / path).exists()


def all_sft_files_exist(dataset_summary: dict[str, Any] | None) -> bool:
    sft_files = nested(dataset_summary, "sft_files") or {}
    for split in ("train", "dev", "test"):
        item = sft_files.get(split)
        if not isinstance(item, dict):
            return False
        if int(item.get("n") or 0) <= 0:
            return False
        if not artifact_exists(item.get("raw")) or not artifact_exists(item.get("sft")):
            return False
    return True


def no_question_control_pass(summary: dict[str, Any] | None) -> bool:
    if not summary or not summary.get("gate_pass"):
        return False
    for split in ("train", "dev", "test"):
        item = nested(summary, "splits", split)
        if not isinstance(item, dict):
            return False
        for key in ("raw_summary", "sft_summary"):
            split_summary = item.get(key)
            if not isinstance(split_summary, dict):
                return False
            if int(split_summary.get("n") or 0) <= 0:
                return False
            if int(split_summary.get("question_marker_count") or 0) != 0:
                return False
            if int(split_summary.get("missing_prompt_count") or 0) != 0:
                return False
    return True


def probe_summary(probe: dict[str, Any] | None) -> dict[str, Any]:
    baselines = nested(probe, "baselines") or {}
    accuracies = {
        key: as_float(nested(baselines, key, "accuracy"))
        for key in ("natural_oracle", "generic_caption", "statistical_caption", "question_only")
    }
    non_oracle = [value for key, value in accuracies.items() if key != "natural_oracle" and value is not None]
    max_non_oracle = max(non_oracle) if non_oracle else None
    oracle = accuracies.get("natural_oracle")
    return {
        "exists": probe is not None,
        "accuracy": accuracies,
        "max_non_oracle": max_non_oracle,
        "oracle_load_bearing": oracle is not None and max_non_oracle is not None and oracle > max_non_oracle,
    }


def gpu_audit_summary(audit: dict[str, Any] | None) -> dict[str, Any]:
    metrics = nested(audit, "generated_qa_metrics") or {}
    decision = nested(audit, "decision") or {}
    return {
        "audit_exists": audit is not None,
        "audit_pass": bool(audit and audit.get("audit_pass")),
        "generated_accuracy": as_float(metrics.get("accuracy")),
        "generated_rows": int(metrics.get("n") or 0),
        "decision_status": decision.get("status"),
        "beats_all_non_oracle_baselines": bool(decision.get("beats_all_non_oracle_baselines")),
        "beats_question_only": bool(decision.get("beats_question_only")),
        "claim_scope": decision.get("claim_scope"),
    }


def compare_summary(compare: dict[str, Any] | None) -> dict[str, Any]:
    decision = nested(compare, "decision") or {}
    status = decision.get("status")
    return {
        "exists": compare is not None,
        "status": status,
        "complete": bool(status and status != "incomplete_or_blocked"),
        "qcond_accuracy": as_float(decision.get("qcond_accuracy")),
        "no_question_accuracy": as_float(decision.get("no_question_accuracy")),
        "qcond_minus_no_question": as_float(decision.get("qcond_minus_no_question")),
        "min_gap": as_float(decision.get("min_gap")),
        "claim_scope": decision.get("claim_scope"),
    }


def manifest_summary(manifest: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "exists": manifest is not None,
        "manifest_pass": bool(manifest and manifest.get("manifest_pass")),
        "unsafe_path_detected": bool(manifest and manifest.get("unsafe_path_detected")),
        "required_missing": nested(manifest, "required_missing") or [],
    }


def remote_access_summary(remote: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "exists": remote is not None,
        "any_access_pass": bool(remote and remote.get("any_access_pass")),
        "profiles": [
            {
                "profile": item.get("profile"),
                "reachable": item.get("reachable"),
                "access_pass": item.get("access_pass"),
                "stderr_tail": item.get("stderr_tail"),
            }
            for item in (nested(remote, "profiles") or [])
            if isinstance(item, dict)
        ],
    }


def objective_decision(completion_checks: dict[str, bool], result_checks: dict[str, Any]) -> dict[str, Any]:
    blockers = [key for key, value in completion_checks.items() if not value]
    objective_complete = not blockers
    qcond_beats_baselines = bool(result_checks.get("qcond_beats_all_non_oracle_baselines"))
    gap = as_float(result_checks.get("qcond_minus_no_question"))
    min_gap = as_float(result_checks.get("min_gap")) or 0.0
    qcond_beats_no_question = gap is not None and gap > 0
    qcond_gap_meets_min = gap is not None and gap >= min_gap

    if not objective_complete:
        status = "incomplete_or_blocked"
        summary_zh = "目标尚未完成：真实 QCC/no-question 训练、生成 caption、QA 或安全同步证据仍缺失。"
        claim_scope = "No generated-caption training claim allowed."
    elif qcond_beats_baselines and qcond_gap_meets_min:
        status = "complete_positive_qcc_signal"
        summary_zh = "目标完成，并且 q-conditioned generated-caption QA 同时超过非 oracle 基线和 no-question 对照。"
        claim_scope = "Cross-domain smoke-level positive QCC signal; not a full method claim."
    elif qcond_beats_baselines or qcond_beats_no_question:
        status = "complete_mixed_or_weak_signal"
        summary_zh = "目标完成，但 QCC 训练信号不完整；需要按弱信号或混合结果报告。"
        claim_scope = "Completed smoke with mixed result; do not overclaim."
    else:
        status = "complete_negative_signal"
        summary_zh = "目标完成，但 q-conditioned generated-caption QA 没有证明优于基线或 no-question 对照。"
        claim_scope = "Completed smoke with negative result; report failure plainly."

    return {
        "objective_complete": objective_complete,
        "status": status,
        "summary_zh": summary_zh,
        "claim_scope": claim_scope,
        "blockers": blockers,
        "qcond_beats_no_question": qcond_beats_no_question,
        "qcond_gap_meets_min": qcond_gap_meets_min,
    }


def build_report() -> dict[str, Any]:
    dataset = load_json(PATHS["dataset_summary"])
    no_question = load_json(PATHS["no_question_summary"])
    probe = load_json(PATHS["probe_results"])
    qcond_audit = load_json(PATHS["qcond_audit"])
    no_question_audit = load_json(PATHS["no_question_audit"])
    compare = load_json(PATHS["compare_audit"])
    manifest = load_json(PATHS["manifest"])
    remote_access = load_json(PATHS["remote_access"])

    probe_info = probe_summary(probe)
    qcond_info = gpu_audit_summary(qcond_audit)
    no_question_info = gpu_audit_summary(no_question_audit)
    compare_info = compare_summary(compare)
    manifest_info = manifest_summary(manifest)
    remote_info = remote_access_summary(remote_access)

    completion_checks = {
        "dataset_schema_gate_pass": bool(dataset and dataset.get("schema_gate_pass")),
        "positive_dataset_rows_present": int(nested(dataset, "positive", "n") or 0) > 0,
        "sft_split_files_present": all_sft_files_exist(dataset),
        "no_question_control_gate_pass": no_question_control_pass(no_question),
        "probe_results_present": probe_info["exists"],
        "oracle_evidence_baseline_present": probe_info["accuracy"].get("natural_oracle") is not None,
        "non_oracle_baselines_present": all(
            probe_info["accuracy"].get(key) is not None
            for key in ("generic_caption", "statistical_caption", "question_only")
        ),
        "oracle_caption_load_bearing": bool(probe_info["oracle_load_bearing"]),
        "qcond_gpu_audit_pass": bool(qcond_info["audit_pass"]),
        "no_question_gpu_audit_pass": bool(no_question_info["audit_pass"]),
        "qcond_generated_metrics_present": qcond_info["generated_accuracy"] is not None and qcond_info["generated_rows"] > 0,
        "no_question_generated_metrics_present": (
            no_question_info["generated_accuracy"] is not None and no_question_info["generated_rows"] > 0
        ),
        "qcond_vs_no_question_comparison_complete": bool(compare_info["complete"]),
        "safe_result_manifest_pass": bool(manifest_info["manifest_pass"]),
        "safe_result_manifest_has_no_unsafe_paths": bool(manifest_info["exists"] and not manifest_info["unsafe_path_detected"]),
    }
    result_checks = {
        "qcond_accuracy": qcond_info["generated_accuracy"],
        "no_question_accuracy": no_question_info["generated_accuracy"],
        "qcond_minus_no_question": compare_info["qcond_minus_no_question"],
        "min_gap": compare_info["min_gap"],
        "qcond_beats_all_non_oracle_baselines": qcond_info["beats_all_non_oracle_baselines"],
        "qcond_beats_question_only": qcond_info["beats_question_only"],
        "compare_status": compare_info["status"],
    }
    decision = objective_decision(completion_checks, result_checks)

    return {
        "objective": (
            "Run the new natural TS-QA construction through data asset evaluation, "
            "QCC caption training, no-question control training, generated-caption QA, "
            "and improvement/comparison analysis."
        ),
        "paths": {key: rel(path) for key, path in PATHS.items()},
        "dataset": {
            "schema_gate_pass": bool(dataset and dataset.get("schema_gate_pass")),
            "positive_n": int(nested(dataset, "positive", "n") or 0),
            "by_source": nested(dataset, "positive", "by_source") or {},
            "by_split": nested(dataset, "positive", "by_split") or {},
        },
        "probe": probe_info,
        "qcond": qcond_info,
        "no_question": no_question_info,
        "compare": compare_info,
        "manifest": manifest_info,
        "remote_access": remote_info,
        "completion_checks": completion_checks,
        "result_checks": result_checks,
        "decision": decision,
    }


def markdown(report: dict[str, Any]) -> str:
    decision = report["decision"]
    lines = [
        "# Natural QCC Objective Completion Gate（2026-05-20）",
        "",
        f"- status: `{decision['status']}`",
        f"- objective complete: `{decision['objective_complete']}`",
        f"- summary: {decision['summary_zh']}",
        f"- claim scope: `{decision['claim_scope']}`",
        "",
        "## Completion Checks",
        "",
        "| check | pass |",
        "| --- | ---: |",
    ]
    for key, value in report["completion_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## Result Checks", "", "| item | value |", "| --- | --- |"])
    for key, value in report["result_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## Blockers", ""])
    blockers = decision.get("blockers") or []
    if blockers:
        for blocker in blockers:
            lines.append(f"- `{blocker}`")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Remote Access Diagnostic",
            "",
            f"- any access pass: `{report['remote_access']['any_access_pass']}`",
        ]
    )
    for profile in report["remote_access"].get("profiles") or []:
        stderr = (profile.get("stderr_tail") or "").strip().replace("\n", " ")
        lines.append(
            f"- `{profile.get('profile')}` reachable=`{profile.get('reachable')}`, "
            f"access_pass=`{profile.get('access_pass')}`, stderr=`{stderr}`"
        )
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "该 gate 只在 q-conditioned 与 no-question 两条 GPU smoke 都完成、生成 caption 和 rule-QA 指标都存在、"
            "并且安全 manifest 通过时，才会把 objective 标为 complete。",
            "若 objective complete 但 QCC 没有超过 baselines/no-question，应按负结果报告，而不是改写 claim。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = build_report()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.out.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["decision"]["objective_complete"] else 1)


if __name__ == "__main__":
    main()
