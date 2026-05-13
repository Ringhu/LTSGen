#!/usr/bin/env python3
"""Trace-reading rule extractor for the QCC-v0 target schema.

This baseline does not read gold target fields. It parses selectors from the
question, reads the referenced trace, recomputes the evidence value, and emits
the same structured target schema expected from a learned QCC model.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/generate"))

from build_qcc_v0_dataset import (  # noqa: E402
    _fmt,
    _load_pair,
    _load_trace_window,
    target_caption,
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _match(pattern: str, text: str) -> re.Match[str]:
    m = re.match(pattern, text)
    if not m:
        raise ValueError(f"Could not parse question: {text}")
    return m


def extract_fields(row: dict[str, Any]) -> dict[str, Any]:
    task = row["task_family"]
    question = row["question"]
    record = {
        "trace_path": row["trace_ref"].get("trace_path"),
        "trace_window": row["trace_ref"].get("trace_window"),
        "pair_path": row["trace_ref"].get("pair_path"),
    }

    if task == "rho_value_slot":
        m = re.match(r"At local_t=(\d+), what is rho for line (\d+)\?", question)
        if m:
            local_t = int(m.group(1))
            line = int(m.group(2))
        elif m := re.match(r"Read line (\d+) rho at local step (\d+)\.", question):
            line = int(m.group(1))
            local_t = int(m.group(2))
        elif m := re.match(r"For line (\d+), report rho when local_t equals (\d+)\.", question):
            line = int(m.group(1))
            local_t = int(m.group(2))
        else:
            raise ValueError(f"Could not parse question: {question}")
        rows = _load_trace_window(record)
        return {"slot_local_t": local_t, "slot_line": line, "slot_rho": float(rows[local_t]["rho"][line])}

    if task == "load_average_value_slot":
        if m := re.match(r"What is the window-average load_p for load (\d+)\?", question):
            load = int(m.group(1))
        elif m := re.match(r"Across this window, what is the average load_p for load (\d+)\?", question):
            load = int(m.group(1))
        elif m := re.match(r"Compute mean active load_p for load (\d+) over the full trace window\.", question):
            load = int(m.group(1))
        else:
            raise ValueError(f"Could not parse question: {question}")
        rows = _load_trace_window(record)
        value = sum(float(r["load_p"][load]) for r in rows) / len(rows)
        return {"slot_load": load, "slot_avg_load_p": value}

    if task == "generator_average_value_slot":
        if m := re.match(r"What is the window-average gen_p for generator (\d+)\?", question):
            gen = int(m.group(1))
        elif m := re.match(r"Across the full window, what is average gen_p for generator (\d+)\?", question):
            gen = int(m.group(1))
        elif m := re.match(r"Compute the mean generator output gen_p for generator (\d+) in this window\.", question):
            gen = int(m.group(1))
        else:
            raise ValueError(f"Could not parse question: {question}")
        rows = _load_trace_window(record)
        value = sum(float(r["gen_p"][gen]) for r in rows) / len(rows)
        return {"slot_generator": gen, "slot_avg_gen_p": value}

    if task == "quarter_total_load_mean_value_slot":
        if m := re.match(r"What is the mean total_load in quarter (\d+) of this trace window\?", question):
            quarter = int(m.group(1))
        elif m := re.match(r"Average total_load over quarter (\d+) of the selected window\.", question):
            quarter = int(m.group(1))
        elif m := re.match(r"What is the quarter-(\d+) mean of total load in this Grid2Op window\?", question):
            quarter = int(m.group(1))
        else:
            raise ValueError(f"Could not parse question: {question}")
        rows = _load_trace_window(record)
        q = max(1, len(rows) // 4)
        start = (quarter - 1) * q
        end = len(rows) if quarter == 4 else quarter * q
        values = [sum(float(x) for x in r["load_p"]) for r in rows[start:end]]
        return {"slot_quarter": quarter, "slot_mean_total_load": sum(values) / len(values)}

    if task == "cf_delta_max_rho_value_slot":
        if m := re.match(r"At local_t=(\d+), what is intervention_max_rho minus factual_max_rho\?", question):
            local_t = int(m.group(1))
        elif m := re.match(r"At local step (\d+), compute intervention max_rho minus factual max_rho\.", question):
            local_t = int(m.group(1))
        elif m := re.match(r"For local_t (\d+), what is the delta between intervention and factual max_rho\?", question):
            local_t = int(m.group(1))
        else:
            raise ValueError(f"Could not parse question: {question}")
        factual, intervention = _load_pair(record)
        factual_max = max(float(x) for x in factual[local_t]["rho"])
        intervention_max = max(float(x) for x in intervention[local_t]["rho"])
        return {
            "slot_local_t": local_t,
            "slot_factual_max_rho": factual_max,
            "slot_intervention_max_rho": intervention_max,
            "slot_delta_max_rho": intervention_max - factual_max,
        }

    if task == "cf_intervention_max_rho_value_slot":
        if m := re.match(r"At local_t=(\d+), what is intervention_max_rho\?", question):
            local_t = int(m.group(1))
        elif m := re.match(r"In the intervention trace, read max_rho at local step (\d+)\.", question):
            local_t = int(m.group(1))
        elif m := re.match(r"What is max_rho in the counterfactual rollout when local_t is (\d+)\?", question):
            local_t = int(m.group(1))
        else:
            raise ValueError(f"Could not parse question: {question}")
        _, intervention = _load_pair(record)
        return {"slot_local_t": local_t, "slot_intervention_max_rho": max(float(x) for x in intervention[local_t]["rho"])}

    if task == "building_load_value_slot":
        if m := re.match(r"At local_t=(\d+), what is non_shiftable_load for building (\d+)\?", question):
            local_t = int(m.group(1))
            building = int(m.group(2))
        elif m := re.match(r"At local step (\d+), read building (\d+) non_shiftable_load\.", question):
            local_t = int(m.group(1))
            building = int(m.group(2))
        elif m := re.match(r"For building (\d+), what is non_shiftable_load at local_t (\d+)\?", question):
            building = int(m.group(1))
            local_t = int(m.group(2))
        else:
            raise ValueError(f"Could not parse question: {question}")
        rows = _load_trace_window(record)
        return {
            "slot_local_t": local_t,
            "slot_building": building,
            "slot_non_shiftable_load": float(rows[local_t]["buildings"][building - 1]["non_shiftable_load"]),
        }

    if task == "quarter_net_electricity_mean_value_slot":
        if m := re.match(r"What is the mean net_electricity_without_storage in quarter (\d+) of this trace window\?", question):
            quarter = int(m.group(1))
        elif m := re.match(r"Average net_electricity_without_storage over quarter (\d+) of this CityLearn window\.", question):
            quarter = int(m.group(1))
        elif m := re.match(r"What is the quarter-(\d+) mean net electricity without storage\?", question):
            quarter = int(m.group(1))
        else:
            raise ValueError(f"Could not parse question: {question}")
        rows = _load_trace_window(record)
        q = max(1, len(rows) // 4)
        start = (quarter - 1) * q
        end = len(rows) if quarter == 4 else quarter * q
        values = [float(r["totals"]["net_electricity_without_storage"]) for r in rows[start:end]]
        return {"slot_quarter": quarter, "slot_mean_net_electricity_without_storage": sum(values) / len(values)}

    if task == "outdoor_temperature_value_slot":
        if m := re.match(r"At local_t=(\d+), what is outdoor_dry_bulb_temperature\?", question):
            local_t = int(m.group(1))
        elif m := re.match(r"Read outdoor dry-bulb temperature at local step (\d+)\.", question):
            local_t = int(m.group(1))
        elif m := re.match(r"What is the outdoor_dry_bulb_temperature when local_t is (\d+)\?", question):
            local_t = int(m.group(1))
        else:
            raise ValueError(f"Could not parse question: {question}")
        rows = _load_trace_window(record)
        return {"slot_local_t": local_t, "slot_outdoor_dry_bulb_temperature": float(rows[local_t]["weather"]["outdoor_dry_bulb_temperature"])}

    raise ValueError(f"Unsupported task: {task}")


def option_letter_for_value(options: list[str], value: str) -> str:
    for opt in options:
        if ". " not in opt:
            continue
        letter, text = opt.split(". ", 1)
        if text == value:
            return letter
    return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    predictions = []
    for row in load_jsonl(Path(args.data)):
        fields = extract_fields(row)
        caption = target_caption(row, fields)
        value_keys = [k for k, v in fields.items() if k.startswith("slot_") and isinstance(v, float)]
        answer_label = _fmt(float(fields[value_keys[-1]])) if value_keys else ""
        predictions.append({
            "id": row["id"],
            "condition": "trace_rule_extractor",
            "pred_target_fields": fields,
            "pred_target_caption": caption,
            "pred_answer_label": answer_label,
            "pred_answer": option_letter_for_value(row["options"], answer_label),
        })
    write_jsonl(Path(args.out), predictions)
    print(json.dumps({"n_items": len(predictions), "out": args.out}, indent=2))


if __name__ == "__main__":
    main()
