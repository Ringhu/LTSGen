#!/usr/bin/env python3
"""Audit schema and data-link alignment across MultiSim QCC sources."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
                if limit is not None and len(rows) >= limit:
                    break
    return rows


def dataset_report(name: str, path: Path, *, sample_limit: int | None = None) -> dict[str, Any]:
    if not path.exists():
        return {"name": name, "path": str(path), "exists": False, "schema_gate_pass": False}
    rows = load_jsonl(path, limit=sample_limit)
    ids = [row.get("id") for row in rows]
    missing = []
    bad_values = []
    prompt_support_slots = 0
    split_groups: dict[str, set[str]] = defaultdict(set)
    source_kinds = Counter()
    for row in rows:
        split_groups[str(row.get("split", ""))].add(str(row.get("split_group", row.get("id", ""))))
        text = str(row.get("prompt", "")).lower()
        if "support_slots" in text or "support slots" in text:
            prompt_support_slots += 1
        for key in REQUIRED:
            if key not in row or row[key] in ("", [], None):
                missing.append((row.get("id", "?"), key))
        try:
            arr = np.asarray(row.get("values"), dtype=float)
            if arr.ndim != 2 or arr.shape[0] <= 1 or arr.shape[1] < 1:
                bad_values.append((row.get("id", "?"), list(arr.shape)))
        except Exception as exc:  # noqa: BLE001
            bad_values.append((row.get("id", "?"), repr(exc)))
        meta = row.get("meta") or {}
        source_kinds[str(meta.get("source_kind", row.get("source_kind", "")))] += 1
    leakage = 0
    splits = sorted(split_groups)
    for idx, a in enumerate(splits):
        for b in splits[idx + 1 :]:
            leakage += len(split_groups[a] & split_groups[b])
    answers = Counter(row.get("answer", "") for row in rows)
    split_counts = Counter(row.get("split", "") for row in rows)
    max_answer_share = max(answers.values()) / max(1, len(rows)) if answers else 1.0
    return {
        "name": name,
        "path": str(path),
        "exists": True,
        "sampled_n": len(rows),
        "sample_limit": sample_limit,
        "by_split": dict(split_counts),
        "by_domain": dict(Counter(row.get("domain", "") for row in rows)),
        "by_multisim_source_domain": dict(Counter(row.get("multisim_source_domain", "") for row in rows)),
        "by_merge_source_name": dict(Counter(row.get("merge_source_name", "") for row in rows)),
        "by_task_family_count": len(Counter(row.get("task_family", "") for row in rows)),
        "by_abstract_primitive": dict(Counter(row.get("abstract_primitive", "") for row in rows)),
        "source_kinds": dict(source_kinds),
        "duplicate_id_count": len(ids) - len(set(ids)),
        "split_group_leakage_count": leakage,
        "prompt_support_slots_count": prompt_support_slots,
        "missing_required_field_count": len(missing),
        "missing_required_fields": missing[:30],
        "bad_values_count": len(bad_values),
        "bad_values": bad_values[:20],
        "max_answer_share": round(max_answer_share, 4),
        "schema_gate_pass": bool(rows)
        and len(ids) == len(set(ids))
        and not missing
        and not bad_values
        and prompt_support_slots == 0
        and max_answer_share <= 0.35,
    }


def manifest_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    data = load_json(path)
    return {
        "path": str(path),
        "exists": True,
        "run_name": data.get("run_name"),
        "domain_reports": {
            domain: {
                "n": report.get("n"),
                "schema_gate_pass": report.get("schema_gate_pass"),
                "source_kind": (report.get("dependency_status") or {}).get("source_kind"),
                "max_answer_share": report.get("max_answer_share"),
                "splits": report.get("by_split"),
            }
            for domain, report in (data.get("domain_reports") or {}).items()
        },
        "merge_schema_gate_pass": ((data.get("merge_report") or {}).get("schema_gate_pass")),
        "capacity_inventory_present": bool(data.get("capacity_inventory")),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_dir", default=".research/general-qcc-captioner-20260515")
    parser.add_argument("--out", required=True)
    parser.add_argument("--sample_limit", type=int, default=None)
    parser.add_argument("--dataset", action="append", nargs=2, metavar=("NAME", "PATH"), default=[])
    parser.add_argument("--manifest", action="append", default=[])
    args = parser.parse_args()

    base = Path(args.base_dir)
    default_datasets = [
        ("grid2op", base / "grid2op_broad_v5_semantic_anchor" / "grid2op_broad_v5_semantic_anchor.jsonl"),
        ("citylearn", base / "citylearn_broad_semantic_v3_qual" / "citylearn_broad_semantic_v3_qual.jsonl"),
        ("finrl_scaled", base / "finrl_broad_scaled_v1" / "finrl_broad_scaled_v1.jsonl"),
        ("water", base / "multisim_qcc_v3_stable_dataflow" / "water_broad_smoke_v1" / "water_broad_smoke_v1.jsonl"),
        ("traffic", base / "multisim_qcc_v3_stable_dataflow" / "traffic_broad_smoke_v1" / "traffic_broad_smoke_v1.jsonl"),
        ("aiops_fallback", base / "multisim_qcc_v3_stable_dataflow" / "aiops_broad_smoke_v1" / "aiops_broad_smoke_v1.jsonl"),
        ("aiops_official", base / "aiopslab_official_v1" / "aiopslab_official_v1.jsonl"),
        ("multisim_v5_schema_aligned", base / "multisim_qcc_v5_schema_aligned" / "multisim_qcc_v5_schema_aligned.jsonl"),
    ]
    datasets = default_datasets + [(name, Path(path)) for name, path in args.dataset]
    manifests = [
        base / "multisim_qcc_v3_stable_dataflow" / "manifest.json",
        base / "aiopslab_official_v1" / "schema_report.json",
    ] + [Path(path) for path in args.manifest]

    dataset_reports = {name: dataset_report(name, path, sample_limit=args.sample_limit) for name, path in datasets}
    manifest_reports = [manifest_report(path) for path in manifests]
    required_present = ["grid2op", "citylearn", "finrl_scaled", "water", "traffic", "aiops_official", "multisim_v5_schema_aligned"]
    missing_required = [
        name for name in required_present
        if not dataset_reports.get(name, {}).get("exists")
    ]
    canonical_training_dataset = "multisim_v5_schema_aligned"
    raw_required = ["grid2op", "citylearn", "finrl_scaled", "water", "traffic", "aiops_official"]
    raw_source_schema_warnings = [
        name for name in raw_required
        if dataset_reports.get(name, {}).get("exists") and not dataset_reports[name].get("schema_gate_pass")
    ]
    v5_report = dataset_reports.get(canonical_training_dataset, {})
    v5_sources = set((v5_report.get("by_merge_source_name") or {}).keys())
    required_v5_sources = {"grid2op", "citylearn", "finrl_scaled", "water", "traffic", "aiopslab_official"}
    missing_required_sources_in_v5 = sorted(required_v5_sources - v5_sources)
    official_source_gate = {
        name: "official_simulator_export" in (dataset_reports.get(name, {}).get("source_kinds") or {})
        for name in ("water", "traffic", "aiops_official")
    }
    source_kind_by_dataset = {
        name: report.get("source_kinds", {})
        for name, report in dataset_reports.items()
        if report.get("exists")
    }
    canonical_pass = bool(v5_report.get("exists")) and bool(v5_report.get("schema_gate_pass")) and not missing_required_sources_in_v5
    audit = {
        "objective": "Align multi-simulator QCC sources across Grid2Op, CityLearn, WNTR/water, SUMO/traffic, AIOpsLab, and optional FinRL.",
        "base_dir": str(base),
        "datasets": dataset_reports,
        "manifests": manifest_reports,
        "required_present": required_present,
        "missing_required": missing_required,
        "canonical_training_dataset": canonical_training_dataset,
        "canonical_training_schema_pass": canonical_pass,
        "required_v5_sources": sorted(required_v5_sources),
        "missing_required_sources_in_v5": missing_required_sources_in_v5,
        "raw_source_schema_warnings": raw_source_schema_warnings,
        "official_source_gate": official_source_gate,
        "source_kind_by_dataset": source_kind_by_dataset,
        "schema_alignment_pass": not missing_required and canonical_pass and all(official_source_gate.values()),
        "note": "The canonical training/eval entry is multisim_v5_schema_aligned. Raw-source schema warnings are kept for historical Grid2Op/CityLearn/FinRL files that predate the newest alignment fields.",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
