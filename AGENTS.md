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
- Local SSD space is limited. Do not copy large datasets, checkpoints, or full
  GPU result trees from remote machines to local storage; keep large artifacts on
  A100/3090 storage and reference them by manifest or path.

## Remote Machines

- A100 SSH alias: `a100`. Use it for large models, long runs, and experiments
  needing more than 24GB VRAM. A100 code root is `/cluster/home/user1/hulining/`.
  Default GPU preference is `CUDA_VISIBLE_DEVICES=2` unless a run-specific
  command says otherwise.
- 3090 SSH alias: `3090`. Use it for small tests, debugging, and experiments
  that fit in 24GB VRAM. 3090 code root is `/cluster/home/hulining/`.
- A100 conda environments known from the global machine notes include
  `opentslm`, `chatts`, `tsgen`, `tsrl`, `tsci`, and `ptst`.
- 3090 conda environments include `timecraft`, `ts`, `tslib`, and
  `autotimes`.
- Prefer remote commands such as `ssh a100 "..."` and `ssh 3090 "..."` for GPU
  checks, tmux control, and experiment launch. Use SSHFS only for scoped file
  inspection/editing; broad grep/find over mounted remote trees is slow.
- A100 model/deployment assets may live outside this repo, especially under
  `/cluster/home/user1/hulining/TSModel/`, `/cluster/home/user1/hulining/swift`
  if present, and `/cluster/home/user1/fenghaoran/model/`.

## Useful Branches

- `shared-qcc-base`: common code and tests.
- `caption-model-longline`: learned caption model training route.
- `ext/a-gpt-compare`, `p0-case-study-images-20260511`,
  `report/20260413-assets`: archived/reference-only branches.
