# Grid2Op Context-Card Rerun Plan

**Date:** 2026-05-13
**Status:** COMPLETED protocol patch

## Motivation

The current Grid2Op case-study questions assume too much domain knowledge. A
question such as "if line 5 is disconnected..." is not fair unless the answerer
knows what a Grid2Op trace represents, what a power line is, what `rho` means,
and how factual/counterfactual traces should be compared.

This patch adds a fixed context card to the evaluation prompt and the
case-study report. The old no-context results remain valid only as a diagnostic
of underspecified prompts; they should not be presented as the final
Grid2Op-facing protocol.

## Hypothesis

Adding a concise Grid2Op context card will reduce accidental guessing caused by
missing background, while preserving the key comparison: generic captions still
omit task-specific evidence, and oracle evidence captions remain the short,
verifiable upper-bound interface.

## Success / Failure Signals

Success:
- `meta_only` should remain near random on observation and counterfactual tasks
  because background alone should not reveal answers.
- `oracle_evidence_caption` should stay near 1.0 accuracy.
- `generic_caption` may improve on trivial schema-sensitive cases, but should
  remain clearly below oracle evidence on evidence-demanding tasks.
- Prompt length increase from the context card should be small relative to
  sampled numeric prompts.

Failure:
- If `meta_only` becomes very high (>0.50 on either Grid2Op split), the context
  card or question wording leaks answer priors.
- If `generic_caption` matches oracle on most evidence-demanding tasks, the
  case design is not isolating question-conditioned evidence.
- If the context card makes sampled numeric prompts dominate oracle evidence,
  the paper claim must shift from "evidence captions are more reliable" to a
  narrower efficiency-only claim.

## Output Paths

Observation rerun:
- Data: `.research/real-grid2op-20260513/grid2op_real_v1_obs/grid2op_real_v1_obs.jsonl`
- Output: `.research/real-grid2op-20260513/grid2op_real_v1_obs/full72_core_sweep_with_context_v1/`

Counterfactual rerun:
- Data: `.research/real-grid2op-20260513/grid2op_real_cf_v3_compact_fixed/grid2op_real_cf_v3_compact_fixed.jsonl`
- Output: `.research/real-grid2op-20260513/grid2op_real_cf_v3_compact_fixed/sampling_sweep_18_with_context_v1/`

Case study:
- `docs/case-studies/20260513-grid2op/grid2op_case_study.md`
- Add a visible "背景卡片" section to each case.

## Run Order

1. Add `context_card` construction to the evaluator.
2. Add the same context card to the case-study report.
3. Dry-run prompt sizes for observation and counterfactual splits.
4. Run the same LLM conditions as the previous no-context runs.
5. Compare old vs new metrics and update the progress report.

## v1 Result and Protocol Issue

Completed with-context-v1 reruns:

Observation:
- Output: `.research/real-grid2op-20260513/grid2op_real_v1_obs/full72_core_sweep_with_context_v1/`
- `meta_only`: 0.4583
- `generic_caption`: 0.3472
- `oracle_evidence_caption`: 1.0000
- `numbers_sampled_32/64/128`: 0.5278 / 0.5556 / 0.5694

Counterfactual:
- Output: `.research/real-grid2op-20260513/grid2op_real_cf_v3_compact_fixed/sampling_sweep_18_with_context_v1/`
- `meta_only`: 0.5000
- `generic_caption`: 0.2778
- `oracle_evidence_caption`: 1.0000
- `numbers_sampled_32/64/128/256/512`: 0.9444 / 0.9444 / 1.0000 / 1.0000 / 1.0000

Interpretation:
- The context card fixes the underspecified-question problem.
- It also exposes a benchmark flaw: `meta_only` is too high after background is
  supplied.
- Leakage source is not direct answer leakage from the context card. It is
  label/option prior in the generated QA. Examples:
  - `max_avg_generator`: 12/12 correct labels are `generator 0`.
  - `max_avg_load`: 12/12 correct labels are `load 1`.
  - `total_load_trend`: labels are skewed toward `higher`.
  - `cf_intervened_line` is partly a metadata-reading task rather than a trace
    reasoning task.

Decision:
- Do not treat with-context-v1 as the final protocol.
- Build a meta-safe v2 dataset before continuing the main experiment stream.
- Keep context card v1. Change QA construction so answer correctness depends
  on trace-derived numeric statements rather than stable variable-ID priors.

## v2/v3 Negative Protocol Results

Two intermediate attempts were rejected:

1. **v2 statement QA**
   - Observation output:
     `.research/real-grid2op-20260513/grid2op_real_v2_obs_statement/core_sweep_with_context_v1/`
   - Counterfactual output:
     `.research/real-grid2op-20260513/grid2op_real_cf_v4_statement/core_sweep_with_context_v1/`
   - Issue: statement options still carried semantic priors. `meta_only` was
     too high, especially on counterfactual statement questions.

2. **v3 numeric-slot QA**
   - Observation gate:
     `.research/real-grid2op-20260513/grid2op_real_v3_obs_numeric/gate_meta_oracle_with_context_v1/`
   - Counterfactual gate:
     `.research/real-grid2op-20260513/grid2op_real_cf_v5_numeric/gate_meta_oracle_with_context_v1/`
   - Issue: peak/max/severity questions still favored extreme-looking options,
     so `meta_only` remained too high.

Decision:
- Reject v2/v3 as final benchmark protocols.
- Use slot-value questions that ask for a fixed variable/time/window value,
  rather than argmax/peak/severity categories.

## Final Clean Protocol: v4b Slot-Value QA + Context Card v2

Final data:
- Observation:
  `.research/real-grid2op-20260513/grid2op_real_v4_obs_slot/grid2op_real_v4_obs_slot.jsonl`
- Counterfactual:
  `.research/real-grid2op-20260513/grid2op_real_cf_v6_slot/grid2op_real_cf_v6_slot.jsonl`

Generator:
- `scripts/generate/build_grid2op_slot_value_v4.py`

Evaluator:
- `scripts/eval/eval_medium_horizon_simqa_pilot.py`

Important fixes:
- Questions now ask trace-specific numeric slot values, e.g. rho at a specific
  line/time, mean load for a specified load, or factual/intervention max-rho
  difference at a specified time.
- Correct option letters are globally balanced by a hash of sample IDs, not by
  task order, quarter index, or variable ID.
- Context card v2 gives domain definitions and task rules, but no answer facts.

Sanity:
- Observation: 72 items; A/B/C/D = 18/18/18/18; missing fields = 0.
- Counterfactual: 12 items; A/B/C/D = 3/3/3/3; missing fields = 0.

Gate results:

Observation gate:
- Output:
  `.research/real-grid2op-20260513/grid2op_real_v4_obs_slot/gate_meta_oracle_with_context_v2b/`
- `meta_only`: 0.2222
- `oracle_evidence_caption`: 1.0000
- Previously leaky `quarter_total_load_mean_value_slot`: `meta_only` = 0.2500

Counterfactual gate:
- Output:
  `.research/real-grid2op-20260513/grid2op_real_cf_v6_slot/gate_meta_oracle_with_context_v2b/`
- `meta_only`: 0.0833
- `oracle_evidence_caption`: 1.0000

Core sweep:

Observation:
- Output:
  `.research/real-grid2op-20260513/grid2op_real_v4_obs_slot/core_sweep_with_context_v2b/`
- `meta_only`: 0.2361, mean prompt chars 1479.1
- `generic_caption`: 0.3056, mean prompt chars 1617.6
- `oracle_evidence_caption`: 1.0000, mean prompt chars 1541.5
- `numbers_sampled_32/64/128`: 0.3056 / 0.3889 / 0.4028
- Mean prompt chars for sampled numbers: 13920.0 / 26157.6 / 50631.3

Counterfactual:
- Output:
  `.research/real-grid2op-20260513/grid2op_real_cf_v6_slot/core_sweep_with_context_v2b/`
- `meta_only`: 0.1667, mean prompt chars 1590.3
- `generic_caption`: 0.1667, mean prompt chars 1745.3
- `oracle_evidence_caption`: 1.0000, mean prompt chars 1663.4
- `numbers_sampled_32/64/128/256`: 0.5000 / 0.5000 / 0.5833 / 0.5833
- Mean prompt chars for sampled numbers: 9134.3 / 16428.3 / 31015.3 /
  60189.3

Current conclusion:
- The user's criticism was correct: background-free Grid2Op questions were
  underspecified.
- Adding a context card alone is not enough; it can expose hidden answer priors.
- The clean protocol is context-card + slot-value QA + answer-letter balancing.
- Under this protocol, oracle evidence captions are a compact perfect upper
  bound, generic captions are near meta-only, and sampled numeric prompts are
  much longer while still substantially below oracle accuracy.
