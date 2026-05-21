#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/cluster/home/user1/hulining/LTSGEN}"
PY="${PY:-python3}"
BRANCH="${BRANCH:-emnlp-benchmark-pipeline}"

MODEL_PATH="${MODEL_PATH:-/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-$(basename "$MODEL_PATH")}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-9411}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
DTYPE="${DTYPE:-bfloat16}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.88}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-2}"

DATA_DIR="${DATA_DIR:-$ROOT/.research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521}"
RUN_NAME="${RUN_NAME:-qwenlocal_${SERVED_MODEL_NAME}_public_raw_tsqa_v4}"
OUT_DIR="${OUT_DIR:-$DATA_DIR/model_eval_20260521/$RUN_NAME}"
MAX_ITEMS="${MAX_ITEMS:-0}"
PER_DOMAIN="${PER_DOMAIN:-0}"
LANGUAGES="${LANGUAGES:-both}"
CONCURRENCY="${CONCURRENCY:-2}"
TIMEOUT="${TIMEOUT:-600}"
MAX_TOKENS="${MAX_TOKENS:-160}"
PROGRESS_EVERY="${PROGRESS_EVERY:-10}"
USE_EXISTING_SERVER="${USE_EXISTING_SERVER:-0}"
KEEP_SERVER="${KEEP_SERVER:-0}"
HEALTH_TIMEOUT_SEC="${HEALTH_TIMEOUT_SEC:-240}"
RESUME="${RESUME:-1}"

export CUDA_VISIBLE_DEVICES
export PYTHONPATH="$ROOT:$ROOT/tslm:$ROOT/scripts/eval:${PYTHONPATH:-}"

if [[ ! -f "$ROOT/scripts/eval/evaluate_public_raw_tsqa_llm.py" ]]; then
  echo "[error] evaluator not found under ROOT=$ROOT" >&2
  exit 2
fi

CURRENT_BRANCH="$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
if [[ -n "$CURRENT_BRANCH" && "$CURRENT_BRANCH" != "$BRANCH" ]]; then
  echo "[warn] ROOT is on branch '$CURRENT_BRANCH', expected '$BRANCH'" >&2
fi

mkdir -p "$OUT_DIR"
SERVER_LOG="$OUT_DIR/vllm_server.log"
SERVER_PID=""

healthcheck() {
  "$PY" - "$HOST" "$PORT" <<'PY'
import sys
import urllib.request

host, port = sys.argv[1], sys.argv[2]
url = f"http://{host}:{port}/v1/models"
try:
    with urllib.request.urlopen(url, timeout=2) as resp:
        resp.read()
except Exception:
    raise SystemExit(1)
PY
}

if [[ "$USE_EXISTING_SERVER" != "1" ]]; then
  echo "[serve] starting vLLM model=$MODEL_PATH served=$SERVED_MODEL_NAME cuda=$CUDA_VISIBLE_DEVICES port=$PORT"
  "$PY" -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_PATH" \
    --served-model-name "$SERVED_MODEL_NAME" \
    --host "$HOST" \
    --port "$PORT" \
    --trust-remote-code \
    --tensor-parallel-size "$TENSOR_PARALLEL_SIZE" \
    --dtype "$DTYPE" \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    >"$SERVER_LOG" 2>&1 &
  SERVER_PID="$!"
  echo "[serve] pid=$SERVER_PID log=$SERVER_LOG"

  cleanup() {
    if [[ -n "$SERVER_PID" && "$KEEP_SERVER" != "1" ]]; then
      kill "$SERVER_PID" 2>/dev/null || true
    fi
  }
  trap cleanup EXIT
fi

echo "[serve] waiting for http://$HOST:$PORT/v1/models"
DEADLINE=$((SECONDS + HEALTH_TIMEOUT_SEC))
while true; do
  if healthcheck; then
    break
  fi
  if [[ -n "$SERVER_PID" ]] && ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "[error] vLLM server exited before becoming ready. Last log lines:" >&2
    tail -80 "$SERVER_LOG" >&2 || true
    exit 1
  fi
  if (( SECONDS >= DEADLINE )); then
    echo "[error] vLLM server healthcheck timed out. Last log lines:" >&2
    tail -80 "$SERVER_LOG" >&2 || true
    exit 1
  fi
  sleep 5
done

export QWENLOCAL_API_KEY="${QWENLOCAL_API_KEY:-EMPTY}"
export QWENLOCAL_BASE_URL="http://$HOST:$PORT/v1"
export QWENLOCAL_MODEL="$SERVED_MODEL_NAME"
RESUME_ARGS=()
if [[ "$RESUME" == "1" ]]; then
  RESUME_ARGS=(--resume)
fi

echo "[eval] run=$RUN_NAME languages=$LANGUAGES max_items=$MAX_ITEMS per_domain=$PER_DOMAIN out=$OUT_DIR"
"$PY" "$ROOT/scripts/eval/evaluate_public_raw_tsqa_llm.py" \
  --provider qwenlocal \
  --model "$SERVED_MODEL_NAME" \
  --languages "$LANGUAGES" \
  --max_items "$MAX_ITEMS" \
  --per_domain "$PER_DOMAIN" \
  --run_name "$RUN_NAME" \
  --out_dir "$OUT_DIR" \
  --concurrency "$CONCURRENCY" \
  --timeout "$TIMEOUT" \
  --max_tokens "$MAX_TOKENS" \
  --progress_every "$PROGRESS_EVERY" \
  "${RESUME_ARGS[@]}" \
  "$@"

echo "[done] metrics: $OUT_DIR/metrics.json"
