#!/usr/bin/env python3
"""Re-clean generated Natural-QCC predictions from raw caption text."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tslm.scripts.generate_multisim_v5_smoke import clean_caption  # noqa: E402


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def reclean_row(row: dict[str, Any], *, max_sentences: int) -> dict[str, Any]:
    out = dict(row)
    raw = str(row.get("pred_caption_raw") or row.get("pred_caption") or "")
    out["pred_caption_original_clean"] = str(row.get("pred_caption", ""))
    out["pred_caption"] = clean_caption(raw, max_sentences=max_sentences)
    out["recleaned_from_raw"] = bool(row.get("pred_caption_raw"))
    return out


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    changed = sum(1 for row in rows if row.get("pred_caption") != row.get("pred_caption_original_clean"))
    return {
        "n": len(rows),
        "changed_rows": changed,
        "changed_rate": round(changed / len(rows), 4) if rows else 0.0,
        "mean_original_chars": round(
            sum(len(str(row.get("pred_caption_original_clean", ""))) for row in rows) / len(rows), 1
        )
        if rows
        else 0.0,
        "mean_recleaned_chars": round(sum(len(str(row.get("pred_caption", ""))) for row in rows) / len(rows), 1)
        if rows
        else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions_jsonl", type=Path, required=True)
    parser.add_argument("--out_jsonl", type=Path, required=True)
    parser.add_argument("--summary_json", type=Path, default=None)
    parser.add_argument("--max_sentences", type=int, default=2)
    args = parser.parse_args()

    rows = [reclean_row(row, max_sentences=args.max_sentences) for row in load_jsonl(args.predictions_jsonl)]
    write_jsonl(args.out_jsonl, rows)
    summary = {
        "predictions_jsonl": str(args.predictions_jsonl),
        "out_jsonl": str(args.out_jsonl),
        "max_sentences": args.max_sentences,
        "metrics": summarize(rows),
    }
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
