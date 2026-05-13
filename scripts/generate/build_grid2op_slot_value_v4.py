#!/usr/bin/env python3
"""Build Grid2Op slot-value QA with low meta-only priors."""
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


def _fmt(v: float) -> str:
    return f"{float(v):.3f}"


def _stable_slot(*parts: Any) -> int:
    text = "::".join(str(p) for p in parts)
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 4


def _options(correct: str, values: list[str], item_index: int, slot_key: str) -> tuple[list[str], str]:
    vals = []
    for v in values:
        if v != correct and v not in vals:
            vals.append(v)
        if len(vals) == 3:
            break
    if len(vals) < 3:
        raise ValueError(f"Need three unique distractors for {correct}, got {vals}")
    target = LETTERS[_stable_slot(slot_key)]
    texts = {target: correct}
    for letter, value in zip([x for x in LETTERS if x != target], vals):
        texts[letter] = value
    return [f"{letter}. {texts[letter]}" for letter in LETTERS], target


def _set_answer_letter(row: dict[str, Any], target: str) -> dict[str, Any]:
    correct = str(row["answer_label"])
    values = [opt.split(". ", 1)[1] for opt in row["options"]]
    distractors = [v for v in values if v != correct]
    if len(distractors) != 3:
        raise ValueError(f"Expected 3 distractors for {row['id']}, got {distractors}")
    texts = {target: correct}
    for letter, value in zip([x for x in LETTERS if x != target], distractors):
        texts[letter] = value
    out = dict(row)
    out["options"] = [f"{letter}. {texts[letter]}" for letter in LETTERS]
    out["answer"] = target
    out["evidence"] = {
        **row.get("evidence", {}),
        "answer_letter_mode": "global_hash_balanced_v4b",
    }
    return out


def rebalance_answer_letters(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Balance answer letters without tying them to task order or slot values."""
    ranked = sorted(range(len(rows)), key=lambda i: hashlib.sha256(rows[i]["id"].encode("utf-8")).hexdigest())
    targets = {idx: LETTERS[pos % len(LETTERS)] for pos, idx in enumerate(ranked)}
    return [_set_answer_letter(row, targets[i]) for i, row in enumerate(rows)]


def _distractor_numbers(value: float, gap: float, item_index: int, *, nonnegative: bool = False) -> list[str]:
    """Create plausible same-precision distractors with balanced value ranks."""
    rank = (item_index // 4) % 4
    scale = max(abs(value), 1.0)
    step = max(gap, 0.017 * scale)
    lower_needed = rank
    upper_needed = 3 - rank
    vals: list[float] = []

    for k in range(lower_needed, 0, -1):
        vals.append(value - step * (k + 0.37 + 0.11 * ((item_index + k) % 3)))
    for k in range(1, upper_needed + 1):
        vals.append(value + step * (k + 0.29 + 0.13 * ((item_index + k) % 3)))

    if nonnegative and vals and min(vals) < 0:
        shift = abs(min(vals)) + step
        vals = [v + shift for v in vals]
        # Keep the correct value's rank by shifting all distractors upward only
        # when the correct value is intended to be the minimum.
        if rank != 0:
            vals = [max(value + step * (i + 1.23), 0.0) for i in range(3)]

    out: list[float] = []
    for v in vals:
        if abs(v - value) >= gap * 0.5 and _fmt(v) != _fmt(value) and _fmt(v) not in {_fmt(x) for x in out}:
            out.append(v)
    k = 1
    while len(out) < 3:
        sign = -1 if len(out) < rank else 1
        v = value + sign * step * (k + 1.71)
        if not nonnegative or v >= 0:
            if _fmt(v) != _fmt(value) and _fmt(v) not in {_fmt(x) for x in out}:
                out.append(v)
        k += 1
    return [_fmt(x) for x in out[:3]]


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


def _arr(rows: list[dict[str, Any]], key: str) -> np.ndarray:
    return np.asarray([r[key] for r in rows], dtype=float)


def _clone(record: dict[str, Any], task: str, question: str, options: list[str], answer: str, label: str, caption: str, evidence: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    out["id"] = f"{record['id']}::slot_v4"
    out["source_record_id"] = record["id"]
    out["task_family"] = task
    out["question"] = question
    out["options"] = options
    out["answer"] = answer
    out["answer_label"] = label
    out["oracle_evidence_caption"] = caption
    out["evidence"] = {**record.get("evidence", {}), **evidence, "slot_value_mode": "meta_safe_v4"}
    return out


def observation(record: dict[str, Any], cache: Cache, index: int) -> dict[str, Any]:
    rows = cache.window(record)
    horizon = len(rows)
    task = record["task_family"]
    slot_t = min(horizon - 1, max(0, int((index * 97 + horizon // 3) % horizon)))

    if task in {"peak_rho_quarter", "peak_rho_line"}:
        rho = _arr(rows, "rho")
        line = int((index * 7 + 3) % rho.shape[1])
        value = float(rho[slot_t, line])
        correct = _fmt(value)
        question = f"At local_t={slot_t}, what is rho for line {line}?"
        options, answer = _options(
            correct,
            _distractor_numbers(value, 0.005, index, nonnegative=True),
            index,
            f"{record['id']}::{question}",
        )
        caption = f"At local_t={slot_t}, rho for line {line} is {correct}."
        return _clone(record, "rho_value_slot", question, options, answer, correct, caption, {"slot_local_t": slot_t, "slot_line": line, "slot_rho": value})

    if task == "max_avg_load":
        load = _arr(rows, "load_p")
        load_id = int((index * 5 + 2) % load.shape[1])
        value = float(load[:, load_id].mean())
        correct = _fmt(value)
        question = f"What is the window-average load_p for load {load_id}?"
        options, answer = _options(
            correct,
            _distractor_numbers(value, 0.5, index, nonnegative=True),
            index,
            f"{record['id']}::{question}",
        )
        caption = f"The window-average load_p for load {load_id} is {correct}."
        return _clone(record, "load_average_value_slot", question, options, answer, correct, caption, {"slot_load": load_id, "slot_avg_load_p": value})

    if task == "max_avg_generator":
        gen = _arr(rows, "gen_p")
        gen_id = int((index * 3 + 1) % gen.shape[1])
        value = float(gen[:, gen_id].mean())
        correct = _fmt(value)
        question = f"What is the window-average gen_p for generator {gen_id}?"
        options, answer = _options(
            correct,
            _distractor_numbers(value, 0.5, index, nonnegative=True),
            index,
            f"{record['id']}::{question}",
        )
        caption = f"The window-average gen_p for generator {gen_id} is {correct}."
        return _clone(record, "generator_average_value_slot", question, options, answer, correct, caption, {"slot_generator": gen_id, "slot_avg_gen_p": value})

    if task in {"peak_total_load_quarter", "total_load_trend"}:
        total = _arr(rows, "load_p").sum(axis=1)
        quarter = int(index % 4)
        q = max(1, horizon // 4)
        start = quarter * q
        end = horizon if quarter == 3 else (quarter + 1) * q
        value = float(total[start:end].mean())
        correct = _fmt(value)
        question = f"What is the mean total_load in quarter {quarter + 1} of this trace window?"
        options, answer = _options(
            correct,
            _distractor_numbers(value, 1.0, index, nonnegative=True),
            index,
            f"{record['id']}::{question}",
        )
        caption = f"The mean total_load in quarter {quarter + 1} is {correct}."
        return _clone(record, "quarter_total_load_mean_value_slot", question, options, answer, correct, caption, {"slot_quarter": quarter + 1, "slot_mean_total_load": value})

    raise ValueError(task)


def counterfactual(record: dict[str, Any], cache: Cache, index: int) -> dict[str, Any] | None:
    if record["task_family"] == "cf_intervened_line":
        return None
    data = cache.pair(record)
    factual = data["factual_trace"]
    intervention = data["intervention_trace"]
    step = int(record["intervention"]["step"])
    n = min(len(factual), len(intervention))
    local_t = min(n - 1, step + 1 + int((index * 61) % max(1, n - step - 1)))
    f_rho = [float(x) for x in factual[local_t]["rho"]]
    i_rho = [float(x) for x in intervention[local_t]["rho"]]
    f_max = max(f_rho)
    i_max = max(i_rho)
    delta = i_max - f_max

    if record["task_family"] == "cf_peak_rho_direction":
        value = delta
        correct = _fmt(value)
        question = f"At local_t={local_t}, what is intervention_max_rho minus factual_max_rho?"
        options, answer = _options(
            correct,
            _distractor_numbers(value, 0.01, index),
            index,
            f"{record['id']}::{question}",
        )
        caption = f"At local_t={local_t}, intervention_max_rho - factual_max_rho is {correct}."
        return _clone(record, "cf_delta_max_rho_value_slot", question, options, answer, correct, caption, {"slot_local_t": local_t, "slot_factual_max_rho": f_max, "slot_intervention_max_rho": i_max, "slot_delta_max_rho": value})

    if record["task_family"] == "cf_intervention_overload_severity":
        value = i_max
        correct = _fmt(value)
        question = f"At local_t={local_t}, what is intervention_max_rho?"
        options, answer = _options(
            correct,
            _distractor_numbers(value, 0.01, index, nonnegative=True),
            index,
            f"{record['id']}::{question}",
        )
        caption = f"At local_t={local_t}, intervention_max_rho is {correct}."
        return _clone(record, "cf_intervention_max_rho_value_slot", question, options, answer, correct, caption, {"slot_local_t": local_t, "slot_intervention_max_rho": value})

    raise ValueError(record["task_family"])


def convert(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cache = Cache()
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("domain") == "grid2op_real":
            out.append(observation(row, cache, len(out)))
        elif row.get("domain") == "grid2op_real_cf":
            item = counterfactual(row, cache, len(out))
            if item is not None:
                out.append(item)
        else:
            raise ValueError(row.get("domain"))
    return rebalance_answer_letters(out)


def report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    answers = Counter(r["answer"] for r in rows)
    return {
        "n_items": len(rows),
        "answer_counts": dict(answers),
        "max_answer_letter_fraction": max(answers.values()) / max(len(rows), 1) if rows else 1.0,
        "by_horizon": dict(Counter(str(r["horizon"]) for r in rows)),
        "by_task_family": dict(Counter(r["task_family"] for r in rows)),
        "missing_required_field_count": sum(
            1
            for r in rows
            for key in ("id", "question", "options", "answer", "oracle_evidence_caption", "generic_caption", "evidence")
            if key not in r or r[key] in ("", [], None)
        ),
        "schema_gate_pass": bool(rows) and max(answers.values()) / max(len(rows), 1) <= 0.30,
        "note": "Slot-value v4 QA: fixed variable/time/window asks for a trace-specific numeric value; avoids max/argmax answer priors.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--output_name", required=True)
    args = parser.parse_args()

    rows = convert(load_jsonl(Path(args.input)))
    out_dir = Path(args.out_dir)
    write_jsonl(out_dir / args.output_name, rows)
    rep = report(rows)
    (out_dir / "sanity_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rep, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
