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
MODE="${MODE:-qcond}"

case "$MODE" in
  qcond)
    SFT_DIR="$BASE/sft"
    RUN_NAME="natural_qcc_crossdomain"
    RUN_DEFAULT="$BASE/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520"
    ;;
  no_question)
    SFT_DIR="$BASE/sft_no_question"
    RUN_NAME="natural_qcc_crossdomain_no_question"
    RUN_DEFAULT="$BASE/tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520"
    ;;
  *)
    echo "[error] unsupported MODE=$MODE; use qcond or no_question" >&2
    exit 2
    ;;
esac

RUN="${RUN_OVERRIDE:-$RUN_DEFAULT}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-$DEFAULT_GPU}"
export PYTHONPATH="$ROOT/tslm:$ROOT:$ROOT/scripts/eval:${PYTHONPATH:-}"

cd "$ROOT"

if [[ "$MODE" == "no_question" && ! -f "$SFT_DIR/${RUN_NAME}_train_sft.jsonl" ]]; then
  "$PY" scripts/generate/build_natural_qcc_no_question_control.py \
    --sft_dir "$BASE/sft" \
    --out_dir "$SFT_DIR" \
    --run_name natural_qcc_crossdomain \
    --out_run_name "$RUN_NAME"
fi

"$PY" scripts/train/run_natural_qcc_gpu_smoke.py \
  --train_sft "$SFT_DIR/${RUN_NAME}_train_sft.jsonl" \
  --eval_sft "$SFT_DIR/${RUN_NAME}_test_sft.jsonl" \
  --eval_raw "$SFT_DIR/${RUN_NAME}_test_raw.jsonl" \
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
