# LTSGen EMNLP Benchmark Pipeline

This branch is the active benchmark/data-generation workstream for the EMNLP
submission track. It combines shared LTSGEN code with natural TS-QA,
multi-simulator QCC data, case studies, and paper-facing reports.

## Active Branches

- `shared-qcc-base`: common code and lightweight tests.
- `emnlp-benchmark-pipeline`: this benchmark/data and paper-asset branch.
- `caption-model-longline`: longer-term QCC caption model training branch.

## Main Directories

- `ts_cap/`: time-series caption generation utilities and dataset wrappers.
- `ts_align/`, `ts_align_scripts_v2/`: TS-text alignment infrastructure.
- `tslm/`: time-series-to-caption SFT/model baseline code.
- `scripts/`: shared generation, evaluation, training, remote, and utility
  entry points.
- `.research/`: benchmark contracts, trackers, generated examples, audits, and
  reports.
- `docs/case-studies/`: paper-facing and analysis case-study materials.
- `tests/`: regression tests for shared and benchmark utilities.
- `docs/`: engineering and branch-consolidation notes.
- `archive/`: legacy code retained for reference only.

## Artifact Policy

Keep small reproducibility data, schema reports, final tables, figures, and
case-study assets on this branch. Keep checkpoints, large simulator traces, and
full GPU output trees out of Git; use manifests and path references instead.
