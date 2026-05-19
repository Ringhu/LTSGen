#!/usr/bin/env python3
"""Summarize natural-QCC caption adaptation diagnostics.

This report combines downstream QA metrics with the caption-quality audit. It is
not a GPU training result; it is a compact local diagnostic for separating
evidence-caption behavior from answer-label shortcuts before the true QCC smoke
can run on a GPU host.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
DEFAULT_PROBE = BASE / "probe_eval/natural_qcc_probe_results.json"
DEFAULT_OUT = BASE / "natural_qcc_caption_adaptation_summary_20260520.json"


DIAGNOSTICS = (
    {
        "name": "natural_oracle",
        "kind": "oracle_evidence",
        "qa_source": ("baselines", "natural_oracle"),
        "quality": BASE / "probe_eval/natural_oracle_caption_quality_audit.json",
        "scope": "all reviewer-positive rows",
    },
    {
        "name": "natural_evidence_no_label",
        "kind": "oracle_evidence_without_answer_label",
        "qa_source": ("baselines", "natural_evidence_no_label"),
        "quality": BASE / "probe_eval/natural_evidence_no_label_caption_quality_audit.json",
        "scope": "all reviewer-positive rows",
    },
    {
        "name": "nearest_caption_question_conditioned",
        "kind": "train_split_nearest_caption_probe",
        "qa_source": ("trainable", "nearest_caption_question_conditioned"),
        "quality": BASE / "probe_eval/nearest_caption_question_conditioned_caption_quality_audit.json",
        "scope": "test split",
    },
    {
        "name": "nearest_caption_no_question",
        "kind": "train_split_nearest_caption_probe",
        "qa_source": ("trainable", "nearest_caption_no_question"),
        "quality": BASE / "probe_eval/nearest_caption_no_question_caption_quality_audit.json",
        "scope": "test split",
    },
    {
        "name": "local_ranker_qcond",
        "kind": "local_option_ranker_answer_label_shortcut",
        "qa_summary": BASE / "local_caption_ranker/qcond/local_caption_ranker_summary.json",
        "quality": BASE / "local_caption_ranker/qcond/natural_qcc_caption_quality_audit.json",
        "scope": "test split",
    },
    {
        "name": "local_ranker_no_question",
        "kind": "local_option_ranker_answer_label_shortcut",
        "qa_summary": BASE / "local_caption_ranker/no_question/local_caption_ranker_summary.json",
        "quality": BASE / "local_caption_ranker/no_question/natural_qcc_caption_quality_audit.json",
        "scope": "test split",
    },
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


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
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def qa_metrics(item: dict[str, Any], probe: dict[str, Any] | None) -> dict[str, Any]:
    if "qa_source" in item:
        metrics = nested(probe, *item["qa_source"]) or {}
        return {
            "qa_exists": bool(metrics),
            "qa_accuracy": as_float(metrics.get("accuracy")),
            "qa_rows": int(metrics.get("n") or 0),
            "empty_answer_rate": as_float(metrics.get("empty_answer_rate")),
        }
    summary = load_json(item["qa_summary"])
    metrics = nested(summary, "eval_metrics") or {}
    return {
        "qa_exists": summary is not None,
        "qa_accuracy": as_float(metrics.get("accuracy")),
        "qa_rows": int(metrics.get("n") or 0),
        "empty_answer_rate": as_float(metrics.get("empty_answer_rate")),
    }


def quality_metrics(path: Path) -> dict[str, Any]:
    audit = load_json(path)
    metrics = nested(audit, "metrics") or {}
    return {
        "quality_exists": audit is not None,
        "quality_rows": int(metrics.get("n") or 0),
        "quality_gate_pass": bool(metrics.get("quality_gate_pass")),
        "evidence_shape_rate": as_float(metrics.get("evidence_shape_rate")),
        "numeric_evidence_rate": as_float(metrics.get("numeric_evidence_rate")),
        "answer_label_only_rate": as_float(metrics.get("answer_label_only_rate")),
        "failure_reasons": metrics.get("failure_reasons") or {},
    }


def build_report(probe_path: Path) -> dict[str, Any]:
    probe = load_json(probe_path)
    rows = []
    for item in DIAGNOSTICS:
        quality_path = item["quality"]
        row = {
            "name": item["name"],
            "kind": item["kind"],
            "scope": item["scope"],
            "quality_path": rel(quality_path),
        }
        row.update(qa_metrics(item, probe))
        row.update(quality_metrics(quality_path))
        row["evidence_caption_signal"] = bool(
            row["qa_exists"]
            and row["quality_exists"]
            and row["qa_rows"] > 0
            and row["quality_rows"] > 0
            and (row["answer_label_only_rate"] is not None and row["answer_label_only_rate"] <= 0.2)
            and (row["evidence_shape_rate"] is not None and row["evidence_shape_rate"] >= 0.75)
        )
        rows.append(row)

    by_name = {row["name"]: row for row in rows}
    qcond = by_name.get("nearest_caption_question_conditioned", {})
    no_question = by_name.get("nearest_caption_no_question", {})
    ranker_qcond = by_name.get("local_ranker_qcond", {})
    qa_gap = None
    if qcond.get("qa_accuracy") is not None and no_question.get("qa_accuracy") is not None:
        qa_gap = round(qcond["qa_accuracy"] - no_question["qa_accuracy"], 4)
    quality_gap = None
    if qcond.get("evidence_shape_rate") is not None and no_question.get("evidence_shape_rate") is not None:
        quality_gap = round(qcond["evidence_shape_rate"] - no_question["evidence_shape_rate"], 4)

    return {
        "probe_results": rel(probe_path),
        "diagnostics": rows,
        "summary": {
            "nearest_qcond_qa_minus_no_question": qa_gap,
            "nearest_qcond_quality_minus_no_question": quality_gap,
            "nearest_qcond_quality_gate_pass": bool(qcond.get("quality_gate_pass")),
            "nearest_no_question_quality_gate_pass": bool(no_question.get("quality_gate_pass")),
            "local_ranker_qcond_answer_label_only_rate": ranker_qcond.get("answer_label_only_rate"),
            "interpretation": (
                "nearest-caption probe has evidence-shaped captions but is not TS-RLM/Qwen training; "
                "local ranker QA is an answer-label shortcut and is not evidence-caption adaptation."
            ),
            "claim_scope": "local_caption_adaptation_diagnostic_not_final_qcc_training",
        },
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Natural QCC Caption Adaptation Summary（2026-05-20）",
        "",
        "本报告把 QA accuracy 与 caption-quality audit 放在同一张表里，避免把答案标签捷径误认为 evidence-caption 训练成功。",
        "",
        f"- probe results: `{report['probe_results']}`",
        f"- claim scope: `{summary['claim_scope']}`",
        "",
        "## Diagnostics",
        "",
        "| diagnostic | kind | QA | evidence shaped | answer-label-only | quality gate |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in report["diagnostics"]:
        lines.append(
            f"| `{row['name']}` | `{row['kind']}` | {fmt(row['qa_accuracy'])} | "
            f"{fmt(row['evidence_shape_rate'])} | {fmt(row['answer_label_only_rate'])} | "
            f"`{row['quality_gate_pass']}` |"
        )
    lines.extend(
        [
            "",
            "## Key Read",
            "",
            f"- nearest q-conditioned QA minus no-question: `{summary['nearest_qcond_qa_minus_no_question']}`.",
            f"- nearest q-conditioned quality minus no-question: `{summary['nearest_qcond_quality_minus_no_question']}`.",
            f"- local ranker qcond answer-label-only rate: `{summary['local_ranker_qcond_answer_label_only_rate']}`.",
            "- nearest-caption 是 evidence-shaped 弱探针；local ranker 是答案标签捷径诊断；二者都不能替代 GPU 上的 TS-RLM/Qwen QCC caption SFT。",
            "",
        ]
    )
    return "\n".join(lines)


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe_results", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = build_report(args.probe_results)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.out.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
