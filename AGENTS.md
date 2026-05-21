# LTSGEN Shared QCC Base

This branch is the shared engineering base for the post-2026-05-21
consolidation. It is intentionally not a paper or experiment branch.

## Role

Use this branch for code that both active workstreams need:

- reusable time-series caption and wrapper code in `ts_cap/`;
- TS-text alignment infrastructure in `ts_align/` and `ts_align_scripts_v2/`;
- SFT/model plumbing in `tslm/`;
- shared generation, evaluation, training, remote, and utility scripts under
  `scripts/`;
- shared unit tests.

The active research artifacts are kept on workstream branches:

- `emnlp-benchmark-pipeline`: short-to-medium horizon benchmark/data pipeline
  for the EMNLP submission track.
- `caption-model-longline`: longer-term model-training track for learning a
  question-conditioned evidence captioner.

## Artifact Policy

Do not add large generated datasets, simulator traces, predictions, GPU outputs,
or paper case-study assets to this branch. Put those on the appropriate
workstream branch and prefer manifests, reports, and small fixtures over full
intermediate outputs.

## Guardrails

- Keep shared code route-neutral where possible.
- Do not resurrect archived ShapeShift/CPR instructions as active project
  direction.
- Use `python3`, not `python`, in local commands.
- Do not commit local API keys, checkpoints, traces, or large simulator data.
- Do not revert unrelated dirty work in other worktrees.
