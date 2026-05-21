# Research Contract: QCC-v0 Evidence Caption Overfit Gate
**Project:** LTSGEN medium-horizon QCC-v0  
**Date locked:** 2026-05-13  
**Status:** ACTIVE for QCC-v0; immutable once QCC-v0 experiments begin

## 1. Hypothesis

A question-conditioned captioner target can be learned as a compact evidence
extraction problem on the validated Grid2Op and CityLearn slot-value QA: given
the trace metadata, task/question, and access to the trace window, QCC-v0 should
recover the exact answer-supporting evidence caption substantially better than
generic captions and simple metadata priors.

## 2. Success Signal

**Primary metric:** exact evidence slot accuracy.

**Datasets:**
- Grid2Op clean slot QA:
  `.research/real-grid2op-20260513/grid2op_real_v4_obs_slot/`
- Grid2Op clean counterfactual slot QA:
  `.research/real-grid2op-20260513/grid2op_real_cf_v6_slot/`
- CityLearn clean slot QA:
  `.research/real-citylearn-20260513/citylearn_real_v2_slot/`

**QCC-v0 target format:**
- Input: domain context, task family, natural-language question, trace locator,
  and trace-derived table/features.
- Output: structured evidence fields plus a deterministic evidence caption.
- Evaluation must parse structured fields first, then compare generated caption
  only as a secondary string target.

**Threshold for clear success:**
- Data construction sanity:
  - at least 150 total QCC examples across Grid2Op + CityLearn;
  - missing required field rate = 0;
  - duplicate ID rate = 0;
  - every target field recomputes from the underlying trace.
- Tiny overfit sanity:
  - on a fixed 32-example mixed-domain training subset, QCC-v0 reaches at least
    95% exact slot accuracy and at least 95% answer-letter accuracy after
    overfit training or deterministic slot extraction.
- Held-out dev sanity:
  - on held-out windows/items from the same simulator families, QCC-v0 reaches
    at least 70% exact slot accuracy and at least 80% answer-letter accuracy.
- Interface sanity:
  - QA using QCC-v0 generated evidence captions must beat `generic_caption` by
    at least 20 absolute points on the held-out dev subset.

**Threshold for clear failure:**
- If target fields cannot be recomputed from traces for more than 2% of items,
  stop and fix benchmark construction before training.
- If tiny overfit exact slot accuracy stays below 80%, stop: the target format,
  parser, or model interface is broken.
- If held-out answer-letter accuracy is below 60% after tiny overfit succeeds,
  treat QCC-v0 as not yet supporting the method claim; inspect data split and
  feature representation rather than reframing as success.

**Ambiguous zone:**
- Tiny overfit >=80% and <95%: likely implementation or target-format issue;
  debug before scaling.
- Held-out exact slot accuracy 50-70% with answer-letter accuracy >=80%:
  evidence is useful for QA but not faithful enough for the verifiable-caption
  claim. This can motivate SCL, but cannot be presented as QCC success.
- QCC-v0 beats generic by <20 points but improves over meta-only: useful
  diagnostic, not a paper-facing method result.

## 3. Per-Ablation Expectations

| Ablation / condition | Predicted outcome | Why | What surprise would teach us |
| --- | --- | --- | --- |
| `generic_caption` | low slot accuracy, QA near meta/random | generic captions omit exact slots | If close to QCC, current tasks do not require question conditioning |
| `metadata_only_slot` | near-random answer-letter accuracy | trace values are not in metadata | High accuracy means leakage or answer/option priors remain |
| `qcc_no_question` | worse than QCC by at least 15 points | without question, extractor cannot choose slot/time/building/line | If close to QCC, task labels or options leak too much |
| `qcc_with_question` | best learned condition | question supplies the needed slot selector | If it fails overfit, target parser or feature access is broken |
| `oracle_evidence_caption` | upper bound, near 100% QA | it exposes recomputed GT evidence | If QA fails, evaluator/prompt format is broken |

## 4. Stop Conditions

- Do not start SCL or hard-negative training until QCC-v0 passes the tiny
  overfit gate.
- Stop if the data builder needs simulator-specific hacks that cannot be
  represented in a common schema.
- Stop if a result depends on excluding a task family after seeing poor
  performance; exclusions require a new contract and must be justified by a
  pre-training data bug.
- Stop if local artifacts become large; training outputs should go to 3090/A100
  storage, not the local SSD.

## 5. Claim-to-Signal Map

| Paper claim | Contract signal | Evidence |
| --- | --- | --- |
| QCC is a learnable evidence extraction target | tiny overfit exact slot accuracy >=95% | QCC-v0 overfit report |
| Question conditioning is load-bearing | QCC beats `qcc_no_question` by >=15 points | ablation table |
| Generated evidence captions are useful for QA | QCC evidence QA beats generic by >=20 points | held-out QA table |
| Verifiability is preserved | target fields recompute from traces, parseable structured output | data sanity report |

---
**Immutability clause:** Once QCC-v0 experiments begin, this file does not get
edited in place. Revisions require a new contract file with an explicit
changelog. Criteria may not be weakened after observing results.
