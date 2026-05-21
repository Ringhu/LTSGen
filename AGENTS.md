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

## Natural QCC Research Route

The active Natural QCC route is documented in:

`.research/general-qcc-captioner-20260515/NATURAL_QCC_RESEARCH_ROUTE_AND_REVIEWER_GATE_20260521_ZH.md`

Use that document as the current working interpretation when creating,
reviewing, repairing, or scaling TS-QA/QCC data.

The agreed route is **scenario-first and verifier-backed**:

1. Start from a domain scenario or simulator intervention, such as grid line
   outage, building supply reserve, traffic recovery, water leakage, AIOps
   resource pressure, or financial drawdown.
2. Sample or export a time-series window from simulator/trace/historical data.
3. Write a natural QA item with scene, variables, time axis, decision rule,
   question, and human-readable options.
4. Compute the gold answer using deterministic rules, simulator state, trace
   arrays, or counterfactual differences.
5. Use support slots only for supervision, oracle evidence, and verification.
   They must not become the reader-facing question or a slot dump caption.
6. Generate an evidence caption that first describes the relevant time-series
   pattern, then gives concise answer-supporting evidence.
7. Run reviewer gates before scaling or training.

## Reviewer Gate Policy

Reviewer gates are a triage system, not an answer oracle. LLMs may critique
wording, naturalness, answerability, and risk, but must not decide the gold
answer.

Always separate:

- `qa_seed_ready`: whether the QA item itself can be used as a seed.
- `caption_train_ready`: whether the caption target can train an evidence-only
  caption model.

Required gate layers:

- deterministic verification: source trace exists, values are present, support
  slots/gold answer are recomputable, answer/options are consistent, no hidden
  answer leakage;
- naturalness/self-contained review: scene, variables, time axis, thresholds,
  negative cases, and options are understandable without simulator-specific
  background;
- caption quality review: caption is answer-focused, summarizes the relevant
  time-series shape, gives concise verifiable evidence, and avoids slot dumps,
  option letters, `Answer label`, and `supports the answer` templates.

GPT data-only probes are diagnostic only. If a strong model answers incorrectly
when given only scene/rules/variables/options/values, mark the row for error
attribution. Do not automatically reject it: distinguish model capability
failure from ambiguous variables/rules, insufficient compact features, option
mismatch, or a valid hard case.

Current reviewer artifacts:

- `scripts/eval/review_natural_qcc_seed_quality.py`
- `.research/general-qcc-captioner-20260515/seed_quality_review_v1_20260521/`

Do not scale data or start qcond/no-question training from a seed set until the
reviewer gate shows the intended readiness for both QA and caption targets.
