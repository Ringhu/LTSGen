#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# Set LINKAPI_API_KEY before running when using the linkapi provider.
# Optional:
#   export LINKAPI_BASE_URL="https://api.linkapi.org/v1/"
#   export LINKAPI_MODEL="gpt-5"

INPUT="$ROOT_DIR/dataset/classification/UCRArchive_2018"
OUTDIR="$ROOT_DIR/gen_tst_dataset/ucr/train_shards"
mkdir -p "$OUTDIR"

# Dataset: ECG5000 (Length: 140)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name ECG5000 \
  --output "${OUTDIR}/ucr_ecg5000_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: CinCECGTorso (Length: 1639)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name CinCECGTorso \
  --output "${OUTDIR}/ucr_cincecgtorso_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: LargeKitchenAppliances (Length: 720)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name LargeKitchenAppliances \
  --output "${OUTDIR}/ucr_largekitchenappliances_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: PowerCons (Length: 144)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name PowerCons \
  --output "${OUTDIR}/ucr_powercons_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: Yoga (Length: 426)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name Yoga \
  --output "${OUTDIR}/ucr_yoga_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: GunPoint (Length: 150)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name GunPoint \
  --output "${OUTDIR}/ucr_gunpoint_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: CricketX (Length: 300)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name CricketX \
  --output "${OUTDIR}/ucr_cricketx_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: Ham (Length: 431)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name Ham \
  --output "${OUTDIR}/ucr_ham_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: Meat (Length: 448)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name Meat \
  --output "${OUTDIR}/ucr_meat_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: Earthquakes (Length: 512)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name Earthquakes \
  --output "${OUTDIR}/ucr_earthquakes_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: Lightning7  (Length: 319)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name Lightning7 \
  --output "${OUTDIR}/ucr_lightning7_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: CBF (Length: 128)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name CBF \
  --output "${OUTDIR}/ucr_cbf_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: Mallat (Length: 1024)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name Mallat \
  --output "${OUTDIR}/ucr_mallat_train.jsonl" \
  --task classification \
  --ucr_split train \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8
