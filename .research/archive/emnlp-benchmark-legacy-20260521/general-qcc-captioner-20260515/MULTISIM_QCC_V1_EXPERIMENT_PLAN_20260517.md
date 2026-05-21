# MultiSim-QCC-v1 Experiment Plan

**Date:** 2026-05-17
**Contract:** `.research/research-contract-multisim-qcc-v1-20260517.md`

## Problem

Recent Grid2Op-only iterations exposed a real risk: even if a model gets good
on Grid2Op, it may simply learn Grid2Op-specific language templates instead of
general time-series evidence reading.

MultiSim-QCC-v1 is a first smoke test for mixed simulator training.

## Method Thesis

Train one natural-language QCC captioner on Grid2Op + CityLearn + FinRL, then
evaluate each domain separately. The first goal is not to win the final paper
table; it is to reveal domain imbalance, cross-domain interference, and whether
Grid2Op counterfactual failures persist after adding other simulators.

## Claim Map

| Claim | Why It Matters | Minimum Evidence | Linked Blocks |
|---|---|---|---|
| C1: Mixed simulator training is feasible | Prevents Grid2Op-only overfitting | Clean 3-domain data, A100 run starts | B1, B2 |
| C2: Per-domain metrics reveal generalization gaps | Average accuracy can hide one failed domain | Domain-wise dev/test QA and empty rate | B3 |
| C3: CE-only is a diagnostic baseline, not final method | Prior failures show target-only repair is insufficient | Grid2Op CF and slot-sensitive tasks checked separately | B3, B4 |

## Experiment Blocks

### B1: Build MultiSim-QCC-v1 Data

- Sources:
  - `grid2op_broad_v5_semantic_anchor`
  - `citylearn_broad_semantic_v3_qual`
  - `finrl_broad_mini_v1`
- Splits:
  - all-domain train
  - all-domain source-dev eval
  - per-domain heldout dev/test
- Gate:
  - three non-empty domains
  - duplicate ID count is zero
  - train vs heldout ID overlap is zero
  - prompts do not include `support_slots`
  - each domain has heldout dev/test raw JSONL

Priority: MUST-RUN.

### B2: Train First All-Domain Captioner

- System: `local_gated_qprefix`
- Loss: CE-only
- Base model: Qwen3-4B-Instruct-2507
- Epochs: 3 for first smoke, to reduce turnaround
- Data: MultiSim-QCC-v1 all-domain train/eval
- Gate:
  - training starts on A100
  - command reads `multisim_qcc_v1_train_sft.jsonl`
  - final model is not required for the launch objective, but should be monitored if possible

Priority: MUST-RUN.

### B3: Per-Domain Evaluation

If training completes:

- Generate captions for each domain's heldout dev/test:
  - Grid2Op -> `evaluate_grid2op_broad_predictions.py`
  - CityLearn -> `evaluate_citylearn_broad_predictions.py`
  - FinRL -> `evaluate_finrl_broad_predictions.py`
- Metrics:
  - per-domain QA accuracy
  - empty answer rate
  - per-task accuracy
  - Grid2Op CF total, lead-lag, non-CF macro

Priority: MUST-RUN after training completion.

### B4: Failure Diagnosis

Use the failure lessons from AS-043 to AS-047:

- If Grid2Op CF remains weak, inspect whether failures are still fixed-template
  mean/peak/overload collapses.
- If CityLearn or FinRL drops, inspect whether mixed training causes domain
  prompt confusion.
- If empty rate rises, inspect generation cleaning and max_new_tokens.
- If all domains are mediocre, proceed to auxiliary slot loss before SCL.

Priority: MUST-RUN after metrics.

## Run Order

| Run ID | Goal | System | Data | Decision Gate |
|---|---|---|---|---|
| MSQCC-001 | Lock contract/plan | docs | n/a | files exist |
| MSQCC-002 | Build mixed data | data builder | 3 domains | schema gate true |
| MSQCC-003 | Train all-domain smoke | local_gated_qprefix CE | all-domain train | run launched and verified |
| MSQCC-004 | Evaluate if complete | per-domain evaluators | heldout dev/test | metrics exist |
| MSQCC-005 | Decide next run | analysis | metrics + failures | choose slot loss, SCL, or simulator expansion |

## Deferred Simulator Expansion

The user's requested simulator expansion is correct, but v1 should not block on
new environment engineering. v2 candidates:

| Simulator | Domain | Why Useful | First Required Work |
|---|---|---|---|
| AIOpsLab | cloud / AIOps | anomalies, RCA, service metrics | define numeric trace export and QA primitives |
| SUMO | traffic | flow, speed, congestion, intervention | build route/scenario export and controlled signal tasks |
| WNTR | water networks | pressure, flow, failure events | generate pipe/node traces and intervention labels |
| PyPSA / PowerGym | energy systems | power/dispatch transfer beyond Grid2Op | avoid too much overlap with Grid2Op |
| EnergyPlus | building physics | richer building traces than CityLearn | export compact variables and weather/control events |

## Compute Budget

First smoke:

- Dataset generation: CPU, minutes.
- Training: A100 GPU0 or GPU1, roughly 30-45 minutes for 3 epochs on ~2500 rows.
- Generation/eval: additional 15-30 minutes if full heldout is generated.

## Final Checklist

- [ ] Contract locked
- [ ] Data builder implemented
- [ ] Schema gate passes
- [ ] A100 code synced
- [ ] First all-domain training launched
- [ ] If complete, per-domain metrics summarized
