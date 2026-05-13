#!/usr/bin/env python3
"""Create leakage-aware group splits for QCC-v0 expanded data."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def group_id(row: dict[str, Any]) -> str:
    ref = row.get("trace_ref", {})
    if "pair_path" in ref:
        return f"pair::{ref['pair_path']}"
    if "trace_path" in ref:
        return f"trace::{row['domain']}::{ref['trace_path']}"
    raise ValueError(f"No trace/pair ref for {row['id']}")


def split_family(split: str) -> str:
    return "train" if split in {"train", "tiny_overfit"} else split


def stable_hash(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], "big")


def assign_groups(rows: list[dict[str, Any]]) -> dict[str, str]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[group_id(row)].append(row)

    by_kind: dict[tuple[str, str], list[tuple[str, list[dict[str, Any]]]]] = defaultdict(list)
    for gid, items in groups.items():
        kind = "pair" if gid.startswith("pair::") else "trace"
        by_kind[(items[0]["domain"], kind)].append((gid, items))

    assignment: dict[str, str] = {}

    # Grid2Op observation has three local traces. Keep the largest in train,
    # then hold out the smaller traces for dev/test.
    obs = sorted(by_kind.get(("grid2op_real", "trace"), []), key=lambda x: (-len(x[1]), x[0]))
    for idx, (gid, _) in enumerate(obs):
        assignment[gid] = "train" if idx == 0 else ("dev" if idx == 1 else "test")

    # CityLearn currently has only one local trace, so a strict trace-level
    # split cannot provide CityLearn heldout data without adding another trace.
    for gid, _ in by_kind.get(("citylearn_real", "trace"), []):
        assignment[gid] = "train"

    # Counterfactual pairs are independent rollout pairs. Hash-sort then split
    # by pair so no pair appears in both train and dev/test.
    pairs = sorted(by_kind.get(("grid2op_real_cf", "pair"), []), key=lambda x: stable_hash(x[0]))
    n = len(pairs)
    n_train = max(1, round(0.70 * n))
    n_dev = max(1, round(0.15 * n)) if n >= 3 else 0
    for idx, (gid, _) in enumerate(pairs):
        if idx < n_train:
            split = "train"
        elif idx < n_train + n_dev:
            split = "dev"
        else:
            split = "test"
        assignment[gid] = split

    missing = set(groups) - set(assignment)
    if missing:
        raise ValueError(f"Unassigned groups: {sorted(missing)[:5]}")
    return assignment


def choose_tiny(rows: list[dict[str, Any]], n_tiny: int) -> set[str]:
    train_rows = [row for row in rows if row["split"] == "train"]
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(train_rows, key=lambda r: r["id"]):
        buckets[(row["domain"], row["task_family"])].append(row)
    keys = sorted(buckets)
    tiny: set[str] = set()
    cursor = 0
    while len(tiny) < min(n_tiny, len(train_rows)) and cursor < 100000:
        key = keys[cursor % len(keys)]
        if buckets[key]:
            tiny.add(buckets[key].pop(0)["id"])
        cursor += 1
        if all(not b for b in buckets.values()):
            break
    return tiny


def leakage_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    group_splits: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        group_splits[row["group_id"]].add(split_family(row["split"]))
    leaks = {gid: sorted(splits) for gid, splits in group_splits.items() if len(splits) > 1}
    return {
        "group_count": len(group_splits),
        "leakage_group_count": len(leaks),
        "leakage_examples": dict(list(leaks.items())[:10]),
    }


def build(rows: list[dict[str, Any]], tiny_size: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    assignment = assign_groups(rows)
    out: list[dict[str, Any]] = []
    for row in rows:
        gid = group_id(row)
        item = dict(row)
        item["original_split"] = row.get("split")
        item["group_id"] = gid
        item["split"] = assignment[gid]
        item["split_policy"] = "expanded_v1_group_by_trace_or_pair"
        out.append(item)

    tiny_ids = choose_tiny(out, tiny_size)
    for item in out:
        if item["id"] in tiny_ids:
            item["split"] = "tiny_overfit"

    report = {
        "n_examples": len(out),
        "by_split": dict(Counter(r["split"] for r in out)),
        "by_domain_split": {
            f"{domain}/{split}": count
            for (domain, split), count in sorted(Counter((r["domain"], r["split"]) for r in out).items())
        },
        "by_task_family_split": {
            f"{task}/{split}": count
            for (task, split), count in sorted(Counter((r["task_family"], r["split"]) for r in out).items())
        },
        "by_group_split": {
            f"{gid}/{split}": count
            for (gid, split), count in sorted(Counter((r["group_id"], r["split"]) for r in out).items())
        },
        "leakage": leakage_report(out),
        "limitations": [
            "CityLearn has only one local trace in expanded_v1, so strict trace-level splitting keeps CityLearn in train/tiny only.",
            "The split prevents trace/pair group overlap across train-family, dev, and test, but it does not create cross-domain heldout coverage for CityLearn.",
        ],
    }
    report["schema_gate_pass"] = report["leakage"]["leakage_group_count"] == 0
    return out, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--output_name", default="qcc_v0_expanded_group_dataset.jsonl")
    parser.add_argument("--tiny_size", type=int, default=32)
    args = parser.parse_args()

    rows, report = build(load_jsonl(Path(args.data)), args.tiny_size)
    out_dir = Path(args.out_dir)
    write_jsonl(out_dir / args.output_name, rows)
    (out_dir / "group_split_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
