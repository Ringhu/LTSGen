#!/usr/bin/env python3
"""Build QCC-v0 structured evidence targets from validated simulator QA."""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SOURCES = [
    ROOT / ".research/real-grid2op-20260513/grid2op_real_v4_obs_slot/grid2op_real_v4_obs_slot.jsonl",
    ROOT / ".research/real-grid2op-20260513/grid2op_real_cf_v6_slot/grid2op_real_cf_v6_slot.jsonl",
    ROOT / ".research/real-citylearn-20260513/citylearn_real_v2_slot/citylearn_real_v2_slot.jsonl",
]


TARGET_FIELD_KEYS = {
    "rho_value_slot": ["slot_local_t", "slot_line", "slot_rho"],
    "load_average_value_slot": ["slot_load", "slot_avg_load_p"],
    "generator_average_value_slot": ["slot_generator", "slot_avg_gen_p"],
    "quarter_total_load_mean_value_slot": ["slot_quarter", "slot_mean_total_load"],
    "cf_delta_max_rho_value_slot": [
        "slot_local_t",
        "slot_factual_max_rho",
        "slot_intervention_max_rho",
        "slot_delta_max_rho",
    ],
    "cf_intervention_max_rho_value_slot": ["slot_local_t", "slot_intervention_max_rho"],
    "building_load_value_slot": ["slot_local_t", "slot_building", "slot_non_shiftable_load"],
    "quarter_net_electricity_mean_value_slot": ["slot_quarter", "slot_mean_net_electricity_without_storage"],
    "outdoor_temperature_value_slot": ["slot_local_t", "slot_outdoor_dry_bulb_temperature"],
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _abs_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def _fmt(v: float) -> str:
    return f"{float(v):.3f}"


def _close(a: float, b: float, tol: float = 5e-4) -> bool:
    return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)


def _load_trace_window(record: dict[str, Any]) -> list[dict[str, Any]]:
    data = json.loads(_abs_path(record["trace_path"]).read_text(encoding="utf-8"))
    start = int(record["trace_window"]["start"])
    end = int(record["trace_window"]["end"])
    return data["trace"][start:end]


def _load_pair(record: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    data = json.loads(_abs_path(record["pair_path"]).read_text(encoding="utf-8"))
    n = min(len(data["factual_trace"]), len(data["intervention_trace"]))
    return data["factual_trace"][:n], data["intervention_trace"][:n]


def recompute_target(record: dict[str, Any]) -> dict[str, Any]:
    task = record["task_family"]
    evidence = record.get("evidence", {})

    if task == "rho_value_slot":
        rows = _load_trace_window(record)
        local_t = int(evidence["slot_local_t"])
        line = int(evidence["slot_line"])
        value = float(rows[local_t]["rho"][line])
        return {"slot_local_t": local_t, "slot_line": line, "slot_rho": value}

    if task == "load_average_value_slot":
        rows = _load_trace_window(record)
        load = int(evidence["slot_load"])
        value = float(np.mean([float(r["load_p"][load]) for r in rows]))
        return {"slot_load": load, "slot_avg_load_p": value}

    if task == "generator_average_value_slot":
        rows = _load_trace_window(record)
        gen = int(evidence["slot_generator"])
        value = float(np.mean([float(r["gen_p"][gen]) for r in rows]))
        return {"slot_generator": gen, "slot_avg_gen_p": value}

    if task == "quarter_total_load_mean_value_slot":
        rows = _load_trace_window(record)
        quarter = int(evidence["slot_quarter"])
        q = max(1, len(rows) // 4)
        start = (quarter - 1) * q
        end = len(rows) if quarter == 4 else quarter * q
        total_load = [sum(float(x) for x in r["load_p"]) for r in rows[start:end]]
        return {"slot_quarter": quarter, "slot_mean_total_load": float(np.mean(total_load))}

    if task == "cf_delta_max_rho_value_slot":
        factual, intervention = _load_pair(record)
        local_t = int(evidence["slot_local_t"])
        factual_max = max(float(x) for x in factual[local_t]["rho"])
        intervention_max = max(float(x) for x in intervention[local_t]["rho"])
        return {
            "slot_local_t": local_t,
            "slot_factual_max_rho": factual_max,
            "slot_intervention_max_rho": intervention_max,
            "slot_delta_max_rho": intervention_max - factual_max,
        }

    if task == "cf_intervention_max_rho_value_slot":
        _, intervention = _load_pair(record)
        local_t = int(evidence["slot_local_t"])
        intervention_max = max(float(x) for x in intervention[local_t]["rho"])
        return {"slot_local_t": local_t, "slot_intervention_max_rho": intervention_max}

    if task == "building_load_value_slot":
        rows = _load_trace_window(record)
        local_t = int(evidence["slot_local_t"])
        building = int(evidence["slot_building"])
        value = float(rows[local_t]["buildings"][building - 1]["non_shiftable_load"])
        return {"slot_local_t": local_t, "slot_building": building, "slot_non_shiftable_load": value}

    if task == "quarter_net_electricity_mean_value_slot":
        rows = _load_trace_window(record)
        quarter = int(evidence["slot_quarter"])
        q = max(1, len(rows) // 4)
        start = (quarter - 1) * q
        end = len(rows) if quarter == 4 else quarter * q
        values = [float(r["totals"]["net_electricity_without_storage"]) for r in rows[start:end]]
        return {"slot_quarter": quarter, "slot_mean_net_electricity_without_storage": float(np.mean(values))}

    if task == "outdoor_temperature_value_slot":
        rows = _load_trace_window(record)
        local_t = int(evidence["slot_local_t"])
        value = float(rows[local_t]["weather"]["outdoor_dry_bulb_temperature"])
        return {"slot_local_t": local_t, "slot_outdoor_dry_bulb_temperature": value}

    raise ValueError(f"Unsupported task family: {task}")


def validate_target(record: dict[str, Any], target: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    evidence = record.get("evidence", {})
    for key in TARGET_FIELD_KEYS[record["task_family"]]:
        if key not in evidence:
            errors.append(f"missing evidence key {key}")
            continue
        ev = evidence[key]
        tv = target[key]
        if isinstance(tv, float):
            if not _close(float(ev), tv):
                errors.append(f"{key}: evidence={ev} recomputed={tv}")
        elif ev != tv:
            errors.append(f"{key}: evidence={ev} recomputed={tv}")

    value_keys = [k for k in target if k.startswith("slot_") and isinstance(target[k], float)]
    if value_keys:
        main_value = float(target[value_keys[-1]])
        if _fmt(main_value) != str(record["answer_label"]):
            errors.append(f"answer_label={record['answer_label']} recomputed={_fmt(main_value)}")
    return errors


def target_caption(record: dict[str, Any], target: dict[str, Any]) -> str:
    task = record["task_family"]
    if task == "rho_value_slot":
        return f"At local_t={target['slot_local_t']}, rho for line {target['slot_line']} is {_fmt(target['slot_rho'])}."
    if task == "load_average_value_slot":
        return f"The window-average load_p for load {target['slot_load']} is {_fmt(target['slot_avg_load_p'])}."
    if task == "generator_average_value_slot":
        return f"The window-average gen_p for generator {target['slot_generator']} is {_fmt(target['slot_avg_gen_p'])}."
    if task == "quarter_total_load_mean_value_slot":
        return f"The mean total_load in quarter {target['slot_quarter']} is {_fmt(target['slot_mean_total_load'])}."
    if task == "cf_delta_max_rho_value_slot":
        return f"At local_t={target['slot_local_t']}, intervention_max_rho - factual_max_rho is {_fmt(target['slot_delta_max_rho'])}."
    if task == "cf_intervention_max_rho_value_slot":
        return f"At local_t={target['slot_local_t']}, intervention_max_rho is {_fmt(target['slot_intervention_max_rho'])}."
    if task == "building_load_value_slot":
        return f"At local_t={target['slot_local_t']}, non_shiftable_load for building {target['slot_building']} is {_fmt(target['slot_non_shiftable_load'])}."
    if task == "quarter_net_electricity_mean_value_slot":
        return f"The mean net_electricity_without_storage in quarter {target['slot_quarter']} is {_fmt(target['slot_mean_net_electricity_without_storage'])}."
    if task == "outdoor_temperature_value_slot":
        return f"At local_t={target['slot_local_t']}, outdoor_dry_bulb_temperature is {_fmt(target['slot_outdoor_dry_bulb_temperature'])}."
    raise ValueError(task)


def build_example(record: dict[str, Any], source_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    task = record["task_family"]
    if task not in TARGET_FIELD_KEYS:
        return None, [f"unsupported task {task}"]
    target = recompute_target(record)
    errors = validate_target(record, target)
    caption = target_caption(record, target)
    if caption != record["oracle_evidence_caption"]:
        errors.append(f"caption mismatch: expected={record['oracle_evidence_caption']} recomputed={caption}")
    if errors:
        return None, errors
    return {
        "id": "qcc_v0::" + record["id"],
        "source_record_id": record["id"],
        "source_path": str(source_path.relative_to(ROOT)),
        "domain": record["domain"],
        "source": record["source"],
        "task_family": task,
        "horizon": int(record["horizon"]),
        "question": record["question"],
        "options": record["options"],
        "answer": record["answer"],
        "answer_label": record["answer_label"],
        "trace_ref": {
            key: record[key]
            for key in ("trace_path", "trace_window", "pair_path", "intervention")
            if key in record
        },
        "input": {
            "domain": record["domain"],
            "task_family": task,
            "question": record["question"],
            "variables": record.get("variables", []),
            "horizon": int(record["horizon"]),
        },
        "target_fields": target,
        "target_caption": caption,
        "target_schema": "qcc_v0_structured_evidence",
    }, []


def split_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Deterministic mixed-domain splits. The tiny_overfit split is exactly 32
    # examples, balanced by domain/task as much as the current data allows.
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in sorted(rows, key=lambda r: r["id"]):
        buckets.setdefault((row["domain"], row["task_family"]), []).append(row)

    tiny_ids: set[str] = set()
    keys = sorted(buckets)
    cursor = 0
    while len(tiny_ids) < 32 and cursor < 10000:
        key = keys[cursor % len(keys)]
        bucket = buckets[key]
        if bucket:
            tiny_ids.add(bucket.pop(0)["id"])
        cursor += 1
        if all(not b for b in buckets.values()):
            break

    for idx, row in enumerate(sorted(rows, key=lambda r: r["id"])):
        if row["id"] in tiny_ids:
            row["split"] = "tiny_overfit"
        elif idx % 5 == 0:
            row["split"] = "dev"
        else:
            row["split"] = "train"
    return rows


def report(rows: list[dict[str, Any]], failures: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [r["id"] for r in rows]
    duplicate_count = len(ids) - len(set(ids))
    required = ["id", "source_record_id", "domain", "task_family", "question", "target_fields", "target_caption", "answer"]
    missing = [
        {"id": r.get("id", "<missing>"), "field": key}
        for r in rows
        for key in required
        if key not in r or r[key] in ("", [], {}, None)
    ]
    return {
        "n_examples": len(rows),
        "duplicate_id_count": duplicate_count,
        "missing_required_field_count": len(missing),
        "verification_failure_count": len(failures),
        "by_domain": dict(Counter(r["domain"] for r in rows)),
        "by_task_family": dict(Counter(r["task_family"] for r in rows)),
        "by_split": dict(Counter(r["split"] for r in rows)),
        "schema_gate_pass": len(rows) >= 150 and duplicate_count == 0 and not missing and not failures,
        "failures": failures[:20],
        "missing": missing[:20],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", default=None, help="Input QA jsonl. May be passed multiple times.")
    parser.add_argument("--out_dir", default=".research/qcc-v0-20260513")
    parser.add_argument("--output_name", default="qcc_v0_dataset.jsonl")
    args = parser.parse_args()

    sources = [Path(p) for p in args.source] if args.source else DEFAULT_SOURCES
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for source in sources:
        source = source if source.is_absolute() else ROOT / source
        for record in load_jsonl(source):
            example, errors = build_example(record, source)
            if errors:
                failures.append({"source_record_id": record.get("id"), "source_path": str(source.relative_to(ROOT)), "errors": errors})
            elif example:
                rows.append(example)

    rows = split_rows(rows)
    out_dir = ROOT / args.out_dir
    write_jsonl(out_dir / args.output_name, rows)
    rep = report(rows, failures)
    (out_dir / "sanity_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rep, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
