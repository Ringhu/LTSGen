#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

JSONL="${JSONL:-$ROOT_DIR/gen_tst_dataset/ucr/test_shards/ucr_largekitchenappliances_test.jsonl}"
CKPT="${CKPT:-$ROOT_DIR/runs/hsa_clip_v2_hybrid/latest.pt}"
BATCH_SIZE="${BATCH_SIZE:-128}"
NUM_WORKERS="${NUM_WORKERS:-4}"
MAX_RECORDS="${MAX_RECORDS:-}"

cmd=(
  python -m ts_align_scripts_v2.eval_retrieval
  --jsonl "$JSONL"
  --ckpt "$CKPT"
  --batch_size "$BATCH_SIZE"
  --num_workers "$NUM_WORKERS"
)

if [[ -n "$MAX_RECORDS" ]]; then
  cmd+=(--max_records "$MAX_RECORDS")
fi

"${cmd[@]}"
