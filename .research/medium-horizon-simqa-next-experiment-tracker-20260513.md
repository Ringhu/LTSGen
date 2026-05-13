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
dataset. QCC-v0 now has a verified structured-evidence dataset, an evaluator
with oracle/metadata-only/question-only sanity baselines, and a trace-reading
rule extractor that reaches 1.0 without reading gold target fields. A learned
TF-IDF/logreg operator planner trained on 32 tiny examples also reaches 1.0 when
paired with the deterministic trace executor. This passes the QCC-v0 smoke gate
but is not paper-level method evidence because current questions are
template-style and trace reading is rule-based. Paraphrase robustness smoke gets
0.9583 overall but exposes counterfactual delta/operator confusion. Next work
expanded both Grid2Op and CityLearn from existing local traces to 620 QCC-v0
examples, raising Grid2Op counterfactual coverage from 12 to 176 items. This
removes the immediate counterfactual data sparsity bottleneck for template-style
operator planning: the planner reaches 1.0 when trained on the 470-item expanded
train split. Next work should add paraphrase augmentation on expanded_v1 and
then rerun the paraphrase robustness gate before SCL. Do not download larger
simulator data to the local SSD; use A100/3090 storage for real simulator
environments and traces.
