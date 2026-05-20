#!/usr/bin/env python3
"""Audit numeric grounding of natural-QCC evidence captions.

Caption-shape audits only tell us whether a generated caption looks like
evidence. This diagnostic checks whether the caption is actually grounded in
the deterministic support slots that define the gold answer: copied numeric
facts, local window length, and answer-supporting direction.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520"
DEFAULT_GOLD = BASE / "sft_evidence_only_v21/natural_qcc_failure_domain_expanded_v21_evidence_only_test_raw.jsonl"
DEFAULT_PREDICTIONS = (
    BASE
    / "train_v21_style_repair_e5_tok128_20260520/tsrlm_qcond_e5_tok128_qwen3_4b/generate_eval_test_clean/predictions.jsonl"
)
DEFAULT_OUT = BASE / "numeric_grounding_repair_v22_20260520/v21_qcond_slot_factuality_audit.json"

NUM = r"[-+]?(?:\d[\d,]*(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?"
NUM_RE = re.compile(NUM)
STEP_PHRASE_RE = re.compile(rf"\b({NUM})\s*-\s*step\b", flags=re.IGNORECASE)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize(text: str) -> str:
    text = str(text or "").replace("\u2212", "-")
    return re.sub(r"\s+", " ", text.strip().lower())


def parse_float(text: str) -> float | None:
    match = NUM_RE.search(str(text or "").replace("\u2212", "-"))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def caption_numbers(caption: str) -> list[float]:
    numbers: list[float] = []
    for match in NUM_RE.finditer(caption.replace("\u2212", "-")):
        try:
            numbers.append(float(match.group(0).replace(",", "")))
        except ValueError:
            continue
    return numbers


def close_number(actual: float | None, expected: float, *, kind: str = "value") -> bool:
    if actual is None or not math.isfinite(actual):
        return False
    if kind in {"index", "horizon", "lag"}:
        return abs(actual - expected) <= 0.5
    if kind == "corr":
        return abs(actual - expected) <= max(0.005, abs(expected) * 0.005)
    return abs(actual - expected) <= max(0.05, abs(expected) * 0.0001)


def source_name(row: dict[str, Any]) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(
        row.get("merge_source_name")
        or meta.get("merge_source_name")
        or row.get("multisim_source_domain")
        or row.get("domain")
        or "unknown"
    )


def option_labels(row: dict[str, Any]) -> list[str]:
    labels = []
    for option in row.get("options", []) or []:
        text = str(option)
        labels.append(text.split(". ", 1)[1].strip() if ". " in text else text.strip())
    return labels


def gold_label(row: dict[str, Any]) -> str:
    return str(row.get("answer_label") or row.get("gold_answer_label") or "").strip()


def label_category(label: str) -> str:
    label = normalize(label)
    if any(token in label for token in ("similar", "same", "no material", "no clear", "neither", "weak", "flat", "stable")):
        return "similar"
    if any(token in label for token in ("first half higher", "first-half higher")):
        return "first"
    if any(token in label for token in ("second half higher", "second-half higher")):
        return "second"
    if "early" in label:
        return "early"
    if "middle" in label:
        return "middle"
    if "late" in label:
        return "late"
    if any(token in label for token in ("higher after intervention", "greater", "larger upward", "raises", "higher", "increase", "upward")):
        return "positive"
    if any(token in label for token in ("lower", "reduces", "decrease", "downward")):
        return "negative"
    if "cpu-memory" in label or "cpu memory" in label:
        return "cpu_memory"
    if "network" in label or "rx-tx" in label or "rx tx" in label:
        return "network"
    if "x1" in label and "x2" not in label:
        return "x1"
    if "x2" in label:
        return "x2"
    return label


def local_window_len(slots: dict[str, Any]) -> int | None:
    if slots.get("horizon") is not None:
        try:
            return int(slots["horizon"])
        except (TypeError, ValueError):
            pass
    try:
        return int(slots["window_end"]) - int(slots["window_start"])
    except (KeyError, TypeError, ValueError):
        return None


def third_from_index(index: float, horizon: int | None) -> str | None:
    if horizon is None or horizon <= 0:
        return None
    if index < horizon / 3:
        return "early"
    if index < 2 * horizon / 3:
        return "middle"
    return "late"


def extract_first(patterns: list[str], caption: str) -> float | None:
    text = caption.replace("\u2212", "-")
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_float(match.group(1))
    return None


def labeled_patterns(label_patterns: list[str], suffix_patterns: list[str] | None = None) -> list[str]:
    suffix_patterns = suffix_patterns or [""]
    patterns = []
    for label in label_patterns:
        for suffix in suffix_patterns:
            patterns.append(rf"\b{label}\b{suffix}[^0-9+\-]{{0,30}}({NUM})")
            patterns.append(rf"\b{label}\b\s*=\s*({NUM})")
    return patterns


def add_check(checks: list[dict[str, Any]], name: str, expected: Any, patterns: list[str], *, kind: str = "value") -> None:
    if expected is None:
        return
    try:
        expected_float = float(expected)
    except (TypeError, ValueError):
        return
    checks.append({"name": name, "expected": expected_float, "patterns": patterns, "kind": kind})


def task_family_from_slots(slots: dict[str, Any]) -> str:
    keys = set(slots)
    if "first_mean" in keys and "second_mean" in keys:
        return "half_window"
    if isinstance(slots.get("region_stds"), dict):
        return "region_std"
    if "extrema_index" in keys and "extrema_value" in keys:
        return "extrema"
    if "event_abs_z" in keys and "event_index" in keys:
        return "anomaly"
    if "corr_cpu_memory" in keys and "corr_net_rx_tx" in keys:
        return "correlation_pair"
    if "corr_x1" in keys and "corr_x2" in keys:
        return "correlation_pair"
    if "best_lag" in keys and "best_lag_corr" in keys:
        return "lead_lag"
    if "factual_overload_exposure" in keys and "intervention_overload_exposure" in keys:
        return "counterfactual_exposure"
    if "mean_x0_diff" in keys:
        return "counterfactual_mean_diff"
    if "max_x0_diff" in keys and "min_x0_diff" in keys:
        return "counterfactual_range_diff"
    if "event_factual_mean" in keys and "event_baseline_mean" in keys:
        return "event_gap"
    if "factual_mean" in keys and "counterfactual_mean" in keys:
        return "counterfactual_mean"
    if "event_response_score_x0" in keys and "event_response_score_x1" in keys:
        return "event_response"
    if {"pre_mean", "event_mean", "post_mean"}.issubset(keys):
        return "recovery"
    if {"start_value", "end_value", "delta"}.issubset(keys):
        return "trend"
    if "combined_stress_score" in keys:
        return "combined_stress"
    if "x0_mean" in keys and "x0_peak" in keys:
        return "grid_stress_context"
    if "mean_pressure" in keys and "min_pressure" in keys:
        return "water_context"
    if "mean_speed" in keys and "max_queue" in keys:
        return "traffic_context"
    if "controlled_event" in keys and "event_index" in keys:
        return "controlled_event"
    return "generic"


def numeric_checks(slots: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    task = task_family_from_slots(slots)

    if task == "region_std":
        for key in ("early", "middle", "late"):
            add_check(checks, f"region_stds.{key}", slots["region_stds"].get(key), [rf"\b{key}\s*=\s*({NUM})"])

    if task == "half_window":
        add_check(checks, "first_mean", slots.get("first_mean"), labeled_patterns([r"first[- ]half"], [r"[^.\n]{0,40}\bmean(?:\s+\w+)?\b"]), kind="value")
        add_check(checks, "second_mean", slots.get("second_mean"), labeled_patterns([r"second[- ]half"], [r"[^.\n]{0,40}\bmean(?:\s+\w+)?\b"]), kind="value")

    if task == "trend":
        add_check(checks, "start_value", slots.get("start_value"), labeled_patterns([r"starts?", r"signal starts"], [r"[^.\n]{0,20}(?:at|is)?"]), kind="value")
        add_check(checks, "end_value", slots.get("end_value"), labeled_patterns([r"ends?", r"signal ends"], [r"[^.\n]{0,20}(?:at|is)?"]), kind="value")
        add_check(checks, "delta", slots.get("delta"), labeled_patterns([r"changes?", r"delta", r"gap"], [r"[^.\n]{0,30}(?:by|is)?"]), kind="value")
        add_check(checks, "std", slots.get("std"), labeled_patterns([r"variability", r"std", r"standard deviation"]), kind="value")

    if task == "extrema":
        add_check(checks, "extrema_index", slots.get("extrema_index"), labeled_patterns([r"local step", r"step"]), kind="index")
        add_check(checks, "extrema_value", slots.get("extrema_value"), labeled_patterns([r"(?:maximum|minimum|max|min) value", r"value"]), kind="value")
    if task in {"anomaly", "controlled_event"}:
        add_check(checks, "event_index", slots.get("event_index"), labeled_patterns([r"local step", r"step"]), kind="index")
    if task == "anomaly":
        add_check(checks, "event_abs_z", slots.get("event_abs_z"), labeled_patterns([r"absolute z[- ]score", r"z[- ]score"]), kind="value")

    if task == "correlation_pair" and "corr_cpu_memory" in slots:
        add_check(checks, "corr_cpu_memory", slots.get("corr_cpu_memory"), labeled_patterns([r"cpu[- ]memory correlation", r"cpu memory correlation"]), kind="corr")
        add_check(
            checks,
            "corr_net_rx_tx",
            slots.get("corr_net_rx_tx"),
            labeled_patterns([r"network receive/transmit correlation", r"network rx[- ]tx correlation", r"network receive.*?correlation"]),
            kind="corr",
        )
    if task == "correlation_pair" and "corr_x1" in slots:
        add_check(checks, "corr_x1", abs(float(slots.get("corr_x1"))), labeled_patterns([r"x1", r"correlation with x1"]), kind="corr")
        add_check(checks, "corr_x2", abs(float(slots.get("corr_x2"))), labeled_patterns([r"x2", r"correlation with x2"]), kind="corr")
    if task == "lead_lag":
        add_check(checks, "best_lag", slots.get("best_lag"), labeled_patterns([r"strongest tested lag", r"best lag", r"lag"]), kind="lag")
        add_check(checks, "best_lag_corr", slots.get("best_lag_corr"), labeled_patterns([r"correlation"]), kind="corr")
        add_check(checks, "zero_lag_corr", slots.get("zero_lag_corr"), labeled_patterns([r"zero[- ]lag correlation"]), kind="corr")

    if task == "counterfactual_exposure":
        add_check(checks, "factual_overload_exposure", slots.get("factual_overload_exposure"), labeled_patterns([r"factual overload exposure", r"factual exposure"]), kind="value")
        add_check(
            checks,
            "intervention_overload_exposure",
            slots.get("intervention_overload_exposure"),
            labeled_patterns([r"intervention exposure", r"intervention overload exposure"]),
            kind="value",
        )
        add_check(
            checks,
            "exposure_diff",
            slots.get("exposure_diff"),
            labeled_patterns([r"intervention[- ]minus[- ]factual (?:difference|exposure)", r"difference"]),
            kind="value",
        )
    if task == "counterfactual_mean_diff":
        add_check(checks, "mean_x0_diff", slots.get("mean_x0_diff"), labeled_patterns([r"mean intervention[- ]minus[- ]factual stress difference", r"mean difference"]), kind="value")
    if task == "counterfactual_range_diff":
        add_check(checks, "min_x0_diff", slots.get("min_x0_diff"), [rf"ranges?\s+from\s+({NUM})\s+to\s+{NUM}"], kind="value")
        add_check(checks, "max_x0_diff", slots.get("max_x0_diff"), [rf"ranges?\s+from\s+{NUM}\s+to\s+({NUM})"], kind="value")

    if task == "event_gap":
        add_check(checks, "event_factual_mean", slots.get("event_factual_mean"), labeled_patterns([r"event[- ]window mean", r"event mean"]), kind="value")
        add_check(checks, "event_baseline_mean", slots.get("event_baseline_mean"), labeled_patterns([r"baseline mean", r"matched baseline mean"]), kind="value")
        add_check(checks, "event_gap", slots.get("event_gap"), labeled_patterns([r"gap"]), kind="value")
    if task == "counterfactual_mean":
        add_check(checks, "factual_mean", slots.get("factual_mean"), labeled_patterns([r"factual mean"]), kind="value")
        add_check(checks, "counterfactual_mean", slots.get("counterfactual_mean"), labeled_patterns([r"counterfactual mean"]), kind="value")
        add_check(checks, "delta", slots.get("delta"), labeled_patterns([r"delta", r"factual[- ]minus[- ]counterfactual"]), kind="value")

    if task == "event_response":
        add_check(checks, "event_response_score_x0", slots.get("event_response_score_x0"), labeled_patterns([r"x0 event[- ]response score", r"x0 response score"]), kind="value")
        add_check(checks, "event_response_score_x1", slots.get("event_response_score_x1"), labeled_patterns([r"x1 event[- ]response score", r"x1 response score"]), kind="value")
    if task == "combined_stress":
        add_check(checks, "combined_stress_score", slots.get("combined_stress_score"), labeled_patterns([r"combined stress score"]), kind="value")
    if task == "grid_stress_context":
        add_check(checks, "x0_mean", slots.get("x0_mean"), labeled_patterns([r"mean line[- ]loading stress", r"x0 mean"]), kind="value")
        add_check(checks, "x0_peak", slots.get("x0_peak"), labeled_patterns([r"peak stress", r"x0 peak"]), kind="value")
        add_check(checks, "x1_mean", slots.get("x1_mean"), labeled_patterns([r"mean demand", r"x1 mean"]), kind="value")
    if task == "water_context":
        add_check(checks, "mean_pressure", slots.get("mean_pressure"), labeled_patterns([r"mean pressure"]), kind="value")
        add_check(checks, "min_pressure", slots.get("min_pressure"), labeled_patterns([r"minimum pressure", r"min pressure"]), kind="value")
        add_check(checks, "mean_flow", slots.get("mean_flow"), labeled_patterns([r"mean flow"]), kind="value")
    if task == "traffic_context":
        add_check(checks, "mean_speed", slots.get("mean_speed"), labeled_patterns([r"mean speed"]), kind="value")
        add_check(checks, "max_queue", slots.get("max_queue"), labeled_patterns([r"maximum queue", r"max queue"]), kind="value")
        add_check(checks, "mean_occupancy", slots.get("mean_occupancy"), labeled_patterns([r"mean occupancy"]), kind="value")

    return checks


def evaluate_numeric_checks(caption: str, slots: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    results = []
    for check in numeric_checks(slots):
        actual = extract_first(check["patterns"], caption)
        passed = close_number(actual, float(check["expected"]), kind=str(check["kind"]))
        results.append(
            {
                "name": check["name"],
                "expected": check["expected"],
                "actual": actual,
                "kind": check["kind"],
                "pass": passed,
            }
        )
    return results, all(item["pass"] for item in results) if results else True


def first_second_from_caption(caption: str) -> tuple[float | None, float | None]:
    first = extract_first(labeled_patterns([r"first[- ]half"], [r"[^.\n]{0,40}\bmean(?:\s+\w+)?\b"]), caption)
    second = extract_first(labeled_patterns([r"second[- ]half"], [r"[^.\n]{0,40}\bmean(?:\s+\w+)?\b"]), caption)
    return first, second


def region_stds_from_caption(caption: str) -> dict[str, float | None]:
    return {key: extract_first([rf"\b{key}\s*=\s*({NUM})"], caption) for key in ("early", "middle", "late")}


def sign_category(value: float | None, *, tol: float = 0.02) -> str | None:
    if value is None:
        return None
    if abs(value) <= tol:
        return "similar"
    return "positive" if value > 0 else "negative"


def values_category(values: dict[str, float | None]) -> str | None:
    if any(values.get(key) is None for key in ("early", "middle", "late")):
        return None
    vals = {key: float(values[key]) for key in ("early", "middle", "late")}  # type: ignore[arg-type]
    if max(vals.values()) - min(vals.values()) <= max(0.05, max(abs(v) for v in vals.values()) * 0.05):
        return "similar"
    return max(vals, key=vals.get)


def half_category(first: float | None, second: float | None) -> str | None:
    if first is None or second is None:
        return None
    if abs(first - second) / max(abs(first), abs(second), 1.0) < 0.05:
        return "similar"
    return "first" if first > second else "second"


def corr_pair_category(left: float | None, right: float | None, *, left_name: str, right_name: str) -> str | None:
    if left is None or right is None:
        return None
    left_abs = abs(left)
    right_abs = abs(right)
    if left_abs < 0.30 and right_abs < 0.30:
        return "similar"
    if left_abs >= 0.30 and right_abs >= 0.30 and abs(left_abs - right_abs) < 0.05:
        return "similar"
    return left_name if left_abs > right_abs else right_name


def local_step_from_caption(caption: str) -> float | None:
    return extract_first(labeled_patterns([r"local step", r"step"]), caption)


def horizon_from_caption(caption: str) -> int | None:
    matches = [parse_float(match.group(1)) for match in STEP_PHRASE_RE.finditer(caption)]
    matches = [value for value in matches if value is not None]
    if not matches:
        return None
    return int(round(matches[-1]))


def expected_direction(slots: dict[str, Any], row: dict[str, Any]) -> str:
    label = str(slots.get("answer_label") or gold_label(row))
    if "event_abs_z" in slots and any(token in normalize(label) for token in ("no pronounced", "no clear", "weak")):
        return "similar"
    if "event_response_score_x0" in slots and "event_response_score_x1" in slots:
        if any(token in normalize(label) for token in ("speed", "x0")):
            return "positive"
        if any(token in normalize(label) for token in ("queue", "occupancy", "x1")):
            return "negative"
    return label_category(label)


def predicted_direction(caption: str, slots: dict[str, Any]) -> tuple[str | None, str]:
    if "event_abs_z" in slots:
        text = normalize(caption)
        therefore = text.split("therefore", 1)[-1] if "therefore" in text else text
        if any(token in therefore for token in ("no pronounced", "no clear", "not pronounced", "weak")):
            return "similar", "anomaly_no_pronounced_phrase"
    if "first_mean" in slots and "second_mean" in slots:
        return half_category(*first_second_from_caption(caption)), "half_mean_numeric"
    if isinstance(slots.get("region_stds"), dict):
        return values_category(region_stds_from_caption(caption)), "region_std_numeric"
    if "extrema_index" in slots or ("event_abs_z" in slots and "event_index" in slots) or "controlled_event" in slots:
        horizon = horizon_from_caption(caption) or local_window_len(slots)
        return third_from_index(local_step_from_caption(caption) or -1, horizon), "local_step_third"
    if "corr_cpu_memory" in slots and "corr_net_rx_tx" in slots:
        left = extract_first(labeled_patterns([r"cpu[- ]memory correlation", r"cpu memory correlation"]), caption)
        right = extract_first(labeled_patterns([r"network receive/transmit correlation", r"network rx[- ]tx correlation", r"network receive.*?correlation"]), caption)
        return corr_pair_category(left, right, left_name="cpu_memory", right_name="network"), "correlation_pair_numeric"
    if "corr_x1" in slots and "corr_x2" in slots:
        x1 = extract_first(labeled_patterns([r"x1", r"correlation with x1"]), caption)
        x2 = extract_first(labeled_patterns([r"x2", r"correlation with x2"]), caption)
        return corr_pair_category(x1, x2, left_name="x1", right_name="x2"), "correlation_pair_numeric"
    if "best_lag" in slots and "best_lag_corr" in slots:
        lag = extract_first(labeled_patterns([r"strongest tested lag", r"best lag", r"lag"]), caption)
        if lag is None:
            return None, "lead_lag_numeric"
        return "similar" if int(round(lag)) == 0 else ("positive" if lag > 0 else "negative"), "lead_lag_numeric"
    if "factual_overload_exposure" in slots and "intervention_overload_exposure" in slots:
        diff = extract_first(labeled_patterns([r"intervention[- ]minus[- ]factual (?:difference|exposure)", r"difference"]), caption)
        if diff is None:
            factual = extract_first(labeled_patterns([r"factual overload exposure", r"factual exposure"]), caption)
            intervention = extract_first(labeled_patterns([r"intervention exposure", r"intervention overload exposure"]), caption)
            diff = None if factual is None or intervention is None else intervention - factual
        return sign_category(diff), "counterfactual_exposure_numeric"
    if "mean_x0_diff" in slots:
        diff = extract_first(labeled_patterns([r"mean intervention[- ]minus[- ]factual stress difference", r"mean difference"]), caption)
        return sign_category(diff), "mean_diff_numeric"
    if "max_x0_diff" in slots and "min_x0_diff" in slots:
        min_v = extract_first([rf"ranges?\s+from\s+({NUM})\s+to\s+{NUM}"], caption)
        max_v = extract_first([rf"ranges?\s+from\s+{NUM}\s+to\s+({NUM})"], caption)
        if min_v is None or max_v is None:
            return None, "range_diff_numeric"
        if min_v > 0 and max_v > 0:
            return "positive", "range_diff_numeric"
        if min_v < 0 and max_v < 0:
            return "negative", "range_diff_numeric"
        return "similar", "range_diff_numeric"
    if "event_gap" in slots:
        return sign_category(extract_first(labeled_patterns([r"gap"]), caption), tol=0.05), "event_gap_numeric"
    if "delta" in slots:
        return sign_category(extract_first(labeled_patterns([r"changes?", r"delta", r"gap"], [r"[^.\n]{0,30}(?:by|is)?"]), caption), tol=0.05), "delta_numeric"
    if "event_response_score_x0" in slots and "event_response_score_x1" in slots:
        x0 = extract_first(labeled_patterns([r"x0 event[- ]response score", r"x0 response score"]), caption)
        x1 = extract_first(labeled_patterns([r"x1 event[- ]response score", r"x1 response score"]), caption)
        if x0 is None or x1 is None:
            return None, "event_response_numeric"
        if max(abs(x0), abs(x1)) < 1.0:
            return "similar", "event_response_numeric"
        if abs(abs(x0) - abs(x1)) < 0.2:
            return "similar", "event_response_numeric"
        return "positive" if abs(x0) > abs(x1) else "negative", "event_response_numeric"

    text = normalize(caption)
    for label in [str(slots.get("answer_label") or ""), *option_labels({})]:
        if label and normalize(label) in text:
            return label_category(label), "label_phrase"
    label = str(slots.get("answer_label") or "")
    if label and normalize(label) in text:
        return label_category(label), "label_phrase"
    return None, "not_implemented"


def horizon_check(caption: str, slots: dict[str, Any]) -> tuple[bool | None, int | None, int | None]:
    expected = local_window_len(slots)
    found = horizon_from_caption(caption)
    if found is None:
        if task_family_from_slots(slots) in {"extrema", "anomaly", "controlled_event"}:
            return False, expected, None
        return None, expected, None
    if expected is None:
        return None, None, found
    return found == expected, expected, found


def audit_one(pred: dict[str, Any], gold: dict[str, Any], *, caption_field: str) -> dict[str, Any]:
    caption = str(pred.get(caption_field, ""))
    if not caption and caption_field in gold:
        caption = str(gold.get(caption_field, ""))
    slots = gold.get("support_slots") if isinstance(gold.get("support_slots"), dict) else {}
    numeric_results, slot_value_pass = evaluate_numeric_checks(caption, slots)
    expected = expected_direction(slots, gold)
    predicted, direction_rule = predicted_direction(caption, slots)
    direction_applicable = predicted is not None and expected not in {"", "cannot determine"}
    direction_pass = None if not direction_applicable else predicted == expected
    horizon_pass, expected_horizon, found_horizon = horizon_check(caption, slots)
    failures: list[str] = []
    if not slot_value_pass:
        failures.append("slot_value_mismatch")
    if direction_pass is False:
        failures.append("direction_mismatch")
    if horizon_pass is False:
        failures.append("horizon_mismatch")
    overall = slot_value_pass and (direction_pass is not False) and (horizon_pass is not False)
    return {
        "id": pred.get("id") or gold.get("id"),
        "split": str(gold.get("split", pred.get("split", ""))),
        "merge_source_name": source_name(gold),
        "task_family": str(gold.get("task_family", "")),
        "gold_answer": gold.get("answer") or pred.get("gold_answer"),
        "gold_answer_label": gold_label(gold),
        "caption": caption.strip(),
        "slot_value_checks": numeric_results,
        "slot_value_pass": slot_value_pass,
        "slot_value_pass_count": sum(1 for item in numeric_results if item["pass"]),
        "slot_value_check_count": len(numeric_results),
        "direction_rule": direction_rule,
        "expected_direction": expected,
        "predicted_direction": predicted,
        "direction_applicable": direction_applicable,
        "direction_pass": direction_pass,
        "expected_horizon": expected_horizon,
        "found_horizon": found_horizon,
        "horizon_applicable": horizon_pass is not None,
        "horizon_pass": horizon_pass,
        "overall_slot_factuality_pass": overall,
        "failure_reasons": failures,
    }


def rate(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(1 for row in rows if row.get(key)) / len(rows), 4) if rows else 0.0


def applicable_rate(rows: list[dict[str, Any]], key: str, applicable_key: str) -> float:
    subset = [row for row in rows if row.get(applicable_key)]
    return round(sum(1 for row in subset if row.get(key)) / len(subset), 4) if subset else 0.0


def summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_checks = sum(int(row.get("slot_value_check_count", 0)) for row in rows)
    passed_checks = sum(int(row.get("slot_value_pass_count", 0)) for row in rows)
    return {
        "n": len(rows),
        "slot_value_pass_rate": rate(rows, "slot_value_pass"),
        "slot_value_recall": round(passed_checks / total_checks, 4) if total_checks else 1.0,
        "direction_applicable_n": sum(1 for row in rows if row.get("direction_applicable")),
        "direction_pass_rate": applicable_rate(rows, "direction_pass", "direction_applicable"),
        "horizon_applicable_n": sum(1 for row in rows if row.get("horizon_applicable")),
        "horizon_pass_rate": applicable_rate(rows, "horizon_pass", "horizon_applicable"),
        "overall_slot_factuality_rate": rate(rows, "overall_slot_factuality_pass"),
        "failure_reasons": dict(Counter(reason for row in rows for reason in row.get("failure_reasons", []))),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_source[str(row["merge_source_name"])].append(row)
        by_task[str(row["task_family"])].append(row)
    return {
        **summarize_group(rows),
        "by_source": {key: summarize_group(items) for key, items in sorted(by_source.items())},
        "by_task_family": {key: summarize_group(items) for key, items in sorted(by_task.items())},
    }


def audit_rows(
    predictions: list[dict[str, Any]],
    gold_rows: list[dict[str, Any]],
    *,
    caption_field: str,
    splits: set[str] | None = None,
) -> list[dict[str, Any]]:
    gold_by_id = {str(row.get("id")): row for row in gold_rows}
    audited = []
    for pred in predictions:
        row_id = str(pred.get("id"))
        gold = gold_by_id.get(row_id)
        if not gold:
            continue
        if splits and str(gold.get("split", "")) not in splits:
            continue
        audited.append(audit_one(pred, gold, caption_field=caption_field))
    return audited


def markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Natural QCC Slot Factuality Audit（2026-05-20）",
        "",
        "本审计只检查 generated/target caption 是否和 deterministic support slots 对齐；它不让 LLM 判答案，也不替代 downstream QA。",
        "",
        f"- predictions: `{report['predictions_jsonl']}`",
        f"- gold: `{report['gold_jsonl']}`",
        f"- caption field: `{report['caption_field']}`",
        f"- rows: `{metrics['n']}`",
        f"- overall slot factuality: `{metrics['overall_slot_factuality_rate']:.4f}`",
        f"- slot value pass rate: `{metrics['slot_value_pass_rate']:.4f}`",
        f"- slot value recall: `{metrics['slot_value_recall']:.4f}`",
        f"- direction pass rate: `{metrics['direction_pass_rate']:.4f}`",
        f"- horizon pass rate: `{metrics['horizon_pass_rate']:.4f}`",
        "",
        "## By Source",
        "",
        "| source | n | overall | value pass | value recall | direction | horizon | failures |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for source, item in metrics["by_source"].items():
        lines.append(
            f"| `{source}` | {item['n']} | {item['overall_slot_factuality_rate']:.4f} | "
            f"{item['slot_value_pass_rate']:.4f} | {item['slot_value_recall']:.4f} | "
            f"{item['direction_pass_rate']:.4f} | {item['horizon_pass_rate']:.4f} | "
            f"`{item['failure_reasons']}` |"
        )
    lines.extend(
        [
            "",
            "## Main Failure Reasons",
            "",
            f"`{metrics['failure_reasons']}`",
            "",
            "## Guardrail",
            "",
            "如果 caption 形态 gate 通过但本审计低，说明模型学会了证据模板，但没有稳定从当前 trace 复制关键数值或方向。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions_jsonl", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--gold_jsonl", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--caption_field", default="pred_caption")
    parser.add_argument("--splits", nargs="*", default=None)
    args = parser.parse_args()

    predictions = load_jsonl(args.predictions_jsonl)
    gold_rows = load_jsonl(args.gold_jsonl)
    rows = audit_rows(predictions, gold_rows, caption_field=args.caption_field, splits=set(args.splits) if args.splits else None)
    report = {
        "predictions_jsonl": rel(args.predictions_jsonl),
        "gold_jsonl": rel(args.gold_jsonl),
        "caption_field": args.caption_field,
        "splits": args.splits,
        "metrics": summarize(rows),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.out.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    write_jsonl(args.out.with_suffix(".rows.jsonl"), rows)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if rows else 1)


if __name__ == "__main__":
    main()
