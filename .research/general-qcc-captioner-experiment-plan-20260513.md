# General QCC Captioner Experiment Plan
**Date:** 2026-05-13  
**Project:** LTSGEN  
**Status:** Planned, not executed  
**Active contract:** `.research/research-contract-general-qcc-captioner-20260513.md`

## Purpose

This plan replaces the drifted `structured query + executor` plan. The project
goal is a general QCC captioner:

```text
time series + question -> natural-language answer-supporting caption -> LLM QA
```

Executors/verifiers remain important, but only as scaffolding:

```text
simulator trace / numpy extractor -> verifiable supervision + factuality loss
```

They are not the final method unless a separate tool-agent direction is
explicitly approved.

## Paper Claims to Support

| Claim | Evidence Needed | Experiments |
| --- | --- | --- |
| C1: Question-conditioned captions are better than generic captions | QCC captions improve QA and evidence coverage over task-agnostic captions | B2, B4, B5 |
| C2: QCC is general, not just a lookup tool | Works across trend, extrema, volatility, anomaly, comparison, temporal relation, and counterfactual/domain tasks | B1, B4 |
| C3: Verifiable supervision improves faithfulness | Lower hallucination/unsupported rate; higher slot factuality | B3, B5 |
| C4: Medium-horizon captioning is token-efficient | Similar/better QA with much shorter prompts than raw sampled numbers | B4, B6 |

## B1: General Caption Data Generation

**Goal:** Build QCC-General data that covers broad QA primitives, not only
slot-value lookup.

**Data sources:**
- Grid2Op: physical grid traces, line overload, load/generator averages,
  intervention/counterfactual effects.
- CityLearn: building load, weather, seasonal/diurnal changes, aggregate energy
  behavior.
- Synthetic primitive branch: trend, extrema, volatility region, anomaly/spike,
  periodicity, regime change, lead/lag, cross-variable comparison.
- Existing LTSGen-v1 synthetic captions: reuse as seed material if schema can
  be converted.

**Caption targets:**
- For each QA item, generate a natural-language `target_caption` that contains
  enough evidence to answer the question but is not just the answer.
- Include `support_slots` for verification, e.g. trend label, extrema third,
  volatility region, variable ids, event time, comparison direction.
- Keep the natural-language caption as the model target; slots are auxiliary
  supervision and evaluation metadata.

**Task families required for v1:**
- `trend_direction`
- `extrema_location`
- `volatility_region`
- `anomaly_event`
- `periodicity_or_seasonality`
- `window_comparison`
- `cross_variable_comparison`
- `temporal_lead_lag`
- `counterfactual_effect`
- `domain_context_reasoning`

**Success gate:**
- >=5000 training captions across at least 8 task families.
- >=1000 heldout eval captions, split by trace/group/source.
- No task family above 25% of the training set.
- Verifier recomputation failure <=2%.
- Answer-letter balance for QA eval max option share <=35%.

## B2: Baseline Captioners and Oracle Bound

**Goal:** Establish the target gap before training.

**Compared systems:**
- `meta_only`
- raw sampled numbers
- task-agnostic generic caption
- statistical summary caption
- oracle evidence caption
- existing ChatTS/OpenTSLM captions where conversion is feasible

**Metrics:**
- downstream QA accuracy;
- prompt chars/token proxy;
- verifier factuality on support slots;
- evidence coverage rate.

**Success gate for proceeding to training:**
- oracle evidence caption beats generic caption by >=15 QA points.
- generic/statistical captions leave clear missing-evidence or factuality gaps.
- sampled numbers are substantially longer than captions at medium horizons.

If this gate fails, task design is too easy or too generic; fix data before
training.

## B3: Captioner Architecture Smoke

**Goal:** Train an actual captioner, not an executor.

**Preferred starting model:**
- Use the existing OpenTSLM/tslm pipeline if practical.
- Input should include:
  - TS representation from encoder or compact TS features;
  - natural-language question;
  - domain/context card when needed.
- Output is natural-language caption.

**Minimum viable architecture options:**
1. TS encoder + question encoder + decoder captioner.
2. Existing TS-LLM captioner fine-tuned with question prepended.
3. Lightweight feature-conditioned seq2seq model for a fast smoke, but still
   generating natural language.

**Not allowed as final method in this contract:**
- model outputs only operator/query JSON;
- executor fills the final evidence at inference and this is claimed as QCC.

**Training losses:**
- Caption generation loss: cross entropy on `target_caption`.
- Slot auxiliary loss: predict verifier slots from hidden state or decoded
  caption.
- Self-consistency / verifier loss:
  - extract slots from generated caption;
  - compare to recomputed support slots;
  - penalize wrong/unsupported claims.
- Hard negative contrastive loss:
  - pair caption with near-miss slots/captions;
  - train model/verifier to prefer grounded caption.

**Smoke success:**
- Tiny overfit: generated captions match target support slots >=90%.
- Heldout small split: QCC caption QA beats generic caption by >=5 points.
- Generated captions are parseable by verifier for >=80% of examples.

## B4: Main QCC Evaluation

**Goal:** Test the central paper claim.

**Datasets:**
- QCC-General-Eval simulator heldout.
- Existing benchmarks where feasible:
  - TSShapeQA-OOD for trend/extrema/volatility;
  - TSAQA for mixed task types;
  - dataset_a for local/season/trend/causal/deductive style;
  - FREDQA/domain multivariate subset as qualitative or partial eval.

**Compared systems:**
- generic caption;
- statistical caption;
- ChatTS/OpenTSLM caption;
- QCC captioner without question;
- QCC captioner with question;
- QCC + verifier/SCL;
- oracle evidence caption;
- sampled raw numbers.

**Metrics:**
- QA accuracy overall and by task family;
- factuality known-slot accuracy;
- hallucination/unsupported rate;
- prompt length;
- caption+numbers help/harm if using caption as auxiliary context.

**Main success:**
- QCC with question beats generic caption by >=10 QA points on simulator
  heldout.
- QCC with question beats no-question QCC by >=10 QA points.
- QCC recovers >=50% of oracle-vs-generic gap.
- QCC improves factuality or unsupported rate over existing captioners.

## B5: Loss Ablation

**Goal:** Decide whether SCL/hard negatives are real contributions.

**Ablations:**
- CE-only captioner.
- CE + question conditioning.
- CE + slot auxiliary loss.
- CE + verifier consistency loss.
- CE + hard negative contrastive loss.
- CE + verifier + hard negatives.

**Expected outcome:**
- question conditioning improves evidence coverage;
- verifier/SCL reduces unsupported claims;
- hard negatives help most on counterfactual, extrema, comparison, and lead/lag
  tasks.

**Promotion rule:**
- SCL becomes a main contribution only if it improves factuality by >=5pp or QA
  by >=3pp over CE-only QCC.

## B6: Medium-Horizon Scaling

**Goal:** Support the medium-to-long horizon framing.

**Horizon sweep:**
- 512, 1024, 2048, 4096, 8192 where data supports it.

**Compared systems:**
- sampled numbers;
- generic caption;
- QCC captioner;
- oracle evidence caption.

**Metrics:**
- QA accuracy by horizon;
- prompt chars/token proxy;
- factuality by horizon;
- evidence coverage by horizon.

**Success:**
- QCC caption quality degrades slower than sampled-number QA or generic
  captions as horizon increases.
- QCC stays far shorter than numeric prompts.

## Execution Tracker

| Run ID | Block | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GQCC-R001 | B1 | Build task taxonomy and schema | general support slots + caption target | design | coverage checklist | MUST | TODO | Start here; prevent slot-value drift. |
| GQCC-R002 | B1 | Generate synthetic primitive captions | trend/extrema/vol/anomaly/periodicity/comparison/leadlag | train/dev/test | sanity, verifier | MUST | TODO | Use structured slots only for supervision. |
| GQCC-R003 | B1 | Extend simulator captions beyond lookup | Grid2Op + CityLearn broad tasks | group split | task balance, verifier | MUST | TODO | Include domain context in question/caption. |
| GQCC-R004 | B2 | Oracle/generic/stat baseline gate | all generated eval tasks | heldout | QA, factuality, chars | MUST | TODO | Do before model training. |
| GQCC-R005 | B3 | Captioner tiny-overfit smoke | Q-conditioned captioner | tiny | slot factuality, QA | MUST | TODO | Natural-language output required. |
| GQCC-R006 | B3/B4 | QCC heldout smoke | QCC vs generic/no-question | dev | QA, factuality | MUST | TODO | First real method signal. |
| GQCC-R007 | B5 | Loss ablation | CE vs CE+slot vs CE+SCL vs hard negatives | dev/test | QA, factuality | MUST AFTER R006 | TODO | SCL promotion depends on this. |
| GQCC-R008 | B4 | Existing benchmark transfer | TSShapeQA/TSAQA/dataset_a/FREDQA subset | eval | QA, factuality | MUST | TODO | Shows generality beyond simulator data. |
| GQCC-R009 | B6 | Horizon scaling | 512-8192 | heldout | QA, chars | NICE/MUST | TODO | MUST if final story emphasizes medium-high horizon. |

## Immediate Next Steps

1. Build `GQCC-R001`: a task taxonomy + support-slot schema for broad
   captioning tasks.
2. Build `GQCC-R002`: synthetic primitive data generator producing
   natural-language QCC captions plus verifier slots.
3. Build `GQCC-R004`: run oracle/generic/stat baselines before any captioner
   training to verify the benchmark has a real QCC gap.

## Guardrails

- Do not implement executor-at-inference as the method under this plan.
- Do not train only on slot-value lookup tasks.
- Do not treat trace-rule extractor 1.0 as model success.
- Do not start SCL until a CE-only QCC captioner has a measurable but imperfect
  baseline.
- Keep all future reports explicit about whether a number comes from:
  - oracle/verifier;
  - executor/tool diagnostic;
  - generated natural-language captioner.
