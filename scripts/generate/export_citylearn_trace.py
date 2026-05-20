#!/usr/bin/env python3
"""Export a CityLearn packaged-dataset trace into the SimQA trace format."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


BUILDING_COLUMNS = [
    "non_shiftable_load",
    "dhw_demand",
    "cooling_demand",
    "heating_demand",
    "solar_generation",
]

WEATHER_COLUMNS = [
    "outdoor_dry_bulb_temperature",
    "outdoor_relative_humidity",
    "diffuse_solar_irradiance",
    "direct_solar_irradiance",
]


def _series(row: pd.Series, columns: list[str]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for col in columns:
        value = row[col]
        out[col] = None if pd.isna(value) else float(value)
    return out


def export_trace(dataset_dir: Path, *, start: int, horizon: int, n_buildings: int) -> dict[str, Any]:
    weather = pd.read_csv(dataset_dir / "weather.csv")
    pricing = pd.read_csv(dataset_dir / "pricing.csv")
    carbon = pd.read_csv(dataset_dir / "carbon_intensity.csv")
    building_frames = []
    for i in range(1, n_buildings + 1):
        building_frames.append(pd.read_csv(dataset_dir / f"Building_{i}.csv"))

    total_len = min(len(weather), len(pricing), len(carbon), *(len(df) for df in building_frames))
    end = min(start + horizon, total_len)
    if start < 0 or start >= total_len or end <= start:
        raise ValueError(f"Invalid window start={start}, horizon={horizon}, total_len={total_len}")

    rows: list[dict[str, Any]] = []
    for t in range(start, end):
        buildings = []
        totals = {col: 0.0 for col in BUILDING_COLUMNS}
        for building_id, df in enumerate(building_frames, start=1):
            values = _series(df.iloc[t], BUILDING_COLUMNS)
            buildings.append({"building_id": building_id, **values})
            for col, value in values.items():
                if value is not None:
                    totals[col] += float(value)
        net_electricity = totals["non_shiftable_load"] - totals["solar_generation"]
        rows.append(
            {
                "t": t,
                "local_t": t - start,
                "calendar": _series(
                    building_frames[0].iloc[t],
                    ["month", "hour", "day_type", "daylight_savings_status"],
                ),
                "weather": _series(weather.iloc[t], WEATHER_COLUMNS),
                "price": float(pricing.iloc[t]["electricity_pricing"]),
                "carbon_intensity": float(carbon.iloc[t]["carbon_intensity"]),
                "buildings": buildings,
                "totals": {**totals, "net_electricity_without_storage": net_electricity},
            }
        )

    return {
        "source": "citylearn_packaged_dataset",
        "dataset_dir": str(dataset_dir),
        "dataset_name": dataset_dir.name,
        "requested_horizon": horizon,
        "actual_horizon": len(rows),
        "start": start,
        "end": end,
        "n_buildings": n_buildings,
        "variables": {
            "building": BUILDING_COLUMNS,
            "weather": WEATHER_COLUMNS,
            "global": ["electricity_pricing", "carbon_intensity"],
            "derived": ["totals", "net_electricity_without_storage"],
        },
        "trace": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--horizon", type=int, default=2048)
    parser.add_argument("--n_buildings", type=int, default=5)
    args = parser.parse_args()

    trace = export_trace(
        Path(args.dataset_dir),
        start=args.start,
        horizon=args.horizon,
        n_buildings=args.n_buildings,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(out),
                "actual_horizon": trace["actual_horizon"],
                "n_buildings": trace["n_buildings"],
                "dataset_name": trace["dataset_name"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
