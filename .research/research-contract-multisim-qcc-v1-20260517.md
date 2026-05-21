# Research Contract: MultiSim-QCC-v1

**Project:** LTSGEN General QCC
**Date locked:** 2026-05-17
**Status:** ACTIVE for the MultiSim-QCC-v1 smoke phase

## 1. Hypothesis

A QCC captioner trained on multiple simulator-derived domains will expose and
partly reduce simulator-specific overfitting compared with a Grid2Op-only
recipe, while preserving natural-language evidence captioning as the final
inference interface.

## 2. Scope

This contract covers the first multi-simulator smoke run, not the final paper
recipe.

Included in v1:
- Grid2Op broad semantic data, including counterfactual rows.
- CityLearn broad semantic data.
- FinRL broad market data.
- One all-domain CE-only mixed training run.
- Per-domain heldout generation and rule-QA evaluation.

Explicitly deferred to v2:
- AIOpsLab, SUMO, WNTR, PyPSA, EnergyPlus, or other new simulator adapters.
- Auxiliary slot loss implementation.
- SCL reruns on the all-domain mixture.
- Paper-facing final model selection.

The final method must still output natural-language evidence captions. Support
slots, verifiers, and deterministic feature extractors may be used for data
construction, evaluation, and future auxiliary losses, but not as an
inference-time executor in this v1 claim.

## 3. Success Signal

Primary objective for v1:
- Produce a schema-clean all-domain dataset from at least three real domains.
- Launch one all-domain CE-only captioner run.
- Complete or at minimum start a traceable training run whose inputs are the
  all-domain dataset.

Clear success for the v1 smoke:
- Dataset includes Grid2Op, CityLearn, and FinRL with non-empty train/dev/test
  splits.
- No duplicate IDs across the merged dataset.
- Train vs heldout ID overlap is zero.
- Each domain has its own heldout dev/test raw JSONL for generation.
- A `local_gated_qprefix` CE run starts on A100 and reads the all-domain train
  and eval JSONL.
- If the run completes, per-domain dev/test metrics are computed.

Clear scientific success, if the run completes:
- Dev+test QA accuracy is not dominated by one simulator: worst-domain accuracy
  is at least `0.35`.
- Empty answer rate stays below `0.05` on every domain.
- Grid2Op counterfactual total improves over AS-047 `0.1852` without reducing
  CityLearn or FinRL below `0.35`.

Clear failure, if the run completes:
- Worst-domain accuracy is below `0.25`.
- Any domain has empty answer rate above `0.15`.
- The model only performs on the largest or easiest domain and fails another
  domain near chance.
- Grid2Op CF remains at or below `0.1852` and the added domains do not improve
  heldout generality.

Ambiguous zone:
- Worst-domain accuracy between `0.25` and `0.35`, or Grid2Op CF improves but
  one non-Grid2Op domain regresses. Treat this as a diagnostic result, not a
  selected recipe.

## 4. Per-Ablation Expectations

| Condition | Predicted outcome | Why | What surprise would teach us |
|---|---|---|---|
| All-domain CE-only | Better domain balance than Grid2Op-only, but still weak on Grid2Op CF | More domains discourage pure Grid2Op templates, but no explicit slot grounding is added | If Grid2Op CF jumps strongly, data diversity alone helps counterfactual grounding |
| All-domain CE + SCL | Deferred; expected to improve only if negatives are domain-local and slot-local | Prior SCL improved train margins but hurt heldout QA | If SCL helps all domains, previous failures were mostly negative construction/mixing issues |
| All-domain CE + auxiliary slot loss | Deferred; expected to help Grid2Op CF and domain-specific numeric grounding | AS-045/046 showed the model can write from slots but struggles reading slots from TS | If no help, encoder/bridge capacity is likely the bottleneck |
| Leave-one-simulator-out | Existing LOSO is diagnostic; expected to be lower than all-domain seen-domain testing | True cross-simulator transfer is harder than mixed training | If LOSO is strong, simulator-invariant primitives are already learnable |

## 5. Stop Conditions

- Stop if the merged data contains duplicate IDs or train/heldout overlap.
- Stop if any v1 dataset prompt includes `support_slots` as input.
- Stop if the run silently uses a Grid2Op-only evaluator for all domains.
- Stop if the model path or run script would overwrite a completed run.
- Do not claim a final method recipe from v1, even if the first run is strong.

## 6. Claim-to-Signal Map

| Claim | Contract signal | Evidence |
|---|---|---|
| Multi-simulator training is feasible | Clean three-domain dataset and launched all-domain training | schema report + A100 run log |
| Grid2Op-only overfitting is a real risk | Per-domain metrics differ and LOSO/all-domain comparison exposes domain gaps | per-domain dev/test table |
| More domains alone may not solve grounding | Grid2Op CF and slot-sensitive tasks remain weak under CE-only | per-task failure analysis |

---

**Immutability clause:** This file is locked before MultiSim-QCC-v1 data
generation and training. Do not edit thresholds after seeing v1 results; create
a v2 contract for changed claims or new simulator adapters.
