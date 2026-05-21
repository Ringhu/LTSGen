#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/cluster/home/user1/hulining/LTSGEN}"
PY="${PY:-python3}"
BRANCH="${BRANCH:-emnlp-benchmark-pipeline}"
DATA_DIR="${DATA_DIR:-$ROOT/.research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521}"
MODEL_EVAL_DIR="${MODEL_EVAL_DIR:-$DATA_DIR/model_eval_20260521}"
MODEL_SPECS="${MODEL_SPECS:-qwen3_4b|Qwen3-4B-Instruct-2507|/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507|2|9411|1|32768|bfloat16|0.88}"

failures=0

check() {
  local label="$1"
  shift
  if "$@"; then
    echo "[ok] $label"
  else
    echo "[fail] $label" >&2
    failures=$((failures + 1))
  fi
}

check_file() {
  local path="$1"
  if [[ -f "$path" ]]; then
    echo "[ok] file $path"
  else
    echo "[fail] missing file $path" >&2
    failures=$((failures + 1))
  fi
}

check_dir() {
  local path="$1"
  if [[ -d "$path" ]]; then
    echo "[ok] dir $path"
  else
    echo "[fail] missing dir $path" >&2
    failures=$((failures + 1))
  fi
}

echo "[preflight] root=$ROOT"
echo "[preflight] py=$PY"
echo "[preflight] data_dir=$DATA_DIR"

check_dir "$ROOT"
check_dir "$DATA_DIR"
mkdir -p "$MODEL_EVAL_DIR"

check_file "$DATA_DIR/canonical_raw_tsqa_v4.jsonl"
check_file "$DATA_DIR/llm_text_view.jsonl"
check_file "$DATA_DIR/tsllm_array_view.jsonl"
check_file "$ROOT/scripts/eval/evaluate_public_raw_tsqa_llm.py"
check_file "$ROOT/scripts/eval/summarize_public_raw_tsqa_model_eval.py"
check_file "$ROOT/scripts/eval/compare_public_raw_tsqa_model_evals.py"
check_file "$ROOT/scripts/remote/run_public_raw_tsqa_qwen_eval_a100.sh"
check_file "$ROOT/scripts/remote/run_public_raw_tsqa_qwen_suite_a100.sh"
check_file "$ROOT/scripts/remote/package_public_raw_tsqa_qwen_eval_a100.sh"

if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  current_branch="$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
  head_sha="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || true)"
  if [[ "$current_branch" == "$BRANCH" ]]; then
    echo "[ok] git branch $current_branch@$head_sha"
  else
    echo "[fail] git branch '$current_branch', expected '$BRANCH' (head $head_sha)" >&2
    failures=$((failures + 1))
  fi
else
  echo "[warn] git not available or ROOT is not a git checkout"
fi

check "python executable" "$PY" -c "import sys; print(sys.executable)"
check "python can import json/urllib" "$PY" -c "import json, urllib.request"
check "python can import vllm" "$PY" -c "import vllm"
check "dataset sanity" "$PY" "$ROOT/scripts/eval/check_public_raw_tsqa_v4.py"
check "remote scripts bash syntax" bash -n \
  "$ROOT/scripts/remote/run_public_raw_tsqa_qwen_eval_a100.sh" \
  "$ROOT/scripts/remote/run_public_raw_tsqa_qwen_suite_a100.sh" \
  "$ROOT/scripts/remote/package_public_raw_tsqa_qwen_eval_a100.sh"

if command -v nvidia-smi >/dev/null 2>&1; then
  if nvidia-smi >/tmp/public_raw_tsqa_nvidia_smi.txt 2>&1; then
    echo "[ok] nvidia-smi"
    sed -n '1,12p' /tmp/public_raw_tsqa_nvidia_smi.txt
  else
    echo "[fail] nvidia-smi failed" >&2
    sed -n '1,20p' /tmp/public_raw_tsqa_nvidia_smi.txt >&2
    failures=$((failures + 1))
  fi
else
  echo "[fail] nvidia-smi not found" >&2
  failures=$((failures + 1))
fi

while IFS= read -r raw_spec; do
  spec="${raw_spec#"${raw_spec%%[![:space:]]*}"}"
  spec="${spec%"${spec##*[![:space:]]}"}"
  if [[ -z "$spec" || "$spec" == \#* ]]; then
    continue
  fi
  IFS="|" read -r slug served_name model_path cuda_devices port tensor_parallel_size max_model_len dtype gpu_memory_utilization <<<"$spec"
  echo "[model] slug=$slug served=$served_name path=$model_path cuda=$cuda_devices port=$port tp=${tensor_parallel_size:-1}"
  check_dir "$model_path"
  check "model config for $slug" test -f "$model_path/config.json"
  check "CUDA_VISIBLE_DEVICES parse for $slug" test -n "$cuda_devices"
  check "port parse for $slug" test -n "$port"
  if command -v ss >/dev/null 2>&1; then
    if ss -ltn | awk '{print $4}' | grep -Eq "(:|\\])$port$"; then
      echo "[warn] port $port already appears to be in use"
    else
      echo "[ok] port $port appears free"
    fi
  fi
done <<<"$MODEL_SPECS"

if (( failures > 0 )); then
  echo "[preflight] failed checks=$failures" >&2
  exit 1
fi

echo "[preflight] pass"
