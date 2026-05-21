#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/cluster/home/user1/hulining/LTSGEN}"
DATA_DIR="${DATA_DIR:-$ROOT/.research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521}"
OUT_FILE="${OUT_FILE:-}"
MAX_DEPTH="${MAX_DEPTH:-6}"
MAX_EXAMPLE_MATCHES="${MAX_EXAMPLE_MATCHES:-80}"
CUDA_VISIBLE_DEVICES_FOR_SPECS="${CUDA_VISIBLE_DEVICES_FOR_SPECS:-2}"
PORT_FOR_SPECS="${PORT_FOR_SPECS:-9411}"
TENSOR_PARALLEL_SIZE_FOR_SPECS="${TENSOR_PARALLEL_SIZE_FOR_SPECS:-1}"
MAX_MODEL_LEN_FOR_SPECS="${MAX_MODEL_LEN_FOR_SPECS:-32768}"
DTYPE_FOR_SPECS="${DTYPE_FOR_SPECS:-bfloat16}"
GPU_MEMORY_UTILIZATION_FOR_SPECS="${GPU_MEMORY_UTILIZATION_FOR_SPECS:-0.88}"

# Space-separated roots. Override this on A100 if the storage layout differs.
DISCOVERY_ROOTS="${DISCOVERY_ROOTS:-/cluster/home/user1/hulining/swift /cluster/home/hulining/swift /cluster/home/user1/hulining/TSModel/OpenTSLM /cluster/home/user1/fenghaoran/model /cluster/home/user1/hulining/.cache/huggingface/hub /cluster/home/hulining/.cache/huggingface/hub}"

emit() {
  printf '%s\n' "$*"
}

slugify() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/_/g; s/^_+//; s/_+$//'
}

is_qwen_config() {
  local cfg="$1"
  local dir
  dir="$(dirname "$cfg")"
  [[ "$dir" =~ [Qq]wen ]] && return 0
  grep -Eiq '"model_type"[[:space:]]*:[[:space:]]*"qwen|qwen' "$cfg" 2>/dev/null
}

print_header() {
  emit "# Public Raw TSQA Qwen A100 Discovery"
  emit
  emit "- root: \`$ROOT\`"
  emit "- data_dir: \`$DATA_DIR\`"
  emit "- max_depth: \`$MAX_DEPTH\`"
  emit "- discovery_roots:"
  for root in $DISCOVERY_ROOTS; do
    emit "  - \`$root\`"
  done
  emit
}

print_deploy_examples() {
  emit "## Deployment Examples"
  emit
  local tmp
  tmp="$(mktemp)"
  for root in $DISCOVERY_ROOTS; do
    [[ -d "$root" ]] || continue
    find "$root" -maxdepth "$MAX_DEPTH" -type f \
      \( -name '*.sh' -o -name '*.py' -o -name '*.md' -o -name '*.yml' -o -name '*.yaml' -o -name '*.txt' \) \
      -print 2>/dev/null
  done | sort -u >"$tmp"

  if [[ ! -s "$tmp" ]]; then
    emit "No candidate deployment files found under the configured roots."
    emit
    rm -f "$tmp"
    return
  fi

  local matcher=(grep -nEi 'qwen|vllm|swift|api_server|served-model-name|model_path|MODEL_PATH|CUDA_VISIBLE_DEVICES')
  local count=0
  while IFS= read -r file; do
    if "${matcher[@]}" "$file" >/tmp/public_raw_tsqa_qwen_discovery_match.txt 2>/dev/null; then
      while IFS= read -r line; do
        emit "$file:$line"
        count=$((count + 1))
        if (( count >= MAX_EXAMPLE_MATCHES )); then
          emit
          emit "... truncated after MAX_EXAMPLE_MATCHES=$MAX_EXAMPLE_MATCHES"
          rm -f "$tmp" /tmp/public_raw_tsqa_qwen_discovery_match.txt
          emit
          return
        fi
      done </tmp/public_raw_tsqa_qwen_discovery_match.txt
    fi
  done <"$tmp"

  if (( count == 0 )); then
    emit "No Qwen/vLLM/SWIFT deployment references found in candidate files."
  fi
  rm -f "$tmp" /tmp/public_raw_tsqa_qwen_discovery_match.txt
  emit
}

print_model_candidates() {
  emit "## Qwen Model Directory Candidates"
  emit
  local tmp
  tmp="$(mktemp)"
  for root in $DISCOVERY_ROOTS; do
    [[ -d "$root" ]] || continue
    find "$root" -maxdepth "$MAX_DEPTH" -type f -name config.json -print 2>/dev/null
  done | sort -u >"$tmp"

  local spec_tmp
  spec_tmp="$(mktemp)"
  local idx=0
  while IFS= read -r cfg; do
    if is_qwen_config "$cfg"; then
      local dir base slug served port
      dir="$(dirname "$cfg")"
      base="$(basename "$dir")"
      served="$base"
      slug="$(slugify "$base")"
      if [[ -z "$slug" ]]; then
        slug="qwen_candidate_$idx"
      fi
      port=$((PORT_FOR_SPECS + idx))
      emit "- \`$dir\`"
      if [[ -f "$dir/tokenizer_config.json" ]]; then
        emit "  - tokenizer: yes"
      else
        emit "  - tokenizer: missing tokenizer_config.json"
      fi
      printf '%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
        "$slug" \
        "$served" \
        "$dir" \
        "$CUDA_VISIBLE_DEVICES_FOR_SPECS" \
        "$port" \
        "$TENSOR_PARALLEL_SIZE_FOR_SPECS" \
        "$MAX_MODEL_LEN_FOR_SPECS" \
        "$DTYPE_FOR_SPECS" \
        "$GPU_MEMORY_UTILIZATION_FOR_SPECS" >>"$spec_tmp"
      idx=$((idx + 1))
    fi
  done <"$tmp"

  if [[ ! -s "$spec_tmp" ]]; then
    emit "No Qwen model directories found. Try increasing MAX_DEPTH or overriding DISCOVERY_ROOTS."
    rm -f "$tmp" "$spec_tmp"
    emit
    return
  fi

  emit
  emit "## MODEL_SPECS Candidate"
  emit
  emit "Use one or more lines below with \`run_public_raw_tsqa_qwen_suite_a100.sh\`:"
  emit
  emit '```bash'
  emit "MODEL_SPECS=\$'$(sed ':a;N;$!ba;s/\n/\\n/g' "$spec_tmp")' \\"
  emit "scripts/remote/run_public_raw_tsqa_qwen_suite_a100.sh"
  emit '```'
  emit
  emit "Raw lines:"
  emit
  emit '```text'
  cat "$spec_tmp"
  emit '```'
  emit
  rm -f "$tmp" "$spec_tmp"
}

main() {
  if [[ -n "$OUT_FILE" ]]; then
    mkdir -p "$(dirname "$OUT_FILE")"
    {
      print_header
      print_deploy_examples
      print_model_candidates
    } | tee "$OUT_FILE"
  else
    print_header
    print_deploy_examples
    print_model_candidates
  fi
}

main "$@"
