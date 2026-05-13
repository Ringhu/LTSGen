# QCC-v0 Dataset Build
**Date:** 2026-05-13

This directory contains the first QCC-v0 structured evidence dataset generated
from the validated Grid2Op and CityLearn simulator QA gates.

## Source Inputs

- `.research/real-grid2op-20260513/grid2op_real_v4_obs_slot/grid2op_real_v4_obs_slot.jsonl`
- `.research/real-grid2op-20260513/grid2op_real_cf_v6_slot/grid2op_real_cf_v6_slot.jsonl`
- `.research/real-citylearn-20260513/citylearn_real_v2_slot/citylearn_real_v2_slot.jsonl`

## Output

- `qcc_v0_dataset.jsonl`
- `sanity_report.json`

## Sanity Result

- total examples: 156
- duplicate IDs: 0
- missing required fields: 0
- trace recomputation failures: 0
- split: train 100 / dev 24 / tiny_overfit 32
- schema gate: pass

By domain:

| Domain | Count |
| --- | ---: |
| `grid2op_real` | 72 |
| `grid2op_real_cf` | 12 |
| `citylearn_real` | 72 |

By task family:

| Task family | Count |
| --- | ---: |
| `rho_value_slot` | 24 |
| `load_average_value_slot` | 12 |
| `generator_average_value_slot` | 12 |
| `quarter_total_load_mean_value_slot` | 24 |
| `cf_delta_max_rho_value_slot` | 6 |
| `cf_intervention_max_rho_value_slot` | 6 |
| `building_load_value_slot` | 24 |
| `quarter_net_electricity_mean_value_slot` | 24 |
| `outdoor_temperature_value_slot` | 24 |

## Interpretation

The important result is not model performance yet. The dataset builder
recomputed every target field from the underlying simulator trace and matched it
against the stored oracle evidence caption and answer label. This establishes
that QCC-v0 can be trained/evaluated against structured, verifiable targets
rather than free-form LLM-written captions.

Current limitation:
- Grid2Op load/generator and counterfactual dev counts are small. Future QCC-v0
  dev metrics should be interpreted per domain/task or after expanding the
  Grid2Op slot dataset.

## Deterministic Evaluator Baselines

Scripts:
- `scripts/eval/eval_qcc_v0_outputs.py`
- `scripts/eval/run_qcc_v0_deterministic_baselines.py`

Outputs:
- `deterministic_baselines/oracle_structured_target.jsonl`
- `deterministic_baselines/metadata_only_slot.jsonl`
- `deterministic_baselines/question_only_selectors.jsonl`

Overall metrics:

| Condition | Field exact | Caption exact | Answer label | Answer letter |
| --- | ---: | ---: | ---: | ---: |
| `oracle_structured_target` | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `metadata_only_slot` | 0.0000 | 0.0000 | 0.0000 | 0.2500 |
| `question_only_selectors` | 0.0000 | 0.0000 | 0.0000 | 0.2500 |

Interpretation:
- The evaluator recovers the oracle upper bound exactly.
- Metadata-only is at random answer-letter accuracy, so the structured target
  is not solved by answer priors.
- Question-only can recover selector fields such as `slot_local_t`,
  `slot_line`, `slot_building`, and `slot_quarter`, but all numeric evidence
  fields remain wrong. This is the intended sanity check: QCC must read trace
  evidence, not only parse the question.

Next:
- Run an actual tiny-overfit QCC-v0 model or LLM extractor against the same
  evaluator.
- The contract success threshold for tiny overfit remains >=95% exact slot
  accuracy and >=95% answer-letter accuracy on the 32-example tiny split.

## Trace-Rule Extractor Gate

Script:
- `scripts/eval/run_qcc_v0_trace_rule_extractor.py`

Output:
- `trace_rule_extractor/predictions.jsonl`
- `trace_rule_extractor/eval/metrics.json`

Overall metrics:

| Condition | Field exact | Caption exact | Answer label | Answer letter |
| --- | ---: | ---: | ---: | ---: |
| `trace_rule_extractor` | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

Interpretation:
- This extractor does not read gold `target_fields`.
- It parses the question selectors, reads the referenced trace/pair, recomputes
  the numeric evidence, and emits the QCC-v0 target schema.
- This establishes that the QCC-v0 target is an executable evidence-extraction
  behavior. The next learned model should approximate this behavior without
  hard-coded task-specific rules.

## Learned Planner Smoke

Script:
- `scripts/eval/run_qcc_v0_learned_planner.py`

Output:
- `learned_planner_tiny/planner.joblib`
- `learned_planner_tiny/planner_summary.json`
- `learned_planner_tiny/predictions_all_eval_splits.jsonl`
- `learned_planner_tiny/eval_all_eval_splits/metrics.json`

Setup:
- Train split: `tiny_overfit`
- Training examples: 32
- Eval splits: `tiny_overfit`, `dev`, `train`
- Learned component: TF-IDF + logistic regression operator planner
- Deterministic component: executor parses selector arguments and reads trace
  values

Results:

| Split | Operator acc | Field exact | Caption exact | Answer letter |
| --- | ---: | ---: | ---: | ---: |
| `tiny_overfit` | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `dev` | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `train` | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

Interpretation:
- This passes the QCC-v0 tiny-overfit contract gate.
- The result is a smoke, not a paper-level learned captioner result. It learns
  the question-conditioned operator planner, while trace reading and numeric
  computation remain deterministic.
- Because current questions are template-style, dev generalization is easy.
  The next real method step should expand question paraphrases and train a
  less rule-dependent QCC model.

## Paraphrase Robustness Smoke

Scripts:
- `scripts/generate/build_qcc_v0_paraphrase_eval.py`
- `scripts/eval/run_qcc_v0_learned_planner.py`

Data:
- source split: `dev`
- paraphrases per item: 2
- total paraphrase eval items: 48
- output: `paraphrase_eval_dev/qcc_v0_paraphrase_eval.jsonl`

Trace-rule upper bound:

| Condition | Field exact | Caption exact | Answer label | Answer letter |
| --- | ---: | ---: | ---: | ---: |
| `trace_rule_extractor` | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

Learned planner trained on original `tiny_overfit` templates:

| Eval set | Operator acc | Field exact | Caption exact | Answer letter |
| --- | ---: | ---: | ---: | ---: |
| `dev_paraphrase` | 0.9583 | 0.9583 | 0.9583 | 0.9583 |

Failure concentration:
- All 2 failures are `cf_delta_max_rho_value_slot`.
- The planner predicted `read_cf_intervention_max_rho` instead of
  `delta_cf_max_rho` for the paraphrased counterfactual delta questions.

Interpretation:
- The planner is not just memorizing the original exact question templates:
  it transfers to 46/48 paraphrased questions after training on only 32
  original-template examples.
- The weak spot is counterfactual operator disambiguation, especially
  distinguishing "read intervention max_rho" from "intervention minus factual
  max_rho".
- This is still a smoke, not a final method result. The next data step should
  expand counterfactual examples and include paraphrase augmentation in training.

## Expanded v1 Data Scale-Up

Scripts:
- `scripts/generate/assess_qcc_v0_expansion_capacity.py`
- `scripts/generate/build_qcc_v0_expanded_slot_qa.py`
- `scripts/generate/build_qcc_v0_dataset.py`

Capacity assessment:
- output: `expanded_v1/capacity_report.json`
- no new simulator rollout or remote trace copy was used
- planned total from existing local trace/pair files: 620 slot QA items
- Grid2Op observation: 224 planned items from 16 windows
- Grid2Op counterfactual: 176 planned items from 11 usable paired traces
- CityLearn: 220 planned items from 11 windows

Expanded structured dataset:
- slot QA: `expanded_v1/qcc_v0_expanded_slot_qa.jsonl`
- QCC structured evidence: `expanded_v1/qcc_v0_expanded_dataset.jsonl`
- total examples: 620
- split: train 470 / dev 118 / tiny_overfit 32
- duplicate IDs: 0
- missing required fields: 0
- trace recomputation failures: 0
- answer letters: A/B/C/D = 155/155/155/155

By domain:

| Domain | Count |
| --- | ---: |
| `grid2op_real` | 224 |
| `grid2op_real_cf` | 176 |
| `citylearn_real` | 220 |

By task family:

| Task family | Count |
| --- | ---: |
| `rho_value_slot` | 64 |
| `load_average_value_slot` | 48 |
| `generator_average_value_slot` | 48 |
| `quarter_total_load_mean_value_slot` | 64 |
| `cf_delta_max_rho_value_slot` | 88 |
| `cf_intervention_max_rho_value_slot` | 88 |
| `building_load_value_slot` | 110 |
| `quarter_net_electricity_mean_value_slot` | 44 |
| `outdoor_temperature_value_slot` | 66 |

Verification:

| Condition | Train split | Field exact | Caption exact | Answer label | Answer letter |
| --- | --- | ---: | ---: | ---: | ---: |
| `trace_rule_extractor` | none | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `learned_planner_tiny` | 32 tiny examples | 0.9823 | 0.9823 | 0.9823 | 0.9823 |
| `learned_planner_train` | 470 train examples | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

Interpretation:
- The expanded dataset fixes the most important data bottleneck: Grid2Op
  counterfactual evidence grows from 12 to 176 items, with 88 delta examples and
  88 intervention-max-rho examples.
- The trace-rule extractor remains exact on all 620 examples, so the expanded
  target is still executable and verifiable.
- The 32-example tiny planner still makes 11 counterfactual
  `cf_intervention_max_rho_value_slot` mistakes, mostly confusing direct
  intervention max-rho reads with delta queries. After training on the 470-item
  expanded train split, the same planner reaches 1.0000 on dev/tiny/train.
- This supports the practical conclusion that the earlier counterfactual
  operator confusion was mostly a data sparsity issue, not a schema or executor
  issue. It still does not constitute a final learned captioner result because
  trace reading is deterministic.
