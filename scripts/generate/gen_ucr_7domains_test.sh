#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# Set LINKAPI_API_KEY before running when using the linkapi provider.
# Optional:
#   export LINKAPI_BASE_URL="https://api.linkapi.org/v1/"
#   export LINKAPI_MODEL="gpt-5"

INPUT="$ROOT_DIR/dataset/classification/UCRArchive_2018"
OUTDIR="$ROOT_DIR/gen_tst_dataset/ucr/test_shards"
mkdir -p "$OUTDIR"



# Dataset: LargeKitchenAppliances (Length: 720)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name LargeKitchenAppliances \
  --output "${OUTDIR}/ucr_largekitchenappliances_test.jsonl" \
  --task classification \
  --ucr_split test \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: PowerCons (Length: 144)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name PowerCons \
  --output "${OUTDIR}/ucr_powercons_test.jsonl" \
  --task classification \
  --ucr_split test \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8



# Dataset: GunPoint (Length: 150)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name GunPoint \
  --output "${OUTDIR}/ucr_gunpoint_test.jsonl" \
  --task classification \
  --ucr_split test \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: CricketX (Length: 300)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name CricketX \
  --output "${OUTDIR}/ucr_cricketx_test.jsonl" \
  --task classification \
  --ucr_split test \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: Ham (Length: 431)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name Ham \
  --output "${OUTDIR}/ucr_ham_test.jsonl" \
  --task classification \
  --ucr_split test \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: Meat (Length: 448)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name Meat \
  --output "${OUTDIR}/ucr_meat_test.jsonl" \
  --task classification \
  --ucr_split test \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: Earthquakes (Length: 512)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name Earthquakes \
  --output "${OUTDIR}/ucr_earthquakes_test.jsonl" \
  --task classification \
  --ucr_split test \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8

# Dataset: Lightning7  (Length: 319)
python -m ts_cap.cli \
  --dataset ucr2018 \
  --input "$INPUT" \
  --ucr_name Lightning7 \
  --output "${OUTDIR}/ucr_lightning7_test.jsonl" \
  --task classification \
  --ucr_split test \
  --ucr_label_semantics readme \
  --llm_provider linkapi \
  --llm_model gpt-5 \
  --num_workers 8
