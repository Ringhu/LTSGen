#!/usr/bin/env python3
"""Build meta-safe Grid2Op statement QA from existing Grid2Op QA records."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
LETTERS = ("A", "B", "C", "D")
QUARTERS = ("first", "second", "third", "fourth")
QUARTER_TEXT = {
    "first": "the first quarter",
    "second": "the second quarter",
    "third": "the third quarter",
    "fourth": "the fourth quarter",
}
DIRECTION_THRESHOLD = 0.05


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


def _balanced_options(correct_text: str, distractors: list[str], item_index: int) -> tuple[list[str], str]:
    if len(distractors) < 3:
        raise ValueError("Need at least three distractors")
    target = LETTERS[item_index % len(LETTERS)]
    option_texts = {target: correct_text}
    remaining = [x for x in LETTERS if x != target]
    for letter, text in zip(remaining, distractors[:3]):
        option_texts[letter] = text
    return [f"{letter}. {option_texts[letter]}" for letter in LETTERS], target


def _quarter_for_t(t: int, horizon: int) -> str:
    return QUARTERS[min(3, int(t / max(horizon, 1) * 4))]


def _format(v: float) -> str:
    return f"{float(v):.3f}"


def _direction_phrase(direction: str) -> str:
    if direction == "increase":
        return "an increase"
    if direction == "decrease":
        return "a decrease"
    return direction


class TraceCache:
    def __init__(self) -> None:
        self._traces: dict[str, dict[str, Any]] = {}
        self._pairs: dict[str, dict[str, Any]] = {}

    def window(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        path = record["trace_path"]
        if path not in self._traces:
            self._traces[path] = json.loads(_resolve(path).read_text(encoding="utf-8"))
        rows = self._traces[path]["trace"]
        start = int(record["trace_window"]["start"])
        end = int(record["trace_window"]["end"])
        return rows[start:end]

    def pair(self, record: dict[str, Any]) -> dict[str, Any]:
        path = record["pair_path"]
        if path not in self._pairs:
            self._pairs[path] = json.loads(_resolve(path).read_text(encoding="utf-8"))
        return self._pairs[path]


def _array(rows: list[dict[str, Any]], key: str) -> np.ndarray:
    return np.asarray([r[key] for r in rows], dtype=float)


def _clone(record: dict[str, Any], task_family: str, question: str, options: list[str], answer: str, answer_label: str, caption: str, evidence: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    out["id"] = f"{record['id']}::statement_v2"
    out["source_record_id"] = record["id"]
    out["task_family"] = task_family
    out["question"] = question
    out["options"] = options
    out["answer"] = answer
    out["answer_label"] = answer_label
    out["oracle_evidence_caption"] = caption
    out["evidence"] = {**record.get("evidence", {}), **evidence, "statement_mode": "meta_safe_v2"}
    return out


def build_observation_record(record: dict[str, Any], cache: TraceCache, item_index: int) -> dict[str, Any]:
    rows = cache.window(record)
    horizon = len(rows)
    task = record["task_family"]

    if task == "peak_rho_quarter":
        rho = _array(rows, "rho")
        peak_flat = int(np.argmax(rho))
        peak_t, peak_line = np.unravel_index(peak_flat, rho.shape)
        quarter = _quarter_for_t(int(peak_t), horizon)
        correct = f"The maximum rho occurs on line {int(peak_line)} at local t={int(peak_t)}, in {QUARTER_TEXT[quarter]}."
        answer_label = f"line {int(peak_line)} t={int(peak_t)} {quarter}"
        caption = (
            f"The trace-supported statement is: maximum rho occurs on line {int(peak_line)} "
            f"at local t={int(peak_t)}, in {QUARTER_TEXT[quarter]}."
        )
        evidence = {"statement_peak_line": int(peak_line), "statement_peak_local_t": int(peak_t), "statement_quarter": quarter, "statement_peak_rho": float(rho[peak_t, peak_line])}
        distractors = []
        wrong_lines = [int(i) for i in np.argsort(rho.max(axis=0))[::-1] if int(i) != int(peak_line)]
        wrong_quarters = [q for q in QUARTERS if q != quarter]
        distractors.append(f"The maximum rho occurs on line {wrong_lines[0]} at local t={int(peak_t)}, in {QUARTER_TEXT[quarter]}.")
        distractors.append(f"The maximum rho occurs on line {int(peak_line)} at local t={max(0, int(peak_t) - max(10, horizon // 8))}, in {QUARTER_TEXT[wrong_quarters[0]]}.")
        distractors.append(f"The maximum rho occurs on line {wrong_lines[1]} at local t={min(horizon - 1, int(peak_t) + max(10, horizon // 8))}, in {QUARTER_TEXT[wrong_quarters[-1]]}.")
        options, answer = _balanced_options(correct, distractors, item_index)
        return _clone(record, "peak_rho_statement", "Which statement about the maximum line loading is supported by the trace?", options, answer, answer_label, caption, evidence)

    if task == "peak_rho_line":
        rho = _array(rows, "rho")
        per_line_peak = rho.max(axis=0)
        per_line_t = rho.argmax(axis=0)
        ranked = list(np.argsort(per_line_peak)[::-1])
        line = int(ranked[0])
        correct = f"Line {line} reaches the highest rho in the window, at local t={int(per_line_t[line])}."
        distractors = [
            f"Line {int(i)} reaches the highest rho in the window, at local t={int(per_line_t[int(i)])}."
            for i in ranked[1:8]
        ]
        options, answer = _balanced_options(correct, distractors, item_index)
        caption = f"The trace-supported statement is: line {line} reaches the highest rho, at local t={int(per_line_t[line])}."
        evidence = {"statement_peak_line": line, "statement_peak_local_t": int(per_line_t[line]), "statement_peak_rho": float(per_line_peak[line])}
        return _clone(record, "peak_rho_line_statement", "Which statement about the line with the highest rho is supported by the trace?", options, answer, f"line {line}", caption, evidence)

    if task == "max_avg_load":
        load = _array(rows, "load_p")
        means = load.mean(axis=0)
        idx = int(np.argmax(means))
        ranked = list(np.argsort(np.abs(means - means[idx])))
        wrong_values = [float(means[int(i)]) for i in ranked if int(i) != idx][:3]
        candidates = [
            f"Load {idx}'s window-average active power is about {_format(means[idx])}.",
            f"Load {idx}'s window-average active power is about {_format(wrong_values[0])}.",
            f"Load {int(np.argsort(means)[-2])}'s window-average active power is about {_format(means[idx])}.",
            f"Load {int(np.argsort(means)[0])}'s window-average active power is about {_format(means[idx])}.",
        ]
        options, answer = _balanced_options(candidates[0], candidates[1:], item_index)
        caption = f"The trace-supported statement is: load {idx}'s window-average active power is about {_format(means[idx])}."
        evidence = {"statement_load": idx, "statement_avg_load_p": float(means[idx])}
        return _clone(record, "avg_load_statement", "Which statement about window-average load_p is supported by the trace?", options, answer, f"load {idx} avg {_format(means[idx])}", caption, evidence)

    if task == "max_avg_generator":
        gen = _array(rows, "gen_p")
        means = gen.mean(axis=0)
        idx = int(np.argmax(means))
        ranked = list(np.argsort(np.abs(means - means[idx])))
        wrong_values = [float(means[int(i)]) for i in ranked if int(i) != idx][:3]
        candidates = [
            f"Generator {idx}'s window-average active power is about {_format(means[idx])}.",
            f"Generator {idx}'s window-average active power is about {_format(wrong_values[0])}.",
            f"Generator {int(np.argsort(means)[-2])}'s window-average active power is about {_format(means[idx])}.",
            f"Generator {int(np.argsort(means)[0])}'s window-average active power is about {_format(means[idx])}.",
        ]
        options, answer = _balanced_options(candidates[0], candidates[1:], item_index)
        caption = f"The trace-supported statement is: generator {idx}'s window-average active power is about {_format(means[idx])}."
        evidence = {"statement_generator": idx, "statement_avg_gen_p": float(means[idx])}
        return _clone(record, "avg_generator_statement", "Which statement about window-average gen_p is supported by the trace?", options, answer, f"generator {idx} avg {_format(means[idx])}", caption, evidence)

    if task == "peak_total_load_quarter":
        load = _array(rows, "load_p")
        total = load.sum(axis=1)
        ranked_t = list(np.argsort(total)[::-1])
        peak_t = int(ranked_t[0])
        quarter = _quarter_for_t(peak_t, horizon)
        correct = f"The peak total load occurs at local t={peak_t}, in {QUARTER_TEXT[quarter]}."
        distractors = []
        for t in ranked_t[1:]:
            q = _quarter_for_t(int(t), horizon)
            text = f"The peak total load occurs at local t={int(t)}, in {QUARTER_TEXT[q]}."
            if text not in distractors:
                distractors.append(text)
            if len(distractors) >= 3:
                break
        options, answer = _balanced_options(correct, distractors, item_index)
        caption = f"The trace-supported statement is: peak total load occurs at local t={peak_t}, in {QUARTER_TEXT[quarter]}."
        evidence = {"statement_peak_total_load": float(total[peak_t]), "statement_peak_local_t": peak_t, "statement_quarter": quarter}
        return _clone(record, "peak_total_load_statement", "Which statement about peak total load is supported by the trace?", options, answer, f"t={peak_t} {quarter}", caption, evidence)

    if task == "total_load_trend":
        load = _array(rows, "load_p")
        total = load.sum(axis=1)
        q = max(1, horizon // 4)
        first = float(total[:q].mean())
        last = float(total[-q:].mean())
        direction = "higher" if last > first * 1.03 else "lower" if last < first * 0.97 else "roughly unchanged"
        mid = (first + last) / 2
        correct = f"The first-quarter mean total load is about {_format(first)} and the last-quarter mean is about {_format(last)}, so the last quarter is {direction}."
        distractors = [
            f"The first-quarter mean total load is about {_format(last)} and the last-quarter mean is about {_format(first)}, so the last quarter is {'lower' if direction == 'higher' else 'higher'}.",
            f"The first-quarter mean total load is about {_format(first)} and the last-quarter mean is about {_format(first)}, so the last quarter is roughly unchanged.",
            f"The first-quarter mean total load is about {_format(mid)} and the last-quarter mean is about {_format(mid)}, so the last quarter is roughly unchanged.",
        ]
        options, answer = _balanced_options(correct, distractors, item_index)
        caption = f"The trace-supported statement is: first-quarter mean total load is about {_format(first)} and last-quarter mean is about {_format(last)}; the last quarter is {direction}."
        evidence = {"statement_first_quarter_mean_total_load": first, "statement_last_quarter_mean_total_load": last, "statement_direction": direction}
        return _clone(record, "total_load_trend_statement", "Which statement about first-vs-last-quarter total load is supported by the trace?", options, answer, direction, caption, evidence)

    raise ValueError(f"Unsupported observation task: {task}")


def _severity_label(v: float) -> str:
    if v >= 1.20:
        return "severe overload"
    if v >= 1.00:
        return "overload"
    return "no overload"


def _direction_label(delta: float) -> str:
    if delta > DIRECTION_THRESHOLD:
        return "increase"
    if delta < -DIRECTION_THRESHOLD:
        return "decrease"
    return "roughly unchanged"


def build_counterfactual_record(record: dict[str, Any], cache: TraceCache, item_index: int) -> dict[str, Any] | None:
    task = record["task_family"]
    if task == "cf_intervened_line":
        return None
    data = cache.pair(record)
    factual = data["factual_trace"]
    intervention = data["intervention_trace"]
    step = int(record["intervention"]["step"])
    n = min(len(factual), len(intervention))
    start = min(step + 1, n)
    f_max = np.asarray([max(r["rho"]) for r in factual[start:n]], dtype=float)
    i_max = np.asarray([max(r["rho"]) for r in intervention[start:n]], dtype=float)
    f_peak = float(np.max(f_max))
    i_peak = float(np.max(i_max))
    delta = i_peak - f_peak

    if task == "cf_peak_rho_direction":
        direction = _direction_label(delta)
        reverse = _direction_label(-delta)
        same = (f_peak + i_peak) / 2
        correct = f"The factual post-intervention peak max-rho is about {_format(f_peak)}, while the intervention peak is about {_format(i_peak)}; under the 0.05 tolerance this is {_direction_phrase(direction)}."
        distractors = [
            f"The factual post-intervention peak max-rho is about {_format(i_peak)}, while the intervention peak is about {_format(f_peak)}; under the 0.05 tolerance this is {_direction_phrase(reverse)}.",
            f"The factual post-intervention peak max-rho is about {_format(same)}, while the intervention peak is about {_format(same)}; under the 0.05 tolerance this is roughly unchanged.",
            f"The factual post-intervention peak max-rho is about {_format(f_peak)}, while the intervention peak is about {_format(f_peak)}; under the 0.05 tolerance this is roughly unchanged.",
        ]
        options, answer = _balanced_options(correct, distractors, item_index)
        caption = f"The trace-supported statement is: factual post-intervention peak max-rho is about {_format(f_peak)}, intervention peak is about {_format(i_peak)}, delta is {delta:+.3f}, so the direction is {direction}."
        evidence = {"statement_factual_post_peak_max_rho": f_peak, "statement_intervention_post_peak_max_rho": i_peak, "statement_delta": delta, "statement_direction": direction}
        return _clone(record, "cf_peak_rho_direction_statement", "Which statement about the factual-vs-intervention post-peak max-rho is supported by the paired traces?", options, answer, direction, caption, evidence)

    if task == "cf_intervention_overload_severity":
        severity = _severity_label(i_peak)
        severity_values = {
            "severe overload": max(1.25, i_peak + 0.15),
            "overload": 1.08,
            "no overload": 0.94,
        }
        correct = f"The intervention post-peak max-rho is about {_format(i_peak)}, so the severity is {severity}."
        distractors = []
        for label, value in severity_values.items():
            if label != severity:
                distractors.append(f"The intervention post-peak max-rho is about {_format(value)}, so the severity is {label}.")
        distractors.append(f"The intervention post-peak max-rho is about {_format(f_peak)}, so the severity is {_severity_label(f_peak)}.")
        options, answer = _balanced_options(correct, distractors, item_index)
        caption = f"The trace-supported statement is: intervention post-peak max-rho is about {_format(i_peak)}, so the severity is {severity}."
        evidence = {"statement_intervention_post_peak_max_rho": i_peak, "statement_severity": severity}
        return _clone(record, "cf_overload_severity_statement", "Which statement about post-intervention overload severity is supported by the paired traces?", options, answer, severity, caption, evidence)

    raise ValueError(f"Unsupported counterfactual task: {task}")


def convert(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cache = TraceCache()
    out: list[dict[str, Any]] = []
    for record in records:
        if record.get("source") == "grid2op" or record.get("domain") == "grid2op_real":
            out.append(build_observation_record(record, cache, len(out)))
        elif record.get("source") == "grid2op_intervention" or record.get("domain") == "grid2op_real_cf":
            converted = build_counterfactual_record(record, cache, len(out))
            if converted is not None:
                out.append(converted)
        else:
            raise ValueError(f"Unsupported record source/domain: {record.get('source')} / {record.get('domain')}")
    return out


def sanity_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    answer_counts = Counter(r["answer"] for r in records)
    by_task = Counter(r["task_family"] for r in records)
    by_horizon = Counter(str(r["horizon"]) for r in records)
    missing = []
    for r in records:
        for key in ("id", "question", "options", "answer", "oracle_evidence_caption", "generic_caption", "evidence"):
            if key not in r or r[key] in ("", [], None):
                missing.append((r.get("id", "?"), key))
    return {
        "n_items": len(records),
        "answer_counts": dict(answer_counts),
        "max_answer_letter_fraction": max(answer_counts.values()) / max(len(records), 1) if records else 1.0,
        "by_horizon": dict(by_horizon),
        "by_task_family": dict(by_task),
        "missing_required_field_count": len(missing),
        "missing_required_fields": missing[:20],
        "schema_gate_pass": bool(records) and len(missing) == 0 and max(answer_counts.values()) / len(records) <= 0.30,
        "note": "Meta-safe v2 statement QA. Context card should not reveal these trace-specific statements.",
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
