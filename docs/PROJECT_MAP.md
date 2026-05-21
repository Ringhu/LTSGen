# Project Map

This branch is a shared code base, not an artifact branch. Generated data and
paper materials are intentionally kept out of `shared-qcc-base`.

## Directory Roles

- `ts_cap/`: reusable time-series caption utilities and dataset wrappers.
- `ts_align/`: TS-text alignment datasets, losses, metrics, and model modules.
- `ts_align_scripts_v2/`: alignment training, retrieval, grounding, and
  visualization entry points.
- `tslm/`: time-series-to-caption SFT/model baseline code.
- `scripts/generate/`: shared data and prompt construction utilities.
- `scripts/eval/`: shared evaluation and audit utilities.
- `scripts/train/`: shared training entry points.
- `scripts/remote/`: remote run helpers that are not tied to one artifact set.
- `scripts/utils/`: small operational helpers.
- `tests/`: lightweight regression tests for shared utilities.
- `docs/research/`: historical engineering notes retained for orientation.
- `archive/`: legacy code and old scripts retained for reference only.

## Workstream Branches

- `emnlp-benchmark-pipeline` owns benchmark data, multi-simulator QA/caption
  generation, case studies, and EMNLP-facing reports.
- `caption-model-longline` owns model-training datasets, GPU smoke outputs,
  caption-quality audits, and long-horizon captioner diagnostics.

## Practical Rule

If a file is a reusable implementation dependency for both workstreams, keep it
here. If it is a generated artifact, paper figure, prediction dump, simulator
trace, or workstream-specific report, keep it on the owning workstream branch.
