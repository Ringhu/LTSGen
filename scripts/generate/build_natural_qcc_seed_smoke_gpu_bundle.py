#!/usr/bin/env python3
"""Build self-contained GPU-smoke JSONL files for the Natural QCC seed set."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED_DIR = (
    ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_seed_smoke_v1_20260521"
)
DEFAULT_OUT_DIR = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_seed_smoke_3090_20260521/gpu_bundle"
)


EN_OPTIONS_BY_ID = {
    "natural_qcc_quality_v2::grid2op::grid_counterfactual_overload_exposure": [
        "A. lower overload exposure",
        "B. similar overload exposure",
        "C. greater overload exposure",
        "D. insufficient evidence",
    ],
    "natural_qcc_quality_v2::grid2op::grid_domain_stress_context": [
        "A. high grid stress",
        "B. low grid stress",
        "C. moderate grid stress",
        "D. unclear grid stress",
    ],
    "natural_qcc_quality_v2::citylearn::city_domain_demand_context": [
        "A. moderate building demand pressure",
        "B. low building demand pressure",
        "C. high building demand pressure",
        "D. unclear demand pressure",
    ],
    "natural_qcc_quality_v2::citylearn::city_window_total_load": [
        "A. second half higher",
        "B. similar halves",
        "C. first half higher",
        "D. unclear priority",
    ],
    "natural_qcc_quality_v2::traffic::traffic_domain_congestion_context": [
        "A. severe congestion",
        "B. moderate congestion",
        "C. free-flow traffic",
        "D. unclear traffic state",
    ],
    "natural_qcc_quality_v2::traffic::traffic_event_recovery_context": [
        "A. traffic speed recovers",
        "B. persistent congestion",
        "C. traffic speed overshoots",
        "D. no event recovery evidence",
    ],
    "natural_qcc_quality_v2::water::water_domain_resilience_context": [
        "A. low-pressure risk",
        "B. leak-stressed network",
        "C. stable water service",
        "D. unclear hydraulic state",
    ],
    "natural_qcc_quality_v2::water::water_leak_counterfactual_pressure": [
        "A. leak lowers pressure",
        "B. leak raises pressure",
        "C. field review needed",
        "D. no material pressure change",
    ],
    "natural_qcc_quality_v2::aiopslab::aiops_official_cross_signal_relation": [
        "A. CPU-memory coupling",
        "B. similar coupling strength",
        "C. weak coupling in both pairs",
        "D. network rx-tx coupling",
    ],
    "natural_qcc_quality_v2::aiopslab::aiops_official_memory_extrema": [
        "A. middle",
        "B. early",
        "C. late",
        "D. no clear peak",
    ],
    "natural_qcc_quality_v2::finrl::fin_domain_market_regime": [
        "A. bullish trend",
        "B. volatile sideways regime",
        "C. bearish trend",
        "D. low-volatility sideways regime",
    ],
    "natural_qcc_quality_v2::finrl::fin_drawdown_price": [
        "A. severe drawdown",
        "B. moderate drawdown",
        "C. tiny drawdown",
        "D. mild drawdown",
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


def option_label_by_letter(options: list[str]) -> dict[str, str]:
    out = {}
    for option in options:
        if ". " in option:
            letter, label = option.split(". ", 1)
            out[letter.strip()] = label.strip()
    return out


def normalized_gold(row: dict[str, Any], *, split: str) -> dict[str, Any]:
    out = dict(row)
    out["source_split"] = row.get("split", "")
    out["split"] = split
    out["question"] = row.get("question") or row.get("question_zh") or ""
    out["options"] = row.get("options") or EN_OPTIONS_BY_ID.get(row.get("id", ""), row.get("options_zh") or [])
    out["option_label_by_letter"] = row.get("option_label_by_letter") or option_label_by_letter(out["options"])
    out["answer_label"] = row.get("answer_label") or out["option_label_by_letter"].get(row.get("answer", ""), "")
    out["target_caption"] = row.get("target_caption") or row.get("output") or row.get("oracle_evidence_caption") or ""
    out["output"] = out["target_caption"]
    return out


def training_row(sft_row: dict[str, Any], gold_row: dict[str, Any]) -> dict[str, Any]:
    out = dict(gold_row)
    meta = dict(gold_row.get("meta") or {})
    meta.update(
        {
            "merge_source_name": gold_row.get("merge_source_name", ""),
            "task_family": gold_row.get("task_family", ""),
            "source_split": gold_row.get("source_split", ""),
        }
    )
    out.update(
        {
            "id": sft_row["id"],
            "values": sft_row["values"],
            "prompt": sft_row["prompt"],
            "output": sft_row["output"],
            "target_caption": sft_row.get("target_caption") or sft_row["output"],
            "meta": meta,
        }
    )
    return out


def dim(row: dict[str, Any]) -> int:
    values = row.get("values") or []
    if not values:
        return 0
    first = values[0]
    return len(first) if isinstance(first, list) else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed_dir", type=Path, default=DEFAULT_SEED_DIR)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--split", default="test")
    args = parser.parse_args()

    seed_dir = args.seed_dir
    gold_rows = load_jsonl(seed_dir / "combined_seed_rows.jsonl")
    qcond_rows = load_jsonl(seed_dir / "combined_qcond_sft.jsonl")
    no_question_rows = load_jsonl(seed_dir / "combined_no_question_sft.jsonl")
    gold_by_id = {row["id"]: normalized_gold(row, split=args.split) for row in gold_rows}

    missing = [row["id"] for row in qcond_rows + no_question_rows if row["id"] not in gold_by_id]
    if missing:
        raise KeyError(f"SFT rows missing from gold: {missing[:5]}")

    qcond_out = [training_row(row, gold_by_id[row["id"]]) for row in qcond_rows]
    no_question_out = [training_row(row, gold_by_id[row["id"]]) for row in no_question_rows]
    gold_out = [gold_by_id[row["id"]] for row in gold_rows]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "seed_qcond_smoke.jsonl", qcond_out)
    write_jsonl(args.out_dir / "seed_no_question_smoke.jsonl", no_question_out)
    write_jsonl(args.out_dir / "seed_gold_smoke.jsonl", gold_out)

    summary = {
        "seed_dir": str(seed_dir),
        "out_dir": str(args.out_dir),
        "split_policy": f"all rows forced to {args.split} for overfit-style smoke evaluation",
        "n": len(gold_out),
        "qcond_n": len(qcond_out),
        "no_question_n": len(no_question_out),
        "by_domain": dict(Counter(row.get("merge_source_name", "unknown") for row in gold_out)),
        "value_dim_counts": dict(Counter(str(dim(row)) for row in gold_out)),
        "missing_english_options_filled": sum(1 for row in gold_rows if not row.get("options")),
        "missing_question_filled_from_zh": sum(1 for row in gold_rows if not row.get("question")),
    }
    (args.out_dir / "seed_gpu_smoke_bundle_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
