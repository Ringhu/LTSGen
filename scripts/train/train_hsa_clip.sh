#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-2}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export CUDA_LAUNCH_BLOCKING="${CUDA_LAUNCH_BLOCKING:-1}"

TRAIN_JSONL="$ROOT_DIR/gen_tst_dataset/ucr/merged/ucr_train_merged.jsonl"
VAL_JSONL="$ROOT_DIR/gen_tst_dataset/ucr/test_shards/ucr_largekitchenappliances_test.jsonl"
OUT_DIR="$ROOT_DIR/runs/hsa_clip_v2_hybrid"

# ----------------------------
# A) 推荐：hybrid（全局Chronos2 + 局部patch）
# ----------------------------
python -m ts_align_scripts_v2.train_hsa_clip \
  --train_jsonl "$TRAIN_JSONL" \
  --val_jsonl "$VAL_JSONL" \
  --out_dir "$OUT_DIR" \
  --epochs 20 \
  --batch_size 64 \
  --lr 1e-4 \
  --weight_decay 1e-4 \
  --warmup_ratio 0.1 \
  --min_lr_ratio 0.01 \
  --grad_clip 1.0 \
  --amp 1 \
  --seed 0 \
  \
  --global_captions "global_en,domain_en" \
  --max_global_texts_per_sample 1 \
  --positive_key instance \
  \
  --local_caption local_zh \
  --max_local_per_sample 4 \
  --lambda_local 0.5 \
  --lambda_loc 0.5 \
  \
  --time_backbone hybrid \
  --chronos2_model "autogluon/chronos-2" \
  --chronos2_device_map cuda \
  --chronos2_dtype bfloat16 \
  --fine_tune_chronos2 0 \
  --chronos2_channel_pool first \
  \
  --hier_pool 1 \
  --hier_stride 4 \
  --hier_pool_for_global 1 \
  \
  --patch_size 16 \
  --d_model 256 \
  --time_layers 6 \
  --time_heads 8 \
  --d_embed 256 \
  --text_model "sentence-transformers/all-MiniLM-L6-v2" \
  --freeze_text 1 \
  --dropout 0.1 \
  \
  --random_crop 0 \
  --crop_lengths "96,128,192,256,384,512" \
  --strip_numbers_on_crop 1


# ----------------------------
# B) baseline：纯patch（不依赖Chronos2）
# ----------------------------
# OUT_DIR=runs/hsa_clip_v2_patch
# python -m ts_align_scripts_v2.train_hsa_clip \
#   --train_jsonl "$TRAIN_JSONL" \
#   --val_jsonl "$VAL_JSONL" \
#   --out_dir "$OUT_DIR" \
#   --epochs 10 \
#   --batch_size 64 \
#   --lr 1e-4 \
#   --weight_decay 1e-4 \
#   --warmup_ratio 0.1 \
#   --amp 1 \
#   --seed 0 \
#   \
#   --global_captions "global_zh" \
#   --max_global_texts_per_sample 1 \
#   --positive_key instance \
#   \
#   --local_caption local_zh \
#   --max_local_per_sample 4 \
#   --lambda_local 0.5 \
#   --lambda_loc 0.5 \
#   \
#   --time_backbone patch \
#   \
#   --patch_size 16 \
#   --d_model 256 \
#   --time_layers 6 \
#   --time_heads 8 \
#   --d_embed 256 \
#   --text_model "sentence-transformers/all-MiniLM-L6-v2" \
#   --freeze_text 1 \
#   --dropout 0.1
