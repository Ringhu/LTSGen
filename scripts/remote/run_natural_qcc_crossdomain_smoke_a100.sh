#!/usr/bin/env bash
set -euo pipefail

PROFILE="${PROFILE:-a100}"

case "$PROFILE" in
  a100)
    DEFAULT_ROOT="/cluster/home/user1/hulining/LTSGEN"
    DEFAULT_PY="/cluster/home/user1/anaconda3/envs/opentslm/bin/python3"
    DEFAULT_MODEL="/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507"
    DEFAULT_GPU="2"
    ;;
  3090)
    DEFAULT_ROOT="/cluster/home/hulining/LTSGEN"
    DEFAULT_PY="/cluster/home/hulining/anaconda3/envs/opentslm/bin/python3"
    DEFAULT_MODEL="Qwen/Qwen3-4B"
    DEFAULT_GPU="1"
    ;;
  *)
    echo "[error] unsupported PROFILE=$PROFILE; use a100 or 3090" >&2
    exit 2
    ;;
esac

ROOT="${ROOT_OVERRIDE:-$DEFAULT_ROOT}"
PY="${PY_OVERRIDE:-$DEFAULT_PY}"
MODEL="${MODEL_OVERRIDE:-$DEFAULT_MODEL}"
BASE="$ROOT/.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
RUN="${RUN_OVERRIDE:-$BASE/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-$DEFAULT_GPU}"
export PYTHONPATH="$ROOT/tslm:$ROOT:$ROOT/scripts/eval:${PYTHONPATH:-}"

cd "$ROOT"

"$PY" scripts/train/run_natural_qcc_gpu_smoke.py \
  --train_sft "$BASE/sft/natural_qcc_crossdomain_train_sft.jsonl" \
  --eval_sft "$BASE/sft/natural_qcc_crossdomain_test_sft.jsonl" \
  --eval_raw "$BASE/sft/natural_qcc_crossdomain_test_raw.jsonl" \
  --gold_jsonl "$BASE/natural_qcc_crossdomain_positive.jsonl" \
  --model_path "$MODEL" \
  --run_dir "$RUN" \
  --bridge_type "${BRIDGE_TYPE:-prefix}" \
  --target_num_vars "${TARGET_NUM_VARS:-4}" \
  --ts_num_vars "${TS_NUM_VARS:-4}" \
  --num_train_epochs "${NUM_TRAIN_EPOCHS:-1}" \
  --gradient_accumulation_steps "${GRADIENT_ACCUMULATION_STEPS:-4}" \
  --max_new_tokens "${MAX_NEW_TOKENS:-48}" \
  --clean_max_sentences "${CLEAN_MAX_SENTENCES:-2}" \
  "$@"

if [[ " $* " == *" --dry_run "* ]]; then
  exit 0
fi

"$PY" scripts/eval/audit_natural_qcc_gpu_smoke_result.py \
  --run_dir "$RUN" \
  --probe_results "$BASE/probe_eval/natural_qcc_probe_results.json"
