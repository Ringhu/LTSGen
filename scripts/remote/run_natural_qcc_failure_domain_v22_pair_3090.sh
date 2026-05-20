#!/usr/bin/env bash
set -euo pipefail

PROFILE="${PROFILE:-3090}"

case "$PROFILE" in
  a100)
    DEFAULT_ROOT="/cluster/home/user1/hulining/LTSGEN"
    DEFAULT_PY="/cluster/home/user1/anaconda3/envs/opentslm/bin/python3"
    ;;
  3090)
    DEFAULT_ROOT="/cluster/home/hulining/LTSGEN"
    DEFAULT_PY="/cluster/home/hulining/anaconda3/envs/opentslm/bin/python3"
    ;;
  *)
    echo "[error] unsupported PROFILE=$PROFILE; use a100 or 3090" >&2
    exit 2
    ;;
esac

ROOT="${ROOT_OVERRIDE:-$DEFAULT_ROOT}"
PY="${PY_OVERRIDE:-$DEFAULT_PY}"
MODEL_PATH="${MODEL_PATH:-Qwen/Qwen3-4B}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"

BASE_REL=".research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520"
REPAIR_REL="$BASE_REL/numeric_grounding_repair_v22_20260520"
SFT_REL="$REPAIR_REL/sft_evidence_only_v22"
TRAIN_REL="$REPAIR_REL/train_v22_e5_tok128_20260520"
GOLD_REL="$BASE_REL/merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl"
PROBE_REL="$BASE_REL/probe_eval_v2/natural_qcc_probe_results.json"

QCOND_RUN_REL="$TRAIN_REL/tsrlm_qcond_e5_tok128_qwen3_4b"
NOQ_RUN_REL="$TRAIN_REL/tsrlm_no_question_e5_tok128_qwen3_4b"
COMPARE_OUT_REL="$TRAIN_REL/natural_qcc_failure_domain_expanded_v22_e5_tok128_qcond_vs_noquestion_audit.json"

cd "$ROOT"
export CUDA_VISIBLE_DEVICES
export PYTHONPATH="$ROOT/tslm:$ROOT:${PYTHONPATH:-}"

run_one() {
  local mode="$1"
  local run_rel="$2"
  local train_sft_rel="$3"
  local eval_sft_rel="$4"
  local eval_raw_rel="$5"
  shift 5

  echo "[run] mode=$mode run=$run_rel"
  "$PY" scripts/train/run_natural_qcc_gpu_smoke.py \
    --train_sft "$train_sft_rel" \
    --eval_sft "$eval_sft_rel" \
    --eval_raw "$eval_raw_rel" \
    --gold_jsonl "$GOLD_REL" \
    --model_path "$MODEL_PATH" \
    --run_dir "$run_rel" \
    --bridge_type prefix \
    --target_num_vars 4 \
    --ts_num_vars 4 \
    --num_train_epochs 5 \
    --gradient_accumulation_steps 2 \
    --max_new_tokens 128 \
    --clean_max_sentences 3 \
    --qa_evaluator semantic \
    "$@"

  if [[ " $* " == *" --dry_run "* ]]; then
    return 0
  fi

  "$PY" scripts/eval/audit_natural_qcc_gpu_smoke_result.py \
    --run_dir "$run_rel" \
    --probe_results "$PROBE_REL" \
    --qa_metrics semantic \
    --out "$run_rel/natural_qcc_gpu_smoke_result_audit.json"

  "$PY" scripts/eval/audit_natural_qcc_caption_quality.py \
    --predictions_jsonl "$run_rel/generate_eval_test_clean/predictions.jsonl" \
    --gold_jsonl "$GOLD_REL" \
    --caption_field pred_caption \
    --splits test \
    --out "$run_rel/natural_qcc_caption_quality_audit.json"

  "$PY" scripts/eval/audit_natural_qcc_slot_factuality.py \
    --predictions_jsonl "$run_rel/generate_eval_test_clean/predictions.jsonl" \
    --gold_jsonl "$eval_raw_rel" \
    --caption_field pred_caption \
    --out "$run_rel/natural_qcc_slot_factuality_audit.json"
}

run_one \
  qcond \
  "$QCOND_RUN_REL" \
  "$SFT_REL/natural_qcc_failure_domain_expanded_v22_numeric_grounding_train_sft.jsonl" \
  "$SFT_REL/natural_qcc_failure_domain_expanded_v22_numeric_grounding_test_sft.jsonl" \
  "$SFT_REL/natural_qcc_failure_domain_expanded_v22_numeric_grounding_test_raw.jsonl" \
  "$@"

run_one \
  no_question \
  "$NOQ_RUN_REL" \
  "$SFT_REL/natural_qcc_failure_domain_expanded_v22_numeric_grounding_no_question_train_sft.jsonl" \
  "$SFT_REL/natural_qcc_failure_domain_expanded_v22_numeric_grounding_no_question_test_sft.jsonl" \
  "$SFT_REL/natural_qcc_failure_domain_expanded_v22_numeric_grounding_no_question_test_raw.jsonl" \
  "$@"

if [[ " $* " == *" --dry_run "* ]]; then
  exit 0
fi

"$PY" scripts/eval/audit_natural_qcc_gpu_qcond_vs_noquestion.py \
  --qcond_run_dir "$QCOND_RUN_REL" \
  --no_question_run_dir "$NOQ_RUN_REL" \
  --out "$COMPARE_OUT_REL"

echo "[done] v2.2 qcond/no-question training validation artifacts are under $TRAIN_REL"
