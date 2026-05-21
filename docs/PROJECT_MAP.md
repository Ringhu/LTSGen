# Project Map

This branch is `caption-model-longline`. It is the compact workstream for
Natural QCC caption-model training, caption-quality diagnostics, and long-running
model smoke results.

Generated artifacts are kept only when they are small and useful for current
model-design decisions. Large simulator traces, checkpoints, prediction dumps,
and superseded case-study banks should stay in history, on GPU storage, or on
their owning artifact branch.

## Directory Roles

- `tslm/`: time-series-to-caption SFT/model baseline code.
- `scripts/generate/`: Natural QCC/TS-QA data construction and prompt builders.
- `scripts/eval/`: audit, factuality, caption-quality, and probe utilities.
- `scripts/train/`: local training entry points.
- `scripts/remote/`: GPU/cluster launch helpers.
- `tests/`: lightweight regression tests for imported builders and audits.
- `.research/general-qcc-captioner-20260515/`: compact reports, summaries,
  manifests, and current seed artifacts for the caption-model route.
- `docs/`: branch organization notes and project maps.
- `archive/`: legacy code retained for reference only.

## Active Research Files

- `.research/general-qcc-captioner-20260515/CAPTION_MODEL_LONGLINE_MANIFEST_20260521.md`
- `.research/general-qcc-captioner-20260515/CAPTION_MODEL_LONGLINE_ACTIVE_ARCHIVE_INDEX_20260521_ZH.md`
- `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/`
- `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/`
- `.research/general-qcc-captioner-20260515/natural_qcc_case_quality_v1_20260521/`
- `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/`
- `.research/general-qcc-captioner-20260515/scenario_first_real_source_smoke_v2_20260521/`

## Workstream Branches

- `caption-model-longline` owns model-training datasets, GPU smoke outputs,
  caption-quality audits, and long-horizon captioner diagnostics.
- `emnlp-benchmark-pipeline` owns benchmark/data pipeline assets and
  EMNLP-facing reports.
- `shared-qcc-base` owns reusable shared code that is not tied to one
  workstream's generated artifacts.

## Practical Rule

Keep reusable implementation and compact current-route evidence on this branch.
Do not restore old branches wholesale. If a historical artifact is needed,
restore only the specific path and document it in the active/archive index.
