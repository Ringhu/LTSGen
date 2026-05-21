# LTSGen Shared QCC Base

This branch is a compact shared engineering base. It keeps reusable code and
tests while leaving research artifacts to the two active workstream branches.

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
- `scripts/`: shared generation, evaluation, training, remote, and utility
  entry points.
- `tests/`: lightweight regression tests for shared utilities.
- `docs/`: engineering notes for the shared code base.
- `archive/`: legacy code retained for reference only.

## Artifact Policy

Generated benchmark datasets, simulator traces, prediction dumps, GPU run
outputs, paper figures, and case studies do not belong on this branch. Keep
those in the workstream branch that owns them, and prefer manifests or small
fixtures when shared code needs examples.
