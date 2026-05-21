# Branch Consolidation 2026-05-21

This repository was split into three active local branches:

- `shared-qcc-base`: compact shared engineering base.
- `emnlp-benchmark-pipeline`: benchmark/data pipeline and EMNLP-facing assets.
- `caption-model-longline`: long-running QCC caption model training assets.

This branch is `caption-model-longline`. It selectively imports the useful
training, audit, and remote-run pieces from
`codex/question-repair-20260519-ready`, while keeping large generated assets out
of git. The retained `.research/` files are reports, summaries, manifests, and
pathspecs; full predictions and checkpoint outputs should remain on GPU/cluster
storage.

Archived or reference-only branches:

- `ext/a-gpt-compare`: older TSAQA/ChatTS comparison assets.
- `p0-case-study-images-20260511`: case-study images.
- `report/20260413-assets`: older report assets.
- `report/2026-04-21`, `fredqa-rerun-zh-20260512`,
  `codex/multisim-qcc-v1-results-20260517`: already contained in the newer
  benchmark branch history and retained as references.

The original dirty worktree at `/home/cris/Research/LTSGEN` was not changed by
the consolidation work. New branches were built in sibling worktrees.
