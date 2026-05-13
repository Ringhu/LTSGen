#!/usr/bin/env python3
"""Build meta-safe Grid2Op numeric-slot QA from existing Grid2Op records."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
LETTERS = ("A", "B", "C", "D")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def _format(v: float) -> str:
    return f"{float(v):.3f}"


def _options(correct: str, distractors: list[str], item_index: int) -> tuple[list[str], str]:
    target = LETTERS[item_index % len(LETTERS)]
    texts = {target: correct}
    for letter, text in zip([x for x in LETTERS if x != target], distractors[:3]):
        texts[letter] = text
    if set(texts) != set(LETTERS):
        raise ValueError(f"Need four options, got {texts}")
    return [f"{letter}. {texts[letter]}" for letter in LETTERS], target


def _near_values(value: float, pool: list[float], min_gap: float = 0.02) -> list[float]:
    out: list[float] = []
    for v in sorted(pool, key=lambda x: abs(float(x) - value)):
        fv = float(v)
        if abs(fv - value) >= min_gap and all(abs(fv - x) >= min_gap for x in out):
            out.append(fv)
        if len(out) >= 3:
            return out
    scale = max(abs(value), 1.0)
    for factor in (0.92, 1.08, 1.16, 0.84, 1.24):
        fv = value * factor
        if abs(fv - value) >= min_gap * scale and all(abs(fv - x) >= min_gap * scale for x in out):
            out.append(fv)
        if len(out) >= 3:
            break
    step = max(abs(value) * 0.03, min_gap * 2, 0.05)
    k = 1
    while len(out) < 3 and k < 20:
        for sign in (1, -1):
            fv = value + sign * step * k
            if abs(fv - value) >= min_gap and all(abs(fv - x) >= min_gap for x in out):
                out.append(fv)
            if len(out) >= 3:
                break
        k += 1
    return out[:3]


def _clone(
    record: dict[str, Any],
    *,
    task_family: str,
    question: str,
    options: list[str],
    answer: str,
    answer_label: str,
    caption: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    out = dict(record)
    out["id"] = f"{record['id']}::numeric_v3"
    out["source_record_id"] = record["id"]
    out["task_family"] = task_family
    out["question"] = question
    out["options"] = options
    out["answer"] = answer
    out["answer_label"] = answer_label
    out["oracle_evidence_caption"] = caption
    out["evidence"] = {**record.get("evidence", {}), **evidence, "numeric_slot_mode": "meta_safe_v3"}
    return out


class Cache:
    def __init__(self) -> None:
        self.traces: dict[str, dict[str, Any]] = {}
        self.pairs: dict[str, dict[str, Any]] = {}

    def window(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        path = record["trace_path"]
        if path not in self.traces:
            self.traces[path] = json.loads(_resolve(path).read_text(encoding="utf-8"))
        rows = self.traces[path]["trace"]
        start = int(record["trace_window"]["start"])
        end = int(record["trace_window"]["end"])
        return rows[start:end]

    def pair(self, record: dict[str, Any]) -> dict[str, Any]:
        path = record["pair_path"]
        if path not in self.pairs:
            self.pairs[path] = json.loads(_resolve(path).read_text(encoding="utf-8"))
        return self.pairs[path]


def _array(rows: list[dict[str, Any]], key: str) -> np.ndarray:
    return np.asarray([r[key] for r in rows], dtype=float)


def observation(record: dict[str, Any], cache: Cache, item_index: int) -> dict[str, Any]:
    rows = cache.window(record)
    horizon = len(rows)
    task = record["task_family"]

    if task == "peak_rho_quarter":
        rho = _array(rows, "rho")
        max_rho = rho.max(axis=1)
        peak_t = int(np.argmax(max_rho))
        line = int(np.argmax(rho[peak_t]))
        correct = f"line={line}, local_t={peak_t}, max_rho={_format(max_rho[peak_t])}"
        candidate_idx = [int(i) for i in np.argsort(max_rho)[::-1] if int(i) != peak_t][:6]
        distractors = [
            f"line={int(np.argmax(rho[t]))}, local_t={t}, max_rho={_format(max_rho[t])}"
            for t in candidate_idx[:3]
        ]
        options, answer = _options(correct, distractors, item_index)
        caption = f"The peak max-rho slot is line={line}, local_t={peak_t}, max_rho={_format(max_rho[peak_t])}."
        return _clone(record, task_family="peak_rho_numeric_slot", question="Which numeric slot matches the maximum line loading in this trace window?", options=options, answer=answer, answer_label=correct, caption=caption, evidence={"slot_line": line, "slot_local_t": peak_t, "slot_max_rho": float(max_rho[peak_t])})

    if task == "peak_rho_line":
        rho = _array(rows, "rho")
        n_line = rho.shape[1]
        target = (item_index * 7 + 3) % n_line
        values = rho[:, target]
        peak = float(values.max())
        peak_t = int(values.argmax())
        distractors = [f"peak_rho={_format(v)}" for v in _near_values(peak, [float(x) for x in rho.max(axis=0)], 0.005)]
        options, answer = _options(f"peak_rho={_format(peak)}", distractors, item_index)
        caption = f"For line {target}, peak_rho={_format(peak)} at local_t={peak_t}."
        return _clone(record, task_family="line_peak_rho_numeric_slot", question=f"For line {target}, which peak_rho value is supported by the trace?", options=options, answer=answer, answer_label=f"line {target} peak {_format(peak)}", caption=caption, evidence={"slot_line": int(target), "slot_peak_rho": peak, "slot_peak_local_t": peak_t})

    if task == "max_avg_load":
        load = _array(rows, "load_p")
        n_load = load.shape[1]
        target = (item_index * 5 + 1) % n_load
        means = load.mean(axis=0)
        value = float(means[target])
        distractors = [f"avg_load_p={_format(v)}" for v in _near_values(value, [float(x) for x in means], 0.5)]
        options, answer = _options(f"avg_load_p={_format(value)}", distractors, item_index)
        caption = f"For load {target}, window-average load_p={_format(value)}."
        return _clone(record, task_family="load_avg_numeric_slot", question=f"For load {target}, which window-average load_p value is supported by the trace?", options=options, answer=answer, answer_label=f"load {target} avg {_format(value)}", caption=caption, evidence={"slot_load": int(target), "slot_avg_load_p": value})

    if task == "max_avg_generator":
        gen = _array(rows, "gen_p")
        n_gen = gen.shape[1]
        target = (item_index * 3 + 1) % n_gen
        means = gen.mean(axis=0)
        value = float(means[target])
        distractors = [f"avg_gen_p={_format(v)}" for v in _near_values(value, [float(x) for x in means], 0.5)]
        options, answer = _options(f"avg_gen_p={_format(value)}", distractors, item_index)
        caption = f"For generator {target}, window-average gen_p={_format(value)}."
        return _clone(record, task_family="generator_avg_numeric_slot", question=f"For generator {target}, which window-average gen_p value is supported by the trace?", options=options, answer=answer, answer_label=f"generator {target} avg {_format(value)}", caption=caption, evidence={"slot_generator": int(target), "slot_avg_gen_p": value})

    if task == "peak_total_load_quarter":
        load = _array(rows, "load_p")
        total = load.sum(axis=1)
        peak_t = int(total.argmax())
        value = float(total[peak_t])
        candidate_idx = [int(i) for i in np.argsort(total)[::-1] if int(i) != peak_t][:6]
        distractors = [f"local_t={t}, total_load={_format(total[t])}" for t in candidate_idx[:3]]
        options, answer = _options(f"local_t={peak_t}, total_load={_format(value)}", distractors, item_index)
        caption = f"The peak total-load slot is local_t={peak_t}, total_load={_format(value)}."
        return _clone(record, task_family="peak_total_load_numeric_slot", question="Which numeric slot matches the peak total load in this trace window?", options=options, answer=answer, answer_label=f"t {peak_t} total {_format(value)}", caption=caption, evidence={"slot_peak_total_load": value, "slot_peak_local_t": peak_t})

    if task == "total_load_trend":
        load = _array(rows, "load_p")
        total = load.sum(axis=1)
        q = max(1, horizon // 4)
        quarter = item_index % 4
        start = quarter * q
        end = horizon if quarter == 3 else (quarter + 1) * q
        value = float(total[start:end].mean())
        quarter_means = [float(total[i * q : (horizon if i == 3 else (i + 1) * q)].mean()) for i in range(4)]
        distractors = [f"mean_total_load={_format(v)}" for v in _near_values(value, quarter_means, 1.0)]
        options, answer = _options(f"mean_total_load={_format(value)}", distractors, item_index)
        caption = f"For quarter {quarter + 1}, mean_total_load={_format(value)}."
        return _clone(record, task_family="quarter_total_load_mean_numeric_slot", question=f"For quarter {quarter + 1}, which mean_total_load value is supported by the trace?", options=options, answer=answer, answer_label=f"q{quarter + 1} mean {_format(value)}", caption=caption, evidence={"slot_quarter": quarter + 1, "slot_mean_total_load": value})

    raise ValueError(f"Unsupported observation task: {task}")


def counterfactual(record: dict[str, Any], cache: Cache, item_index: int) -> dict[str, Any] | None:
    if record["task_family"] == "cf_intervened_line":
        return None
    data = cache.pair(record)
    factual = data["factual_trace"]
    intervention = data["intervention_trace"]
    step = int(record["intervention"]["step"])
    n = min(len(factual), len(intervention))
    start = min(step + 1, n)
    f_max = np.asarray([max(r["rho"]) for r in factual[start:n]], dtype=float)
    i_max = np.asarray([max(r["rho"]) for r in intervention[start:n]], dtype=float)
    f_peak = float(f_max.max())
    i_peak = float(i_max.max())
    delta = i_peak - f_peak

    if record["task_family"] == "cf_peak_rho_direction":
        correct = f"factual_peak={_format(f_peak)}, intervention_peak={_format(i_peak)}, delta={delta:+.3f}"
        distractors = [
            f"factual_peak={_format(i_peak)}, intervention_peak={_format(f_peak)}, delta={-delta:+.3f}",
            f"factual_peak={_format(f_peak)}, intervention_peak={_format(f_peak)}, delta=+0.000",
            f"factual_peak={_format((f_peak + i_peak) / 2)}, intervention_peak={_format(i_peak)}, delta={(i_peak - (f_peak + i_peak) / 2):+.3f}",
        ]
        options, answer = _options(correct, distractors, item_index)
        caption = f"The paired post-intervention slot is factual_peak={_format(f_peak)}, intervention_peak={_format(i_peak)}, delta={delta:+.3f}."
        return _clone(record, task_family="cf_peak_rho_numeric_slot", question="Which numeric slot matches the post-intervention factual/intervention peak max_rho comparison?", options=options, answer=answer, answer_label=correct, caption=caption, evidence={"slot_factual_peak_max_rho": f_peak, "slot_intervention_peak_max_rho": i_peak, "slot_delta": delta})

    if record["task_family"] == "cf_intervention_overload_severity":
        pool = [float(x) for x in i_max]
        distractors = [f"intervention_peak={_format(v)}" for v in _near_values(i_peak, pool, 0.01)]
        options, answer = _options(f"intervention_peak={_format(i_peak)}", distractors, item_index)
        caption = f"The intervention post-peak slot is intervention_peak={_format(i_peak)}."
        return _clone(record, task_family="cf_intervention_peak_numeric_slot", question="Which intervention_peak max_rho value after the intervention is supported by the paired traces?", options=options, answer=answer, answer_label=f"intervention_peak {_format(i_peak)}", caption=caption, evidence={"slot_intervention_peak_max_rho": i_peak})

    raise ValueError(f"Unsupported counterfactual task: {record['task_family']}")


def convert(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cache = Cache()
    out = []
    for record in records:
        if record.get("domain") == "grid2op_real":
            out.append(observation(record, cache, len(out)))
        elif record.get("domain") == "grid2op_real_cf":
            item = counterfactual(record, cache, len(out))
            if item is not None:
                out.append(item)
        else:
            raise ValueError(record.get("domain"))
    return out


def sanity_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    answers = Counter(r["answer"] for r in records)
    return {
        "n_items": len(records),
        "answer_counts": dict(answers),
        "max_answer_letter_fraction": max(answers.values()) / max(len(records), 1) if records else 1.0,
        "by_horizon": dict(Counter(str(r["horizon"]) for r in records)),
        "by_task_family": dict(Counter(r["task_family"] for r in records)),
        "missing_required_field_count": sum(
            1
            for r in records
            for key in ("id", "question", "options", "answer", "oracle_evidence_caption", "generic_caption", "evidence")
            if key not in r or r[key] in ("", [], None)
        ),
        "schema_gate_pass": bool(records) and max(answers.values()) / max(len(records), 1) <= 0.30,
        "note": "Meta-safe v3 numeric-slot QA. All options use the same format and require trace-specific numeric evidence.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--output_name", required=True)
    args = parser.parse_args()

    records = convert(load_jsonl(Path(args.input)))
    out_dir = Path(args.out_dir)
    write_jsonl(out_dir / args.output_name, records)
    report = sanity_report(records)
    (out_dir / "sanity_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
