#!/usr/bin/env python3
"""Compare q-conditioned and no-question natural-QCC GPU smoke runs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.eval.audit_natural_qcc_gpu_smoke_result import as_float, load_json, rel  # noqa: E402

BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
DEFAULT_QCOND = BASE / "tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520"
DEFAULT_NOQ = BASE / "tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520"
DEFAULT_OUT = BASE / "tsrlm_natural_qcc_crossdomain_qcond_vs_noquestion_audit_20260520.json"


def smoke_audit_path(run_dir: Path) -> Path:
    return run_dir / "natural_qcc_gpu_smoke_result_audit.json"


def run_summary(run_dir: Path) -> dict[str, Any]:
    audit = load_json(smoke_audit_path(run_dir))
    strict_path = run_dir / "generate_eval_test_clean/rule_qa/qa_metrics.json"
    semantic_path = run_dir / "generate_eval_test_clean/rule_qa/semantic_qa_metrics.json"
    if semantic_path.exists():
        qa_metrics = load_json(semantic_path)
        qa_metric_kind = "semantic"
        qa_metrics_path = semantic_path
    else:
        qa_metrics = load_json(strict_path)
        qa_metric_kind = "strict"
        qa_metrics_path = strict_path
    generated = (qa_metrics or {}).get("metrics", {})
    decision = (audit or {}).get("decision", {})
    return {
        "run_dir": rel(run_dir),
        "audit_json": rel(smoke_audit_path(run_dir)),
        "qa_metrics_json": rel(qa_metrics_path),
        "qa_metric_kind": qa_metric_kind,
        "audit_exists": audit is not None,
        "audit_pass": bool(audit and audit.get("audit_pass")),
        "generated_accuracy": as_float(generated.get("accuracy")),
        "generated_rows": int(generated.get("n") or 0),
        "empty_answer_rate": as_float(generated.get("empty_answer_rate")),
        "decision_status": decision.get("status"),
        "claim_scope": decision.get("claim_scope"),
    }


def decision(qcond: dict[str, Any], noq: dict[str, Any], min_gap: float) -> dict[str, Any]:
    q_acc = qcond.get("generated_accuracy")
    n_acc = noq.get("generated_accuracy")
    both_complete = bool(qcond.get("audit_pass") and noq.get("audit_pass"))
    gap = q_acc - n_acc if q_acc is not None and n_acc is not None else None
    if not both_complete:
        status = "incomplete_or_blocked"
        summary_zh = "q-conditioned 或 no-question GPU smoke 尚未完整完成，不能解释 Q-conditioning gap。"
        claim_scope = "No q-conditioning training comparison allowed."
    elif gap is not None and gap >= min_gap:
        status = "qconditioning_gap_positive"
        summary_zh = "q-conditioned generated-caption QA 明显高于 no-question 对照，可作为 smoke-level Q-conditioning 正信号。"
        claim_scope = "Cross-domain smoke only; not a full method claim."
    elif gap is not None and gap > 0:
        status = "qconditioning_gap_small"
        summary_zh = "q-conditioned generated-caption QA 高于 no-question，但差距低于预设阈值，只能算弱信号。"
        claim_scope = "Weak smoke signal; do not overclaim."
    else:
        status = "no_qconditioning_gap"
        summary_zh = "q-conditioned generated-caption QA 没有超过 no-question 对照，不能作为 QCC conditioning 成功。"
        claim_scope = "Report as training/interface failure or insufficient conditioning signal."
    return {
        "status": status,
        "summary_zh": summary_zh,
        "claim_scope": claim_scope,
        "min_gap": min_gap,
        "qcond_accuracy": q_acc,
        "no_question_accuracy": n_acc,
        "qcond_minus_no_question": gap,
    }


def markdown(report: dict[str, Any]) -> str:
    qcond = report["qcond"]
    noq = report["no_question"]
    dec = report["decision"]
    lines = [
        "# Natural QCC GPU QCond vs No-Question Audit（2026-05-20）",
        "",
        f"- status: `{dec['status']}`",
        f"- summary: {dec['summary_zh']}",
        f"- claim scope: `{dec['claim_scope']}`",
        f"- min gap: `{dec['min_gap']}`",
        "",
        "## Run Comparison",
        "",
        "| run | audit pass | rows | QA acc | empty |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| q-conditioned | `{qcond['audit_pass']}` | {qcond['generated_rows']} | `{qcond['generated_accuracy']}` | `{qcond['empty_answer_rate']}` |",
        f"| no-question | `{noq['audit_pass']}` | {noq['generated_rows']} | `{noq['generated_accuracy']}` | `{noq['empty_answer_rate']}` |",
        "",
        "## Gap",
        "",
        f"- qcond minus no-question: `{dec['qcond_minus_no_question']}`",
        "",
        "## Guardrail",
        "",
        "只有两条 GPU smoke 的单 run audit 都 `audit_pass=true` 时，才能解释 Q-conditioning gap。",
        "如果 no-question 持平或更好，应报告为 Q-conditioning 未被证明，而不是 QCC 成功。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qcond_run_dir", type=Path, default=DEFAULT_QCOND)
    parser.add_argument("--no_question_run_dir", type=Path, default=DEFAULT_NOQ)
    parser.add_argument("--min_gap", type=float, default=0.05)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    qcond = run_summary(args.qcond_run_dir)
    noq = run_summary(args.no_question_run_dir)
    report = {
        "qcond": qcond,
        "no_question": noq,
        "decision": decision(qcond, noq, min_gap=args.min_gap),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.out.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["decision"]["status"] != "incomplete_or_blocked" else 1)


if __name__ == "__main__":
    main()
