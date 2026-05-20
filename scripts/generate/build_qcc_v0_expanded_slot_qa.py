#!/usr/bin/env python3
"""Build expanded Grid2Op/CityLearn slot QA from existing local traces."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
LETTERS = ("A", "B", "C", "D")
GRID2OP_TRACES = [
    ROOT / ".research/real-grid2op-20260513/rte_case14_realistic_trace_512.json",
    ROOT / ".research/real-grid2op-20260513/rte_case14_realistic_trace_1024.json",
    ROOT / ".research/real-grid2op-20260513/rte_case14_realistic_trace_2048_nooverflow.json",
]
GRID2OP_PAIR_GLOB = ".research/real-grid2op-20260513/**/pairs/*.json"
CITYLEARN_TRACES = [
    ROOT / ".research/real-citylearn-20260513/citylearn_challenge_2022_phase_1_trace_2048.json",
]


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _fmt(v: float) -> str:
    return f"{float(v):.3f}"


def _stable_int(*parts: Any) -> int:
    digest = hashlib.sha256("::".join(str(p) for p in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def _distractors(value: float, gap: float, item_index: int, *, nonnegative: bool = False) -> list[str]:
    rank = (item_index // 4) % 4
    scale = max(abs(value), 1.0)
    step = max(gap, 0.021 * scale)
    vals: list[float] = []
    for k in range(rank, 0, -1):
        vals.append(value - step * (k + 0.23 + 0.07 * ((item_index + k) % 5)))
    for k in range(1, 4 - rank):
        vals.append(value + step * (k + 0.31 + 0.05 * ((item_index + k) % 5)))
    if nonnegative:
        vals = [v for v in vals if v >= 0]
    out: list[str] = []
    for v in vals:
        s = _fmt(v)
        if s != _fmt(value) and s not in out:
            out.append(s)
    k = 1
    while len(out) < 3:
        sign = -1 if len(out) < rank else 1
        v = value + sign * step * (k + 1.47)
        if (not nonnegative or v >= 0) and _fmt(v) != _fmt(value) and _fmt(v) not in out:
            out.append(_fmt(v))
        k += 1
    return out[:3]


def _options(correct: str, distractors: list[str], key: str) -> tuple[list[str], str]:
    target = LETTERS[_stable_int(key) % len(LETTERS)]
    values = {target: correct}
    clean = []
    for value in distractors:
        if value != correct and value not in clean:
            clean.append(value)
    if len(clean) < 3:
        raise ValueError(f"Need 3 unique distractors for {key}; got {clean}")
    for letter, value in zip([x for x in LETTERS if x != target], clean[:3]):
        values[letter] = value
    return [f"{letter}. {values[letter]}" for letter in LETTERS], target


def _set_answer_letter(row: dict[str, Any], target: str) -> dict[str, Any]:
    correct = str(row["answer_label"])
    values = [opt.split(". ", 1)[1] for opt in row["options"]]
    distractors = [v for v in values if v != correct]
    out_values = {target: correct}
    for letter, value in zip([x for x in LETTERS if x != target], distractors):
        out_values[letter] = value
    out = dict(row)
    out["answer"] = target
    out["options"] = [f"{letter}. {out_values[letter]}" for letter in LETTERS]
    out["evidence"] = {**row["evidence"], "answer_letter_mode": "global_hash_balanced_expanded_v1"}
    return out


def rebalance(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(range(len(rows)), key=lambda i: hashlib.sha256(rows[i]["id"].encode("utf-8")).hexdigest())
    targets = {idx: LETTERS[pos % len(LETTERS)] for pos, idx in enumerate(ranked)}
    return [_set_answer_letter(row, targets[i]) for i, row in enumerate(rows)]


def unique_indices(*, key: str, count: int, modulo: int) -> list[int]:
    if count > modulo:
        raise ValueError(f"Cannot draw {count} unique indices from {modulo}")
    values: list[int] = []
    cursor = 0
    while len(values) < count:
        value = int(_stable_int(key, cursor) % modulo)
        if value not in values:
            values.append(value)
        cursor += 1
    return values


def window_starts(n: int, horizon: int, stride: int) -> list[int]:
    if n < horizon:
        return []
    starts = list(range(0, n - horizon + 1, stride))
    if starts[-1] != n - horizon:
        starts.append(n - horizon)
    return sorted(set(starts))


def grid_record(
    *,
    trace_path: Path,
    horizon: int,
    start: int,
    task: str,
    question: str,
    answer_label: str,
    options: list[str],
    answer: str,
    caption: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    rid = hashlib.sha1(f"{trace_path}:{horizon}:{start}:{task}:{question}".encode()).hexdigest()[:10]
    return {
        "id": f"simqa::grid2op_real::{trace_path.stem}::h{horizon}::s{start}::{task}::expanded_v1::{rid}",
        "domain": "grid2op_real",
        "source": "grid2op",
        "horizon": horizon,
        "trace_path": _rel(trace_path),
        "trace_window": {"start": start, "end": start + horizon},
        "variables": ["rho", "line_status", "load_p", "gen_p", "p_or", "p_ex"],
        "task_family": task,
        "question": question,
        "options": options,
        "answer": answer,
        "answer_label": answer_label,
        "oracle_evidence_caption": caption,
        "generic_caption": (
            f"This Grid2Op power-grid trace window contains {horizon} simulator steps with line loading, "
            "line status, loads, generators, and power flows."
        ),
        "evidence": {**evidence, "slot_value_mode": "expanded_v1"},
    }


def pair_record(
    *,
    pair_path: Path,
    horizon: int,
    step: int,
    line_id: int | None,
    task: str,
    question: str,
    answer_label: str,
    options: list[str],
    answer: str,
    caption: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    rid = hashlib.sha1(f"{pair_path}:{task}:{question}".encode()).hexdigest()[:10]
    return {
        "id": f"simqa::grid2op_real_cf::{pair_path.stem}::{task}::expanded_v1::{rid}",
        "domain": "grid2op_real_cf",
        "source": "grid2op_intervention",
        "horizon": horizon,
        "pair_path": _rel(pair_path),
        "intervention": {
            "type": "disconnect_line",
            "step": step,
            "line_id": line_id,
            "line_selection": "manual",
        },
        "variables": ["factual.rho", "intervention.rho", "line_status"],
        "task_family": task,
        "question": question,
        "options": options,
        "answer": answer,
        "answer_label": answer_label,
        "oracle_evidence_caption": caption,
        "generic_caption": (
            "This paired Grid2Op trace contains a factual rollout and a counterfactual rollout after "
            f"disconnecting line {line_id} at local_t={step}."
        ),
        "evidence": {**evidence, "slot_value_mode": "expanded_v1"},
    }


def city_record(
    *,
    trace: dict[str, Any],
    trace_path: Path,
    horizon: int,
    start: int,
    task: str,
    question: str,
    answer_label: str,
    options: list[str],
    answer: str,
    caption: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    rid = hashlib.sha1(f"{trace_path}:{horizon}:{start}:{task}:{question}".encode()).hexdigest()[:10]
    return {
        "id": f"simqa::citylearn_real::{trace_path.stem}::h{horizon}::s{start}::{task}::expanded_v1::{rid}",
        "domain": "citylearn_real",
        "source": "citylearn_packaged_dataset",
        "horizon": horizon,
        "trace_path": _rel(trace_path),
        "trace_window": {"start": start, "end": start + horizon},
        "variables": [
            "building.non_shiftable_load",
            "weather.outdoor_dry_bulb_temperature",
            "totals.net_electricity_without_storage",
        ],
        "task_family": task,
        "question": question,
        "options": options,
        "answer": answer,
        "answer_label": answer_label,
        "oracle_evidence_caption": caption,
        "generic_caption": (
            f"This CityLearn building-energy trace window contains {horizon} hourly steps for "
            f"{trace['n_buildings']} buildings, with building loads, weather, price, and carbon intensity."
        ),
        "evidence": {**evidence, "slot_value_mode": "expanded_v1"},
        "simulator_meta": {
            "dataset_name": trace["dataset_name"],
            "n_buildings": trace["n_buildings"],
            "source": trace["source"],
        },
    }


def build_grid_observation(max_windows_per_trace_horizon: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in GRID2OP_TRACES:
        if not path.exists():
            continue
        trace = _load(path)["trace"]
        n = len(trace)
        for horizon in (512, 1024, 2048):
            starts = window_starts(n, horizon, max(1, horizon // 2))
            if max_windows_per_trace_horizon is not None:
                starts = starts[:max_windows_per_trace_horizon]
            for start in starts:
                window = trace[start : start + horizon]
                rho = np.asarray([r["rho"] for r in window], dtype=float)
                load = np.asarray([r["load_p"] for r in window], dtype=float)
                gen = np.asarray([r["gen_p"] for r in window], dtype=float)
                total_load = load.sum(axis=1)
                item_seed = len(rows)
                for j, frac in enumerate([0.11, 0.31, 0.57, 0.83]):
                    local_t = min(horizon - 1, int(round(frac * (horizon - 1))))
                    line = int(_stable_int(path.stem, horizon, start, "rho", j) % rho.shape[1])
                    value = float(rho[local_t, line])
                    correct = _fmt(value)
                    question = f"At local_t={local_t}, what is rho for line {line}?"
                    options, answer = _options(correct, _distractors(value, 0.005, item_seed + j, nonnegative=True), question)
                    rows.append(
                        grid_record(
                            trace_path=path,
                            horizon=horizon,
                            start=start,
                            task="rho_value_slot",
                            question=question,
                            answer_label=correct,
                            options=options,
                            answer=answer,
                            caption=f"At local_t={local_t}, rho for line {line} is {correct}.",
                            evidence={"slot_local_t": local_t, "slot_line": line, "slot_rho": value},
                        )
                    )
                for j, load_id in enumerate(unique_indices(key=f"{path.stem}:{horizon}:{start}:load", count=3, modulo=load.shape[1])):
                    value = float(load[:, load_id].mean())
                    correct = _fmt(value)
                    question = f"What is the window-average load_p for load {load_id}?"
                    options, answer = _options(correct, _distractors(value, 0.5, item_seed + j, nonnegative=True), question)
                    rows.append(
                        grid_record(
                            trace_path=path,
                            horizon=horizon,
                            start=start,
                            task="load_average_value_slot",
                            question=question,
                            answer_label=correct,
                            options=options,
                            answer=answer,
                            caption=f"The window-average load_p for load {load_id} is {correct}.",
                            evidence={"slot_load": load_id, "slot_avg_load_p": value},
                        )
                    )
                for j, gen_id in enumerate(unique_indices(key=f"{path.stem}:{horizon}:{start}:gen", count=3, modulo=gen.shape[1])):
                    value = float(gen[:, gen_id].mean())
                    correct = _fmt(value)
                    question = f"What is the window-average gen_p for generator {gen_id}?"
                    options, answer = _options(correct, _distractors(value, 0.5, item_seed + j, nonnegative=True), question)
                    rows.append(
                        grid_record(
                            trace_path=path,
                            horizon=horizon,
                            start=start,
                            task="generator_average_value_slot",
                            question=question,
                            answer_label=correct,
                            options=options,
                            answer=answer,
                            caption=f"The window-average gen_p for generator {gen_id} is {correct}.",
                            evidence={"slot_generator": gen_id, "slot_avg_gen_p": value},
                        )
                    )
                q = max(1, horizon // 4)
                for quarter in range(4):
                    q_start = quarter * q
                    q_end = horizon if quarter == 3 else (quarter + 1) * q
                    value = float(total_load[q_start:q_end].mean())
                    correct = _fmt(value)
                    question = f"What is the mean total_load in quarter {quarter + 1} of this trace window?"
                    options, answer = _options(correct, _distractors(value, 1.0, item_seed + quarter, nonnegative=True), question)
                    rows.append(
                        grid_record(
                            trace_path=path,
                            horizon=horizon,
                            start=start,
                            task="quarter_total_load_mean_value_slot",
                            question=question,
                            answer_label=correct,
                            options=options,
                            answer=answer,
                            caption=f"The mean total_load in quarter {quarter + 1} is {correct}.",
                            evidence={"slot_quarter": quarter + 1, "slot_mean_total_load": value},
                        )
                    )
    return rows


def build_grid_counterfactual(max_query_points_per_pair: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(ROOT.glob(GRID2OP_PAIR_GLOB)):
        data = _load(path)
        factual = data.get("factual_trace", [])
        intervention = data.get("intervention_trace", [])
        n = min(len(factual), len(intervention))
        step = data.get("meta", {}).get("intervention", {}).get("step", data.get("summary", {}).get("intervention_step"))
        line_id = data.get("meta", {}).get("intervention", {}).get("line_id", data.get("summary", {}).get("line_id"))
        if n == 0 or step is None or int(step) >= n - 1:
            continue
        step = int(step)
        post_start = step + 1
        span = n - post_start
        query_count = min(max_query_points_per_pair, span)
        if query_count <= 0:
            continue
        if query_count == 1:
            local_ts = [post_start]
        else:
            local_ts = sorted({post_start + int(round(frac * (span - 1))) for frac in np.linspace(0.05, 0.95, query_count)})
        for local_t in local_ts:
            f_max = max(float(x) for x in factual[local_t]["rho"])
            i_max = max(float(x) for x in intervention[local_t]["rho"])
            delta = i_max - f_max
            for task, value, caption, evidence in (
                (
                    "cf_delta_max_rho_value_slot",
                    delta,
                    f"At local_t={local_t}, intervention_max_rho - factual_max_rho is {_fmt(delta)}.",
                    {
                        "slot_local_t": local_t,
                        "slot_factual_max_rho": f_max,
                        "slot_intervention_max_rho": i_max,
                        "slot_delta_max_rho": delta,
                    },
                ),
                (
                    "cf_intervention_max_rho_value_slot",
                    i_max,
                    f"At local_t={local_t}, intervention_max_rho is {_fmt(i_max)}.",
                    {"slot_local_t": local_t, "slot_intervention_max_rho": i_max},
                ),
            ):
                correct = _fmt(value)
                question = (
                    f"At local_t={local_t}, what is intervention_max_rho minus factual_max_rho?"
                    if task == "cf_delta_max_rho_value_slot"
                    else f"At local_t={local_t}, what is intervention_max_rho?"
                )
                options, answer = _options(correct, _distractors(value, 0.01, len(rows), nonnegative=task.endswith("intervention_max_rho_value_slot")), question)
                rows.append(
                    pair_record(
                        pair_path=path,
                        horizon=n,
                        step=step,
                        line_id=int(line_id) if line_id is not None else None,
                        task=task,
                        question=question,
                        answer_label=correct,
                        options=options,
                        answer=answer,
                        caption=caption,
                        evidence=evidence,
                    )
                )
    return rows


def build_citylearn(max_windows_per_trace_horizon: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in CITYLEARN_TRACES:
        if not path.exists():
            continue
        trace = _load(path)
        all_rows = trace["trace"]
        n = len(all_rows)
        for horizon in (512, 1024, 2048):
            starts = window_starts(n, horizon, max(1, horizon // 2))
            if max_windows_per_trace_horizon is not None:
                starts = starts[:max_windows_per_trace_horizon]
            for start in starts:
                window = all_rows[start : start + horizon]
                seed = len(rows)
                for j, frac in enumerate([0.09, 0.19, 0.29, 0.39, 0.49, 0.59, 0.69, 0.79, 0.89, 0.97]):
                    local_t = min(horizon - 1, int(round(frac * (horizon - 1))))
                    building = int(_stable_int(path.stem, horizon, start, "building", j) % int(trace["n_buildings"])) + 1
                    value = float(window[local_t]["buildings"][building - 1]["non_shiftable_load"])
                    correct = _fmt(value)
                    question = f"At local_t={local_t}, what is non_shiftable_load for building {building}?"
                    options, answer = _options(correct, _distractors(value, 0.05, seed + j), question)
                    rows.append(
                        city_record(
                            trace=trace,
                            trace_path=path,
                            horizon=horizon,
                            start=start,
                            task="building_load_value_slot",
                            question=question,
                            answer_label=correct,
                            options=options,
                            answer=answer,
                            caption=f"At local_t={local_t}, non_shiftable_load for building {building} is {correct}.",
                            evidence={"slot_local_t": local_t, "slot_building": building, "slot_non_shiftable_load": value},
                        )
                    )
                q = max(1, horizon // 4)
                for quarter in range(4):
                    q_start = quarter * q
                    q_end = horizon if quarter == 3 else (quarter + 1) * q
                    value = float(np.mean([float(r["totals"]["net_electricity_without_storage"]) for r in window[q_start:q_end]]))
                    correct = _fmt(value)
                    question = f"What is the mean net_electricity_without_storage in quarter {quarter + 1} of this trace window?"
                    options, answer = _options(correct, _distractors(value, 8.0, seed + quarter), question)
                    rows.append(
                        city_record(
                            trace=trace,
                            trace_path=path,
                            horizon=horizon,
                            start=start,
                            task="quarter_net_electricity_mean_value_slot",
                            question=question,
                            answer_label=correct,
                            options=options,
                            answer=answer,
                            caption=f"The mean net_electricity_without_storage in quarter {quarter + 1} is {correct}.",
                            evidence={"slot_quarter": quarter + 1, "slot_mean_net_electricity_without_storage": value},
                        )
                    )
                for j, frac in enumerate([0.07, 0.23, 0.41, 0.63, 0.81, 0.93]):
                    local_t = min(horizon - 1, int(round(frac * (horizon - 1))))
                    value = float(window[local_t]["weather"]["outdoor_dry_bulb_temperature"])
                    correct = _fmt(value)
                    question = f"At local_t={local_t}, what is outdoor_dry_bulb_temperature?"
                    options, answer = _options(correct, _distractors(value, 0.3, seed + j), question)
                    rows.append(
                        city_record(
                            trace=trace,
                            trace_path=path,
                            horizon=horizon,
                            start=start,
                            task="outdoor_temperature_value_slot",
                            question=question,
                            answer_label=correct,
                            options=options,
                            answer=answer,
                            caption=f"At local_t={local_t}, outdoor_dry_bulb_temperature is {correct}.",
                            evidence={"slot_local_t": local_t, "slot_outdoor_dry_bulb_temperature": value},
                        )
                    )
    return rows


def report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    answers = Counter(r["answer"] for r in rows)
    ids = [r["id"] for r in rows]
    required = ("id", "question", "options", "answer", "oracle_evidence_caption", "generic_caption", "evidence")
    return {
        "n_items": len(rows),
        "duplicate_id_count": len(ids) - len(set(ids)),
        "answer_counts": dict(answers),
        "max_answer_letter_fraction": max(answers.values()) / max(1, len(rows)) if rows else 1.0,
        "by_domain": dict(Counter(r["domain"] for r in rows)),
        "by_horizon": dict(Counter(str(r["horizon"]) for r in rows)),
        "by_task_family": dict(Counter(r["task_family"] for r in rows)),
        "missing_required_field_count": sum(
            1
            for r in rows
            for key in required
            if key not in r or r[key] in ("", [], {}, None)
        ),
        "schema_gate_pass": bool(rows) and len(ids) == len(set(ids)) and max(answers.values()) / max(1, len(rows)) <= 0.27,
        "note": "Expanded slot QA from existing local Grid2Op/CityLearn trace files; no new simulator rollout.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--output_name", default="qcc_v0_expanded_slot_qa.jsonl")
    parser.add_argument("--max_windows_per_trace_horizon", type=int, default=None)
    parser.add_argument("--max_query_points_per_pair", type=int, default=8)
    args = parser.parse_args()

    rows = []
    rows.extend(build_grid_observation(args.max_windows_per_trace_horizon))
    rows.extend(build_grid_counterfactual(args.max_query_points_per_pair))
    rows.extend(build_citylearn(args.max_windows_per_trace_horizon))
    rows = rebalance(rows)

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / args.output_name, rows)
    rep = report(rows)
    (out_dir / "sanity_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rep, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
