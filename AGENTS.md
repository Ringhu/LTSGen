# LTSGEN EMNLP Benchmark Pipeline

This branch is the short-track benchmark/data-generation workstream for the
EMNLP submission target.

## Active Direction

Build a multi-simulator benchmark around natural TS-QA, question-conditioned
evidence captions, and verifier-checkable QA generation. This branch owns
benchmark assets, case studies, reports, and data-pipeline artifacts.

The companion longline branch is `caption-model-longline`, which owns model
training and captioner diagnostics. Shared reusable code should land first in
`shared-qcc-base` when possible.

## Primary Scope

- Multi-simulator QA/caption generation across Grid2Op, CityLearn, FinRL,
  traffic, water, and AIOpsLab-style sources.
- Natural TS-QA candidate generation, rewriting, review, quality audit, and
  case-study assets.
- EMNLP-facing reports, figures, artifact inventories, schema reports, and
  small reproducibility datasets.
- Benchmark diagnostics such as question-only, generic caption, oracle evidence
  caption, statistical caption, and sampled-number baselines.

## Boundaries

- Do not treat tool/executor inference as the final QCC method on this branch.
- Do not use archived ShapeShift/CPR files as active instructions.
- Do not add checkpoints, large simulator traces, or full GPU output trees.
- Prefer manifest/path references for large generated artifacts.
- Keep case-study reports Chinese-first by default while preserving method,
  task-family, and path names in English/code form.

## Useful Branches

- `shared-qcc-base`: common code and tests.
- `caption-model-longline`: learned caption model training route.
- `ext/a-gpt-compare`, `p0-case-study-images-20260511`,
  `report/20260413-assets`: archived/reference-only branches.
