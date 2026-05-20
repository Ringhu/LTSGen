#!/usr/bin/env python3
"""Audit the six-domain scenario-first Natural-QCC smoke set."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DOMAINS = ("grid2op", "citylearn", "traffic", "water", "aiopslab", "finrl")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", required=True)
    parser.add_argument("--sft", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--min_per_domain", type=int, default=10)
    args = parser.parse_args()

    rows_path = Path(args.rows)
    sft_path = Path(args.sft)
    summary_path = Path(args.summary)
    rows = load_jsonl(rows_path)
    sft_rows = load_jsonl(sft_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    issues: list[dict[str, Any]] = []
    required_fields = [
        "id",
        "merge_source_name",
        "smoke_source_tier",
        "raw_compact_values",
        "values",
        "scenario_first_generation",
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
    ]
    by_domain = Counter(row.get("merge_source_name", "") for row in rows)
    by_source_tier = Counter(row.get("smoke_source_tier", "") for row in rows)
    by_domain_source_tier: dict[str, Counter[str]] = defaultdict(Counter)

    seen_ids: set[str] = set()
    for row in rows:
        row_id = str(row.get("id", ""))
        if row_id in seen_ids:
            issues.append({"id": row_id, "issue": "duplicate_id"})
        seen_ids.add(row_id)

        for field in required_fields:
            if field not in row or row[field] in ("", [], None):
                issues.append({"id": row_id, "issue": f"missing_{field}"})
        domain = row.get("merge_source_name", "")
        source_tier = row.get("smoke_source_tier", "")
        by_domain_source_tier[str(domain)][str(source_tier)] += 1

        if domain not in DOMAINS:
            issues.append({"id": row_id, "issue": "unexpected_domain", "domain": domain})
        if source_tier not in {"controlled_scenario_first_generator", "real_grid2op_pair_adapter"}:
            issues.append({"id": row_id, "issue": "unexpected_source_tier", "source_tier": source_tier})
        if source_tier == "real_grid2op_pair_adapter" and domain != "grid2op":
            issues.append({"id": row_id, "issue": "real_adapter_non_grid2op"})
        if len(row.get("options", [])) != 4 or len(row.get("options_zh", [])) != 4:
            issues.append({"id": row_id, "issue": "bad_option_count"})
        if row.get("answer_label") != (row.get("support_slots") or {}).get("answer_label"):
            issues.append({"id": row_id, "issue": "answer_support_mismatch"})
        if row.get("target_caption") != row.get("output"):
            issues.append({"id": row_id, "issue": "target_output_mismatch"})
        if str(row.get("answer_label", "")) not in str(row.get("target_caption", "")):
            issues.append({"id": row_id, "issue": "caption_missing_answer_label"})
        order = (row.get("scenario_first_generation") or {}).get("generation_order") or []
        if not order:
            issues.append({"id": row_id, "issue": "missing_generation_order"})
        elif source_tier == "real_grid2op_pair_adapter":
            if not any("roll out factual and intervention traces" in str(x) for x in order):
                issues.append({"id": row_id, "issue": "real_adapter_missing_rollout_order"})
        elif not str(order[0]).startswith("sample domain scenario"):
            issues.append({"id": row_id, "issue": "controlled_missing_scenario_first_order"})

    for domain in DOMAINS:
        if by_domain.get(domain, 0) < args.min_per_domain:
            issues.append(
                {
                    "id": domain,
                    "issue": "domain_below_minimum",
                    "count": by_domain.get(domain, 0),
                    "minimum": args.min_per_domain,
                }
            )

    sft_ids = {row.get("id") for row in sft_rows}
    row_ids = {row.get("id") for row in rows}
    if len(sft_rows) != len(rows):
        issues.append({"id": "sft", "issue": "sft_count_mismatch", "rows": len(rows), "sft": len(sft_rows)})
    if sft_ids != row_ids:
        issues.append({"id": "sft", "issue": "sft_id_set_mismatch"})
    for row in sft_rows:
        for field in ("id", "values", "prompt", "output", "target_caption", "meta"):
            if field not in row or row[field] in ("", [], None):
                issues.append({"id": row.get("id", ""), "issue": f"sft_missing_{field}"})

    checks = {
        "summary_n_matches": summary.get("n") == len(rows),
        "all_domains_present": all(by_domain.get(domain, 0) > 0 for domain in DOMAINS),
        "min_per_domain_met": all(by_domain.get(domain, 0) >= args.min_per_domain for domain in DOMAINS),
        "sft_count_matches": len(sft_rows) == len(rows),
        "no_empty_caption": all(row.get("target_caption") for row in rows),
        "no_missing_chinese": all(row.get("question_zh") and row.get("options_zh") and row.get("natural_evidence_zh") for row in rows),
        "answer_support_caption_consistent": not any(
            issue["issue"] in {"answer_support_mismatch", "target_output_mismatch", "caption_missing_answer_label"}
            for issue in issues
        ),
    }
    report = {
        "pass": all(checks.values()) and not issues,
        "checks": checks,
        "issue_count": len(issues),
        "issues": issues[:200],
        "n_rows": len(rows),
        "by_domain": dict(by_domain),
        "by_source_tier": dict(by_source_tier),
        "by_domain_source_tier": {domain: dict(counter) for domain, counter in sorted(by_domain_source_tier.items())},
        "answer_distribution": dict(Counter(row.get("answer", "") for row in rows)),
        "rows_path": str(rows_path),
        "sft_path": str(sft_path),
        "summary_path": str(summary_path),
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
