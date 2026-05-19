#!/usr/bin/env bash
set -euo pipefail

PROFILE="${PROFILE:-a100}"
BRANCH="${BRANCH:-codex/question-repair-20260519-ready}"
REMOTE="${REMOTE:-origin}"
SSH_TARGET="${SSH_TARGET:-$PROFILE}"
PUSH_RESULTS="${PUSH_RESULTS:-0}"

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
echo "[launch] push results: $PUSH_RESULTS"

ssh -o BatchMode=yes "$SSH_TARGET" \
  "PROFILE='$PROFILE' ROOT_OVERRIDE='$ROOT' BRANCH='$BRANCH' REMOTE='$REMOTE' LOG_PATH='$LOG_PATH' PUSH_RESULTS='$PUSH_RESULTS' bash -s" <<'REMOTE_SCRIPT'
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

if [[ "$PUSH_RESULTS" == "1" ]]; then
  python3 scripts/eval/audit_natural_qcc_objective_completion.py || true
  python3 scripts/eval/collect_natural_qcc_gpu_result_manifest.py
  git add --pathspec-from-file=.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_gpu_result_manifest_20260520.pathspec
  if git diff --cached --quiet; then
    echo "[remote] no result artifact changes to commit"
  else
    git commit -m "Add natural QCC GPU pair results"
    git push "$REMOTE" "$BRANCH"
  fi
fi
REMOTE_SCRIPT
