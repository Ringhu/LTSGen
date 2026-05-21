# LTSGen Caption Model Longline

This branch contains the learned-caption training line for General QCC. It is
based on `shared-qcc-base` and selectively imports the useful parts of
`codex/question-repair-20260519-ready` without turning the branch into a full
artifact mirror.

## Active Branches

- `shared-qcc-base`: common code, tests, and lightweight documentation.
- `emnlp-benchmark-pipeline`: benchmark/data generation and EMNLP-facing
  artifacts.
- `caption-model-longline`: longer-term QCC caption model training and
  diagnostics.

## Main Directories

- `ts_cap/`: time-series caption generation utilities and dataset wrappers.
- `ts_align/`, `ts_align_scripts_v2/`: TS-text alignment infrastructure.
- `tslm/`: time-series-to-caption SFT/model baseline code.
- `scripts/train/`: local/remote training pipeline entry points.
- `scripts/eval/`: QCC caption QA, factuality, manifest, and objective audits.
- `scripts/remote/`: A100/3090 launch wrappers.
- `scripts/generate/`: small QCC SFT/control builders used by training.
- `tests/`: regression tests for the imported training/audit path.
- `.research/`: compact longline reports and manifests only.
- `docs/`: branch consolidation and engineering notes.
- `archive/`: legacy code retained for reference only.

## Artifact Policy

This branch keeps reports, summaries, and manifest/pathspec files needed to
reproduce or audit training runs. It intentionally excludes checkpoints, full
prediction dumps, `final_model/`, `checkpoint-*`, `*.safetensors`,
`pytorch_model.bin`, large simulator traces, and paper case-study figures.
