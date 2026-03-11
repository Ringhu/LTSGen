#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/tslm"

python scripts/build_sft_jsonl.py \
  --in_jsonl  "$ROOT_DIR/gen_tst_dataset/ucr/merged/ucr_train_merged.jsonl" \
  --out_jsonl data/test_sft.jsonl \
  --lang en \
  --styles json_caption \
  --keep_meta 
