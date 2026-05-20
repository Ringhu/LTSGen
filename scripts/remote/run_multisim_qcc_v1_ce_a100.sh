#!/usr/bin/env bash
set -euo pipefail

ROOT="/cluster/home/user1/hulining/LTSGEN"
PY="/cluster/home/user1/anaconda3/envs/opentslm/bin/python3"
MODEL="/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507"
BASE="${BASE_OVERRIDE:-$ROOT/.research/general-qcc-captioner-20260515/multisim_qcc_v1}"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <run_name> <bridge_type>" >&2
  echo "Example: $0 multisim_qcc_v1 local_gated_qprefix" >&2
  exit 2
fi

RUN_NAME="$1"
BRIDGE_TYPE="$2"
DATA="$BASE/$RUN_NAME"
RUN="${RUN_OVERRIDE:-$DATA/tsrlm_${RUN_NAME}_${BRIDGE_TYPE}_ce_qwen3_4b}"

case "$BRIDGE_TYPE" in
  qprefix|hybrid_qprefix|local_gated_qprefix|task_gated_qprefix|prefix|xattn) ;;
  *) echo "[error] unsupported bridge_type=$BRIDGE_TYPE" >&2; exit 2 ;;
esac

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-2}"
export PYTHONPATH="$ROOT/tslm:$ROOT:$ROOT/scripts/eval:${PYTHONPATH:-}"

if [[ ! -f "$DATA/schema_report.json" ]]; then
  echo "[error] missing schema report: $DATA/schema_report.json" >&2
  exit 2
fi

"$PY" - "$DATA/schema_report.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
report = json.loads(path.read_text())
if not report.get("schema_gate_pass"):
    raise SystemExit(f"[error] schema gate failed: {path}")
PY

if [[ -e "$RUN/final_model/pytorch_model.bin" ]]; then
  if [[ "${ALLOW_EXISTING_FINAL_MODEL:-0}" == "1" ]]; then
    echo "[train-skip] Reusing existing completed run: $RUN"
  else
    echo "[error] Refusing to overwrite existing completed run: $RUN" >&2
    echo "[hint] Set ALLOW_EXISTING_FINAL_MODEL=1 to skip training and rerun heldout generation/eval." >&2
    exit 2
  fi
else
  mkdir -p "$RUN"
  echo "[train] MULTISIM=$RUN_NAME bridge=$BRIDGE_TYPE CE"
  "$PY" "$ROOT/tslm/scripts/train_sft.py" \
    --train_jsonl "$DATA/${RUN_NAME}_train_sft.jsonl" \
    --eval_jsonl "$DATA/${RUN_NAME}_eval_source_dev_sft.jsonl" \
    --llm_name_or_path "$MODEL" \
    --trust_remote_code \
    --encoder_type patchtst \
    --bridge_type "$BRIDGE_TYPE" \
    --ts_num_vars 3 \
    --ts_patch_len 16 \
    --ts_d_model 128 \
    --ts_layers 2 \
    --ts_heads 4 \
    --prefix_tokens 8 \
    --resampler_layers 1 \
    --resampler_heads 4 \
    --n_stat_tokens 2 \
    --output_dir "$RUN" \
    --num_train_epochs "${NUM_TRAIN_EPOCHS:-3}" \
    --per_device_train_batch_size 1 \
    --per_device_eval_batch_size 1 \
    --gradient_accumulation_steps 1 \
    --learning_rate "${LEARNING_RATE:-2e-4}" \
    --weight_decay 0.01 \
    --warmup_ratio 0.03 \
    --max_text_length 224 \
    --max_prompt_length 320 \
    --logging_steps 100 \
    --save_strategy no \
    --eval_steps "${EVAL_STEPS:-500}" \
    --seed 42 \
    --bf16 \
    --freeze_llm \
    --lora_r 8 \
    --lora_alpha 32 \
    --lora_dropout 0.05 \
    --save_trainable_only \
    --max_train_samples "${MAX_TRAIN_SAMPLES:-0}" \
    --max_eval_samples "${MAX_EVAL_SAMPLES:-0}"
fi

for domain in grid2op citylearn finrl; do
  case "$domain" in
    grid2op) EVAL_SCRIPT="evaluate_grid2op_broad_predictions.py" ;;
    citylearn) EVAL_SCRIPT="evaluate_citylearn_broad_predictions.py" ;;
    finrl) EVAL_SCRIPT="evaluate_finrl_broad_predictions.py" ;;
    *) echo "[error] unsupported domain=$domain" >&2; exit 2 ;;
  esac

  for split in dev test; do
    RAW="$DATA/${RUN_NAME}_heldout_${domain}_${split}.jsonl"
    if [[ ! -f "$RAW" ]]; then
      echo "[error] missing heldout file: $RAW" >&2
      exit 2
    fi

    OUT="$RUN/generate_${domain}_${split}_clean"
    echo "[generate] MULTISIM=$RUN_NAME bridge=$BRIDGE_TYPE domain=$domain split=$split"
    "$PY" "$ROOT/tslm/scripts/generate_general_qcc_evidence_captions.py" \
      --raw_jsonl "$RAW" \
      --checkpoint_dir "$RUN/final_model" \
      --out_dir "$OUT" \
      --batch_size 1 \
      --max_new_tokens 48 \
      --repetition_penalty 1.12 \
      --no_repeat_ngram_size 4 \
      --clean_caption \
      --clean_max_sentences 1 \
      --flush_every 32 \
      --progress_every 32 \
      --limit "${GEN_LIMIT:-0}"

    "$PY" "$ROOT/scripts/eval/$EVAL_SCRIPT" \
      --predictions_jsonl "$OUT/predictions.jsonl" \
      --splits "$split" \
      --out_dir "$OUT/rule_qa"
  done
done

echo "[done] $RUN"
