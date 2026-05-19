#!/usr/bin/env bash
set -euo pipefail

PROFILE="${PROFILE:-a100}"

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
BASE="$ROOT/.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
QCOND_RUN="${QCOND_RUN_OVERRIDE:-$BASE/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520}"
NOQ_RUN="${NOQ_RUN_OVERRIDE:-$BASE/tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520}"
COMPARE_OUT="${COMPARE_OUT_OVERRIDE:-$BASE/tsrlm_natural_qcc_crossdomain_qcond_vs_noquestion_audit_20260520.json}"

cd "$ROOT"

MODE=qcond RUN_OVERRIDE="$QCOND_RUN" scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh "$@"
MODE=no_question RUN_OVERRIDE="$NOQ_RUN" scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh "$@"

if [[ " $* " == *" --dry_run "* ]]; then
  "$PY" scripts/eval/audit_natural_qcc_gpu_qcond_vs_noquestion.py \
    --qcond_run_dir "$QCOND_RUN" \
    --no_question_run_dir "$NOQ_RUN" \
    --out "$COMPARE_OUT" || true
  exit 0
fi

"$PY" scripts/eval/audit_natural_qcc_gpu_qcond_vs_noquestion.py \
  --qcond_run_dir "$QCOND_RUN" \
  --no_question_run_dir "$NOQ_RUN" \
  --out "$COMPARE_OUT"
