#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

OUTDIR="$ROOT_DIR/gen_tst_dataset/fred"
mkdir -p "$OUTDIR"

python -m ts_cap.cli \
  --dataset fred \
  --input "$ROOT_DIR/dataset/fred_blog.jsonl" \
  --output "${OUTDIR}/fred_captions_full.jsonl" \
  --window_mode full \
  --disable_llm
