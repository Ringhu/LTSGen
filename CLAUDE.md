# LTSGEN EMNLP Benchmark Pipeline

This branch owns the near-term benchmark/data-generation line for an EMNLP
submission.

Active goal:

- create a multi-simulator natural TS-QA benchmark;
- generate natural-language question-conditioned evidence captions;
- keep answer grounding verifier-checkable from simulator state, traces, or
  deterministic support slots;
- preserve reports, figures, and small reproducibility artifacts needed for the
  paper.

Shared reusable code should be factored through `shared-qcc-base`. Learned
caption-model training and GPU diagnostics belong on `caption-model-longline`.

Do not revive the old ShapeShift/CPR route as active work unless explicitly
requested.
