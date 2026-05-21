#!/usr/bin/env python3
"""Sanity checks for public raw TSQA v4 artifacts."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = ROOT / ".research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521"
FORBIDDEN = (
    "压缩表",
    "compact table",
    "block feature",
    "support slot",
    "Answer label",
    "rule maps this to",
    "无需了解任何特定",
    "scenario_first_pilot",
    "window_start",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def scan_forbidden(row: dict[str, Any]) -> list[str]:
    public_text = "\n".join(
        [
            str(row.get("id", "")),
            str(row.get("context_en", "")),
            str(row.get("context_zh", "")),
            str(row.get("decision_rule_en", "")),
            str(row.get("decision_rule_zh", "")),
            str(row.get("question_en", "")),
            str(row.get("question_zh", "")),
            json.dumps(row.get("options_en", {}), ensure_ascii=False),
            json.dumps(row.get("options_zh", {}), ensure_ascii=False),
        ]
    )
    return [pattern for pattern in FORBIDDEN if re.search(re.escape(pattern), public_text, flags=re.I)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--min_length", type=int, default=32)
    parser.add_argument("--require_domains", nargs="*", default=["power_grid", "building_energy", "traffic", "water_service", "service_telemetry", "market"])
    args = parser.parse_args()

    canonical = load_jsonl(args.data_dir / "canonical_raw_tsqa_v4.jsonl")
    llm = load_jsonl(args.data_dir / "llm_text_view.jsonl")
    tsllm = load_jsonl(args.data_dir / "tsllm_array_view.jsonl")
    oracle = load_jsonl(args.data_dir / "oracle_evidence.jsonl")
    audit = load_jsonl(args.data_dir / "audit_support.jsonl")
    errors: list[dict[str, Any]] = []

    ids = [row["id"] for row in canonical]
    if len(ids) != len(set(ids)):
        errors.append({"code": "duplicate_canonical_ids"})
    for name, rows in {"llm": llm, "tsllm": tsllm, "oracle": oracle, "audit": audit}.items():
        view_ids = [row["id"] for row in rows]
        if view_ids != ids:
            errors.append({"code": "view_id_mismatch", "view": name})

    by_domain = Counter(row["domain"] for row in canonical)
    for domain in args.require_domains:
        if by_domain.get(domain, 0) == 0:
            errors.append({"code": "missing_required_domain", "domain": domain})

    for row, llm_row, tsllm_row, oracle_row, audit_row in zip(canonical, llm, tsllm, oracle, audit):
        values = row.get("time_series", {}).get("values", [])
        columns = row.get("time_series", {}).get("columns", [])
        if len(values) < args.min_length:
            errors.append({"id": row["id"], "code": "series_too_short", "length": len(values)})
        if not values or any(len(record) != len(columns) for record in values):
            errors.append({"id": row["id"], "code": "bad_series_shape"})
        if row["answer"] not in {"A", "B", "C", "D"}:
            errors.append({"id": row["id"], "code": "bad_answer_letter"})
        if row["answer_label"] != row["options_en"][row["answer"]]:
            errors.append({"id": row["id"], "code": "answer_label_option_mismatch"})
        if row["answer"] != llm_row["answer"] or row["answer"] != tsllm_row["answer"] or row["answer"] != oracle_row["answer"]:
            errors.append({"id": row["id"], "code": "view_answer_mismatch"})
        if tsllm_row["timeseries"] != values:
            errors.append({"id": row["id"], "code": "tsllm_timeseries_mismatch"})
        prompt_text = "\n".join([llm_row.get("prompt_en", ""), llm_row.get("prompt_zh", ""), tsllm_row.get("text_en", ""), tsllm_row.get("text_zh", "")])
        prompt_hits = [pattern for pattern in FORBIDDEN if re.search(re.escape(pattern), prompt_text, flags=re.I)]
        if prompt_hits:
            errors.append({"id": row["id"], "code": "forbidden_public_view_text", "hits": prompt_hits})
        if audit_row["raw_semantic_answer_label"] != row["semantic_answer_label"]:
            errors.append({"id": row["id"], "code": "audit_semantic_label_mismatch"})
        hits = scan_forbidden(row)
        if hits:
            errors.append({"id": row["id"], "code": "forbidden_public_text", "hits": hits})

    summary = {
        "pass": not errors,
        "n": len(canonical),
        "error_count": len(errors),
        "errors": errors[:100],
        "by_domain": dict(by_domain),
        "answer_distribution": dict(Counter(row["answer"] for row in canonical)),
        "min_series_length": min(len(row["time_series"]["values"]) for row in canonical) if canonical else 0,
        "max_series_length": max(len(row["time_series"]["values"]) for row in canonical) if canonical else 0,
    }
    out = args.data_dir / "public_raw_tsqa_v4_sanity_check.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0 if summary["pass"] else 1)


if __name__ == "__main__":
    main()
