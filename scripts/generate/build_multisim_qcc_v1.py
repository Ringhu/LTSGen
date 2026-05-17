#!/usr/bin/env python3
"""Build the first all-domain MultiSim QCC training set.

This script merges existing Grid2Op, CityLearn, and FinRL broad semantic data
into one all-domain train/eval set and keeps per-domain heldout dev/test files
for separate evaluation. It does not introduce support slots into prompts.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


DOMAIN_CONFIG = {
    "grid2op": {
        "domain_dir": "grid2op_broad_v5_semantic_anchor",
        "prefix": "grid2op_broad_v5_semantic_anchor",
        "evaluator": "evaluate_grid2op_broad_predictions.py",
    },
    "citylearn": {
        "domain_dir": "citylearn_broad_semantic_v3_qual",
        "prefix": "citylearn_broad_semantic_v3_qual",
        "evaluator": "evaluate_citylearn_broad_predictions.py",
    },
    "finrl": {
        "domain_dir": "finrl_broad_mini_v1",
        "prefix": "finrl_broad_mini_v1",
        "evaluator": "evaluate_finrl_broad_predictions.py",
    },
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row.get("target_caption", row.get("output", "")),
        "meta": row.get("meta", {}),
    }


def rows_for(base_dir: Path, domain: str, split: str) -> list[dict[str, Any]]:
    cfg = DOMAIN_CONFIG[domain]
    path = base_dir / cfg["domain_dir"] / f"{cfg['prefix']}_{split}.jsonl"
    rows = load_jsonl(path)
    out: list[dict[str, Any]] = []
    for row in rows:
        new = dict(row)
        new["multisim_source_domain"] = domain
        meta = dict(new.get("meta") or {})
        meta["multisim_source_domain"] = domain
        meta["multisim_v1_evaluator"] = cfg["evaluator"]
        new["meta"] = meta
        out.append(new)
    return out


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [row["id"] for row in rows]
    prompts_with_support_slots = sum(
        1 for row in rows if "support slots" in str(row.get("prompt", "")).lower()
    )
    return {
        "n": len(rows),
        "duplicate_id_count": len(ids) - len(set(ids)),
        "prompt_support_slots_count": prompts_with_support_slots,
        "by_split": dict(Counter(row.get("split", "") for row in rows)),
        "by_multisim_source_domain": dict(Counter(row.get("multisim_source_domain", "") for row in rows)),
        "by_domain": dict(Counter(row.get("domain", "") for row in rows)),
        "by_task_family": dict(Counter(row.get("task_family", "") for row in rows)),
        "by_horizon": dict(Counter(str(row.get("horizon", "")) for row in rows)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_dir", default=".research/general-qcc-captioner-20260515")
    parser.add_argument("--out_dir", default=".research/general-qcc-captioner-20260515/multisim_qcc_v1")
    parser.add_argument("--run_name", default="multisim_qcc_v1")
    parser.add_argument("--domains", nargs="+", default=["grid2op", "citylearn", "finrl"])
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    unknown = sorted(set(args.domains) - set(DOMAIN_CONFIG))
    if unknown:
        raise ValueError(f"Unknown domains: {unknown}")

    base_dir = Path(args.base_dir)
    out_root = Path(args.out_dir)
    run_dir = out_root / args.run_name
    rng = random.Random(args.seed)

    train_rows: list[dict[str, Any]] = []
    eval_rows: list[dict[str, Any]] = []
    heldout_by_domain: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for domain in args.domains:
        train_rows.extend(rows_for(base_dir, domain, "train"))
        eval_rows.extend(rows_for(base_dir, domain, "dev"))
        heldout_by_domain[domain] = {
            "dev": rows_for(base_dir, domain, "dev"),
            "test": rows_for(base_dir, domain, "test"),
        }

    rng.shuffle(train_rows)
    rng.shuffle(eval_rows)

    write_jsonl(run_dir / f"{args.run_name}_train.jsonl", train_rows)
    write_jsonl(run_dir / f"{args.run_name}_train_sft.jsonl", [sft_row(row) for row in train_rows])
    write_jsonl(run_dir / f"{args.run_name}_eval_source_dev.jsonl", eval_rows)
    write_jsonl(run_dir / f"{args.run_name}_eval_source_dev_sft.jsonl", [sft_row(row) for row in eval_rows])

    heldout_all: list[dict[str, Any]] = []
    for domain, splits in heldout_by_domain.items():
        for split, rows in splits.items():
            write_jsonl(run_dir / f"{args.run_name}_heldout_{domain}_{split}.jsonl", rows)
            heldout_all.extend(rows)

    train_ids = {row["id"] for row in train_rows}
    eval_ids = {row["id"] for row in eval_rows}
    heldout_ids = {row["id"] for row in heldout_all}
    heldout_domains = {
        domain: {split: summarize(rows) for split, rows in splits.items()}
        for domain, splits in heldout_by_domain.items()
    }
    overlap = {
        "train_vs_eval_source": len(train_ids & eval_ids),
        "train_vs_heldout": len(train_ids & heldout_ids),
        "eval_source_vs_heldout": len(eval_ids & heldout_ids),
    }
    report = {
        "run_name": args.run_name,
        "base_dir": str(base_dir),
        "out_dir": str(run_dir),
        "domains": args.domains,
        "domain_config": {domain: DOMAIN_CONFIG[domain] for domain in args.domains},
        "train": summarize(train_rows),
        "eval_source_dev": summarize(eval_rows),
        "heldout_domains": heldout_domains,
        "id_overlap": overlap,
        "schema_gate_pass": bool(train_rows)
        and bool(eval_rows)
        and all(
            bool(heldout_by_domain[domain]["dev"]) and bool(heldout_by_domain[domain]["test"])
            for domain in args.domains
        )
        and summarize(train_rows)["duplicate_id_count"] == 0
        and summarize(eval_rows)["duplicate_id_count"] == 0
        and overlap["train_vs_heldout"] == 0
        and summarize(train_rows)["prompt_support_slots_count"] == 0,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "schema_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_root / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
