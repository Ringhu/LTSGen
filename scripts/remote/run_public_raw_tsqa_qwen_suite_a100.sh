#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/cluster/home/user1/hulining/LTSGEN}"
PY="${PY:-python3}"
BRANCH="${BRANCH:-emnlp-benchmark-pipeline}"

DATA_DIR="${DATA_DIR:-$ROOT/.research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521}"
MODEL_EVAL_DIR="${MODEL_EVAL_DIR:-$DATA_DIR/model_eval_20260521}"
SUITE_NAME="${SUITE_NAME:-qwen_suite_public_raw_tsqa_v4_$(date +%Y%m%d_%H%M%S)}"
SUITE_DIR="${SUITE_DIR:-$MODEL_EVAL_DIR/$SUITE_NAME}"

LANGUAGES="${LANGUAGES:-both}"
MAX_ITEMS="${MAX_ITEMS:-0}"
PER_DOMAIN="${PER_DOMAIN:-0}"
CONCURRENCY="${CONCURRENCY:-2}"
TIMEOUT="${TIMEOUT:-600}"
MAX_TOKENS="${MAX_TOKENS:-160}"
PROGRESS_EVERY="${PROGRESS_EVERY:-10}"
RESUME="${RESUME:-1}"
NO_RESPONSE_FORMAT="${NO_RESPONSE_FORMAT:-1}"
STRICT_MODEL_PATHS="${STRICT_MODEL_PATHS:-1}"

# Format, one model per line:
#   slug|served_model_name|model_path|cuda_visible_devices|port|tensor_parallel_size|max_model_len|dtype|gpu_memory_utilization
#
# Override MODEL_SPECS to run a Qwen series. Example:
# MODEL_SPECS=$'qwen3_4b|Qwen3-4B-Instruct-2507|/path/to/Qwen3-4B-Instruct-2507|2|9411|1|32768|bfloat16|0.88\nqwen3_8b|Qwen3-8B|/path/to/Qwen3-8B|3|9412|1|32768|bfloat16|0.88'
MODEL_SPECS="${MODEL_SPECS:-qwen3_4b|Qwen3-4B-Instruct-2507|/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507|2|9411|1|32768|bfloat16|0.88}"

if [[ ! -x "$ROOT/scripts/remote/run_public_raw_tsqa_qwen_eval_a100.sh" ]]; then
  echo "[error] missing or non-executable single-model runner under ROOT=$ROOT" >&2
  exit 2
fi

if [[ ! -x "$ROOT/scripts/remote/package_public_raw_tsqa_qwen_eval_a100.sh" ]]; then
  echo "[error] missing or non-executable package script under ROOT=$ROOT" >&2
  exit 2
fi

mkdir -p "$SUITE_DIR"
SUMMARY_JSONL="$SUITE_DIR/summary.jsonl"
SUMMARY_MD="$SUITE_DIR/summary.md"
: >"$SUMMARY_JSONL"
{
  echo "# Qwen Public Raw TSQA v4 Suite"
  echo
  echo "- suite: \`$SUITE_NAME\`"
  echo "- data: \`$DATA_DIR\`"
  echo "- languages: \`$LANGUAGES\`"
  echo "- max_items: \`$MAX_ITEMS\`"
  echo "- per_domain: \`$PER_DOMAIN\`"
  echo
  echo "| Run | Model | Prompts | Accuracy | EN | ZH | Errors | Archive |"
  echo "|---|---|---:|---:|---:|---:|---:|---|"
} >"$SUMMARY_MD"

EVAL_ARGS=()
if [[ "$NO_RESPONSE_FORMAT" == "1" ]]; then
  EVAL_ARGS+=(--no_response_format)
fi

run_count=0
skip_count=0

while IFS= read -r raw_spec; do
  spec="${raw_spec#"${raw_spec%%[![:space:]]*}"}"
  spec="${spec%"${spec##*[![:space:]]}"}"
  if [[ -z "$spec" || "$spec" == \#* ]]; then
    continue
  fi

  IFS="|" read -r slug served_name model_path cuda_devices port tensor_parallel_size max_model_len dtype gpu_memory_utilization <<<"$spec"
  if [[ -z "${slug:-}" || -z "${served_name:-}" || -z "${model_path:-}" || -z "${cuda_devices:-}" || -z "${port:-}" ]]; then
    echo "[error] invalid MODEL_SPECS line: $raw_spec" >&2
    exit 2
  fi

  tensor_parallel_size="${tensor_parallel_size:-1}"
  max_model_len="${max_model_len:-32768}"
  dtype="${dtype:-bfloat16}"
  gpu_memory_utilization="${gpu_memory_utilization:-0.88}"

  if [[ ! -d "$model_path" ]]; then
    if [[ "$STRICT_MODEL_PATHS" == "1" ]]; then
      echo "[error] missing model path for $slug: $model_path" >&2
      exit 2
    fi
    echo "[skip] missing model path for $slug: $model_path" >&2
    skip_count=$((skip_count + 1))
    continue
  fi

  run_name="full_${slug}_public_raw_tsqa_v4_39items_bilingual"
  run_dir="$MODEL_EVAL_DIR/$run_name"
  archive="$run_dir.tar.gz"

  echo "[suite] running $slug model=$model_path cuda=$cuda_devices port=$port"
  ROOT="$ROOT" \
  PY="$PY" \
  BRANCH="$BRANCH" \
  DATA_DIR="$DATA_DIR" \
  MODEL_PATH="$model_path" \
  SERVED_MODEL_NAME="$served_name" \
  CUDA_VISIBLE_DEVICES="$cuda_devices" \
  PORT="$port" \
  TENSOR_PARALLEL_SIZE="$tensor_parallel_size" \
  MAX_MODEL_LEN="$max_model_len" \
  DTYPE="$dtype" \
  GPU_MEMORY_UTILIZATION="$gpu_memory_utilization" \
  RUN_NAME="$run_name" \
  OUT_DIR="$run_dir" \
  LANGUAGES="$LANGUAGES" \
  MAX_ITEMS="$MAX_ITEMS" \
  PER_DOMAIN="$PER_DOMAIN" \
  CONCURRENCY="$CONCURRENCY" \
  TIMEOUT="$TIMEOUT" \
  MAX_TOKENS="$MAX_TOKENS" \
  PROGRESS_EVERY="$PROGRESS_EVERY" \
  RESUME="$RESUME" \
  "$ROOT/scripts/remote/run_public_raw_tsqa_qwen_eval_a100.sh" \
    "${EVAL_ARGS[@]}" \
    "$@"

  "$PY" "$ROOT/scripts/eval/summarize_public_raw_tsqa_model_eval.py" \
    --predictions_jsonl "$run_dir/predictions.jsonl" \
    --out_json "$run_dir/error_summary.json"

  ROOT="$ROOT" \
  DATA_DIR="$DATA_DIR" \
  RUN_NAME="$run_name" \
  ARCHIVE="$archive" \
  "$ROOT/scripts/remote/package_public_raw_tsqa_qwen_eval_a100.sh"

  "$PY" - "$run_dir/metrics.json" "$SUMMARY_JSONL" "$SUMMARY_MD" "$archive" <<'PY'
import json
import sys
from pathlib import Path

metrics_path = Path(sys.argv[1])
summary_jsonl = Path(sys.argv[2])
summary_md = Path(sys.argv[3])
archive = Path(sys.argv[4])

metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
run = metrics.get("run", {})
overall = metrics.get("overall", {})
by_language = metrics.get("by_language", {})

row = {
    "run_name": metrics_path.parent.name,
    "model": run.get("model", ""),
    "n": overall.get("n", 0),
    "accuracy": overall.get("accuracy", 0.0),
    "en_accuracy": by_language.get("en", {}).get("accuracy", 0.0),
    "zh_accuracy": by_language.get("zh", {}).get("accuracy", 0.0),
    "error_count": run.get("error_count", 0),
    "archive": str(archive),
}
with summary_jsonl.open("a", encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=False) + "\n")
with summary_md.open("a", encoding="utf-8") as f:
    f.write(
        f"| `{row['run_name']}` | `{row['model']}` | {row['n']} | "
        f"{row['accuracy']:.4f} | {row['en_accuracy']:.4f} | "
        f"{row['zh_accuracy']:.4f} | {row['error_count']} | `{archive.name}` |\n"
    )
PY

  run_count=$((run_count + 1))
done <<<"$MODEL_SPECS"

echo "[suite] completed runs=$run_count skipped=$skip_count summary=$SUMMARY_MD"
