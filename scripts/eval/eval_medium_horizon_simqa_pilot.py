#!/usr/bin/env python3
"""Evaluate the medium-horizon SimQA pilot with an OpenAI-compatible LLM."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "generate"))
from build_medium_horizon_simqa_pilot import regenerate_trace  # noqa: E402

sys.path.insert(0, "/home/cris/Research/gptapi")
from llm_client import check_model, get_async_client  # noqa: E402


CONDITIONS = ("meta_only", "generic_caption", "oracle_evidence_caption", "numbers_sampled_256")
NUMBERS_SAMPLED_RE = re.compile(r"^numbers_sampled_(\d+)$")
SYSTEM = (
    "You answer multiple-choice questions about time-series traces. "
    "Return only the option letter A, B, C, or D."
)

GRID2OP_DOMAIN_CONTEXT = """Grid2Op context card:
- Grid2Op is a power-grid simulation environment. A trace is a time-ordered rollout of grid state.
- A power line transports electricity between grid nodes. Disconnecting a line changes the grid topology and can redistribute flows across other lines.
- `rho[line]` is the loading ratio of each power line. A larger rho means a more heavily loaded line; rho >= 1.00 means overload, and rho > 1.20 means severe overload in these questions.
- `max_rho` means the largest rho across all lines at a timestep. `argmax rho line` is the line index with that largest rho.
- `load_p[load]` is active power demand for each load. `gen_p[generator]` is active power output for each generator.
- `line_status[line]` is 1 when a line is connected and 0 when disconnected.
- Use the trace values to answer. Do not infer the effect of an intervention from domain intuition alone."""

GRID2OP_OBSERVATION_CONTEXT = """Trace setup:
- This is a single factual trace window.
- `local_t` indexes time within the selected window; `global_t` indexes the original exported trace.
- For quarter-based questions, divide the local window into four equal contiguous quarters."""

GRID2OP_COUNTERFACTUAL_CONTEXT = """Trace setup:
- This is a paired factual/counterfactual setting.
- The factual trace is the original rollout.
- The intervention trace follows the same setup except that one specified power line is disconnected at the intervention time.
- For post-intervention questions, compare timesteps after the intervention time in the factual and intervention traces."""

CITYLEARN_DOMAIN_CONTEXT = """CityLearn context card:
- CityLearn is a building-energy simulation benchmark. A trace is an hourly sequence of building, weather, electricity price, and carbon-intensity variables.
- `building` indexes a building in a district or neighborhood.
- `non_shiftable_load` is a building's electricity demand that cannot be shifted by control actions.
- `solar_generation` is local photovoltaic generation. Larger solar_generation can make net electricity lower or negative.
- `net_electricity_without_storage` is total non-shiftable building load minus total solar generation in this exported trace.
- `outdoor_dry_bulb_temperature` is outdoor air temperature.
- Use the trace values to answer. Background definitions do not determine the answer."""

CITYLEARN_OBSERVATION_CONTEXT = """Trace setup:
- This is a packaged CityLearn dataset trace, exported as one factual observation window.
- `local_t` indexes time within the selected hourly window.
- For quarter-based questions, divide the local window into four equal contiguous quarters."""

TASK_CONTEXT = {
    "peak_rho_quarter": (
        "Task rule: find the single largest `rho` value across all lines and all timesteps in the window, "
        "then report which local quarter contains that timestep."
    ),
    "peak_rho_line": (
        "Task rule: find which power line reaches the highest `rho` value anywhere in the window."
    ),
    "max_avg_load": (
        "Task rule: compute each load's average `load_p` over the whole window, then choose the load with the largest average."
    ),
    "max_avg_generator": (
        "Task rule: compute each generator's average `gen_p` over the whole window, then choose the generator with the largest average."
    ),
    "peak_total_load_quarter": (
        "Task rule: total load at a timestep is the sum of all `load_p` entries; find which quarter contains the maximum total load."
    ),
    "total_load_trend": (
        "Task rule: total load at a timestep is the sum of all `load_p` entries; compare the mean total load in the first and last quarters."
    ),
    "cf_peak_rho_direction": (
        "Task rule: after the intervention time, compute the peak `max_rho` in the factual trace and in the intervention trace. "
        "Compare the intervention peak against the factual peak using the tolerance stated in the question."
    ),
    "cf_intervention_overload_severity": (
        "Task rule: after the intervention time, find the largest `max_rho` in the intervention trace and map it to the overload thresholds in the options."
    ),
    "cf_intervened_line": (
        "Task rule: identify the line explicitly disconnected by the intervention metadata or by the line status change."
    ),
    "rho_value_slot": (
        "Task rule: read the `rho` value for the exact line and `local_t` specified in the question."
    ),
    "load_average_value_slot": (
        "Task rule: compute the average `load_p` over the whole window for the exact load specified in the question."
    ),
    "generator_average_value_slot": (
        "Task rule: compute the average `gen_p` over the whole window for the exact generator specified in the question."
    ),
    "quarter_total_load_mean_value_slot": (
        "Task rule: compute total load at each timestep as the sum of all `load_p` values, then average it over the exact quarter specified in the question."
    ),
    "cf_delta_max_rho_value_slot": (
        "Task rule: at the exact `local_t` specified in the question, subtract factual `max_rho` from intervention `max_rho`."
    ),
    "cf_intervention_max_rho_value_slot": (
        "Task rule: at the exact `local_t` specified in the question, read `max_rho` from the intervention trace."
    ),
    "building_load_value_slot": (
        "Task rule: read `non_shiftable_load` for the exact building and `local_t` specified in the question."
    ),
    "quarter_net_electricity_mean_value_slot": (
        "Task rule: average `net_electricity_without_storage` over the exact quarter specified in the question."
    ),
    "outdoor_temperature_value_slot": (
        "Task rule: read `outdoor_dry_bulb_temperature` at the exact `local_t` specified in the question."
    ),
}

CONTEXT_CARD_VERSION = "domain_context_v3_grid2op_citylearn_slot_value_rules"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def select_balanced(records: list[dict[str, Any]], max_items: int, seed: int) -> list[dict[str, Any]]:
    if max_items <= 0 or max_items >= len(records):
        return records
    rng = np.random.default_rng(seed)
    buckets: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        buckets[(r["domain"], int(r["horizon"]), r["task_family"])].append(r)
    keys = sorted(buckets)
    selected: list[dict[str, Any]] = []
    cursor = 0
    while len(selected) < max_items and cursor < 10000:
        key = keys[cursor % len(keys)]
        pool = buckets[key]
        if pool:
            idx = int(rng.integers(0, len(pool)))
            selected.append(pool.pop(idx))
        cursor += 1
        if all(not v for v in buckets.values()):
            break
    return selected


def _format_value(v: float) -> str:
    av = abs(float(v))
    if av >= 1000 or (0 < av < 0.001):
        return f"{v:.3e}"
    return f"{v:.3f}"


def _load_real_grid2op_window(record: dict[str, Any]) -> list[dict[str, Any]]:
    trace_path = Path(record["trace_path"])
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    start = int(record["trace_window"]["start"])
    end = int(record["trace_window"]["end"])
    return data["trace"][start:end]


def _load_grid2op_pair(record: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pair_path = Path(record["pair_path"])
    data = json.loads(pair_path.read_text(encoding="utf-8"))
    n = min(len(data["factual_trace"]), len(data["intervention_trace"]))
    return data["factual_trace"][:n], data["intervention_trace"][:n]


def _load_citylearn_window(record: dict[str, Any]) -> list[dict[str, Any]]:
    trace_path = Path(record["trace_path"])
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    start = int(record["trace_window"]["start"])
    end = int(record["trace_window"]["end"])
    return data["trace"][start:end]


def _format_vector(values: list[float], max_items: int | None = None) -> str:
    arr = values if max_items is None else values[:max_items]
    body = ", ".join(_format_value(float(v)) for v in arr)
    if max_items is not None and len(values) > max_items:
        body += ", ..."
    return "[" + body + "]"


def format_real_grid2op_trace_table(record: dict[str, Any], *, max_steps: int | None) -> str:
    rows = _load_real_grid2op_window(record)
    horizon = len(rows)
    if max_steps is None or max_steps >= horizon:
        idx = np.arange(horizon)
        label = f"all {horizon} steps"
    else:
        idx = np.linspace(0, horizon - 1, max_steps).astype(int)
        label = f"{len(idx)} evenly sampled steps from {horizon}"
    lines = [
        f"Grid2Op factual trace table ({label}). Each row gives local/global time, "
        "total load, total generation, maximum rho, argmax rho line, load vector, "
        "generator vector, and rho vector."
    ]
    for local_i in idx:
        r = rows[int(local_i)]
        load = [float(x) for x in r["load_p"]]
        gen = [float(x) for x in r["gen_p"]]
        rho = [float(x) for x in r["rho"]]
        max_rho = max(rho)
        max_line = rho.index(max_rho)
        lines.append(
            "local_t={local_t}, global_t={global_t}: total_load={total_load}, "
            "total_gen={total_gen}, max_rho={max_rho}, max_rho_line={max_line}, "
            "load_p={load_p}, gen_p={gen_p}, rho={rho}".format(
                local_t=int(local_i),
                global_t=int(r["t"]),
                total_load=_format_value(sum(load)),
                total_gen=_format_value(sum(gen)),
                max_rho=_format_value(max_rho),
                max_line=max_line,
                load_p=_format_vector(load),
                gen_p=_format_vector(gen),
                rho=_format_vector(rho),
            )
        )
    return "\n".join(lines)


def format_grid2op_pair_trace_table(record: dict[str, Any], *, max_steps: int | None) -> str:
    factual_rows, intervention_rows = _load_grid2op_pair(record)
    horizon = len(factual_rows)
    if max_steps is None or max_steps >= horizon:
        idx = np.arange(horizon)
        label = f"all {horizon} paired steps"
    else:
        idx = np.linspace(0, horizon - 1, max_steps).astype(int)
        label = f"{len(idx)} evenly sampled paired steps from {horizon}"
    meta = record.get("intervention", {})
    lines = [
        f"Grid2Op paired factual/counterfactual trace table ({label}). "
        f"Intervention: {meta.get('type', 'unknown')} line {meta.get('line_id', '?')} "
        f"at t={meta.get('step', '?')}. Each row gives factual and intervention "
        "maximum rho, argmax rho line, total load, and intervened line status."
    ]
    line_id = int(meta.get("line_id", 0))
    for local_i in idx:
        f = factual_rows[int(local_i)]
        i = intervention_rows[int(local_i)]
        f_rho = [float(x) for x in f["rho"]]
        i_rho = [float(x) for x in i["rho"]]
        f_max_rho = max(f_rho)
        i_max_rho = max(i_rho)
        lines.append(
            "local_t={local_t}: factual_total_load={f_load}, factual_max_rho={f_rho}, "
            "factual_max_rho_line={f_line}, factual_line_status={f_status}; "
            "intervention_total_load={i_load}, intervention_max_rho={i_rho}, "
            "intervention_max_rho_line={i_line}, intervention_line_status={i_status}".format(
                local_t=int(local_i),
                f_load=_format_value(sum(float(x) for x in f["load_p"])),
                f_rho=_format_value(f_max_rho),
                f_line=int(f_rho.index(f_max_rho)),
                f_status=int(f["line_status"][line_id]),
                i_load=_format_value(sum(float(x) for x in i["load_p"])),
                i_rho=_format_value(i_max_rho),
                i_line=int(i_rho.index(i_max_rho)),
                i_status=int(i["line_status"][line_id]),
            )
        )
    return "\n".join(lines)


def format_citylearn_trace_table(record: dict[str, Any], *, max_steps: int | None) -> str:
    rows = _load_citylearn_window(record)
    horizon = len(rows)
    if max_steps is None or max_steps >= horizon:
        idx = np.arange(horizon)
        label = f"all {horizon} hourly steps"
    else:
        idx = np.linspace(0, horizon - 1, max_steps).astype(int)
        label = f"{len(idx)} evenly sampled hourly steps from {horizon}"
    lines = [
        f"CityLearn factual trace table ({label}). Each row gives local/global time, "
        "weather, price, carbon intensity, total net electricity without storage, "
        "and per-building non-shiftable load and solar generation vectors."
    ]
    for local_i in idx:
        r = rows[int(local_i)]
        loads = [float(b["non_shiftable_load"]) for b in r["buildings"]]
        solar = [float(b["solar_generation"]) for b in r["buildings"]]
        lines.append(
            "local_t={local_t}, global_t={global_t}: outdoor_temp={temp}, price={price}, "
            "carbon_intensity={carbon}, net_electricity_without_storage={net}, "
            "non_shiftable_load={loads}, solar_generation={solar}".format(
                local_t=int(local_i),
                global_t=int(r["t"]),
                temp=_format_value(float(r["weather"]["outdoor_dry_bulb_temperature"])),
                price=_format_value(float(r["price"])),
                carbon=_format_value(float(r["carbon_intensity"])),
                net=_format_value(float(r["totals"]["net_electricity_without_storage"])),
                loads=_format_vector(loads),
                solar=_format_vector(solar),
            )
        )
    return "\n".join(lines)


def format_trace_table(record: dict[str, Any], *, max_steps: int | None) -> str:
    if record.get("source") == "grid2op_intervention" and "pair_path" in record:
        return format_grid2op_pair_trace_table(record, max_steps=max_steps)
    if record.get("source") == "grid2op" and "trace_path" in record:
        return format_real_grid2op_trace_table(record, max_steps=max_steps)
    if record.get("source") == "citylearn_packaged_dataset" and "trace_path" in record:
        return format_citylearn_trace_table(record, max_steps=max_steps)

    factual, _ = regenerate_trace(record)
    variables = record["variables"]
    horizon = int(record["horizon"])
    if max_steps is None or max_steps >= horizon:
        idx = np.arange(horizon)
        label = f"all {horizon} steps"
    else:
        idx = np.linspace(0, horizon - 1, max_steps).astype(int)
        label = f"{len(idx)} evenly sampled steps from {horizon}"
    lines = [f"Factual trace table ({label}); columns: t, " + ", ".join(variables)]
    for i in idx:
        vals = ", ".join(_format_value(float(factual[v][i])) for v in variables)
        lines.append(f"t={int(i)}: {vals}")
    return "\n".join(lines)


def build_context_card(record: dict[str, Any]) -> str:
    domain = str(record.get("domain", ""))
    source = str(record.get("source", ""))
    if domain.startswith("grid2op"):
        parts = [GRID2OP_DOMAIN_CONTEXT]
        if source == "grid2op_intervention" or "pair_path" in record:
            parts.append(GRID2OP_COUNTERFACTUAL_CONTEXT)
        else:
            parts.append(GRID2OP_OBSERVATION_CONTEXT)
    elif domain.startswith("citylearn"):
        parts = [CITYLEARN_DOMAIN_CONTEXT, CITYLEARN_OBSERVATION_CONTEXT]
    else:
        return ""
    task = str(record.get("task_family", ""))
    if task in TASK_CONTEXT:
        parts.append(TASK_CONTEXT[task])
    return "\n\n".join(parts)


def build_prompt(record: dict[str, Any], condition: str, *, full_numbers: bool = False) -> str:
    domain_text = record["domain"].replace("_", " ")
    parts = [
        f"Domain: {domain_text}.",
        f"Horizon: {record['horizon']} time steps.",
        "Choose the single best answer.",
    ]
    context_card = build_context_card(record)
    if context_card:
        parts.append(context_card)
    if condition == "meta_only":
        pass
    elif condition == "generic_caption":
        parts.append("Trace description: " + record["generic_caption"])
    elif condition == "oracle_evidence_caption":
        parts.append("Trace evidence: " + record["oracle_evidence_caption"])
    elif m := NUMBERS_SAMPLED_RE.match(condition):
        parts.append(format_trace_table(record, max_steps=int(m.group(1))))
    elif condition == "numbers_full":
        parts.append(format_trace_table(record, max_steps=None))
    else:
        raise ValueError(condition)

    parts.append("Question: " + record["question"])
    parts.append("Options:")
    parts.extend(record["options"])
    parts.append("Answer with only A, B, C, or D.")
    return "\n\n".join(parts)


def parse_letter(text: str) -> str:
    text = (text or "").strip().upper()
    if text in {"A", "B", "C", "D"}:
        return text
    m = re.search(r"\b([ABCD])\b", text)
    if m:
        return m.group(1)
    m = re.search(r"([ABCD])", text)
    return m.group(1) if m else ""


async def ask(client, model: str, prompt: str, sem: asyncio.Semaphore) -> str:
    for attempt in range(4):
        try:
            async with sem:
                resp = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                    max_tokens=8,
                )
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            if attempt == 3:
                return f"ERROR: {exc}"
            await asyncio.sleep(2 ** attempt)
    return ""


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {"overall": {}, "by_horizon": {}, "by_task_family": {}, "by_domain": {}}
    conditions = sorted({r["condition"] for r in results})
    for cond in conditions:
        cr = [r for r in results if r["condition"] == cond]
        metrics["overall"][cond] = {
            "n": len(cr),
            "accuracy": round(float(np.mean([r["correct"] for r in cr])) if cr else 0.0, 4),
            "mean_prompt_chars": round(float(np.mean([r["prompt_chars"] for r in cr])) if cr else 0.0, 1),
        }
    for key_name, field in (("by_horizon", "horizon"), ("by_task_family", "task_family"), ("by_domain", "domain")):
        values = sorted({r[field] for r in results}, key=str)
        for value in values:
            metrics[key_name][str(value)] = {}
            for cond in conditions:
                rr = [r for r in results if r[field] == value and r["condition"] == cond]
                metrics[key_name][str(value)][cond] = {
                    "n": len(rr),
                    "accuracy": round(float(np.mean([x["correct"] for x in rr])) if rr else 0.0, 4),
                }
    return metrics


async def run(args: argparse.Namespace) -> dict[str, Any]:
    records = load_jsonl(Path(args.data))
    records = select_balanced(records, args.max_items, args.seed)
    conditions = args.conditions or list(CONDITIONS)
    sem = asyncio.Semaphore(args.concurrency)
    client = get_async_client()
    check_model(args.model)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prompts: list[tuple[dict[str, Any], str, str]] = []
    for r in records:
        for cond in conditions:
            prompts.append((r, cond, build_prompt(r, cond, full_numbers=args.full_numbers)))

    prompt_report = {
        "n_items": len(records),
        "n_prompts": len(prompts),
        "conditions": conditions,
        "context_card": CONTEXT_CARD_VERSION,
        "prompt_chars": {
            cond: {
                "mean": round(float(np.mean([len(p) for _, c, p in prompts if c == cond])), 1),
                "max": int(max([len(p) for _, c, p in prompts if c == cond] or [0])),
            }
            for cond in conditions
        },
    }
    (out_dir / "prompt_report.json").write_text(json.dumps(prompt_report, indent=2), encoding="utf-8")
    print(json.dumps(prompt_report, indent=2))
    if args.dry_run:
        return {"prompt_report": prompt_report}

    started = time.time()
    outputs = await asyncio.gather(*[ask(client, args.model, p, sem) for _, _, p in prompts])
    results: list[dict[str, Any]] = []
    for (record, cond, prompt), raw in zip(prompts, outputs):
        pred = parse_letter(raw)
        results.append({
            "id": record["id"],
            "domain": record["domain"],
            "horizon": record["horizon"],
            "task_family": record["task_family"],
            "condition": cond,
            "gold": record["answer"],
            "raw_output": raw,
            "pred": pred,
            "correct": pred == record["answer"],
            "prompt_chars": len(prompt),
        })
    metrics = aggregate(results)
    metrics["run_info"] = {
        "model": args.model,
        "n_items": len(records),
        "n_prompts": len(prompts),
        "elapsed_sec": round(time.time() - started, 2),
        "full_numbers": bool(args.full_numbers),
        "context_card": CONTEXT_CARD_VERSION,
    }
    with (out_dir / "predictions.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return metrics


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=".research/medium-horizon-simqa-pilot-20260512/simqa_pilot.jsonl")
    p.add_argument("--out_dir", default=".research/medium-horizon-simqa-pilot-20260512/llm_smoke")
    p.add_argument("--model", default="gpt-5.4-mini")
    p.add_argument("--max_items", type=int, default=40)
    p.add_argument("--seed", type=int, default=20260512)
    p.add_argument("--conditions", nargs="*", default=None)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--full_numbers", action="store_true", help="Deprecated; use condition numbers_full instead.")
    p.add_argument("--dry_run", action="store_true", help="Write prompt_report.json and exit before API calls.")
    args = p.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
