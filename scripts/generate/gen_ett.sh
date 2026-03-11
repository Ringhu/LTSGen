#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

OUTDIR="$ROOT_DIR/gen_tst_dataset/forecasting/ett"
mkdir -p "$OUTDIR"

python -m ts_cap.cli \
  --dataset ett \
  --input "$ROOT_DIR/dataset/forecast/ETT-small/ETTh1.csv" \
  --output "${OUTDIR}/ett_h1_samples.jsonl" \
  --task forecasting \
  --time_col date \
  --target_col OT \
  --window_mode sliding \
  --window_len 128 \
  --stride 64 \
  --series_cols HUFL,HULL,MUFL,MULL,LUFL,LULL,OT \
  --disable_llm
