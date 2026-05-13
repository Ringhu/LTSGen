#!/usr/bin/env python3
"""Build deterministic paraphrase eval items for QCC-v0."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PARAPHRASES = {
    "rho_value_slot": [
        lambda f: f"Read line {f['slot_line']} rho at local step {f['slot_local_t']}.",
        lambda f: f"For line {f['slot_line']}, report rho when local_t equals {f['slot_local_t']}.",
    ],
    "load_average_value_slot": [
        lambda f: f"Across this window, what is the average load_p for load {f['slot_load']}?",
        lambda f: f"Compute mean active load_p for load {f['slot_load']} over the full trace window.",
    ],
    "generator_average_value_slot": [
        lambda f: f"Across the full window, what is average gen_p for generator {f['slot_generator']}?",
        lambda f: f"Compute the mean generator output gen_p for generator {f['slot_generator']} in this window.",
    ],
    "quarter_total_load_mean_value_slot": [
        lambda f: f"Average total_load over quarter {f['slot_quarter']} of the selected window.",
        lambda f: f"What is the quarter-{f['slot_quarter']} mean of total load in this Grid2Op window?",
    ],
    "cf_delta_max_rho_value_slot": [
        lambda f: f"At local step {f['slot_local_t']}, compute intervention max_rho minus factual max_rho.",
        lambda f: f"For local_t {f['slot_local_t']}, what is the delta between intervention and factual max_rho?",
    ],
    "cf_intervention_max_rho_value_slot": [
        lambda f: f"In the intervention trace, read max_rho at local step {f['slot_local_t']}.",
        lambda f: f"What is max_rho in the counterfactual rollout when local_t is {f['slot_local_t']}?",
    ],
    "building_load_value_slot": [
        lambda f: f"At local step {f['slot_local_t']}, read building {f['slot_building']} non_shiftable_load.",
        lambda f: f"For building {f['slot_building']}, what is non_shiftable_load at local_t {f['slot_local_t']}?",
    ],
    "quarter_net_electricity_mean_value_slot": [
        lambda f: f"Average net_electricity_without_storage over quarter {f['slot_quarter']} of this CityLearn window.",
        lambda f: f"What is the quarter-{f['slot_quarter']} mean net electricity without storage?",
    ],
    "outdoor_temperature_value_slot": [
        lambda f: f"Read outdoor dry-bulb temperature at local step {f['slot_local_t']}.",
        lambda f: f"What is the outdoor_dry_bulb_temperature when local_t is {f['slot_local_t']}?",
    ],
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_rows(rows: list[dict[str, Any]], *, source_split: str, variants: int) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        if row["split"] != source_split:
            continue
        templates = PARAPHRASES[row["task_family"]]
        for variant_idx, make_question in enumerate(templates[:variants]):
            new_row = dict(row)
            new_row["id"] = f"{row['id']}::paraphrase_v{variant_idx + 1}"
            new_row["source_id"] = row["id"]
            new_row["original_question"] = row["question"]
            new_row["question"] = make_question(row["target_fields"])
            new_row["input"] = {**row.get("input", {}), "question": new_row["question"]}
            new_row["split"] = f"{source_split}_paraphrase"
            new_row["paraphrase_variant"] = variant_idx + 1
            out.append(new_row)
    return out


def build_augmented_rows(
    rows: list[dict[str, Any]],
    *,
    splits: set[str],
    variants: int,
    include_original: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if include_original:
        for row in rows:
            if row["split"] not in splits:
                continue
            original = dict(row)
            original["source_id"] = row["id"]
            original["original_question"] = row["question"]
            original["paraphrase_variant"] = 0
            original["is_paraphrase"] = False
            out.append(original)
    for row in rows:
        if row["split"] not in splits:
            continue
        templates = PARAPHRASES[row["task_family"]]
        for variant_idx, make_question in enumerate(templates[:variants]):
            new_row = dict(row)
            new_row["id"] = f"{row['id']}::paraphrase_v{variant_idx + 1}"
            new_row["source_id"] = row["id"]
            new_row["original_question"] = row["question"]
            new_row["question"] = make_question(row["target_fields"])
            new_row["input"] = {**row.get("input", {}), "question": new_row["question"]}
            new_row["paraphrase_variant"] = variant_idx + 1
            new_row["is_paraphrase"] = True
            out.append(new_row)
    return out


def report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from collections import Counter

    return {
        "n_examples": len(rows),
        "by_task_family": dict(Counter(r["task_family"] for r in rows)),
        "by_domain": dict(Counter(r["domain"] for r in rows)),
        "by_split": dict(Counter(r["split"] for r in rows)),
        "missing_required_field_count": sum(
            1
            for r in rows
            for k in ("id", "source_id", "original_question", "question", "target_fields", "target_caption")
            if k not in r or r[k] in ("", [], {}, None)
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--source_split", default="dev")
    parser.add_argument("--splits", nargs="+", default=None)
    parser.add_argument("--variants", type=int, default=2)
    parser.add_argument("--output_name", default="qcc_v0_paraphrase_eval.jsonl")
    parser.add_argument("--augment", action="store_true")
    parser.add_argument("--include_original", action="store_true")
    args = parser.parse_args()

    source_rows = load_jsonl(Path(args.data))
    if args.augment:
        splits = set(args.splits or [args.source_split])
        rows = build_augmented_rows(
            source_rows,
            splits=splits,
            variants=args.variants,
            include_original=args.include_original,
        )
    else:
        rows = build_rows(source_rows, source_split=args.source_split, variants=args.variants)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / args.output_name, rows)
    rep = report(rows)
    (out_dir / "sanity_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rep, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
