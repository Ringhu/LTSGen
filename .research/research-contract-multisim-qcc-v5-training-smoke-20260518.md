# Research Contract
**Project:** MultiSim-QCC-v5 source-aware dataloader, AIOpsLab expansion, and training smoke
**Date locked:** 2026-05-18
**Status:** ACTIVE -- immutable until this v5 training-smoke experiment concludes

## 1. Hypothesis
Using a schema-aligned MultiSim-v5 dataset with source-aware batching or safe
channel padding will make the General QCC training stack run end-to-end across
Grid2Op, CityLearn, FinRL, WNTR/water, SUMO/traffic, and AIOpsLab official
telemetry without mixed-dimension dataloader failures, while preserving
per-source evaluation diagnostics.

## 2. Success Signal
**Primary metric:** executable end-to-end training and evaluation readiness.

**Dataset(s):**
- `multisim_qcc_v5_schema_aligned` on A100.
- An expanded AIOpsLab official dataset if additional AIOpsLab cases can be
  collected without infrastructure failures.

**Threshold for clear success:**
- dataloader smoke loads the v5 train and eval SFT files with mixed 3D/4D
  values and produces at least one valid batch containing padded or
  source-consistent tensors;
- a bounded Qwen3-4B frozen-LLM smoke run completes training, saves
  `final_model/pytorch_model.bin`, and generates predictions on a small
  per-source eval subset;
- rule QA or caption-evidence evaluation produces per-source metrics for every
  required source present in the run: Grid2Op, CityLearn, FinRL, water, traffic,
  and AIOpsLab official;
- if AIOpsLab expansion is attempted, all successful cases must convert to the
  same QCC schema with zero duplicate ids and zero split-group leakage; failed
  AIOpsLab cases must be recorded rather than silently ignored;
- the final report must state whether this is a training-stack success, a model
  quality success, or only an engineering smoke success.

**Threshold for clear failure:**
- dataloader/collator cannot batch the v5 data without dropping a required
  source; or
- training crashes before the first optimizer step for a data/model reason; or
- generation/evaluation cannot produce per-source metrics; or
- AIOpsLab expansion corrupts split isolation or schema alignment; or
- the report cannot identify which source or channel count caused a failure.

**Ambiguous zone:** if the smoke training and generation run, but caption QA is
low, this is not a method success. It is an engineering readiness result only,
and the next model/loss change must be decided from the failure diagnostics.

## 3. Per-Ablation Expectations
| Ablation | Predicted outcome | Why (mental model) | What surprise would teach us |
| --- | --- | --- | --- |
| Safe channel padding versus source-only batching | Both should eliminate mixed 3D/4D collator failure; source-only batching should be cleaner for training. | PatchTST currently has a fixed `ts_num_vars`; padding to 4D is the smallest compatible change, while source-aware grouping avoids heterogeneous source semantics inside one step. | If padding harms even smoke stability, source-specific input projection is mandatory before mixed training. |
| Per-source evaluation versus overall-only evaluation | Per-source metrics should reveal larger variance than the overall score. | The six sources differ in domain semantics and task family distributions. | If overall and per-source metrics match closely, the current task mix may be too homogeneous or the evaluator too coarse. |
| AIOpsLab expansion | More fault families should improve AIOpsLab diversity but may expose collector fragility. | Current AIOpsLab v1 has only three port-misconfig cases. | If expansion is unstable, AIOpsLab should remain a verified small official source until infra is hardened. |

## 4. Stop Conditions
- Stop before long training if the dataloader smoke cannot handle mixed channel
  counts.
- Stop before claiming model improvement if only the training script runs but
  per-source evaluation is missing.
- Stop AIOpsLab expansion if Kubernetes recovery leaves residual jobs/pods or
  if two consecutive cases fail for infrastructure reasons.
- Stop before adding SCL loss if CE-only smoke cannot complete and generate
  evaluable captions.

## 5. Claim-to-Signal Map
| Paper claim | Contract signal | Evidence |
| --- | --- | --- |
| Multi-simulator schema can feed QCC training | dataloader and training smoke pass | Filled in after run |
| Expanded AIOpsLab official data is usable | conversion schema pass and gate report | Filled in after run |
| Model quality improves after data expansion | per-source QA metrics exceed pre-run baselines | Only claim if results support it |

---
**Immutability clause:** Once `Status: ACTIVE` and experiments have begun, this
file does not get edited. Revisions require a new file with an explicit
changelog explaining what changed and why. Changes that weaken success criteria
or redefine failure after seeing results are forbidden.
