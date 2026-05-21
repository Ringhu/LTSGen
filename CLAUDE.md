# LTSGEN Caption Model Longline

This branch is the model-training workstream for learned General QCC evidence
captioners after the 2026-05-21 branch cleanup.

Use it for:

- QCC SFT and caption-generation scripts in `tslm/` and `scripts/train/`;
- GPU launch wrappers in `scripts/remote/`;
- caption QA, factuality, manifest, and objective-completion audits in
  `scripts/eval/`;
- small regression tests for the above;
- compact `.research/` reports and manifests needed to understand the training
  line.

Do not use this branch as the benchmark/paper asset branch. Multi-simulator
benchmark data generation, case-study figures, and EMNLP-facing reports belong
on `emnlp-benchmark-pipeline`.

Large generated outputs should not be committed here. Prefer manifest/pathspec
files, summaries, and small fixtures; leave checkpoints and full prediction
dumps on GPU/cluster storage.
