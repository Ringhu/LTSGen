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
