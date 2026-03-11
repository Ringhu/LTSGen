#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATASET_HOME="$(cd "$ROOT_DIR/.." && pwd)"
cd "$ROOT_DIR"

NAB_INPUT="${NAB_INPUT:-$DATASET_HOME/NAB}"
OUTDIR="$ROOT_DIR/gen_tst_dataset/anomaly/nab"
mkdir -p "$OUTDIR"

python -m ts_cap.cli \
  --dataset nab \
  --input "$NAB_INPUT" \
  --output "${OUTDIR}/nab_caption.jsonl" \
  --task anomaly_detection \
  --window_mode sliding \
  --window_len 512 \
  --stride 256 \
  --max_windows 2000 \
  --disable_llm
