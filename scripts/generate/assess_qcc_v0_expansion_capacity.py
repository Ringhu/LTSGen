#!/usr/bin/env python3
"""Assess local trace capacity for QCC-v0 Grid2Op/CityLearn expansion."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
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


def window_starts(n: int, horizon: int, stride: int) -> list[int]:
    if n < horizon:
        return []
    starts = list(range(0, n - horizon + 1, stride))
    if starts[-1] != n - horizon:
        starts.append(n - horizon)
    return sorted(set(starts))


def grid2op_observation_capacity() -> dict[str, Any]:
    windows: list[dict[str, Any]] = []
    per_trace: list[dict[str, Any]] = []
    for path in GRID2OP_TRACES:
        if not path.exists():
            continue
        data = _load(path)
        n = len(data["trace"])
        first = data["trace"][0]
        trace_windows = []
        for horizon in (512, 1024, 2048):
            stride = max(1, horizon // 2)
            for start in window_starts(n, horizon, stride):
                item = {"trace_path": _rel(path), "horizon": horizon, "start": start, "end": start + horizon}
                windows.append(item)
                trace_windows.append(item)
        per_trace.append(
            {
                "trace_path": _rel(path),
                "steps": n,
                "n_lines": len(first["rho"]),
                "n_loads": len(first["load_p"]),
                "n_generators": len(first["gen_p"]),
                "candidate_windows": len(trace_windows),
            }
        )
    # The planned expanded builder emits 4 rho + 3 load + 3 gen + 4 quarter
    # examples per observation window.
    return {
        "candidate_windows": len(windows),
        "planned_examples_per_window": 14,
        "planned_examples": len(windows) * 14,
        "per_trace": per_trace,
        "window_policy": "horizons 512/1024/2048 with stride=horizon/2, including final aligned window",
    }


def grid2op_counterfactual_capacity() -> dict[str, Any]:
    pairs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for path in sorted(ROOT.glob(GRID2OP_PAIR_GLOB)):
        data = _load(path)
        n_f = len(data.get("factual_trace", []))
        n_i = len(data.get("intervention_trace", []))
        n = min(n_f, n_i)
        step = data.get("meta", {}).get("intervention", {}).get("step", data.get("summary", {}).get("intervention_step"))
        line_id = data.get("meta", {}).get("intervention", {}).get("line_id", data.get("summary", {}).get("line_id"))
        if n == 0 or step is None or int(step) >= n - 1:
            skipped.append({"pair_path": _rel(path), "factual_steps": n_f, "intervention_steps": n_i, "reason": "missing trace or post-intervention span"})
            continue
        post_n = n - int(step) - 1
        planned_points = min(8, post_n)
        pairs.append(
            {
                "pair_path": _rel(path),
                "steps": n,
                "intervention_step": int(step),
                "line_id": int(line_id) if line_id is not None else None,
                "post_intervention_steps": post_n,
                "planned_query_points": planned_points,
            }
        )
    return {
        "candidate_pairs": len(pairs),
        "skipped_pairs": skipped,
        "planned_examples_per_query_point": 2,
        "planned_examples": sum(p["planned_query_points"] * 2 for p in pairs),
        "per_pair": pairs,
        "query_policy": "up to 8 post-intervention local_t values per pair, with delta and intervention-max-rho questions",
    }


def citylearn_capacity() -> dict[str, Any]:
    windows: list[dict[str, Any]] = []
    per_trace: list[dict[str, Any]] = []
    for path in CITYLEARN_TRACES:
        if not path.exists():
            continue
        data = _load(path)
        n = len(data["trace"])
        trace_windows = []
        for horizon in (512, 1024, 2048):
            stride = max(1, horizon // 2)
            for start in window_starts(n, horizon, stride):
                item = {"trace_path": _rel(path), "horizon": horizon, "start": start, "end": start + horizon}
                windows.append(item)
                trace_windows.append(item)
        per_trace.append(
            {
                "trace_path": _rel(path),
                "steps": n,
                "n_buildings": int(data["n_buildings"]),
                "candidate_windows": len(trace_windows),
            }
        )
    # The planned expanded builder emits 10 building load + 4 quarter net
    # electricity + 6 outdoor temperature examples per CityLearn window.
    return {
        "candidate_windows": len(windows),
        "planned_examples_per_window": 20,
        "planned_examples": len(windows) * 20,
        "per_trace": per_trace,
        "window_policy": "horizons 512/1024/2048 with stride=horizon/2, including final aligned window",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    report = {
        "grid2op_observation": grid2op_observation_capacity(),
        "grid2op_counterfactual": grid2op_counterfactual_capacity(),
        "citylearn": citylearn_capacity(),
    }
    report["planned_total_examples"] = (
        report["grid2op_observation"]["planned_examples"]
        + report["grid2op_counterfactual"]["planned_examples"]
        + report["citylearn"]["planned_examples"]
    )
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
