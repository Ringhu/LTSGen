# LTSGEN Shared QCC Base

This branch is the shared code base for the two active LTSGEN workstreams after
the 2026-05-21 branch cleanup.

It deliberately does not declare a single active research contract. Research
contracts, trackers, generated artifacts, and case-study reports live on the
workstream branches:

- `emnlp-benchmark-pipeline`
- `caption-model-longline`

Use this branch for reusable implementation only: `ts_cap/`, `ts_align/`,
`ts_align_scripts_v2/`, `tslm/`, `scripts/`, and tests.

Large generated outputs should not be added here. Prefer small fixtures and
manifests when a shared test needs data.
