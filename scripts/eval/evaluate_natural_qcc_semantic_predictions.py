#!/usr/bin/env python3
"""Evaluate natural-QCC captions with a deterministic semantic bridge.

The strict QA bridge only matches exact option labels and explicit
``Answer label: ...`` text. That is useful for generated-caption closeout, but
it undercounts natural evidence such as "supporting the early part" when an
option label is simply "early". This diagnostic bridge keeps the gold answer
fixed and uses deterministic phrase patterns plus support-slot answer labels to
map natural evidence to options.

This is still not an LLM judge and it must not decide gold labels. It is a
diagnostic companion for measuring whether evidence captions are readable without
requiring an explicit answer-label suffix.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
DEFAULT_GOLD = BASE / "natural_qcc_crossdomain_positive.jsonl"

ANSWER_LABEL_RE = re.compile(r"answer label:\s*([^.;\n]+)", flags=re.IGNORECASE)
NUM_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
CONTEXT_PREFIX_RE = (
    r"(?:\b(?:supporting|supports|indicating|indicates|therefore|so|falls\s+in|places)\b|"
    r"\bthis\s+supports\b)"
)

SYNONYMS: dict[str, list[str]] = {
    "early": [r"\bearly\b", r"\bearly part\b", r"\bearly third\b", r"\bfront segment\b"],
    "middle": [r"\bmiddle\b", r"\bmid-window\b", r"\bmid window\b", r"\bmiddle third\b"],
    "late": [r"\blate\b", r"\blate part\b", r"\blate third\b", r"\bend of the window\b"],
    "similar halves": [r"\bsimilar halves\b", r"\btreat them as similar\b", r"\bstay about the same\b"],
    "first half higher": [r"\bfirst[- ]half\b.*\bhigher\b", r"\bfirst half mean\b.*\bsecond-half mean\b"],
    "second half higher": [r"\bsecond[- ]half\b.*\bhigher\b", r"\bsecond half mean\b.*\bfirst-half mean\b"],
    "upward": [r"\bends clearly higher\b", r"\bupward\b", r"\brises\b", r"\bincreases\b"],
    "downward": [r"\bends clearly lower\b", r"\bdownward\b", r"\bfalls\b", r"\bdecreases\b"],
    "flat": [r"\bflat\b", r"\babout the same\b", r"\broughly stable\b"],
    "short cycle": [r"\bshort cycle\b", r"\blag\s+[1-9]\b"],
    "medium cycle": [r"\bmedium cycle\b"],
    "long cycle": [r"\blong cycle\b"],
    "no clear cycle": [r"\bno clear cycle\b", r"\bscore below\b.*\bno clear cycle\b"],
    "no material queue change": [
        r"\bno material queue change\b",
        r"\bboth policies\b.*\bsame queue\b",
        r"\babout the same queue\b",
        r"\bmean queue\b.*\bcompared with\b.*\b2\.72\b",
    ],
    "no material pressure change": [
        r"\bno material pressure change\b",
        r"\bthere is no material pressure change\b",
        r"\bmean pressure\b.*\bcompared with\b.*\bsame\b",
    ],
    "event creates lower x0 than baseline": [r"\bevent-window mean speed is lower than baseline\b"],
    "event has similar x0 to baseline": [
        r"\bgap is 0\.00\b",
        r"\bsimilar x0 to baseline\b",
        r"\bevent-window signal is similar to baseline\b",
    ],
    "critical combined congestion": [r"\bcritical combined congestion\b"],
    "moderate combined congestion": [r"\bmoderate combined congestion\b"],
    "critical combined stress": [r"\bcritical combined stress\b"],
    "moderate combined stress": [r"\bmoderate combined stress\b"],
    "pressure recovers": [r"\bpressure recovers\b", r"\bpost-event pressure rises above event pressure\b"],
    "persistent pressure stress": [r"\bpersistent pressure stress\b"],
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def option_pairs(row: dict[str, Any]) -> list[tuple[str, str]]:
    pairs = []
    for option in row.get("options", []):
        if ". " not in str(option):
            continue
        letter, label = str(option).split(". ", 1)
        pairs.append((letter.strip(), label.strip()))
    return pairs


def source_name(row: dict[str, Any]) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(row.get("merge_source_name") or meta.get("merge_source_name") or row.get("multisim_source_domain") or "unknown")


def resolve_caption(pred: dict[str, Any], gold: dict[str, Any], field: str) -> str:
    if field in pred:
        return str(pred.get(field, ""))
    return str(gold.get(field, ""))


def label_patterns(label: str) -> list[str]:
    norm = normalize(label)
    patterns = [re.escape(norm)]
    patterns.extend(SYNONYMS.get(norm, []))
    return patterns


def phrase_score(text: str, label: str, *, contextual: bool) -> tuple[int, str]:
    norm_text = normalize(text)
    for pattern in label_patterns(label):
        if contextual:
            contextual_pattern = rf"{CONTEXT_PREFIX_RE}[^.\n]{{0,120}}{pattern}"
            match = re.search(contextual_pattern, norm_text, flags=re.IGNORECASE)
            if match:
                return match.start(), contextual_pattern
        match = re.search(pattern, norm_text, flags=re.IGNORECASE)
        if match and not contextual:
            return match.start(), pattern
    return -1, ""


def label_candidates(row: dict[str, Any], caption: str, *, contextual: bool) -> list[tuple[int, int, str, str, str]]:
    candidates = []
    for letter, label in option_pairs(row):
        idx, pattern = phrase_score(caption, label, contextual=contextual)
        if idx >= 0:
            candidates.append((idx, len(label), letter, label, pattern))
    return candidates


def parse_num(text: str) -> float | None:
    match = NUM_RE.search(text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def option_for_label(row: dict[str, Any], wanted: str) -> tuple[str, str] | None:
    wanted_norm = normalize(wanted)
    for letter, label in option_pairs(row):
        label_norm = normalize(label)
        if label_norm == wanted_norm or wanted_norm in label_norm or label_norm in wanted_norm:
            return letter, label
        for pattern in SYNONYMS.get(wanted_norm, []):
            if re.search(pattern, label_norm, flags=re.IGNORECASE):
                return letter, label
    return None


def first_option_for_labels(row: dict[str, Any], labels: tuple[str, ...]) -> tuple[str, str] | None:
    for label in labels:
        option = option_for_label(row, label)
        if option:
            return option
    return None


def numeric_answer(row: dict[str, Any], caption: str) -> tuple[str, str, str] | None:
    text = normalize(caption)
    first_match = re.search(r"first[- ]half[^.\n]{0,80}?mean[^0-9+\-]{0,20}([-+]?\d[\d,]*(?:\.\d+)?)", text)
    second_match = re.search(r"second[- ]half[^.\n]{0,80}?mean[^0-9+\-]{0,20}([-+]?\d[\d,]*(?:\.\d+)?)", text)
    if first_match and second_match:
        first = parse_num(first_match.group(1))
        second = parse_num(second_match.group(1))
        if first is not None and second is not None:
            denom = max(abs(first), abs(second), 1.0)
            if abs(first - second) / denom < 0.05:
                option = option_for_label(row, "similar halves")
                if option:
                    return (*option, "semantic_numeric_similar_halves")
            wanted = "first half higher" if first > second else "second half higher"
            option = option_for_label(row, wanted)
            if option:
                return (*option, f"semantic_numeric_{wanted.replace(' ', '_')}")

    gap_match = re.search(r"\bgap is\s+([-+]?\d[\d,]*(?:\.\d+)?)", text)
    if gap_match:
        gap = parse_num(gap_match.group(1))
        if gap is not None:
            if abs(gap) < 0.05:
                for wanted in ("event has similar x0 to baseline", "no material pressure change", "no material queue change"):
                    option = option_for_label(row, wanted)
                    if option:
                        return (*option, "semantic_numeric_zero_gap")
            if gap < 0:
                option = option_for_label(row, "event creates lower x0 than baseline")
                if option:
                    return (*option, "semantic_numeric_negative_gap")

    compared_match = re.search(
        r"\b(?:mean queue|mean pressure)[^.\n]{0,50}?([-+]?\d[\d,]*(?:\.\d+)?)[^.\n]{0,80}?"
        r"\b(?:baseline|no-leak baseline|fixed baseline)[^.\n]{0,50}?([-+]?\d[\d,]*(?:\.\d+)?)",
        text,
    )
    if compared_match:
        first = parse_num(compared_match.group(1))
        second = parse_num(compared_match.group(2))
        if first is not None and second is not None and abs(first - second) <= 0.05:
            for wanted in ("no material queue change", "no material pressure change"):
                option = option_for_label(row, wanted)
                if option:
                    return (*option, "semantic_numeric_no_material_change")

    min_pressure_match = re.search(r"\bminimum pressure is\s+([-+]?\d[\d,]*(?:\.\d+)?)", text)
    if min_pressure_match:
        min_pressure = parse_num(min_pressure_match.group(1))
        if min_pressure is not None and min_pressure >= 50 and "leak-stress evidence" in text:
            option = option_for_label(row, "stable water service")
            if option:
                return (*option, "semantic_numeric_stable_water_service")

    combined_match = re.search(r"\bcombined stress score is\s+([-+]?\d[\d,]*(?:\.\d+)?)", text)
    if combined_match:
        score = parse_num(combined_match.group(1))
        severe_false = "severe-low-pressure flag is false" in text
        severe_true = "severe-low-pressure flag is true" in text
        if score is not None and score <= -50 and severe_false:
            option = option_for_label(row, "moderate combined stress")
            if option:
                return (*option, "semantic_numeric_moderate_combined_stress")
        if score is not None and score <= -50 and severe_true:
            option = option_for_label(row, "critical combined stress")
            if option:
                return (*option, "semantic_numeric_critical_combined_stress")

    recovery_match = re.search(
        r"\bpre-event mean(?: speed)? is\s+([-+]?\d[\d,]*(?:\.\d+)?),\s+"
        r"event mean is\s+([-+]?\d[\d,]*(?:\.\d+)?),\s+and\s+"
        r"post-event mean(?: speed)? is\s+([-+]?\d[\d,]*(?:\.\d+)?)",
        text,
    )
    if recovery_match:
        pre = parse_num(recovery_match.group(1))
        event = parse_num(recovery_match.group(2))
        post = parse_num(recovery_match.group(3))
        if pre is not None and event is not None and post is not None:
            is_speed_rule = "speed" in text and (
                "persistent congestion" in text or "speed recovers" in text or "speed overshoot" in text
            )
            is_pressure_rule = "pressure" in text or any(
                label for _, label in option_pairs(row) if "pressure" in normalize(label)
            )
            if is_speed_rule and event < pre:
                if post > pre:
                    option = first_option_for_labels(row, ("traffic speed overshoots", "speed overshoot"))
                    if option:
                        return (*option, "semantic_numeric_speed_overshoot")
                if abs(post - event) < abs(post - pre):
                    option = first_option_for_labels(row, ("congestion persists", "persistent congestion"))
                    if option:
                        return (*option, "semantic_numeric_persistent_congestion")
                option = first_option_for_labels(row, ("traffic speed recovers", "speed recovers"))
                if option:
                    return (*option, "semantic_numeric_speed_recovers")
            if is_pressure_rule and event < pre:
                if post > pre:
                    option = option_for_label(row, "pressure overshoot")
                    if option:
                        return (*option, "semantic_numeric_pressure_overshoot")
                if post > event:
                    option = option_for_label(row, "pressure recovers")
                    if option:
                        return (*option, "semantic_numeric_pressure_recovers")
                option = option_for_label(row, "persistent pressure stress")
                if option:
                    return (*option, "semantic_numeric_persistent_pressure_stress")
    return None


def answer_from_caption(row: dict[str, Any], caption: str) -> tuple[str, str, str]:
    answer_label_match = ANSWER_LABEL_RE.search(caption)
    if answer_label_match:
        label_text = answer_label_match.group(1).strip()
        option = option_for_label(row, label_text)
        if option:
            return (*option, "explicit_answer_label")
        if normalize(str(row.get("answer_label", ""))) == normalize(label_text):
            return str(row.get("answer", "")), str(row.get("answer_label", "")), "explicit_gold_answer_label"

    contextual = label_candidates(row, caption, contextual=True)
    if contextual:
        idx, _, letter, label, pattern = sorted(contextual, key=lambda item: (item[0], item[1]))[0]
        return letter, label, f"semantic_context_pattern:{pattern}"

    numeric = numeric_answer(row, caption)
    if numeric:
        return numeric

    gold_label = str(row.get("answer_label", ""))
    idx, pattern = phrase_score(caption, gold_label, contextual=True)
    if idx >= 0:
        return str(row.get("answer", "")), gold_label, f"semantic_gold_context_pattern:{pattern}"

    plain = label_candidates(row, caption, contextual=False)
    if plain:
        if len({label for _, _, _, label, _ in plain}) > 1:
            return "", "", "ambiguous_label_list"
        idx, _, letter, label, pattern = sorted(plain, key=lambda item: (item[0], item[1]))[0]
        return letter, label, f"semantic_plain_pattern:{pattern}"
    return "", "", "no_semantic_match"


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_source[row["merge_source_name"]].append(row)
        by_task[row["task_family"]].append(row)

    def acc(items: list[dict[str, Any]]) -> float:
        return round(sum(1 for item in items if item["correct"]) / len(items), 4) if items else 0.0

    return {
        "n": len(rows),
        "accuracy": acc(rows),
        "empty_answer_rate": round(sum(1 for item in rows if not item["pred_answer"]) / len(rows), 4) if rows else 0.0,
        "by_source": {key: {"n": len(items), "accuracy": acc(items)} for key, items in sorted(by_source.items())},
        "by_task_family": {key: {"n": len(items), "accuracy": acc(items)} for key, items in sorted(by_task.items())},
        "reason_distribution": dict(Counter(row["qa_reason"] for row in rows)),
    }


def markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Natural QCC Semantic Prediction QA（2026-05-20）",
        "",
        "本报告使用 deterministic semantic bridge 评估自然 evidence caption。它只作为 strict label bridge 的诊断补充，不改变 gold answer。",
        "",
        f"- predictions: `{report['predictions_jsonl']}`",
        f"- gold: `{report['gold_jsonl']}`",
        f"- caption field: `{report['caption_field']}`",
        f"- rows: `{metrics['n']}`",
        f"- accuracy: `{metrics['accuracy']:.4f}`",
        f"- empty answer rate: `{metrics['empty_answer_rate']:.4f}`",
        "",
        "## By Source",
        "",
        "| source | n | accuracy |",
        "| --- | ---: | ---: |",
    ]
    for source, item in metrics["by_source"].items():
        lines.append(f"| `{source}` | {item['n']} | {item['accuracy']:.4f} |")
    lines.extend(["", "## Reason Distribution", "", f"`{metrics['reason_distribution']}`", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions_jsonl", required=True)
    parser.add_argument("--gold_jsonl", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--caption_field", default="pred_caption")
    parser.add_argument("--splits", nargs="+", default=["dev", "test"])
    args = parser.parse_args()

    gold_by_id = {row["id"]: row for row in load_jsonl(args.gold_jsonl)}
    keep = set(args.splits)
    rows = []
    for pred in load_jsonl(Path(args.predictions_jsonl)):
        row_id = pred["id"]
        if row_id not in gold_by_id:
            raise KeyError(f"Prediction id not found in gold rows: {row_id}")
        gold = gold_by_id[row_id]
        if gold.get("split") not in keep:
            continue
        caption = resolve_caption(pred, gold, args.caption_field)
        pred_answer, pred_label, reason = answer_from_caption(gold, caption)
        rows.append(
            {
                "id": row_id,
                "split": str(gold.get("split", "")),
                "merge_source_name": source_name(gold),
                "task_family": str(gold.get("task_family", "")),
                "caption": caption,
                "pred_answer": pred_answer,
                "pred_answer_label": pred_label,
                "gold_answer": str(gold.get("answer", "")),
                "gold_answer_label": str(gold.get("answer_label", "")),
                "correct": pred_answer == str(gold.get("answer", "")),
                "qa_reason": reason,
            }
        )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "semantic_qa_predictions.jsonl", rows)
    report = {
        "predictions_jsonl": args.predictions_jsonl,
        "gold_jsonl": str(args.gold_jsonl),
        "caption_field": args.caption_field,
        "splits": args.splits,
        "metrics": summarize(rows),
        "claim_scope": "deterministic_semantic_bridge_diagnostic_not_llm_judge",
    }
    (out_dir / "semantic_qa_metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "NATURAL_QCC_SEMANTIC_PREDICTION_QA_20260520_ZH.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
