# Next Experiment Tracker
**Date:** 2026-05-13
**Plan:** `.research/medium-horizon-simqa-next-experiment-plan-20260513.md`

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NEXT-R001 | M0 | Inventory longer Grid2Op envs on remote | Grid2Op catalog and local cache | A100/3090 | env names, max timestep, size | MUST | DONE | 3090 has `/cluster/home/hulining/envs/grid2op` with Grid2Op 1.12.3; no local env cache; CLI can download `l2rpn_2019`, `rte_case14_realistic`, `rte_case14_redisp`. A100 common TS envs do not have Grid2Op. |
| NEXT-R002 | M1 | Export longer neutral Grid2Op traces | `rte_case14_realistic`, no-op/safe policy | 512/1024/2048 | actual horizon, fields, metadata | MUST | DONE | downloaded to 3090; max_timestep 8064; exported 512/1024 no-op; 2048 no-op failed at 1381, but 2048 succeeds with `NO_OVERFLOW_DISCONNECTION=True` |
| NEXT-R003 | M2 | Prototype one intervention type | line disconnection/topology action | small dev episodes | valid rollout rate, effect size | MUST | DONE | controlled factual/counterfactual pairs exported for selected lines; compact effect buckets built for 1024-step pairs |
| NEXT-R004 | M3 | Build Grid2Op real-v1 observation QA | observation tasks only | train/dev/test | sanity, balance | MUST | DONE | built 72 observation QA items from 512/1024/nooverflow-2048 traces; answer letters exactly balanced; schema gate passed |
| NEXT-R005 | M3 | Build Grid2Op real-v1 intervention QA | intervention/counterfactual tasks | train/dev/test | sanity, no-effect rate | MUST | DONE | built v2 from 512/1024/2048 paired traces for line 1/3/4; 27 QA items; schema gate passed; effectful positive and near-no-effect negative both present |
| NEXT-R006 | M4 | LLM smoke on real-v1 dev | meta/generic/stat/oracle/numbers | balanced dev subset | accuracy, prompt chars | MUST | DONE | added sampling sweep. Observation: oracle 1.0 vs best sampled 0.6667 with 25k chars. Counterfactual v2: oracle 1.0 vs sampled 0.8889-0.9259, so v2 mostly supports efficiency rather than accuracy collapse |
| NEXT-R007 | M5 | Strong baseline check | OpenTSLM/ChatTS/stat captions | test subset | QA, factuality, chars | MUST | TODO | keep baseline list short |
| NEXT-R008 | M6 | QCC-v0 overfit check | slot predictor/template captioner | tiny train/dev | train loss, slot acc | MUST | TODO | do before full training |
| NEXT-R009 | M6 | QCC-v0 full run | QCC vs task-agnostic | real-v1 test | QA, slot F1, unsupported rate | MUST | TODO | 3 seeds after stable |
| NEXT-R010 | M7 | SCL hard-negative ablation | QCC vs QCC+SCL | real-v1 test | QA, factuality, rejection acc | NICE | TODO | promote only if useful |
| NEXT-R011 | M1/M4 | CityLearn second-simulator feasibility | packaged CityLearn trace + slot QA | 512/1024/2048 windows, 8192 export | trace sanity, meta/oracle, prompt chars | MUST | DONE | CityLearn 2.5.0 on 3090; exported 2048/8192 traces. Expanded v2 has 72 items, balanced A/B/C/D, meta 0.2361, generic 0.2500, oracle 1.0, sampled-128 0.4583. |
| NEXT-R012 | M6 | QCC-v0 dataset build | Grid2Op + CityLearn slot QA to structured evidence targets | train/dev/tiny_overfit | target recomputation, schema gate | MUST | DONE | 156 examples; 0 duplicate IDs; 0 missing fields; 0 trace recomputation failures; split train/dev/tiny=100/24/32. |
| NEXT-R013 | M6 | QCC-v0 evaluator baselines | oracle / metadata-only / question-only structured outputs | all splits | field exact, caption exact, answer label, answer letter | MUST | DONE | Oracle = 1.0 on all metrics; metadata-only answer-letter = 0.25; question-only answer-letter = 0.25 and numeric evidence fields = 0.0. |
| NEXT-R014 | M6 | QCC-v0 trace-rule extractor | parse question selectors + read trace values | all splits | field exact, caption exact, answer label, answer letter | MUST | DONE | 1.0 on all metrics without reading gold target fields; confirms QCC target is executable evidence extraction. |
| NEXT-R015 | M6 | Learned QCC-v0 planner smoke | TF-IDF/logreg operator planner + deterministic executor | train on tiny_overfit, eval all splits | operator acc, field exact, answer letter | MUST | DONE | 32-example tiny-overfit gate passed. Operator/field/caption/answer all 1.0 on tiny/dev/train, but this is template-style smoke with rule executor, not final learned captioner. |
| NEXT-R016 | M6 | QCC-v0 paraphrase robustness smoke | train on original tiny templates, eval paraphrased dev | 48 paraphrases | operator acc, field exact, answer letter, failure family | MUST | DONE | Overall field/answer = 0.9583; trace-rule upper bound = 1.0. Only failures are 2 cf_delta paraphrases misclassified as intervention-max-rho. |
| NEXT-R017 | M6 | Expand Grid2Op+CityLearn QCC data | reuse existing trace/pair files, no new rollout | expanded_v1 | capacity, schema, trace-rule, planner | MUST | DONE | Capacity = 620 items. Built 620 structured examples: Grid2Op obs 224, Grid2Op cf 176, CityLearn 220; train/dev/tiny = 470/118/32. Trace-rule = 1.0. Tiny planner = 0.9823 overall with cf intervention/delta confusion; train planner = 1.0. |
| NEXT-R018 | M6 | Group split expanded_v1 | split by trace/pair group to avoid overlapping-window leakage | expanded_v1_group | group leakage, split balance | MUST | DONE | Built train/dev/test/tiny = 470/88/30/32. Observation groups use `trace_path`; counterfactual groups use `pair_path`; train-family/dev/test group leakage = 0. CityLearn has only one local trace, so strict split keeps CityLearn in train/tiny only. |
| NEXT-R019 | M6 | Expanded paraphrase augmentation | two deterministic paraphrases plus original item | expanded_v1_group_paraphrase | trace-rule, split balance | MUST | DONE | Built 1860 examples, train/dev/test/tiny = 1410/264/90/96. Trace-rule extractor remains 1.0 on all paraphrased records. |
| NEXT-R020 | M6 | Expanded training pipeline smoke | executor-assisted planner and no-trace structured smoke | group and group_paraphrase | field exact, answer letter, failure family | MUST | DONE | Executor-assisted planner reaches 1.0 on group split and paraphrase-augmented train. Original-template train on paraphrase eval drops to 0.8968 overall / 0.8222 test, mainly cf_delta confusion. No-trace structured smoke fails exact evidence: field 0.0, answer 0.0016; no-question answer 0.0. |
| NEXT-R021 | B1 | Build CityLearn heldout source | 8192 trace blocks or second remote trace | group dev/test | overlap, trace-rule, balance | MUST | SUPERSEDED | Superseded by the general QCC captioner plan. CityLearn heldout may still be useful, but not as the first action. |
| NEXT-R022 | B2 | Build structured query target | operator + selectors + executor fields | expanded group/paraphrase | schema sanity, executable rate | MUST | SUPERSEDED | Superseded. Structured queries are allowed as supervision/verifier metadata, not the final method route. |
| NEXT-R023 | B2 | Evaluate query baselines | rule parser, TF-IDF, no-question | heldout group/paraphrase | operator, selector, field exact | MUST | SUPERSEDED | Superseded. Future baselines must evaluate natural-language QCC captions. |
| NEXT-R024 | B3 | LLM JSON extractor smoke | zero-shot/few-shot QCC query | heldout group/paraphrase | executable rate, field exact, QA | MUST | SUPERSEDED | Superseded. Do not pursue JSON extractor as main method unless user approves tool-agent direction. |
| NEXT-R025 | B3 | Supervised query model smoke | small text model or classifier heads | tiny/train/dev | overfit, heldout exact | MUST | SUPERSEDED | Superseded by natural-language captioner training. |
| NEXT-R026 | B4 | Strong task-agnostic baselines | statistical caption, sampled numbers | test | QA, chars, factuality | MUST | SUPERSEDED | Recovered as GQCC-R004/R008 under the general captioner plan. |
| NEXT-R027 | B6 | 4096/8192 scaling diagnostic | CityLearn longer windows | heldout blocks | QA, chars, executor success | NICE | SUPERSEDED | Recovered as GQCC-R009, with captioner/factuality metrics rather than executor success. |
| NEXT-R028 | B5 | Hard-negative/SCL ablation | QCC vs QCC+hard negatives | test | field exact, rejection, QA | NICE | SUPERSEDED | Recovered as GQCC-R007 after CE-only captioner baseline exists. |
| GQCC-R001 | B1 | Build broad task taxonomy and support-slot schema | natural-language caption target | design | coverage checklist | MUST | TODO | First action. Prevents drift back to slot-value lookup. |
| GQCC-R002 | B1 | Generate synthetic primitive captions | trend/extrema/vol/anomaly/periodicity/comparison/leadlag | train/dev/test | sanity, verifier | MUST | TODO | Slots are auxiliary supervision; target is natural-language caption. |
| GQCC-R003 | B1 | Extend simulator captions beyond lookup | Grid2Op + CityLearn broad tasks | group split | task balance, verifier | MUST | TODO | Include context cards and domain meaning. |
| GQCC-R004 | B2 | Oracle/generic/stat baseline gate | generated eval tasks | heldout | QA, factuality, chars | MUST | TODO | Must pass before training a captioner. |
| GQCC-R005 | B3 | Captioner tiny-overfit smoke | Q-conditioned natural-language captioner | tiny | slot factuality, QA | MUST | TODO | Natural-language output required. |
| GQCC-R006 | B3/B4 | QCC heldout smoke | QCC vs generic/no-question | dev | QA, factuality | MUST | TODO | First real method signal. |
| GQCC-R007 | B5 | Loss ablation | CE vs CE+slot vs CE+SCL vs hard negatives | dev/test | QA, factuality | MUST AFTER R006 | TODO | SCL promotion depends on this. |
| GQCC-R008 | B4 | Existing benchmark transfer | TSShapeQA/TSAQA/dataset_a/FREDQA subset | eval | QA, factuality | MUST | TODO | Tests generality beyond simulator data. |
| GQCC-R009 | B6 | Horizon scaling | 512-8192 | heldout | QA, chars | NICE/MUST | TODO | MUST if final story emphasizes medium-high horizon. |

## Addendum 2026-05-13
- Built Grid2Op counterfactual v3 compact with selected full 1024-step paired
  traces for line 0/1/2/3/4/5.
- Fixed direction-question ambiguity by making the 0.05 max-rho tolerance
  explicit in the question/options.
- Fixed v3 compact result: oracle 1.0, sampled-256/512 also 1.0. Conclusion:
  current counterfactual set supports token-efficiency/verifiability, not
  numeric-prompt accuracy collapse.
- Full observation 72-item core sweep is now complete: oracle 1.0, best sampled
  numbers 0.5556 with 25k prompt chars, generic 0.3889, meta 0.2361.
- Next priority shifts to localized sparse-event QA and CityLearn feasibility.

## Addendum 2026-05-13 Context-Card Patch
- User review correctly identified that background-free Grid2Op questions were
  unfair: respondents need to know what `line`, `rho`, disconnection,
  factual trace, and counterfactual trace mean.
- Added Grid2Op context-card prompts and Chinese case-study background panels.
- The first context-card rerun exposed label/option priors in the old QA.
- Rebuilt final clean slot-value QA with globally balanced answer letters:
  observation A/B/C/D = 18/18/18/18, counterfactual A/B/C/D = 3/3/3/3.
- Final clean outputs:
  - Observation: `grid2op_real_v4_obs_slot/core_sweep_with_context_v2b/`
  - Counterfactual: `grid2op_real_cf_v6_slot/core_sweep_with_context_v2b/`
- Final clean observation result: meta 0.2361, generic 0.3056, oracle 1.0,
  best sampled numbers 0.4028 with 50.6k prompt chars.
- Final clean counterfactual result: meta 0.1667, generic 0.1667, oracle 1.0,
  best sampled numbers 0.5833 with 31.0k-60.2k prompt chars.
- This supersedes the old no-context and with-context-v1 Grid2Op result for
  paper-facing claims.

## Current Gate
Grid2Op context-card protocol is clean enough for case studies and Grid2Op-only
discussion. CityLearn now passes a 72-item expanded feasibility gate over
512/1024/2048 windows, and a Chinese CityLearn case study has been generated.
The CityLearn result should still be described as second-simulator feasibility,
not a full benchmark: tasks are slot-value oriented and come from one packaged
dataset.

QCC-v0 now has a verified structured-evidence dataset, an evaluator with
oracle/metadata-only/question-only sanity baselines, and a trace-reading rule
extractor that reaches 1.0 without reading gold target fields. Expanded_v1
contains 620 examples: Grid2Op observation 224, Grid2Op counterfactual 176, and
CityLearn 220. A group split now assigns records by `trace_path` or `pair_path`,
giving train/dev/test/tiny = 470/88/30/32 with 0 train-family/dev/test group
leakage. The strict group split exposes one limitation: current CityLearn data
comes from one local trace, so CityLearn heldout evaluation needs another trace
source.

Expanded paraphrase augmentation is complete. The group-paraphrase dataset has
1860 examples with train/dev/test/tiny = 1410/264/90/96, and the trace-rule
extractor remains exact. The executor-assisted planner reaches 1.0 when trained
on either the 470 original train records for the group split or the 1410
paraphrase-augmented train records for the group-paraphrase split. Training only
on original templates and evaluating on the paraphrased set drops to 0.8968
overall and 0.8222 on test, mainly because `cf_delta_max_rho_value_slot`
paraphrases are confused with direct intervention `max_rho` reads. This makes
paraphrase augmentation a real part of the pipeline, not cosmetic data
expansion.

The pure text/metadata structured smoke fails exact numeric evidence recovery
(`field_exact` = 0.0, `answer_letter` = 0.0016; no-question = 0.0). This is an
expected negative diagnostic: a usable QCC model must read the trace through an
executor/tool or a TS encoder, not infer exact values from text alone. The
current executor-assisted 1.0 is a pipeline smoke, not a final learned captioner
result.

Route correction after user review: the project goal remains a general
question-conditioned natural-language captioner, not an executor-at-inference
or JSON-query tool-agent. The active next plan is
`.research/general-qcc-captioner-experiment-plan-20260513.md`, governed by
`.research/research-contract-general-qcc-captioner-20260513.md`. Executors and
structured slots may be used only for data generation, supervision, verification
and loss design unless a separate tool-agent direction is explicitly approved.
The next work is `GQCC-R001`: define a broad task taxonomy and support-slot
schema covering trend, extrema, volatility, anomaly, periodicity, comparison,
lead/lag, counterfactual effect, and domain-context reasoning. Do not download
larger simulator data to the local SSD; use A100/3090 storage for real
simulator environments and traces.
