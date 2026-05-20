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
DIAG_REL="$REPAIR_REL/token_budget_fix_diagnostics_20260520"
RUN_REL="$DIAG_REL/qcond_overfit5_maxtext768_qwen3_4b"
GOLD_REL="$BASE_REL/merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl"

cd "$ROOT"
export CUDA_VISIBLE_DEVICES
export PYTHONPATH="$ROOT/tslm:$ROOT:${PYTHONPATH:-}"

"$PY" scripts/train/run_natural_qcc_gpu_smoke.py \
  --train_sft "$SFT_REL/natural_qcc_failure_domain_expanded_v22_numeric_grounding_train_sft.jsonl" \
  --eval_sft "$SFT_REL/natural_qcc_failure_domain_expanded_v22_numeric_grounding_train_sft.jsonl" \
  --eval_raw "$SFT_REL/natural_qcc_failure_domain_expanded_v22_numeric_grounding_train_raw.jsonl" \
  --gold_jsonl "$GOLD_REL" \
  --model_path "$MODEL_PATH" \
  --run_dir "$RUN_REL" \
  --bridge_type prefix \
  --target_num_vars 4 \
  --ts_num_vars 4 \
  --num_train_epochs "${NUM_TRAIN_EPOCHS:-20}" \
  --train_batch_size 1 \
  --eval_batch_size 1 \
  --gradient_accumulation_steps 1 \
  --max_train_samples 5 \
  --max_eval_samples 5 \
  --generate_limit 5 \
  --max_text_length 768 \
  --max_prompt_length 384 \
  --max_new_tokens 160 \
  --clean_max_sentences 3 \
  --qa_evaluator semantic \
  --qa_splits train dev \
  "$@"

"$PY" scripts/eval/audit_natural_qcc_caption_quality.py \
  --predictions_jsonl "$RUN_REL/generate_eval_test_clean/predictions.jsonl" \
  --gold_jsonl "$GOLD_REL" \
  --caption_field pred_caption \
  --splits train dev \
  --out "$RUN_REL/natural_qcc_caption_quality_audit.json"

"$PY" scripts/eval/audit_natural_qcc_slot_factuality.py \
  --predictions_jsonl "$RUN_REL/generate_eval_test_clean/predictions.jsonl" \
  --gold_jsonl "$SFT_REL/natural_qcc_failure_domain_expanded_v22_numeric_grounding_train_raw.jsonl" \
  --caption_field pred_caption \
  --out "$RUN_REL/natural_qcc_slot_factuality_audit.json"

echo "[done] v2.2 token-budget fix overfit diagnostics are under $RUN_REL"
