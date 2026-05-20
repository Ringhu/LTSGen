# Research Contract: General QCC Captioner
**Project:** LTSGEN medium-horizon simulator TS-QA  
**Date locked:** 2026-05-13  
**Status:** ACTIVE for the next implementation phase; immutable once new
general-captioner experiments begin

## 0. Route Correction

The previous QCC-v0 structured smoke experiments are diagnostics and data
construction checks, not the final method architecture. They showed that exact
facts must be grounded in the trace, but they do not authorize changing the
paper into a pure `extraction + executor` system.

This contract restores the original goal:

> Build a general question-conditioned captioner that reads time-series data and
> produces natural-language, answer-supporting captions for broad TS-QA tasks.

Executors, deterministic feature extractors, and structured fields may be used
for data generation, supervision, verification, and loss design. They must not
be presented as the final inference architecture unless the user explicitly
approves a separate tool-agent paper direction.

## 1. Hypothesis

A general question-conditioned captioner (QCC) trained on simulator-derived and
synthetic verifiable captions can produce faithful, answer-supporting natural
language captions across broad TS-QA primitives better than task-agnostic
captioners, while remaining much more token-efficient than raw-number prompts
on medium-horizon time series.

## 2. Scope and Non-Negotiables

Final target:
- Input: time series window plus the downstream natural-language question.
- Output: natural-language caption/evidence paragraph, not a structured query
  as the primary final output.
- Downstream: a normal LLM answers QA from the generated caption.

Executor/verifier role:
- allowed for generating ground-truth caption fields;
- allowed for checking factuality of generated captions;
- allowed for SCL/hard-negative loss;
- allowed as an oracle upper bound or diagnostic baseline;
- not allowed as the main inference path for the claimed QCC method.

Task coverage must be broad:
- trend and direction;
- extrema location/value region;
- volatility/noise/regime change;
- anomaly/spike/event detection;
- temporal relationship and lead/lag;
- comparison across variables or windows;
- counterfactual/intervention effect where simulator traces support it;
- domain-grounded questions for Grid2Op/CityLearn when context is provided.

Slot-value lookup tasks alone are insufficient for a paper-facing QCC claim.

## 3. Success Signal

**Primary metric:** downstream QA accuracy using generated QCC captions.

**Secondary metrics:**
- caption factuality slot accuracy, using verifier-extracted slots;
- answer-supporting evidence coverage;
- unsupported/hallucinated claim rate;
- prompt length / token proxy;
- robustness to paraphrased questions.

**Datasets for first clear success:**
- QCC-General-Train generated from Grid2Op, CityLearn, and synthetic primitives.
- QCC-General-Eval held out by trace/group and task family.
- Existing benchmark diagnostics: TSShapeQA-OOD, TSAQA, dataset_a, and FREDQA
  where local artifacts permit fair evaluation.

**Threshold for clear success:**
- Generated QCC captions beat task-agnostic generic captions by >=10 absolute
  QA points on the simulator heldout set.
- Generated QCC captions recover >=50% of the oracle-evidence-vs-generic gap.
- Caption factuality known-slot accuracy is >=75% on core primitives.
- Unsupported/hallucinated claim rate is at least 25% lower than the
  task-agnostic captioner on verifier-checkable claims.
- On at least one existing benchmark family, QCC captions improve over the
  strongest existing caption baseline available locally, or match it with
  substantially lower hallucination/unsupported rate.

**Threshold for clear failure:**
- If generated QCC captions beat generic captions by <3 QA points on simulator
  heldout and do not improve factuality, the method is not working.
- If QCC only works on slot-value lookup tasks and fails on trend/extrema/
  volatility/anomaly/comparison primitives, the general-captioner claim fails.
- If QCC gains come only from adding executor outputs at inference, this
  contract is violated and the result must not be framed as a general
  captioner.

**Ambiguous zone:**
- QA gain 3-10 points but factuality improves: continue data/loss debugging, do
  not write paper claims yet.
- Factuality improves but QA does not: treat as a caption-quality result, not a
  downstream QA success.
- Strong simulator result but no improvement on existing benchmarks: keep the
  benchmark contribution, but weaken generalization claims.

## 4. Per-Ablation Expectations

| Ablation / condition | Predicted outcome | Why | What surprise would teach us |
| --- | --- | --- | --- |
| `task_agnostic_captioner` | Lower QA and lower evidence coverage than QCC | It compresses globally and may omit question-relevant facts | If close to QCC, questions may not require conditioning |
| `qcc_no_question` | Drops by >=10 QA points and lower slot coverage | The question selects which facts matter | If close to QCC, task labels/options may leak too much |
| `qcc_question_only_no_ts` | Near meta-only / poor factuality | Captioner cannot know trace facts without TS input | If high, data leakage exists |
| `qcc_with_verifier_loss` | Improves factuality and unsupported rate over QCC CE-only | Verifier discourages hallucinated or wrong evidence claims | If no gain, loss design or verifier signal is weak |
| `qcc_with_hard_negatives` | Helps most on counterfactual, extrema, and comparison tasks | Near-miss facts force grounding | If it hurts QA, negatives may over-regularize or conflict with natural language |
| `oracle_evidence_caption` | Upper bound, high QA | It exposes answer-supporting facts | If low, prompt/QA formulation is broken |
| `raw_numbers_sampled` | Costly, sometimes competitive but less efficient | It preserves values but stresses LLM context | If it dominates QCC, caption target is losing too much information |

## 5. Stop Conditions

- Stop if the training/evaluation plan silently turns the method into
  executor-at-inference without explicit user approval.
- Stop if data generation produces mostly slot-value lookup questions; broaden
  primitives before training.
- Stop if heldout split leakage appears across trace/group/window.
- Stop if verifier labels cannot be recomputed for more than 2% of supervised
  examples.
- Stop if a result misses the success threshold and the proposed response is to
  weaken the claim instead of improving data/model/loss.

## 6. Claim-to-Signal Map

| Paper claim | Contract signal | Evidence |
| --- | --- | --- |
| QCC is a better caption interface than task-agnostic captions | >=10pp QA gain and >=50% oracle-gap recovery | Main simulator heldout table |
| QCC is general, not just lookup | Success across broad primitives beyond slot values | Per-primitive table |
| Verifiable supervision improves faithfulness | Lower hallucination/unsupported rate and higher slot factuality | Factuality/verifier table |
| Medium-horizon captioning is more efficient than raw numbers | Similar or better QA at far lower prompt length | Horizon/token-cost curve |

---
**Immutability clause:** Once new general-captioner experiments begin, this file
does not get edited in place. Revisions require a new contract file with an
explicit changelog. Success/failure thresholds may not be weakened after seeing
results.
