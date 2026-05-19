#!/usr/bin/env python3
"""Add non-leaking background and task-rule context to MultiSim QCC questions.

The repair keeps the QCC target as natural-language evidence. It does not add
support-slot values to the question, because those values are answer evidence.
Instead it adds the variable meanings and the deterministic rule needed to
understand what the question is asking.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


BASE_PROMPT = (
    "You are a question-conditioned time-series evidence captioner. Given the "
    "time series and the clarified question context, write one or two concise "
    "natural-language sentences containing only the evidence needed to answer "
    "the question. Do not choose an answer option, do not write an option "
    "letter, and do not output JSON."
)


DOMAIN_BACKGROUNDS = {
    "grid2op": (
        "This is a Grid2Op power-grid window. x0 is maximum line-loading stress "
        "over grid lines, x1 is total demand, and x2 is generation margin. A "
        "line-loading stress value above 1.0 means overload."
    ),
    "citylearn": (
        "This is a CityLearn building-energy window. x0 is total building load, "
        "x1 is an outdoor/weather support signal, and x2 is solar-generation "
        "support. Higher x0 means higher building demand."
    ),
    "finrl": (
        "This is a financial-market window for the ticker named in the "
        "question. x0 is the target price or return-derived signal, and the "
        "task may also use returns, volume, drawdown, or regime evidence."
    ),
    "water": (
        "This is a water-network simulation window. x0 is water pressure, x1 is "
        "pipe flow, and x2 is tank storage. Low pressure can indicate service "
        "risk; unusually high flow can indicate disruption or leak-like stress."
    ),
    "traffic": (
        "This is a traffic simulation window. x0 is mean traffic speed, x1 is "
        "queue length, and x2 is lane occupancy. Lower speed and higher queue "
        "or occupancy indicate congestion."
    ),
    "aiops": (
        "This is an AIOpsLab microservice telemetry case. Numeric channels "
        "usually include service CPU load, memory working set, network receive "
        "rate, and network transmit rate. Application, service, fault-family, "
        "and provenance questions require official case metadata rather than "
        "inference from numeric telemetry alone."
    ),
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def field(row: dict[str, Any], key: str, default: Any = "") -> Any:
    if row.get(key) not in (None, ""):
        return row[key]
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return meta.get(key, default)


def infer_source(row: dict[str, Any]) -> str:
    text = " ".join(
        str(field(row, key, ""))
        for key in ("merge_source_name", "multisim_source_domain", "domain", "task_family", "id")
    ).lower()
    if "grid2op" in text or text.startswith("grid"):
        return "grid2op"
    if "citylearn" in text or "city_" in text:
        return "citylearn"
    if "finrl" in text or "fin_" in text:
        return "finrl"
    if "water" in text:
        return "water"
    if "traffic" in text:
        return "traffic"
    if "aiops" in text:
        return "aiops"
    return "unknown"


def primitive_from_task(task_family: str) -> str:
    task = task_family.lower()
    if "trend" in task:
        return "trend"
    if "extrema" in task or "peak" in task:
        return "extrema"
    if "volatility" in task or "drawdown" in task:
        return "volatility"
    if "anomaly" in task:
        return "anomaly"
    if "periodicity" in task:
        return "periodicity"
    if "window" in task:
        return "window_comparison"
    if "cross" in task or "relation" in task or "coupling" in task:
        return "cross_variable_relation"
    if "lead_lag" in task or "lead-lag" in task:
        return "lead_lag"
    if "event_gap" in task:
        return "counterfactual_event_gap"
    if "counterfactual" in task:
        return "counterfactual_effect"
    if "event_recovery" in task:
        return "event_recovery"
    if "event_impact" in task:
        return "event_impact"
    if "domain" in task or "context" in task or "regime" in task or "stress" in task:
        return "domain_context"
    return "unknown"


def primitive(row: dict[str, Any]) -> str:
    value = field(row, "abstract_primitive", "")
    if isinstance(value, str) and value:
        return value
    return primitive_from_task(str(field(row, "task_family", "")))


def task_rule(row: dict[str, Any], source: str, prim: str) -> tuple[str, str]:
    """Return a non-leaking task rule and a status tag."""
    task = str(field(row, "task_family", "")).lower()

    if source == "aiops" and any(
        key in task
        for key in (
            "app_context",
            "service_role_context",
            "case_provenance_context",
            "fault_context",
            "faulty_service_context",
            "fault_family",
            "fault_layer",
        )
    ):
        return (
            "This is a metadata-context task. It is not answerable from the "
            "numeric time series alone; the official case metadata field named "
            "by the question must be provided or this row should be excluded "
            "from pure time-series grounding evaluation.",
            "needs_metadata_context",
        )

    if source == "grid2op" and "counterfactual_overload" in task:
        return (
            "Counterfactual rule: compare the factual rollout with the "
            "intervention rollout after the event. Overload exposure is the "
            "fraction of post-event steps where maximum line-loading stress x0 "
            "is above 1.0. Decide whether that fraction is greater, lower, or "
            "similar under intervention.",
            "repaired",
        )
    if source == "grid2op" and "counterfactual_peak" in task:
        return (
            "Counterfactual rule: the trace describes intervention-minus-factual "
            "post-event stress. Positive deviations mean the intervention raises "
            "stress; negative deviations mean it lowers stress. Classify the "
            "strongest deviation as upward peak, downward dip, or no material "
            "change.",
            "repaired",
        )
    if source == "grid2op" and "counterfactual_mean" in task:
        return (
            "Counterfactual rule: average the post-event intervention-minus-"
            "factual x0 differences. Positive mean means higher after "
            "intervention, negative mean means lower after intervention, and a "
            "near-zero mean means no material change.",
            "repaired",
        )

    if prim == "trend":
        return (
            "Trend rule: compare the start and end of the named signal. Treat "
            "the trend as flat when the net change is small relative to window "
            "variability; otherwise classify it as upward or downward.",
            "repaired",
        )
    if prim == "extrema":
        return (
            "Extrema rule: split the window into first, middle, and final "
            "thirds, then locate where the named signal reaches the requested "
            "highest or lowest point.",
            "repaired",
        )
    if prim == "volatility":
        return (
            "Volatility rule: split the window into first, middle, and final "
            "thirds, compute the variability of the named signal in each third, "
            "and choose the third with the largest variability. Use similar "
            "thirds only when the three variability levels are close.",
            "repaired",
        )
    if prim == "anomaly":
        return (
            "Anomaly rule: look for the strongest isolated simulator event or "
            "spike in the named signal. Report whether it is in the first, "
            "middle, or final third, or say no pronounced event if no isolated "
            "event dominates.",
            "repaired",
        )
    if prim == "periodicity":
        return (
            "Periodicity rule: use the strongest autocorrelation peak. If its "
            "score is below the predefined weak-cycle threshold, answer no "
            "clear cycle. Otherwise classify the peak lag relative to the "
            "window length as short, medium, or long.",
            "repaired",
        )
    if prim == "window_comparison":
        return (
            "Window-comparison rule: compare the first-half mean and second-half "
            "mean of the named signal. Use similar halves only when the means "
            "are close.",
            "repaired",
        )
    if prim == "cross_variable_relation":
        return (
            "Cross-variable rule: compare absolute correlations between the "
            "target signal and each companion signal. Use both weak when both "
            "correlations are small, and both similar when the correlations are "
            "close.",
            "repaired",
        )
    if prim == "lead_lag":
        return (
            "Lead-lag rule: compare lagged correlation with zero-lag correlation. "
            "Positive lag means x0 leads x1; negative lag means x1 leads x0. "
            "If the best lagged correlation is not meaningfully stronger than "
            "zero lag, answer no clear lead.",
            "repaired",
        )
    if prim == "counterfactual_effect":
        return (
            "Counterfactual rule: compare the factual simulator trace with the "
            "matched baseline or intervention trace for the named quantity. "
            "Use the direction and size of the mean difference to decide lower, "
            "higher, no material change, or mixed effect.",
            "repaired",
        )
    if prim == "counterfactual_event_gap":
        return (
            "Event-gap rule: inside the event window, compare factual x0 with "
            "the matched baseline x0. A small gap means similar to baseline; a "
            "large positive or negative gap determines the effect direction.",
            "repaired",
        )
    if prim == "event_impact":
        return (
            "Event-impact rule: inside the simulator event window, compare the "
            "event-window change score for x0 with the change score for x1. The "
            "larger score identifies which stress signal changed more strongly.",
            "repaired",
        )
    if prim == "event_recovery":
        return (
            "Event-recovery rule: compare pre-event, event-window, and post-event "
            "means of the primary stress signal. Recovery means post-event moves "
            "back toward pre-event; persistent stress stays displaced; overshoot "
            "moves past the pre-event level.",
            "repaired",
        )
    if prim == "domain_context":
        if source == "water":
            return (
                "Water-context rule: use event presence, mean pressure, minimum "
                "pressure, and mean flow to classify leak stress, low-pressure "
                "risk, stable service, or unclear hydraulic state.",
                "repaired",
            )
        if source == "traffic":
            return (
                "Traffic-context rule: use mean speed, maximum queue, lane "
                "occupancy, and event presence to classify severe congestion, "
                "moderate congestion, free-flow traffic, or unclear state.",
                "repaired",
            )
        if source == "aiops":
            return (
                "AIOps-context rule: use latency, error rate, throughput, and "
                "official incident metadata to classify service condition. "
                "Numeric telemetry alone is not enough for metadata-only labels.",
                "needs_metadata_context",
            )
        return (
            "Domain-context rule: use the domain-specific operational state "
            "variables named in the question and evidence caption. This row "
            "should expose the decision thresholds before paper-facing use.",
            "weak_rule",
        )

    return (
        "Task rule missing: this task family needs an explicit non-leaking rule "
        "before it is used as a paper-facing QCC question.",
        "missing_rule",
    )


def compose_question(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    source = infer_source(row)
    prim = primitive(row)
    background = DOMAIN_BACKGROUNDS.get(
        source,
        "This is a simulator-derived time-series QA row. The variable meanings must be stated before paper-facing use.",
    )
    rule, status = task_rule(row, source, prim)
    original = str(field(row, "question_core", "") or field(row, "question", "")).strip()
    repaired = f"Background: {background} Task rule: {rule} Specific question: {original}"
    info = {
        "source": source,
        "abstract_primitive": prim,
        "status": status,
        "original_question": original,
        "domain_background": background,
        "task_rule": rule,
    }
    return repaired, info


def replace_prompt_question(prompt: str, repaired_question: str) -> str:
    if not prompt:
        return f"{BASE_PROMPT}\nQuestion: {repaired_question}"
    if "Question:" in prompt:
        prefix = prompt.split("Question:", 1)[0].rstrip()
        return f"{prefix}\nQuestion: {repaired_question}"
    return f"{prompt.rstrip()}\nQuestion: {repaired_question}"


def repair_row(row: dict[str, Any]) -> dict[str, Any]:
    repaired_question, info = compose_question(row)
    out = dict(row)
    out["question_core"] = info["original_question"]
    out["question"] = repaired_question
    out["question_context"] = info["domain_background"]
    out["question_task_rule"] = info["task_rule"]
    out["question_repair_status"] = info["status"]
    if "prompt" in out:
        out["prompt"] = replace_prompt_question(str(out.get("prompt", "")), repaired_question)
    meta = dict(out.get("meta") or {})
    meta["question_core"] = info["original_question"]
    meta["question"] = repaired_question
    meta["question_context"] = info["domain_background"]
    meta["question_task_rule"] = info["task_rule"]
    meta["question_repair_status"] = info["status"]
    out["meta"] = meta
    return out


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "values": row.get("values", []),
        "prompt": row.get("prompt", ""),
        "output": row.get("output") or row.get("target_caption") or row.get("oracle_evidence_caption") or "",
        "target_caption": row.get("target_caption", row.get("oracle_evidence_caption", "")),
        "meta": row.get("meta", {}),
    }


def numeric_tokens_from_support(row: dict[str, Any]) -> set[str]:
    slots = row.get("support_slots") if isinstance(row.get("support_slots"), dict) else {}
    if not slots and isinstance(row.get("meta"), dict):
        slots = row["meta"].get("support_slots") if isinstance(row["meta"].get("support_slots"), dict) else {}
    out: set[str] = set()
    for key, value in slots.items():
        if key in {"window_start", "window_end", "event_index"}:
            continue
        if isinstance(value, (int, float)) and abs(float(value)) not in {0.0, 1.0}:
            out.add(f"{float(value):.2f}")
            out.add(f"{float(value):.3f}")
    return out


def audit_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(row.get("question_repair_status", "")) for row in rows)
    by_source = Counter(str((row.get("meta") or {}).get("merge_source_name") or row.get("merge_source_name") or infer_source(row)) for row in rows)
    missing_context = []
    support_value_leaks = []
    for row in rows:
        q = str(row.get("question", ""))
        if "Background:" not in q or "Task rule:" not in q or "Specific question:" not in q:
            missing_context.append(row.get("id", "?"))
        lowered = q.lower()
        for token in numeric_tokens_from_support(row):
            if token in lowered:
                support_value_leaks.append({"id": row.get("id", "?"), "token": token})
                break
    return {
        "n": len(rows),
        "by_source": dict(by_source),
        "by_repair_status": dict(statuses),
        "missing_context_count": len(missing_context),
        "missing_context_examples": missing_context[:20],
        "support_slot_numeric_leak_count": len(support_value_leaks),
        "support_slot_numeric_leak_examples": support_value_leaks[:20],
        "clarity_gate_pass": bool(rows)
        and not missing_context
        and not support_value_leaks
        and statuses.get("missing_rule", 0) == 0,
        "metadata_context_rows": statuses.get("needs_metadata_context", 0),
        "weak_rule_rows": statuses.get("weak_rule", 0),
        "note": (
            "metadata_context_rows are intentionally flagged: those rows need "
            "metadata injected into the prompt or exclusion from pure TS "
            "grounding evaluation."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input JSONL with MultiSim rows or prediction rows.")
    parser.add_argument("--output", required=True, help="Output JSONL with repaired questions.")
    parser.add_argument("--report", required=True, help="Audit report JSON path.")
    parser.add_argument("--sft_output", default="", help="Optional repaired SFT JSONL output path.")
    parser.add_argument("--max_rows", type=int, default=0, help="Optional cap for quick review/smoke artifacts.")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    if args.max_rows:
        rows = rows[: args.max_rows]
    repaired = [repair_row(row) for row in rows]
    write_jsonl(Path(args.output), repaired)
    if args.sft_output:
        write_jsonl(Path(args.sft_output), [sft_row(row) for row in repaired])
    report = audit_rows(repaired)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
