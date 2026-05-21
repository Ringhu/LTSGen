#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/cluster/home/user1/hulining/LTSGEN}"
RUN_NAME="${RUN_NAME:-full_qwen3_4b_public_raw_tsqa_v4_39items_bilingual}"
DATA_DIR="${DATA_DIR:-$ROOT/.research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521}"
RUN_DIR="${RUN_DIR:-$DATA_DIR/model_eval_20260521/$RUN_NAME}"
ARCHIVE="${ARCHIVE:-$RUN_DIR.tar.gz}"

if [[ ! -d "$RUN_DIR" ]]; then
  echo "[error] missing run directory: $RUN_DIR" >&2
  exit 2
fi

for file in prompt_report.json prompt_preview.jsonl predictions.jsonl metrics.json; do
  if [[ ! -f "$RUN_DIR/$file" ]]; then
    echo "[error] missing expected eval artifact: $RUN_DIR/$file" >&2
    exit 2
  fi
done

python3 - "$RUN_DIR/metrics.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
metrics = json.loads(path.read_text())
overall = metrics.get("overall", {})
run = metrics.get("run", {})
print(
    "[metrics]",
    f"model={run.get('model')}",
    f"n={overall.get('n')}",
    f"accuracy={overall.get('accuracy')}",
    f"errors={run.get('error_count')}",
)
PY

tar -C "$DATA_DIR/model_eval_20260521" -czf "$ARCHIVE" "$RUN_NAME"
echo "[archive] $ARCHIVE"
