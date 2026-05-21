#!/usr/bin/env bash
set -euo pipefail

PROFILE="${PROFILE:-3090}"

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
    DEFAULT_GPU="2"
    ;;
  *)
    echo "[error] unsupported PROFILE=$PROFILE; use a100 or 3090" >&2
    exit 2
    ;;
esac

ROOT="${ROOT_OVERRIDE:-$DEFAULT_ROOT}"
PY="${PY_OVERRIDE:-$DEFAULT_PY}"
MODEL_PATH="${MODEL_PATH:-$DEFAULT_MODEL}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-$DEFAULT_GPU}"

BASE_REL=".research/general-qcc-captioner-20260515"
SEED_REL="$BASE_REL/natural_qcc_seed_smoke_v1_20260521"
OUT_REL="$BASE_REL/natural_qcc_seed_smoke_3090_20260521"
BUNDLE_REL="$OUT_REL/gpu_bundle"
TRAIN_REL="$OUT_REL/train_seed72_ep${NUM_TRAIN_EPOCHS:-1}_tok768"

QCOND_RUN_REL="$TRAIN_REL/qcond_seed72"
NOQ_RUN_REL="$TRAIN_REL/no_question_seed72"
COMPARE_OUT_REL="$TRAIN_REL/qcond_vs_no_question_seed72_audit.json"

cd "$ROOT"
export CUDA_VISIBLE_DEVICES
export PYTHONPATH="$ROOT/tslm:$ROOT:${PYTHONPATH:-}"

"$PY" scripts/generate/build_natural_qcc_seed_smoke_gpu_bundle.py \
  --seed_dir "$SEED_REL" \
  --out_dir "$BUNDLE_REL" \
  --split test

run_one() {
  local mode="$1"
  local run_rel="$2"
  local train_sft_rel="$3"
  shift 3

  echo "[run] mode=$mode run=$run_rel"
  "$PY" scripts/train/run_natural_qcc_gpu_smoke.py \
    --train_sft "$train_sft_rel" \
    --eval_sft "$train_sft_rel" \
    --eval_raw "$train_sft_rel" \
    --gold_jsonl "$BUNDLE_REL/seed_gold_smoke.jsonl" \
    --model_path "$MODEL_PATH" \
    --run_dir "$run_rel" \
    --bridge_type prefix \
    --target_num_vars 4 \
    --ts_num_vars 4 \
    --num_train_epochs "${NUM_TRAIN_EPOCHS:-1}" \
    --train_batch_size 1 \
    --eval_batch_size 1 \
    --gradient_accumulation_steps "${GRADIENT_ACCUMULATION_STEPS:-2}" \
    --max_train_samples "${MAX_TRAIN_SAMPLES:-72}" \
    --max_eval_samples "${MAX_EVAL_SAMPLES:-72}" \
    --generate_limit "${GENERATE_LIMIT:-72}" \
    --max_text_length "${MAX_TEXT_LENGTH:-768}" \
    --max_prompt_length "${MAX_PROMPT_LENGTH:-640}" \
    --max_new_tokens "${MAX_NEW_TOKENS:-160}" \
    --clean_max_sentences "${CLEAN_MAX_SENTENCES:-3}" \
    --qa_evaluator semantic \
    --qa_splits test \
    "$@"

  if [[ " $* " == *" --dry_run "* ]]; then
    return 0
  fi

  "$PY" scripts/eval/audit_natural_qcc_caption_quality.py \
    --predictions_jsonl "$run_rel/generate_eval_test_clean/predictions.jsonl" \
    --gold_jsonl "$BUNDLE_REL/seed_gold_smoke.jsonl" \
    --caption_field pred_caption \
    --splits test \
    --out "$run_rel/natural_qcc_caption_quality_audit.json"
}

run_one qcond "$QCOND_RUN_REL" "$BUNDLE_REL/seed_qcond_smoke.jsonl" "$@"
run_one no_question "$NOQ_RUN_REL" "$BUNDLE_REL/seed_no_question_smoke.jsonl" "$@"

if [[ " $* " == *" --dry_run "* ]]; then
  exit 0
fi

"$PY" scripts/eval/audit_natural_qcc_gpu_qcond_vs_noquestion.py \
  --qcond_run_dir "$QCOND_RUN_REL" \
  --no_question_run_dir "$NOQ_RUN_REL" \
  --out "$COMPARE_OUT_REL"

echo "[done] Natural QCC seed smoke artifacts are under $TRAIN_REL"
