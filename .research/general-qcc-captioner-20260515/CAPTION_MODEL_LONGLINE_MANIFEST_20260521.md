# Caption Model Longline Manifest 2026-05-21

This branch is the compact model-training branch created during branch
consolidation. It keeps the learned-caption code path and audit context from
`codex/question-repair-20260519-ready` without copying full generated outputs.

## Retained In Git

- Training/evaluation/remote scripts for natural QCC GPU smoke and cross-domain
  caption experiments.
- Regression tests for the imported QCC builders and audits.
- Compact reports, summaries, audit JSON/Markdown files, and result
  `*.pathspec` files under `.research/general-qcc-captioner-20260515/`.
- Token-budget and factuality diagnostics small enough to review in git.

## Excluded From Git

- Checkpoints and model folders: `final_model/`, `checkpoint-*`,
  `*.safetensors`, `pytorch_model.bin`.
- Full generated prediction dumps from GPU runs.
- Full simulator traces and large intermediate datasets.
- EMNLP-facing benchmark figures and case-study assets; those belong on
  `emnlp-benchmark-pipeline`.

## Main Imported Areas

- `scripts/train/run_natural_qcc_gpu_smoke.py`
- `scripts/remote/run_natural_qcc_*`
- `scripts/eval/audit_natural_qcc_*`
- `scripts/eval/collect_natural_qcc_gpu_result_manifest.py`
- `scripts/generate/build_natural_qcc_*`
- `tslm/scripts/generate_multisim_v5_smoke.py`
- `tslm/scripts/train_multisim_v5_smoke.py`

## Source Branch

The selected training material came from:

- `codex/question-repair-20260519-ready`

The branch was not merged wholesale. Files were imported by path whitelist so
that benchmark/paper assets and generated GPU outputs remain separated.
