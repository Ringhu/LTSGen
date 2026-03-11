#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

JSONL="${JSONL:-$ROOT_DIR/gen_tst_dataset/ucr/test_shards/ucr_largekitchenappliances_test.jsonl}"
CKPT="${CKPT:-$ROOT_DIR/runs/hsa_clip_v2_hybrid/latest.pt}"
SAVE_DIR="${SAVE_DIR:-$ROOT_DIR/vis_alignment/hsa_clip_v2_hybrid}"
BATCH_SIZE="${BATCH_SIZE:-32}"
NUM_WORKERS="${NUM_WORKERS:-2}"
MAX_RECORDS="${MAX_RECORDS:-256}"

python -m ts_align_scripts_v2.visualize_alignment \
  --jsonl "$JSONL" \
  --ckpt "$CKPT" \
  --save_dir "$SAVE_DIR" \
  --batch_size "$BATCH_SIZE" \
  --num_workers "$NUM_WORKERS" \
  --max_records "$MAX_RECORDS"
