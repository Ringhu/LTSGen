#!/usr/bin/env python3
"""Merge schema-aligned General QCC sources into a small MultiSim artifact.

The script is intentionally conservative: it samples bounded subsets from each
source and writes both full rows and SFT rows. It does not force all simulators
to share the same channel count, because the current data contract is schema
alignment first; model-side source encoders or source-batched training should
handle channel heterogeneity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SOURCE_SPECS = {
    "grid2op": ("grid2op_broad_v5_semantic_anchor", "grid2op_broad_v5_semantic_anchor"),
    "citylearn": ("citylearn_broad_semantic_v3_qual", "citylearn_broad_semantic_v3_qual"),
    "finrl_scaled": ("finrl_broad_scaled_v1", "finrl_broad_scaled_v1"),
    "water": ("multisim_qcc_v3_stable_dataflow/water_broad_smoke_v1", "water_broad_smoke_v1"),
    "traffic": ("multisim_qcc_v3_stable_dataflow/traffic_broad_smoke_v1", "traffic_broad_smoke_v1"),
    "aiopslab_official": ("aiopslab_official_v1", "aiopslab_official_v1"),
    "aiopslab_official_v3": ("aiopslab_official_v3", "aiopslab_official_v3"),
}

REQUIRED = (
    "id",
    "domain",
    "split",
    "task_family",
    "horizon",
    "values",
    "prompt",
    "output",
    "target_caption",
    "oracle_evidence_caption",
    "generic_caption",
    "statistical_caption",
    "question",
    "options",
    "answer",
    "answer_label",
    "support_slots",
    "abstract_primitive",
    "abstract_answer_label",
    "meta",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def stable_key(row: dict[str, Any], source: str) -> str:
    return hashlib.sha256(f"{source}::{row.get('id', '')}".encode("utf-8")).hexdigest()


def source_domain(row: dict[str, Any], fallback: str) -> str:
    value = row.get("multisim_source_domain")
    if value:
        return str(value)
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    value = meta.get("multisim_source_domain") or meta.get("domain")
    if value:
        return str(value)
    return fallback


def fmt(value: float) -> str:
    return f"{float(value):.2f}"


def statistical_caption(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "No numeric time-series values were available for this row."
    rows = values
    if not isinstance(rows[0], list):
        rows = [[value] for value in rows]
    dim = max(len(row) for row in rows if isinstance(row, list))
    parts = []
    for idx in range(dim):
        series = []
        for row in rows:
            if isinstance(row, list) and idx < len(row):
                try:
                    series.append(float(row[idx]))
                except (TypeError, ValueError):
                    pass
        if not series:
            continue
        mean = sum(series) / len(series)
        var = sum((value - mean) ** 2 for value in series) / len(series)
        std = var ** 0.5
        parts.append(
            f"x{idx} starts {fmt(series[0])}, ends {fmt(series[-1])}, mean {fmt(mean)}, "
            f"std {fmt(std)}, min {fmt(min(series))}, max {fmt(max(series))}."
        )
    return " ".join(parts) if parts else "No numeric time-series values were available for this row."


def abstract_primitive_for_task(task_family: str) -> str:
    task = task_family.lower()
    if "trend" in task:
        return "trend"
    if "extrema" in task or "peak" in task:
        return "extrema"
    if "volatility" in task or "drawdown" in task:
        return "volatility"
    if "anomaly" in task:
        return "anomaly"
    if "periodicity" in task:
        return "periodicity"
    if "window" in task:
        return "window_comparison"
    if "cross" in task or "relation" in task or "coupling" in task:
        return "cross_variable_relation"
    if "lead_lag" in task or "lead-lag" in task:
        return "lead_lag"
    if "counterfactual" in task:
        return "counterfactual_effect"
    if "context" in task or "domain" in task or "regime" in task:
        return "domain_context"
    return "unknown"


def abstract_answer_label_for(answer_label: Any) -> str:
    text = str(answer_label or "").strip().lower()
    text = text.replace("/", "_").replace("-", "_").replace(" ", "_")
    return "".join(ch for ch in text if ch.isalnum() or ch == "_") or "unknown"


def normalize_row(row: dict[str, Any], source: str, run_name: str) -> dict[str, Any]:
    out = dict(row)
    original_id = str(out["id"])
    out["id"] = f"{run_name}::{source}::{original_id}"
    out["multisim_source_domain"] = source_domain(out, source)
    out["merge_source_name"] = source
    out["merge_original_id"] = original_id
    out["meta"] = dict(out.get("meta", {}))
    out["meta"]["merge_source_name"] = source
    out["meta"]["merge_original_id"] = original_id
    out["meta"]["multisim_source_domain"] = out["multisim_source_domain"]
    if "split_group" not in out:
        out["split_group"] = out.get("meta", {}).get("split_group", original_id)
    if not out.get("statistical_caption"):
        out["statistical_caption"] = statistical_caption(out.get("values", []))
    if not out.get("abstract_primitive"):
        out["abstract_primitive"] = out["meta"].get("abstract_primitive") or abstract_primitive_for_task(str(out.get("task_family", "")))
    if not out.get("abstract_answer_label"):
        out["abstract_answer_label"] = out["meta"].get("abstract_answer_label") or abstract_answer_label_for(out.get("answer_label"))
    out["meta"]["abstract_primitive"] = out["abstract_primitive"]
    out["meta"]["abstract_answer_label"] = out["abstract_answer_label"]
    return out


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row.get("target_caption", row.get("output", "")),
        "meta": row.get("meta", {}),
    }


def split_path(base_dir: Path, source: str, split: str) -> Path:
    domain_dir, prefix = SOURCE_SPECS[source]
    return base_dir / domain_dir / f"{prefix}_{split}.jsonl"


def sample_rows(rows: list[dict[str, Any]], cap: int, source: str) -> list[dict[str, Any]]:
    if cap <= 0 or len(rows) <= cap:
        return rows
    ranked = sorted(rows, key=lambda row: stable_key(row, source))
    return ranked[:cap]


def validate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [row.get("id") for row in rows]
    missing = []
    support_prompt_count = 0
    bad_values = 0
    dims = Counter()
    horizons = Counter()
    split_groups: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        for key in REQUIRED:
            if key not in row or row[key] in ("", [], None):
                missing.append((row.get("id", "?"), key))
        prompt = str(row.get("prompt", "")).lower()
        if "support_slots" in prompt or "support slots" in prompt:
            support_prompt_count += 1
        values = row.get("values", [])
        if not isinstance(values, list) or not values:
            bad_values += 1
        else:
            first = values[0]
            dim = len(first) if isinstance(first, list) else 1
            dims[str(dim)] += 1
            horizons[str(len(values))] += 1
        split_groups[str(row.get("split", ""))].add(str(row.get("split_group", row.get("id", ""))))
    leakage = 0
    splits = sorted(split_groups)
    for i, left in enumerate(splits):
        for right in splits[i + 1 :]:
            leakage += len(split_groups[left] & split_groups[right])
    split_counts = Counter(row.get("split", "") for row in rows)
    return {
        "n": len(rows),
        "by_split": dict(split_counts),
        "by_merge_source_name": dict(Counter(row.get("merge_source_name", "") for row in rows)),
        "by_multisim_source_domain": dict(Counter(row.get("multisim_source_domain", "") for row in rows)),
        "by_task_family": dict(Counter(row.get("task_family", "") for row in rows)),
        "by_abstract_primitive": dict(Counter(row.get("abstract_primitive", "") for row in rows)),
        "by_answer": dict(Counter(row.get("answer", "") for row in rows)),
        "value_dim_counts": dict(dims),
        "horizon_counts": dict(horizons),
        "duplicate_id_count": len(ids) - len(set(ids)),
        "split_group_leakage_count": leakage,
        "missing_required_field_count": len(missing),
        "missing_required_fields": missing[:30],
        "prompt_support_slots_count": support_prompt_count,
        "bad_values_count": bad_values,
        "schema_gate_pass": bool(rows)
        and all(split_counts.get(split, 0) > 0 for split in ("train", "dev", "test"))
        and len(ids) == len(set(ids))
        and leakage == 0
        and not missing
        and support_prompt_count == 0
        and bad_values == 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_dir", default=".research/general-qcc-captioner-20260515")
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--run_name", default="multisim_qcc_v5_schema_aligned")
    parser.add_argument("--sources", nargs="+", default=list(SOURCE_SPECS))
    parser.add_argument("--train_cap_per_source", type=int, default=256)
    parser.add_argument("--eval_cap_per_source", type=int, default=64)
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    split_rows: dict[str, list[dict[str, Any]]] = {"train": [], "dev": [], "test": []}
    source_reports = []
    for source in args.sources:
        if source not in SOURCE_SPECS:
            raise KeyError(f"Unknown source {source}; known={sorted(SOURCE_SPECS)}")
        report: dict[str, Any] = {"source": source, "status": "ok", "splits": {}}
        for split in ("train", "dev", "test"):
            path = split_path(base_dir, source, split)
            if not path.exists():
                report["status"] = "missing"
                report["missing_path"] = str(path)
                break
            rows = load_jsonl(path)
            cap = args.train_cap_per_source if split == "train" else args.eval_cap_per_source
            sampled = [normalize_row(row, source, args.run_name) for row in sample_rows(rows, cap, f"{source}:{split}")]
            split_rows[split].extend(sampled)
            report["splits"][split] = {"path": str(path), "loaded": len(rows), "used": len(sampled)}
        source_reports.append(report)
        if report["status"] != "ok":
            raise FileNotFoundError(report["missing_path"])

    all_rows = split_rows["train"] + split_rows["dev"] + split_rows["test"]
    for split, rows in split_rows.items():
        write_jsonl(out_dir / f"{args.run_name}_{split}.jsonl", rows)
        write_jsonl(out_dir / f"{args.run_name}_{split}_sft.jsonl", [sft_row(row) for row in rows])
    eval_rows = split_rows["dev"] + split_rows["test"]
    write_jsonl(out_dir / f"{args.run_name}.jsonl", all_rows)
    write_jsonl(out_dir / f"{args.run_name}_sft.jsonl", [sft_row(row) for row in all_rows])
    write_jsonl(out_dir / f"{args.run_name}_eval_devtest.jsonl", eval_rows)
    write_jsonl(out_dir / f"{args.run_name}_eval_devtest_sft.jsonl", [sft_row(row) for row in eval_rows])

    report = validate_rows(all_rows)
    report.update(
        {
            "base_dir": str(base_dir),
            "out_dir": str(out_dir),
            "run_name": args.run_name,
            "sources_requested": args.sources,
            "source_reports": source_reports,
            "schema_alignment_note": "All rows share the QCC JSONL/SFT contract. Channel counts remain source-specific and require source-aware batching or projection during model training.",
        }
    )
    (out_dir / "schema_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
