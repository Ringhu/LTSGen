#!/usr/bin/env python3
"""Smoke-test MultiSim-v5 SFT loading, channel padding, and grouped batches."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from transformers import AutoTokenizer

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tslm"))
sys.path.insert(0, str(ROOT / "tslm" / "scripts"))

from train_multisim_v5_smoke import MultiSimV5Collator  # noqa: E402
from tsrlm.data.dataset import TSSFTDataset  # noqa: E402
from tsrlm.data.sampler import inspect_grouped_batches  # noqa: E402


def value_dim(row: dict[str, Any]) -> int:
    values = row.get("values", [])
    if not values:
        return 0
    first = values[0]
    return len(first) if isinstance(first, list) else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_jsonl", required=True)
    parser.add_argument("--eval_jsonl", required=True)
    parser.add_argument("--tokenizer", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--target_num_vars", type=int, default=4)
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--max_samples", type=int, default=256)
    parser.add_argument("--group_key", default="merge_source_name")
    parser.add_argument("--trust_remote_code", action="store_true")
    args = parser.parse_args()

    train_ds = TSSFTDataset(args.train_jsonl, max_samples=args.max_samples)
    eval_ds = TSSFTDataset(args.eval_jsonl, max_samples=args.max_samples)
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, trust_remote_code=args.trust_remote_code)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token or tokenizer.bos_token
    collator = MultiSimV5Collator(
        tokenizer=tokenizer,
        max_text_length=128,
        max_prompt_length=128,
        target_num_vars=args.target_num_vars,
    )

    train_items = [train_ds[i] for i in range(min(args.batch_size, len(train_ds)))]
    eval_items = [eval_ds[i] for i in range(min(args.batch_size, len(eval_ds)))]
    train_batch = collator(train_items)
    eval_batch = collator(eval_items)
    rows = train_ds.rows
    report: dict[str, Any] = {
        "train_jsonl": args.train_jsonl,
        "eval_jsonl": args.eval_jsonl,
        "tokenizer": args.tokenizer,
        "target_num_vars": args.target_num_vars,
        "batch_size": args.batch_size,
        "train_loaded": len(train_ds),
        "eval_loaded": len(eval_ds),
        "train_value_dim_counts": dict(Counter(str(value_dim(row)) for row in train_ds.rows)),
        "eval_value_dim_counts": dict(Counter(str(value_dim(row)) for row in eval_ds.rows)),
        "first_train_batch_shape": list(train_batch["values"].shape),
        "first_eval_batch_shape": list(eval_batch["values"].shape),
        "first_train_value_dim": train_batch["value_dim"].tolist(),
        "first_eval_value_dim": eval_batch["value_dim"].tolist(),
        "grouped_batch_report": inspect_grouped_batches(
            rows,
            batch_size=args.batch_size,
            group_key=args.group_key,
            max_batches=12,
        ),
    }
    report["smoke_pass"] = (
        report["first_train_batch_shape"][-1] == args.target_num_vars
        and report["first_eval_batch_shape"][-1] == args.target_num_vars
        and report["grouped_batch_report"]["mixed_group_batch_violations"] == 0
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
