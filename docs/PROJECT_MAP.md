# Project Map

This branch is the EMNLP-facing benchmark/data pipeline branch. It keeps the
shared code needed to reproduce the benchmark assets, plus small generated data,
audits, reports, and case studies that define the current submission direction.

Generated benchmark assets live here. Large checkpoints, long GPU output trees,
and model-training diagnostics belong on `caption-model-longline` or external
storage, with manifests retained when useful.

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
- `.research/`: benchmark contracts, data assets, audits, reports, and archived
  legacy experiment artifacts.
- `docs/research/`: historical engineering notes retained for orientation.
- `archive/`: legacy code and old scripts retained for reference only.

## Workstream Branches

- `emnlp-benchmark-pipeline` owns benchmark data, multi-simulator QA/caption
  generation, case studies, and EMNLP-facing reports.
- `caption-model-longline` owns model-training datasets, GPU smoke outputs,
  caption-quality audits, and long-horizon captioner diagnostics.

## Practical Rule

If a file is a reusable implementation dependency for both workstreams, keep it
here unless it is already maintained on `shared-qcc-base`. If it is a large model
checkpoint, long GPU output tree, or caption-model-only diagnostic, keep it on
`caption-model-longline` or external storage. If it is an old benchmark/data
artifact that is not part of the current EMNLP route, move it under
`.research/archive/` rather than deleting it.
