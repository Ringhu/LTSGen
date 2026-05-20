#!/usr/bin/env python3
"""Build meta-safe slot-value QA from exported CityLearn traces."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


LETTERS = ("A", "B", "C", "D")


def load_trace(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _fmt(v: float) -> str:
    return f"{float(v):.3f}"


def _stable_slot(*parts: Any) -> int:
    digest = hashlib.sha256("::".join(str(p) for p in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 4


def _distractors(value: float, gap: float, item_index: int) -> list[str]:
    scale = max(abs(value), 1.0)
    step = max(gap, 0.025 * scale)
    rank = (item_index // 4) % 4
    vals = []
    for k in range(rank, 0, -1):
        vals.append(value - step * (k + 0.19))
    for k in range(1, 4 - rank):
        vals.append(value + step * (k + 0.23))
    out = []
    for v in vals:
        if _fmt(v) != _fmt(value) and _fmt(v) not in out:
            out.append(_fmt(v))
    k = 1
    while len(out) < 3:
        sign = -1 if len(out) < rank else 1
        v = value + sign * step * (k + 1.31)
        if _fmt(v) != _fmt(value) and _fmt(v) not in out:
            out.append(_fmt(v))
        k += 1
    return out[:3]


def _quarter_distractors(value: float, observed_values: list[float], item_index: int) -> list[str]:
    """Use neighboring empirical quarter means first, then numeric offsets."""
    candidates: list[str] = []
    for v in sorted(observed_values, key=lambda x: (abs(x - value), x)):
        s = _fmt(v)
        if s != _fmt(value) and s not in candidates:
            candidates.append(s)
        if len(candidates) == 3:
            return candidates
    for v in _distractors(value, 8.0, item_index):
        if v != _fmt(value) and v not in candidates:
            candidates.append(v)
        if len(candidates) == 3:
            return candidates
    raise ValueError(f"Could not create quarter distractors for {value}")


def _options(correct: str, distractors: list[str], key: str) -> tuple[list[str], str]:
    target = LETTERS[_stable_slot(key)]
    texts = {target: correct}
    for letter, value in zip([x for x in LETTERS if x != target], distractors):
        texts[letter] = value
    return [f"{letter}. {texts[letter]}" for letter in LETTERS], target


def _set_answer_letter(row: dict[str, Any], target: str) -> dict[str, Any]:
    correct = str(row["answer_label"])
    values = [opt.split(". ", 1)[1] for opt in row["options"]]
    distractors = [v for v in values if v != correct]
    texts = {target: correct}
    for letter, value in zip([x for x in LETTERS if x != target], distractors):
        texts[letter] = value
    out = dict(row)
    out["answer"] = target
    out["options"] = [f"{letter}. {texts[letter]}" for letter in LETTERS]
    out["evidence"] = {**row["evidence"], "answer_letter_mode": "global_hash_balanced_citylearn_v1"}
    return out


def _rebalance(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(range(len(rows)), key=lambda i: hashlib.sha256(rows[i]["id"].encode("utf-8")).hexdigest())
    targets = {idx: LETTERS[pos % len(LETTERS)] for pos, idx in enumerate(ranked)}
    return [_set_answer_letter(row, targets[i]) for i, row in enumerate(rows)]


def _base_record(
    trace: dict[str, Any],
    trace_path: str,
    task: str,
    question: str,
    answer_label: str,
    options: list[str],
    answer: str,
    caption: str,
    evidence: dict[str, Any],
    *,
    window_start: int,
    window_end: int,
    horizon: int,
) -> dict[str, Any]:
    return {
        "domain": "citylearn_real",
        "source": "citylearn_packaged_dataset",
        "horizon": horizon,
        "trace_path": trace_path,
        "trace_window": {"start": window_start, "end": window_end},
        "variables": [
            "building.non_shiftable_load",
            "building.solar_generation",
            "building.dhw_demand",
            "weather.outdoor_dry_bulb_temperature",
            "weather.direct_solar_irradiance",
            "price",
            "carbon_intensity",
            "totals.net_electricity_without_storage",
        ],
        "id": (
            f"simqa::citylearn_real::{Path(trace_path).stem}::h{horizon}::s{window_start}::"
            f"{task}::{hashlib.sha1(question.encode()).hexdigest()[:10]}"
        ),
        "task_family": task,
        "question": question,
        "options": options,
        "answer": answer,
        "answer_label": answer_label,
        "oracle_evidence_caption": caption,
        "generic_caption": (
            f"This CityLearn building-energy trace window contains {trace['actual_horizon']} hourly steps "
            f"for {trace['n_buildings']} buildings, with building loads, solar generation, weather, price, and carbon intensity."
        ),
        "evidence": {**evidence, "slot_value_mode": "citylearn_slot_v1"},
        "simulator_meta": {
            "dataset_name": trace["dataset_name"],
            "n_buildings": trace["n_buildings"],
            "source": trace["source"],
        },
    }


def build_rows(trace: dict[str, Any], trace_path: str) -> list[dict[str, Any]]:
    all_rows = trace["trace"]
    total_n = len(all_rows)
    out: list[dict[str, Any]] = []

    windows = [
        (0, 512),
        (384, 512),
        (768, 512),
        (0, 1024),
        (1024, 1024),
        (0, 2048),
    ]

    for window_index, (window_start, horizon) in enumerate(windows):
        window_end = min(window_start + horizon, total_n)
        if window_end - window_start != horizon:
            continue
        rows = all_rows[window_start:window_end]

        # Four point-value building load questions per window.
        for j, frac in enumerate([0.13, 0.37, 0.61, 0.83]):
            local_t = min(horizon - 1, int(round(frac * (horizon - 1))))
            building_id = ((window_index + j) % int(trace["n_buildings"])) + 1
            value = float(rows[local_t]["buildings"][building_id - 1]["non_shiftable_load"])
            correct = _fmt(value)
            question = f"At local_t={local_t}, what is non_shiftable_load for building {building_id}?"
            options, answer = _options(correct, _distractors(value, 0.05, len(out)), f"{window_start}:{question}")
            out.append(_base_record(
                trace,
                trace_path,
                "building_load_value_slot",
                question,
                correct,
                options,
                answer,
                f"At local_t={local_t}, non_shiftable_load for building {building_id} is {correct}.",
                {"slot_local_t": local_t, "slot_building": building_id, "slot_non_shiftable_load": value},
                window_start=window_start,
                window_end=window_end,
                horizon=horizon,
            ))

        # Four quarter aggregation questions per window.
        q = max(1, horizon // 4)
        quarter_means = []
        for quarter in range(4):
            start = quarter * q
            end = horizon if quarter == 3 else (quarter + 1) * q
            values = [float(r["totals"]["net_electricity_without_storage"]) for r in rows[start:end]]
            quarter_means.append(float(np.mean(values)))
        for quarter, value in enumerate(quarter_means):
            correct = _fmt(value)
            question = f"What is the mean net_electricity_without_storage in quarter {quarter + 1} of this trace window?"
            options, answer = _options(
                correct,
                _quarter_distractors(value, quarter_means, len(out)),
                f"{window_start}:{question}",
            )
            out.append(_base_record(
                trace,
                trace_path,
                "quarter_net_electricity_mean_value_slot",
                question,
                correct,
                options,
                answer,
                f"The mean net_electricity_without_storage in quarter {quarter + 1} is {correct}.",
                {"slot_quarter": quarter + 1, "slot_mean_net_electricity_without_storage": value},
                window_start=window_start,
                window_end=window_end,
                horizon=horizon,
            ))

        # Four point-value weather questions per window.
        for j, frac in enumerate([0.17, 0.41, 0.69, 0.91]):
            local_t = min(horizon - 1, int(round(frac * (horizon - 1))))
            value = float(rows[local_t]["weather"]["outdoor_dry_bulb_temperature"])
            correct = _fmt(value)
            question = f"At local_t={local_t}, what is outdoor_dry_bulb_temperature?"
            options, answer = _options(correct, _distractors(value, 0.3, len(out)), f"{window_start}:{question}")
            out.append(_base_record(
                trace,
                trace_path,
                "outdoor_temperature_value_slot",
                question,
                correct,
                options,
                answer,
                f"At local_t={local_t}, outdoor_dry_bulb_temperature is {correct}.",
                {"slot_local_t": local_t, "slot_outdoor_dry_bulb_temperature": value},
                window_start=window_start,
                window_end=window_end,
                horizon=horizon,
            ))

    return _rebalance(out)


def report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    answers = Counter(r["answer"] for r in rows)
    return {
        "n_items": len(rows),
        "answer_counts": dict(answers),
        "max_answer_letter_fraction": max(answers.values()) / max(len(rows), 1) if rows else 1.0,
        "by_task_family": dict(Counter(r["task_family"] for r in rows)),
        "missing_required_field_count": sum(
            1
            for r in rows
            for key in ("id", "question", "options", "answer", "oracle_evidence_caption", "generic_caption", "evidence")
            if key not in r or r[key] in ("", [], None)
        ),
        "schema_gate_pass": bool(rows) and max(answers.values()) / max(len(rows), 1) <= 0.35,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True)
    parser.add_argument("--trace_path_for_records", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--output_name", default="citylearn_real_v1_slot.jsonl")
    args = parser.parse_args()

    trace = load_trace(Path(args.trace))
    rows = build_rows(trace, args.trace_path_for_records)
    out_dir = Path(args.out_dir)
    write_jsonl(out_dir / args.output_name, rows)
    rep = report(rows)
    (out_dir / "sanity_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rep, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
