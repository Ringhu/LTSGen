# LTSGEN Caption Model Longline

This branch owns the long-running learned-caption workstream after the
2026-05-21 branch consolidation.

## Active Direction

Train and audit question-conditioned evidence captioners for time-series QA.
The method output remains natural-language evidence captions; structured slots,
deterministic extractors, and rule QA are support tools for supervision,
verification, diagnostics, and oracle baselines.

## Relationship To Other Branches

- `shared-qcc-base` is the compact shared code base.
- `emnlp-benchmark-pipeline` owns benchmark/data-generation assets, paper-facing
  case studies, and final figures.
- `caption-model-longline` owns model-training scripts, GPU launch wrappers,
  result audits, and compact manifests/reports for learned-caption experiments.

## Artifact Policy

Keep this branch lightweight enough to remain a usable code branch:

- commit training/eval/remote scripts and regression tests;
- keep small audit reports, summaries, and manifest/pathspec files under
  `.research/`;
- do not commit checkpoints, full simulator traces, full prediction dumps,
  `final_model/`, `checkpoint-*`, `*.safetensors`, or `pytorch_model.bin`;
- keep large datasets and generated GPU outputs on the GPU/cluster storage they
  were produced on, referenced by manifest when needed.

## Guardrails

- QCC output must be natural-language evidence captions.
- Do not treat executor-at-inference or JSON slot extraction as the final method
  unless the user explicitly changes direction.
- Do not resurrect archived ShapeShift/CPR instructions as active direction.
- Use `python3`, not `python`, in local commands.
- Do not commit local API keys, checkpoints, traces, or large simulator data.
- Do not revert unrelated dirty work in other worktrees.
