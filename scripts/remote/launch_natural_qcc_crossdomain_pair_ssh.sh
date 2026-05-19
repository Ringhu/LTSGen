#!/usr/bin/env bash
set -euo pipefail

PROFILE="${PROFILE:-a100}"
BRANCH="${BRANCH:-codex/question-repair-20260519-ready}"
REMOTE="${REMOTE:-origin}"
SSH_TARGET="${SSH_TARGET:-$PROFILE}"

case "$PROFILE" in
  a100)
    DEFAULT_ROOT="/cluster/home/user1/hulining/LTSGEN"
    ;;
  3090)
    DEFAULT_ROOT="/cluster/home/hulining/LTSGEN"
    ;;
  *)
    echo "[error] unsupported PROFILE=$PROFILE; use a100 or 3090" >&2
    exit 2
    ;;
esac

ROOT="${ROOT_OVERRIDE:-$DEFAULT_ROOT}"
LOG_DIR="$ROOT/.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
LOG_PATH="${LOG_PATH_OVERRIDE:-$LOG_DIR/natural_qcc_crossdomain_pair_${PROFILE}_$(date +%Y%m%d_%H%M%S).log}"

echo "[launch] ssh target: $SSH_TARGET"
echo "[launch] profile: $PROFILE"
echo "[launch] remote root: $ROOT"
echo "[launch] branch: $BRANCH"
echo "[launch] log: $LOG_PATH"

ssh -o BatchMode=yes "$SSH_TARGET" \
  "PROFILE='$PROFILE' ROOT_OVERRIDE='$ROOT' BRANCH='$BRANCH' REMOTE='$REMOTE' LOG_PATH='$LOG_PATH' bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

cd "$ROOT_OVERRIDE"
git fetch "$REMOTE"
git checkout "$BRANCH"
git pull --ff-only "$REMOTE" "$BRANCH"

mkdir -p "$(dirname "$LOG_PATH")"
{
  echo "[remote] host=$(hostname)"
  echo "[remote] cwd=$(pwd)"
  echo "[remote] branch=$(git rev-parse --abbrev-ref HEAD)"
  echo "[remote] head=$(git rev-parse HEAD)"
  echo "[remote] profile=$PROFILE"
  date
  PROFILE="$PROFILE" scripts/remote/run_natural_qcc_crossdomain_pair_a100.sh
  date
} 2>&1 | tee "$LOG_PATH"
REMOTE_SCRIPT
