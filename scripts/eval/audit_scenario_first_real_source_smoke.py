#!/usr/bin/env python3
"""Audit the six-domain real-source Natural-QCC smoke artifact."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = ROOT / ".research/general-qcc-captioner-20260515/scenario_first_real_source_smoke_20260521"
DATASET_NAME = "real_source_natural_qcc_smoke"
DOMAINS = ("grid2op", "citylearn", "traffic", "water", "aiopslab", "finrl")
ALLOWED_SOURCE_KINDS = {
    "grid2op": {"real_trace_artifact"},
    "citylearn": {"real_trace_artifact"},
    "traffic": {"official_simulator_export"},
    "water": {"official_simulator_export"},
    "aiopslab": {"official_simulator_export"},
    "finrl": {"local_historical_ohlcv_smoke"},
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def has_injected_control_signature(row: dict[str, Any]) -> bool:
    support = row.get("support_slots") or (row.get("meta") or {}).get("support_slots") or {}
    probe = json.dumps(
        {
            "task_family": row.get("task_family"),
            "support_slots": support,
            "target_caption": row.get("target_caption") or row.get("oracle_evidence_caption"),
        },
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    return any(
        term in probe
        for term in (
            "controlled_v",
            "controlled_anomaly",
            "anomaly_injected",
            '"injected": true',
            '"injected": 1',
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke_dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--per_domain", type=int, default=10)
    args = parser.parse_args()

    smoke_dir = args.smoke_dir
    rows_path = smoke_dir / f"{DATASET_NAME}.jsonl"
    sft_path = smoke_dir / f"{DATASET_NAME}_sft.jsonl"
    summary_path = smoke_dir / f"{DATASET_NAME}_summary.json"
    report_path = smoke_dir / "REAL_SOURCE_NATURAL_QCC_SMOKE_REPORT_20260521_ZH.md"
    rows = load_jsonl(rows_path)
    sft_rows = load_jsonl(sft_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    issues: list[dict[str, Any]] = []
    required = [
        "id",
        "source_row_id",
        "raw_compact_values",
        "values",
        "source_path",
        "source_kind",
        "real_source_tier",
        "official_target_simulator",
        "real_source_generation",
        "scenario_first_generation",
        "scene_en",
        "scene_zh",
        "question",
        "question_zh",
        "options",
        "options_zh",
        "answer",
        "answer_label",
        "answer_zh",
        "support_slots",
        "natural_evidence_caption",
        "natural_evidence_zh",
        "target_caption",
        "prompt",
        "output",
        "figure_path",
        "meta",
    ]
    for row in rows:
        row_id = row.get("id", "")
        domain = row.get("merge_source_name", "")
        for field in required:
            if field not in row or row[field] in ("", [], None):
                issues.append({"id": row_id, "issue": f"missing_{field}"})
        if domain not in DOMAINS:
            issues.append({"id": row_id, "issue": "unexpected_domain", "domain": domain})
        if row.get("source_kind") not in ALLOWED_SOURCE_KINDS.get(domain, set()):
            issues.append({"id": row_id, "issue": "bad_source_kind", "domain": domain, "source_kind": row.get("source_kind")})
        combined_source_text = f"{row.get('source_kind', '')} {row.get('source_path', '')} {row.get('real_source_tier', '')}".lower()
        if "controlled" in combined_source_text:
            issues.append({"id": row_id, "issue": "controlled_source_leaked"})
        if has_injected_control_signature(row):
            issues.append({"id": row_id, "issue": "injected_control_signature_leaked"})
        order = (row.get("real_source_generation") or {}).get("generation_order") or []
        if not order or not str(order[0]).startswith("load real/official source artifact"):
            issues.append({"id": row_id, "issue": "generation_order_not_real_source_first"})
        if "extract source time-series window without synthesizing a controlled replacement" not in order:
            issues.append({"id": row_id, "issue": "missing_no_controlled_replacement_step"})
        support = row.get("support_slots") or {}
        if row.get("answer_label") != support.get("answer_label"):
            issues.append({"id": row_id, "issue": "answer_label_support_mismatch"})
        if row.get("target_caption") != row.get("output"):
            issues.append({"id": row_id, "issue": "output_target_mismatch"})
        if len(row.get("options") or []) != 4 or len(row.get("options_zh") or []) != 4:
            issues.append({"id": row_id, "issue": "option_count_not_4"})
        if not isinstance(row.get("raw_compact_values"), list) or not row["raw_compact_values"] or not isinstance(row["raw_compact_values"][0], list):
            issues.append({"id": row_id, "issue": "bad_raw_compact_values"})
        figure = row.get("figure_path")
        if figure and not (ROOT / figure).exists():
            issues.append({"id": row_id, "issue": "missing_figure", "figure_path": figure})
        meta = row.get("meta") or {}
        for field in ("source_row_id", "source_kind", "real_source_tier", "question_zh", "natural_evidence_zh"):
            if not meta.get(field):
                issues.append({"id": row_id, "issue": f"meta_missing_{field}"})

    by_domain = Counter(row.get("merge_source_name", "") for row in rows)
    by_source_kind = Counter(row.get("source_kind", "") for row in rows)
    by_domain_source_kind: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        by_domain_source_kind[row.get("merge_source_name", "")][row.get("source_kind", "")] += 1

    sft_count_ok = len(rows) == len(sft_rows)
    if not sft_count_ok:
        issues.append({"id": "sft", "issue": "sft_count_mismatch", "rows": len(rows), "sft": len(sft_rows)})
    for row in sft_rows:
        for field in ("id", "values", "prompt", "output", "target_caption", "meta"):
            if field not in row or row[field] in ("", [], None):
                issues.append({"id": row.get("id", ""), "issue": f"sft_missing_{field}"})

    expected_domain_counts = {domain: by_domain.get(domain, 0) >= args.per_domain for domain in DOMAINS}
    checks = {
        "summary_n_matches": summary.get("n") == len(rows),
        "sft_count_matches": sft_count_ok,
        "all_domains_present": all(by_domain.get(domain, 0) > 0 for domain in DOMAINS),
        "all_domains_meet_per_domain": all(expected_domain_counts.values()),
        "source_kind_allowed": not any(issue["issue"] == "bad_source_kind" for issue in issues),
        "no_controlled_source": not any(issue["issue"] == "controlled_source_leaked" for issue in issues),
        "no_injected_control_signature": not any(issue["issue"] == "injected_control_signature_leaked" for issue in issues),
        "real_source_order_present": not any(
            issue["issue"] in {"generation_order_not_real_source_first", "missing_no_controlled_replacement_step"}
            for issue in issues
        ),
        "caption_and_chinese_present": not any(
            issue["issue"].startswith("missing_question_zh")
            or issue["issue"].startswith("missing_options_zh")
            or issue["issue"].startswith("missing_natural_evidence")
            for issue in issues
        ),
        "answer_support_consistent": not any(
            issue["issue"] in {"answer_label_support_mismatch", "output_target_mismatch"} for issue in issues
        ),
        "figures_exist": not any(issue["issue"] == "missing_figure" for issue in issues),
        "report_exists": report_path.exists(),
    }
    report = {
        "pass": all(checks.values()) and not issues,
        "checks": checks,
        "issue_count": len(issues),
        "issues": issues[:100],
        "n_rows": len(rows),
        "by_domain": dict(by_domain),
        "by_split": dict(Counter(row.get("split", "") for row in rows)),
        "by_source_kind": dict(by_source_kind),
        "by_domain_source_kind": {domain: dict(counter) for domain, counter in sorted(by_domain_source_kind.items())},
        "answer_distribution": dict(Counter(row.get("answer", "") for row in rows)),
        "expected_domain_counts": expected_domain_counts,
        "artifacts": {
            "rows": rel(rows_path),
            "sft": rel(sft_path),
            "summary": rel(summary_path),
            "report": rel(report_path),
        },
    }
    out_path = smoke_dir / f"{DATASET_NAME}_audit.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
