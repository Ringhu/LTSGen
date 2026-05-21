# Real Grid2Op Progress
**Date:** 2026-05-13
**Runs:** NEXT-R001, NEXT-R002 partial

## Remote Target
- Machine: 3090 (`head2`)
- Python: `/cluster/home/hulining/envs/grid2op/bin/python`
- Grid2Op version: `1.12.3`
- Work dir: `/cluster/home/hulining/LTSGEN`
- Data dir: `/cluster/home/hulining/data/grid2op`

## Dataset Download
Downloaded/expanded:
- `/cluster/home/hulining/data/grid2op/rte_case14_realistic`

Notes:
- `grid2op.download` printed `Aborted` after extraction, but the extracted
  environment directory exists and can be instantiated.
- Data size under `/cluster/home/hulining/data/grid2op`: about 296MB.

## Environment Metadata
Instantiation path:
- `/cluster/home/hulining/data/grid2op/rte_case14_realistic`

Metadata:
- backend: `rte_case14_realisticPandaPowerBackend`
- max timestep: 8064
- lines: 20
- loads: 11
- generators: 5
- observation vectors available: `load_p`, `gen_p`, `rho`, `p_or`, `p_ex`,
  `line_status`

## Neutral Trace Export
Script copied to remote:
- `/cluster/home/hulining/LTSGEN/scripts/generate/export_grid2op_trace.py`

Remote outputs:
- `/cluster/home/hulining/LTSGEN/.research/real-grid2op-20260513/rte_case14_realistic_trace_512.json`
  - requested: 512
  - actual: 512
- `/cluster/home/hulining/LTSGEN/.research/real-grid2op-20260513/rte_case14_realistic_trace_1024.json`
  - requested: 1024
  - actual: 1024
- `/cluster/home/hulining/LTSGEN/.research/real-grid2op-20260513/rte_case14_realistic_trace_2048.json`
  - requested: 2048
  - actual: 1381

Interpretation:
- The environment is long enough for 2048/4096 in principle.
- No-op policy fails before 2048 on the default chronic. This is an important
  simulator-specific issue, not a data-length issue.

## Immediate Next Step
NEXT-R003 should solve one of:
1. select a chronic that survives 2048 under no-op; or
2. implement a simple safe policy that prevents early grid failure; or
3. use shorter 1024 neutral traces for observation QA while intervention
   rollouts handle 2048 once a policy is ready.

Do not treat the failed 2048 no-op trace as a valid 2048 sample.

## NEXT-R003 Update: No-Op Chronic Scan
Script:
- `scripts/generate/scan_grid2op_chronics.py`

Remote output:
- `/cluster/home/hulining/LTSGEN/.research/real-grid2op-20260513/chronic_scan_2048_first8.json`

Result for chronic IDs 0-7 at requested horizon 2048:

| Chronic ID | Actual no-op horizon | Survived 2048 | Failure |
| ---: | ---: | --- | --- |
| 0 | 799 | no | powerflow divergence |
| 1 | 1381 | no | powerflow divergence |
| 2 | 1095 | no | powerflow divergence |
| 3 | 810 | no | powerflow divergence |
| 4 | 801 | no | powerflow divergence |
| 5 | 382 | no | powerflow divergence |
| 6 | 1665 | no | powerflow divergence |
| 7 | 1099 | no | powerflow divergence |

Conclusion:
- Brute-force no-op selection is not a good path for 2048 in
  `rte_case14_realistic`.
- Need a simple safe policy or a different environment for 2048+ neutral traces.

## NEXT-R003 Update: Safe 2048 Trace
Two simple alternatives were tested after the no-op scan:

1. `RecoPowerlineAgent`
   - output: `rte_case14_realistic_trace_2048_reco.json`
   - requested: 2048
   - actual: 1381
   - conclusion: conservative reconnection does not fix the default chronic
     failure.

2. no-op with `NO_OVERFLOW_DISCONNECTION=True`
   - output: `rte_case14_realistic_trace_2048_nooverflow.json`
   - requested: 2048
   - actual: 2048
   - conclusion: this is a viable safe neutral trace generation mode for
     observation QA, but it must be labeled transparently because it disables
     Grid2Op's overflow disconnection protection.

Current valid observation trace set:

| File | Requested | Actual | Policy / Parameter |
| --- | ---: | ---: | --- |
| `rte_case14_realistic_trace_512.json` | 512 | 512 | no-op |
| `rte_case14_realistic_trace_1024.json` | 1024 | 1024 | no-op |
| `rte_case14_realistic_trace_2048_nooverflow.json` | 2048 | 2048 | no-op + `NO_OVERFLOW_DISCONNECTION=True` |

Use the failed `rte_case14_realistic_trace_2048.json` and
`rte_case14_realistic_trace_2048_reco.json` only as diagnostics.

## NEXT-R004/NEXT-R006 Update: Observation QA and LLM Smoke
Local observation QA output:
- `.research/real-grid2op-20260513/grid2op_real_v1_obs/grid2op_real_v1_obs.jsonl`
- `.research/real-grid2op-20260513/grid2op_real_v1_obs/sanity_report.json`

Dataset sanity:

| Metric | Value |
| --- | ---: |
| QA items | 72 |
| Answer A/B/C/D | 18 / 18 / 18 / 18 |
| Horizons | 512: 42, 1024: 24, 2048: 6 |
| Task families | 6 families, 12 each |
| Missing required fields | 0 |
| Schema gate | pass |

Prompt dry-run on 24 balanced items:

| Condition | Mean prompt chars | Max prompt chars |
| --- | ---: | ---: |
| `meta_only` | 318.6 | 382 |
| `generic_caption` | 457.1 | 521 |
| `oracle_evidence_caption` | 435.2 | 537 |
| `numbers_sampled_256` | 98,473.0 | 98,709 |

`gpt-5.4-mini` smoke on the same 24 items:

| Condition | Accuracy | Mean prompt chars |
| --- | ---: | ---: |
| `meta_only` | 0.2500 | 318.6 |
| `generic_caption` | 0.4583 | 457.1 |
| `oracle_evidence_caption` | 1.0000 | 435.2 |
| `numbers_sampled_256` | 0.5833 | 98,473.0 |

Interpretation:
- Leakage check is clean: `meta_only` is exactly random for four-way QA.
- Question-conditioned oracle evidence remains a perfect upper-bound interface
  on real Grid2Op observation QA.
- Generic captions are materially below oracle evidence.
- Sampled numbers are better than generic captions here, but remain far below
  oracle while costing about two orders of magnitude more prompt text.

Limitation:
- This is observation-only. It supports the QCC/evidence-interface story but
  does not yet establish the stronger simulator-only counterfactual benchmark
  claim.

Immediate next step:
- Implement a paired factual/intervention exporter for Grid2Op, then build
  intervention/counterfactual QA with effect-size and no-effect-rate sanity
  checks.

## NEXT-R005 Update: Intervention/Counterfactual v0
Implemented local scripts:
- `scripts/generate/export_grid2op_intervention_pair.py`
- `scripts/generate/scan_grid2op_interventions.py`
- `scripts/generate/build_grid2op_intervention_simqa.py`

Remote 512-step intervention scan:
- Env: `/cluster/home/hulining/data/grid2op/rte_case14_realistic`
- Mode: no-op factual vs line-disconnection intervention
- Horizon: 512
- Intervention step: 128
- Parameter: `NO_OVERFLOW_DISCONNECTION=True`
- Lines scanned: 0, 1, 2, 3, 4

Scan summary:

| Line | Factual survived | Intervention survived | Mean post max-rho delta | Max abs post max-rho delta |
| ---: | --- | --- | ---: | ---: |
| 0 | yes | yes | 0.0098 | 0.0479 |
| 1 | yes | yes | 0.3018 | 0.4608 |
| 2 | yes | yes | 0.1325 | 0.2500 |
| 3 | yes | yes | 0.3023 | 0.4581 |
| 4 | yes | yes | -0.0022 | 0.0131 |

Interpretation:
- Lines 1 and 3 give clear effectful interventions: disconnecting either line
  raises post-intervention max-rho from about 0.94 factual to about 1.28-1.29.
- Line 4 is a useful near-no-effect hard negative.
- This is the first real-simulator paired factual/counterfactual evidence in
  the project.

Counterfactual QA v0:
- Output: `.research/real-grid2op-20260513/grid2op_real_cf_v0/grid2op_real_cf_v0.jsonl`
- Pairs used: line 1, line 3, line 4
- QA items: 9
- Task families: `cf_peak_rho_direction`,
  `cf_intervention_overload_severity`, `cf_intervened_line`
- Answer counts: A/B/C/D = 3/2/2/2
- Missing required fields: 0
- Schema gate: pass
- Effectful direction items: 2 of 3

Prompt dry-run on all 9 items:

| Condition | Mean prompt chars | Max prompt chars |
| --- | ---: | ---: |
| `meta_only` | 363.7 | 465 |
| `generic_caption` | 518.7 | 620 |
| `oracle_evidence_caption` | 538.8 | 680 |
| `numbers_sampled_256` | 58,928.7 | 59,030 |

`gpt-5.4-mini` smoke on all 9 items:

| Condition | Accuracy | Mean prompt chars |
| --- | ---: | ---: |
| `meta_only` | 0.3333 | 363.7 |
| `generic_caption` | 0.4444 | 518.7 |
| `oracle_evidence_caption` | 1.0000 | 538.8 |
| `numbers_sampled_256` | 0.8889 | 58,928.7 |

Interpretation:
- The paired-trace counterfactual QA adapter works.
- Oracle evidence remains a perfect upper-bound interface.
- Generic captions are weak because they do not identify the line, factual
  outcome, or intervention outcome.
- Sampled paired numbers are strong at 512 steps, but require roughly 59k
  prompt characters. The current 512-step counterfactual task is therefore
  more an efficiency demonstration than an accuracy failure of numbers.

Next:
- Extend the same intervention protocol to 1024 and then 2048 if runtime is
  acceptable.
- Add more localized counterfactual slots where 256 sampled steps can miss the
  relevant post-intervention maximum or near-no-effect distinction.

## NEXT-R005/NEXT-R006 Update: Counterfactual v2 to 2048
Extended paired interventions to 1024 and 2048:

| Horizon | Step | Line | Factual survived | Intervention survived | Mean post max-rho delta | Factual post peak | Intervention post peak |
| ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |
| 1024 | 256 | 1 | yes | yes | 0.3552 | 0.9990 | 1.5541 |
| 1024 | 256 | 3 | yes | yes | 0.3539 | 0.9990 | 1.5451 |
| 1024 | 256 | 4 | yes | yes | -0.0055 | 0.9990 | 0.9904 |
| 2048 | 512 | 1 | yes | yes | 0.3657 | 1.0730 | 1.6604 |
| 2048 | 512 | 3 | yes | yes | 0.3676 | 1.0730 | 1.6491 |
| 2048 | 512 | 4 | yes | yes | -0.0146 | 1.0730 | 1.0405 |

Counterfactual QA v2:
- Output: `.research/real-grid2op-20260513/grid2op_real_cf_v2/grid2op_real_cf_v2.jsonl`
- Horizons: 512, 1024, 2048
- Lines: 1 and 3 as effectful positives; line 4 as near-no-effect negative
- QA items: 27
- Answer counts: A/B/C/D = 7/7/7/6
- Task families: `cf_peak_rho_direction`,
  `cf_intervention_overload_severity`, `cf_intervened_line`
- Effectful direction items: 6
- Schema gate: pass

Prompt dry-run on all 27 items:

| Condition | Mean prompt chars | Max prompt chars |
| --- | ---: | ---: |
| `meta_only` | 364.3 | 466 |
| `generic_caption` | 519.3 | 621 |
| `oracle_evidence_caption` | 540.1 | 681 |
| `numbers_sampled_256` | 59,002.0 | 59,223 |

`gpt-5.4-mini` smoke on all 27 items:

| Condition | Accuracy | Mean prompt chars |
| --- | ---: | ---: |
| `meta_only` | 0.2222 | 364.3 |
| `generic_caption` | 0.4074 | 519.3 |
| `oracle_evidence_caption` | 1.0000 | 540.1 |
| `numbers_sampled_256` | 0.8889 | 59,002.0 |

Outcome-only subset excluding `cf_intervened_line`:

| Condition | Accuracy |
| --- | ---: |
| `meta_only` | 0.2222 |
| `generic_caption` | 0.3889 |
| `oracle_evidence_caption` | 1.0000 |
| `numbers_sampled_256` | 0.8333 |

Interpretation:
- Real Grid2Op paired factual/counterfactual generation is feasible through
  2048 steps in the safe no-overflow mode.
- The leakage issue observed in the tiny v1 18-item set did not persist in v2;
  `meta_only` is below random.
- Oracle evidence remains a perfect compact upper-bound interface.
- Sampled numbers are strong on the current tasks, so the result currently
  supports an efficiency gap more than an accuracy-collapse claim for
  counterfactual QA.
- The sampled-numbers failures are all near-no-effect `cf_peak_rho_direction`
  items for line 4. This is a concrete hard-negative pattern for SCL: a
  captioner must distinguish small/no-effect interventions from true increases.

Next:
- Build v3 with more near-threshold hard negatives and localized event slots,
  or reduce the sampled-numbers budget in a controlled sweep
  (`numbers_sampled_32/64/128/256`) to show the cost-accuracy curve.
- Start CityLearn feasibility in parallel after the Grid2Op v2 report is
  stable, since Grid2Op now covers only one simulator domain.

## NEXT-R006 Update: Sampling Budget Sweep
Extended evaluator support for `numbers_sampled_N` conditions and ran
`N = 32, 64, 128, 256, 512` sweeps.

Observation QA sweep:
- Data: `grid2op_real_v1_obs`
- Subset: same balanced 24 items as the previous smoke
- Output: `.research/real-grid2op-20260513/grid2op_real_v1_obs/sampling_sweep_24/`

| Condition | Accuracy | Mean prompt chars |
| --- | ---: | ---: |
| `meta_only` | 0.4167 | 318.6 |
| `generic_caption` | 0.2917 | 457.1 |
| `oracle_evidence_caption` | 1.0000 | 435.2 |
| `numbers_sampled_32` | 0.6250 | 12,765.5 |
| `numbers_sampled_64` | 0.6667 | 25,011.0 |
| `numbers_sampled_128` | 0.6250 | 49,497.7 |
| `numbers_sampled_256` | 0.5417 | 98,473.0 |
| `numbers_sampled_512` | 0.4167 | 196,407.9 |

Counterfactual QA sweep:
- Data: `grid2op_real_cf_v2`
- Subset: all 27 items
- Output: `.research/real-grid2op-20260513/grid2op_real_cf_v2/sampling_sweep_27/`

| Condition | Accuracy | Mean prompt chars |
| --- | ---: | ---: |
| `meta_only` | 0.3333 | 364.3 |
| `generic_caption` | 0.4815 | 519.3 |
| `oracle_evidence_caption` | 1.0000 | 540.1 |
| `numbers_sampled_32` | 0.9259 | 7,913.2 |
| `numbers_sampled_64` | 0.8889 | 15,211.3 |
| `numbers_sampled_128` | 0.8889 | 29,808.6 |
| `numbers_sampled_256` | 0.8889 | 59,002.0 |
| `numbers_sampled_512` | 0.8889 | 117,381.2 |

Interpretation:
- Observation QA shows a strong cost-accuracy mismatch: sampled numbers can
  reach only 0.67 on this subset, and increasing from 64 to 512 sampled rows
  increases prompt size by 8x while decreasing accuracy.
- Counterfactual v2 remains easy for sampled numbers. This supports the
  efficiency story but not a counterfactual accuracy-collapse claim.
- Counterfactual sampled-number errors are concentrated in near-no-effect
  `cf_peak_rho_direction` items for line 4 across all horizons. This is a
  concrete hard-negative family for SCL and for v3 benchmark construction.
- The paper should not claim that sampled numeric prompting universally fails
  on the current counterfactual v2. The defensible claim is:
  question-conditioned evidence is much more compact and reliably solves the
  QA, while sampled numbers need much larger prompts and still fail on
  localization/near-threshold cases.

Next:
- Build Grid2Op counterfactual v3 by scanning more line/step combinations and
  selecting balanced effect-size buckets: strong increase, mild increase,
  near-no-effect, and possible decrease.
- Add localized event-slot tasks for observation QA where the relevant maximum
  is sparse or occurs near a boundary.

## NEXT-R005/v3 Prep: Targeted Hard-Negative Scan
Added scanner support for:
- `numbers_sampled_N` in the evaluator.
- `--summary_only` intervention scans.
- streaming `intervention_scan_records.jsonl`, so interrupted scans keep
  partial results.

Attempted broad 1024 summary scan over line 0-19 and steps 128/256/512. It was
stopped after a few candidates because each 1024 paired rollout is still
minute-scale. This is an engineering constraint: future large scans should
reuse factual rollouts or parallelize across processes.

Targeted 1024 summary scan:
- Output: `.research/real-grid2op-20260513/intervention_scan_v3_targeted_h1024/`
- Horizon: 1024
- Step completed: 128
- Lines completed before stopping: 0, 2, 4, 5

| Step | Line | Mean post max-rho delta | Max abs post max-rho delta | Factual post peak | Intervention post peak | Bucket |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 128 | 0 | 0.0090 | 0.0479 | 0.9990 | 1.0240 | near-zero |
| 128 | 2 | 0.1709 | 0.3017 | 0.9990 | 1.2964 | moderate increase |
| 128 | 4 | -0.0050 | 0.0509 | 0.9990 | 0.9904 | near-zero |
| 128 | 5 | 0.0398 | 0.1443 | 0.9990 | 1.1381 | mild increase |

v3 selection implication:
- Existing v2 already has strong positives: line 1 and line 3.
- New targeted scan adds line 0/4 near-zero hard negatives and line 5 mild
  increase near the overload threshold.
- A compact v3 should use full pair traces for only selected candidates instead
  of brute-force scanning all lines.

Recommended v3 buckets:
- Strong increase: line 1, line 3.
- Moderate increase: line 2.
- Mild increase / threshold: line 5.
- Near-zero hard negative: line 0, line 4.

Recommended engineering fix before larger v3:
- Optimize scanner to compute one factual rollout per `(horizon, chronic_id)`
  and reuse it for all interventions, or run candidates in parallel tmux jobs on
  the 3090 server.

## NEXT-R005/v3 Compact Result
Exported selected full 1024-step paired traces:
- `.research/real-grid2op-20260513/intervention_v3_selected_pairs/h1024_t128_line0.json`
- `.research/real-grid2op-20260513/intervention_v3_selected_pairs/h1024_t128_line2.json`
- `.research/real-grid2op-20260513/intervention_v3_selected_pairs/h1024_t128_line5.json`

Combined these with existing 1024 full pairs for line 1, line 3, and line 4.
This yields a compact effect-bucket set:

| Line | Bucket | Post peak delta | Intervention post peak max-rho |
| ---: | --- | ---: | ---: |
| 0 | near-zero / overload boundary | 0.0250 | 1.0240 |
| 4 | near-zero / no-overload | -0.0086 | 0.9904 |
| 5 | mild increase | 0.1391 | 1.1381 |
| 2 | moderate increase | 0.2974 | 1.2964 |
| 1 | strong increase | 0.5551 | 1.5541 |
| 3 | strong increase | 0.5460 | 1.5451 |

Important QA fix:
- The first v3 smoke exposed an ambiguity: a post-peak delta of `+0.025` was
  labeled `roughly_same` using the programmatic threshold, but the question did
  not state the threshold.
- Updated `build_grid2op_intervention_simqa.py` so direction questions now say
  "Using a 0.05 max-rho tolerance..." and option text explicitly says
  "changes by less than 0.05".
- After this fix, oracle evidence returns to 1.0000.

Fixed v3 compact QA:
- Output: `.research/real-grid2op-20260513/grid2op_real_cf_v3_compact_fixed/grid2op_real_cf_v3_compact_fixed.jsonl`
- QA items: 18
- Horizon: 1024 only
- Answer counts: A/B/C/D = 5/5/4/4
- Schema gate: pass

`gpt-5.4-mini` fixed v3 sweep:

| Condition | Accuracy | Mean prompt chars |
| --- | ---: | ---: |
| `meta_only` | 0.2778 | 398.7 |
| `generic_caption` | 0.2222 | 553.7 |
| `oracle_evidence_caption` | 1.0000 | 590.0 |
| `numbers_sampled_32` | 0.9444 | 7,942.7 |
| `numbers_sampled_64` | 0.9444 | 15,236.7 |
| `numbers_sampled_128` | 0.9444 | 29,823.7 |
| `numbers_sampled_256` | 1.0000 | 58,997.7 |
| `numbers_sampled_512` | 1.0000 | 117,344.7 |

Interpretation:
- v3 compact is useful as a benchmark-design lesson: numeric tolerances and
  near-threshold labels must be explicit in the question, not hidden in the
  generator.
- Once the tolerance is explicit, sampled numeric prompts solve this compact
  counterfactual set well, although with 13x-199x more prompt text than oracle
  evidence depending on sampling budget.
- Therefore, current counterfactual Grid2Op is not the best evidence for an
  accuracy-collapse claim. It remains useful for token-efficiency and
  verifiability, but the stronger numeric-prompting weakness is currently in
  observation/localization tasks.

Stop decision for this branch:
- Do not keep expanding counterfactual v3 just to force a gap.
- Next experiment should validate observation/localization on the full 72-item
  set and/or add genuinely localized event-slot tasks where sampled numeric
  rows can miss sparse extrema.

## NEXT-R006 Update: Full Observation 72-Item Core Sweep
Ran full observation/localization evaluation on all 72 `grid2op_real_v1_obs`
items.

Output:
- `.research/real-grid2op-20260513/grid2op_real_v1_obs/full72_core_sweep/`

Conditions:
- `meta_only`
- `generic_caption`
- `oracle_evidence_caption`
- `numbers_sampled_32`
- `numbers_sampled_64`
- `numbers_sampled_128`

Prompt sizes:

| Condition | Mean prompt chars | Max prompt chars |
| --- | ---: | ---: |
| `meta_only` | 318.5 | 382 |
| `generic_caption` | 456.9 | 521 |
| `oracle_evidence_caption` | 434.8 | 538 |
| `numbers_sampled_32` | 12,759.3 | 12,853 |
| `numbers_sampled_64` | 24,997.0 | 25,117 |
| `numbers_sampled_128` | 49,470.7 | 49,649 |

Overall results:

| Condition | Accuracy | Mean prompt chars |
| --- | ---: | ---: |
| `meta_only` | 0.2361 | 318.5 |
| `generic_caption` | 0.3889 | 456.9 |
| `oracle_evidence_caption` | 1.0000 | 434.8 |
| `numbers_sampled_32` | 0.5278 | 12,759.3 |
| `numbers_sampled_64` | 0.5556 | 24,997.0 |
| `numbers_sampled_128` | 0.5139 | 49,470.7 |

By task family:

| Task | Generic | Sampled-32 | Sampled-64 | Sampled-128 | Oracle |
| --- | ---: | ---: | ---: | ---: | ---: |
| `max_avg_generator` | 0.8333 | 0.3333 | 0.5833 | 0.0833 | 1.0000 |
| `max_avg_load` | 0.0000 | 0.5000 | 0.4167 | 0.4167 | 1.0000 |
| `peak_rho_line` | 0.2500 | 0.8333 | 0.8333 | 0.7500 | 1.0000 |
| `peak_rho_quarter` | 0.2500 | 0.3333 | 0.5833 | 0.5000 | 1.0000 |
| `peak_total_load_quarter` | 0.4167 | 0.4167 | 0.1667 | 0.5833 | 1.0000 |
| `total_load_trend` | 0.5833 | 0.7500 | 0.7500 | 0.7500 | 1.0000 |

Interpretation:
- This is currently the strongest real Grid2Op evidence for the QCC story.
- Oracle evidence is both shorter than generic captions and perfectly accurate.
- Sampled numeric prompting is much longer and still unstable:
  sampled-64 is best at 0.5556, while sampled-128 gets worse despite doubling
  prompt size.
- Numeric prompting weaknesses are clearest for average/aggregation and
  localization tasks (`max_avg_generator`, `max_avg_load`,
  `peak_*_quarter`), not for simple trend or peak-line identification.
- This supports a strong but precise paper claim: question-conditioned evidence
  captions provide the relevant statistic/event directly; sampled raw numeric
  tables are expensive and not a reliable substitute for extracting the needed
  evidence.

Next:
- Add localized sparse-event slots to observation QA, because this is where
  sampled numeric prompts are empirically weakest.
- Start CityLearn feasibility after this Grid2Op observation result is stable,
  to avoid the benchmark being single-domain.

## Context-Card Patch and Final Slot-Value Protocol

The case-study review exposed a real protocol issue: previous Grid2Op questions
were underspecified for non-domain experts. A respondent did not know what a
Grid2Op line represents, what disconnecting a line means, or how factual and
counterfactual traces should be compared.

Patch:
- Added a Grid2Op context card to the evaluator and case-study report.
- Added task rules for slot-value questions.
- Switched the final clean QA to fixed slot-value questions.

Rejected intermediate protocols:
- `with_context_v1` fixed the missing-background issue but exposed answer
  priors in the original argmax/semantic QA.
- v2 statement QA and v3 peak/severity numeric QA were rejected because
  `meta_only` remained too high.

Final clean data:
- Observation:
  `.research/real-grid2op-20260513/grid2op_real_v4_obs_slot/grid2op_real_v4_obs_slot.jsonl`
- Counterfactual:
  `.research/real-grid2op-20260513/grid2op_real_cf_v6_slot/grid2op_real_cf_v6_slot.jsonl`

Important generator fix:
- Correct option letters are now globally balanced by sample-ID hash, not by
  task order, quarter index, or variable ID.
- Observation answer counts: A/B/C/D = 18/18/18/18.
- Counterfactual answer counts: A/B/C/D = 3/3/3/3.

Gate results:

| Split | Output | `meta_only` | `oracle_evidence_caption` |
| --- | --- | ---: | ---: |
| Observation | `grid2op_real_v4_obs_slot/gate_meta_oracle_with_context_v2b/` | 0.2222 | 1.0000 |
| Counterfactual | `grid2op_real_cf_v6_slot/gate_meta_oracle_with_context_v2b/` | 0.0833 | 1.0000 |

Final core sweep:

Observation output:
- `.research/real-grid2op-20260513/grid2op_real_v4_obs_slot/core_sweep_with_context_v2b/`

| Condition | Accuracy | Mean prompt chars |
| --- | ---: | ---: |
| `meta_only` | 0.2361 | 1,479.1 |
| `generic_caption` | 0.3056 | 1,617.6 |
| `oracle_evidence_caption` | 1.0000 | 1,541.5 |
| `numbers_sampled_32` | 0.3056 | 13,920.0 |
| `numbers_sampled_64` | 0.3889 | 26,157.6 |
| `numbers_sampled_128` | 0.4028 | 50,631.3 |

Counterfactual output:
- `.research/real-grid2op-20260513/grid2op_real_cf_v6_slot/core_sweep_with_context_v2b/`

| Condition | Accuracy | Mean prompt chars |
| --- | ---: | ---: |
| `meta_only` | 0.1667 | 1,590.3 |
| `generic_caption` | 0.1667 | 1,745.3 |
| `oracle_evidence_caption` | 1.0000 | 1,663.4 |
| `numbers_sampled_32` | 0.5000 | 9,134.3 |
| `numbers_sampled_64` | 0.5000 | 16,428.3 |
| `numbers_sampled_128` | 0.5833 | 31,015.3 |
| `numbers_sampled_256` | 0.5833 | 60,189.3 |

Current conclusion:
- The fair Grid2Op protocol must include background context.
- The benchmark must also guard against option/label priors; context alone is
  insufficient.
- Under the cleaned protocol, oracle evidence caption is a compact perfect
  upper bound; generic captions stay near meta-only; sampled numeric prompts
  are much longer and remain far below oracle.
- This strengthens the precise paper claim: question-conditioned, verifiable
  evidence is a better interface than generic captions or raw sampled tables on
  these medium-horizon Grid2Op tasks.
