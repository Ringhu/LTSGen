#!/usr/bin/env python3
"""Select a deterministic per-source subset from a MultiSim JSONL file."""
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


def source_name(row: dict[str, Any]) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(row.get("merge_source_name") or meta.get("merge_source_name") or row.get("multisim_source_domain") or row.get("domain") or "unknown")


def stable_key(row: dict[str, Any], seed: int) -> str:
    return hashlib.sha256(f"{seed}::{row.get('id', '')}".encode("utf-8")).hexdigest()


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row.get("target_caption", row.get("output", "")),
        "meta": row.get("meta", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out_jsonl", required=True)
    parser.add_argument("--out_sft_jsonl", default="")
    parser.add_argument("--splits", nargs="+", default=["dev", "test"])
    parser.add_argument("--per_source", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = [row for row in load_jsonl(Path(args.input)) if row.get("split") in set(args.splits)]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[source_name(row)].append(row)
    selected = []
    source_reports = {}
    for source, items in sorted(grouped.items()):
        ranked = sorted(items, key=lambda row: stable_key(row, args.seed))
        part = ranked[: args.per_source]
        selected.extend(part)
        source_reports[source] = {"available": len(items), "selected": len(part)}
    selected = sorted(selected, key=lambda row: (source_name(row), stable_key(row, args.seed)))
    out_jsonl = Path(args.out_jsonl)
    write_jsonl(out_jsonl, selected)
    if args.out_sft_jsonl:
        write_jsonl(Path(args.out_sft_jsonl), [sft_row(row) for row in selected])
    report = {
        "input": args.input,
        "out_jsonl": args.out_jsonl,
        "out_sft_jsonl": args.out_sft_jsonl,
        "splits": args.splits,
        "per_source": args.per_source,
        "n": len(selected),
        "by_source": source_reports,
        "by_split": dict(Counter(row.get("split", "") for row in selected)),
    }
    (out_jsonl.parent / "subset_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
