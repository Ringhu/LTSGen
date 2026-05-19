#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT_OVERRIDE:-/cluster/home/user1/hulining/LTSGEN}"
PY="${PY_OVERRIDE:-/cluster/home/user1/anaconda3/envs/opentslm/bin/python3}"
MODEL="${MODEL_OVERRIDE:-/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507}"
BASE="$ROOT/.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519"
RUN="${RUN_OVERRIDE:-$BASE/tsrlm_natural_qcc_expansion_smoke_qwen3_4b_20260520}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-2}"
export PYTHONPATH="$ROOT/tslm:$ROOT:$ROOT/scripts/eval:${PYTHONPATH:-}"

cd "$ROOT"

"$PY" scripts/train/run_natural_qcc_gpu_smoke.py \
  --train_sft "$BASE/sft/natural_qcc_expansion_train_sft.jsonl" \
  --eval_sft "$BASE/sft/natural_qcc_expansion_test_sft.jsonl" \
  --eval_raw "$BASE/sft/natural_qcc_expansion_test_raw.jsonl" \
  --gold_jsonl "$BASE/natural_qcc_expansion_positive.jsonl" \
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

