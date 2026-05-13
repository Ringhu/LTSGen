# LTSGEN Project Instructions

This file is the current project-level operating context for `/home/cris/Research/LTSGEN`.
It overrides the stale `CLAUDE.md` for the active research direction.

## Current Active Workstream

**Active direction:** medium-horizon simulator-derived, verifiable TS-QA for
question-conditioned evidence captioning.

**Active pilot contract:** `./.research/research-contract-medium-horizon-simqa-20260512.md`

**Active method contract:** `./.research/research-contract-qcc-v0-20260513.md`

The older `./.research/research-contract-20260419.md` / ShapeShift-CPR plan is
historical for the current workstream. Do not use it as the active route unless
the user explicitly asks to resume that line.

## Project Framing

The project studies long/medium-horizon time-series understanding with LLMs.
The previous broad claim, "caption is a generally better interface than raw
numbers," is not supported by existing cross-benchmark results. The current
framing is narrower and more defensible:

> For medium-to-long horizon TS-QA, raw numbers are token-inefficient and hard
> for LLMs to use directly, while generic captions are unstable and often
> unfaithful. A useful interface should be question-conditioned and verifiable:
> it should extract only the evidence needed for the downstream question and
> ground that evidence in the input trace or simulator state.

Operational horizon tiers:

| Tier | Steps | Role |
| --- | ---: | --- |
| Short | 256-512 | connect to current TSShapeQA / existing benchmarks |
| Medium-low | 1024-2048 | bridge regime |
| Medium-high | 4096-8192 | main target for this workstream |
| Long | 16k+ | future / stretch, not first-pass target |

For this workstream, "long" in prose should usually be written as
**medium-to-long horizon** or **medium-high horizon** unless 16k+ evidence has
actually been run.

## Current Paper Idea

Working thesis:

> End-to-end TS-LLMs and raw-number prompting are not a clean scaling solution
> for medium-horizon TS-QA. Generic captions also fail because they omit or
> hallucinate task-relevant evidence. We propose question-conditioned,
> verifiable evidence captioning, trained/evaluated on simulator-derived TS-QA
> where ground truth is programmatically known.

Current paper skeleton:

1. Motivation: existing caption-only and caption+numbers results are unstable;
   current captioners often harm QA or collapse to generic summaries.
2. Benchmark need: existing real TS datasets rarely provide reliable QA ground
   truth for long windows; simulator-derived traces can expose state, event,
   and counterfactual ground truth.
3. Method direction: question-conditioned captioning (QCC) plus verifiable /
   self-consistency grounding (SCL or equivalent).
4. Evidence: scaling across horizons, showing oracle evidence caption is an
   effective upper-bound interface before training any new captioner.
5. Later method: train a captioner to approximate oracle evidence captions;
   only after the benchmark/protocol signal is validated.

## Main Contribution Candidates

Keep the paper focused. Do not expand to three full contributions unless the
data becomes strong enough.

Primary contribution:
- **Question-conditioned evidence captioning (QCC):** caption content is
  conditioned on the downstream question or task slot, not task-agnostic.

Supporting contribution:
- **Verifiable grounding / self-consistency:** captions must be checked against
  trace-derived or simulator-derived facts. Hard negatives should come from
  programmatic counterfactuals, swaps, and event perturbations, not from LLM
  preference alone.

Benchmark contribution:
- **Simulator-derived verifiable TS-QA:** use simulator state and
  factual/counterfactual traces to construct QA with programmatic ground truth.
  Treat this initially as support for the method, not automatically as a
  standalone third contribution.

Do not present CFQA as a third core contribution until it has real-simulator
evidence and enough task breadth to stand on its own.

## Data Strategy

Use a staged strategy:

1. **Simulator-lite protocol gate**: small deterministic generators that mimic
   grid/building dynamics. Purpose: test schema, leakage, prompt protocol, and
   oracle evidence interface cheaply.
2. **Real simulator feasibility**: first integrate Grid2Op and CityLearn.
3. **Synthetic branch**: keep existing LTSGen-style synthetic data as auxiliary
   coverage for rare task primitives, not as the sole benchmark.
4. **Real TS OOD diagnostics**: ETT, Time-MMD, dataset_a, TSAQA, FREDQA are
   useful diagnostics, but avoid using LLM-written QA as final GT for long
   horizon claims.

Recommended simulator order:

| Simulator | Priority | Reason |
| --- | --- | --- |
| Grid2Op | first | medium horizon, physical coupling, event/disturbance semantics |
| CityLearn | first | long building-energy traces, weather/building coupling |
| AIOpsLab | second | strong RCA story but heavier engineering dependencies |
| FinRL | later | finance domain appeal, but often historical replay rather than clean intervention simulator |

## Current Pilot Results

Pilot artifacts live under:
`./.research/medium-horizon-simqa-pilot-20260512/`

Important files:
- `simqa_pilot.jsonl`
- `sanity_report.json`
- `llm_smoke_40/metrics.json`
- `numbers_full_smoke_10/metrics.json`
- `full_numbers_prompt_dryrun_40/prompt_report.json`
- `PILOT_SUMMARY.md`

Pilot setup:
- Domains: `grid_lite`, `city_lite`
- Horizons: 512, 1024, 2048, 4096, 8192
- Task families: `event_quarter`, `root_cause`, `first_responder`,
  `counterfactual_direction`
- 120 generated QA items, balanced across domain/horizon/task
- Answer letters A/B/C/D exactly balanced

Main `gpt-5.4-mini` smoke on 40 balanced items:

| Condition | Accuracy | Mean prompt chars |
| --- | ---: | ---: |
| `meta_only` | 0.275 | 348 |
| `generic_caption` | 0.325 | 496 |
| `numbers_sampled_256` | 0.175 | 18,423 |
| `oracle_evidence_caption` | 1.000 | 514 |

Interpretation:
- Leakage sanity passed (`meta_only` close to random).
- Generic caption is not enough.
- Sampled raw numbers are expensive and ineffective in this pilot.
- Oracle question-conditioned evidence caption is a strong upper-bound
  interface.

Full raw-number prompt dry run:
- 40-item mean: 223k chars
- 40-item max: 580k chars

This supports treating `numbers_full` as a diagnostic, not the main large-scale
condition.

## Current Real-Simulator Results

### Grid2Op

Current clean Grid2Op artifacts:
- Observation: `.research/real-grid2op-20260513/grid2op_real_v4_obs_slot/`
- Counterfactual: `.research/real-grid2op-20260513/grid2op_real_cf_v6_slot/`
- Chinese case study:
  `docs/case-studies/20260513-grid2op/grid2op_case_study.md`

Context-card protocol:
- Use `domain_context_v3_grid2op_citylearn_slot_value_rules`.
- Grid2Op questions must include background context explaining `line`, `rho`,
  `line_status`, factual trace, intervention trace, and local/global time.
- The final paper-facing Grid2Op QA uses slot-value options with globally
  hash-balanced answer letters. Earlier no-context and label-style results are
  superseded.

Final clean Grid2Op result:
- Observation, 72 items: meta 0.2361, generic 0.3056, oracle 1.0000,
  sampled-32/64/128 = 0.3056 / 0.3889 / 0.4028.
- Counterfactual, 12 items: meta 0.1667, generic 0.1667, oracle 1.0000,
  sampled-32/64/128/256 = 0.5000 / 0.5000 / 0.5833 / 0.5833.

Interpretation:
- Grid2Op supports the main interface claim: short, question-conditioned
  evidence captions are a reliable upper bound, while generic captions and
  sampled numeric prompts are not enough.
- Current counterfactual evidence is useful for verifiability and efficiency,
  but its sample size is too small for a standalone CFQA contribution.

### CityLearn

Progress artifact:
- `.research/real-citylearn-progress-20260513.md`

Current clean CityLearn artifacts:
- Data/results:
  `.research/real-citylearn-20260513/citylearn_real_v2_slot/`
- Chinese case study:
  `docs/case-studies/20260513-citylearn/citylearn_case_study.md`
- Source trace:
  `.research/real-citylearn-20260513/citylearn_challenge_2022_phase_1_trace_2048.json`
- Remote 8192 trace exists on 3090:
  `/cluster/home/hulining/LTSGEN/.research/real-citylearn-20260513/citylearn_challenge_2022_phase_1_trace_8192.json`

Expanded v2 setup:
- 72 slot-value QA items
- horizons covered: 512, 1024, 2048
- task families: building load point values, quarter mean net electricity, and
  outdoor temperature point values
- answer letters A/B/C/D = 18/18/18/18

Final clean CityLearn v2 result:
- meta 0.2361, generic 0.2500, oracle 1.0000
- sampled-32/64/128 = 0.3333 / 0.3889 / 0.4583
- prompt chars: oracle about 1.4k, sampled-128 about 32.3k

Interpretation:
- CityLearn is now a valid second-simulator feasibility result.
- It should not yet be presented as a full benchmark: it is one packaged
  dataset and the task set is still slot-value oriented.
- The result supports the evidence-caption upper-bound claim and motivates
  QCC-v0 training.

## Implementation Paths

Current scripts:
- `scripts/generate/build_medium_horizon_simqa_pilot.py`
- `scripts/generate/export_grid2op_trace.py`
- `scripts/generate/build_grid2op_simqa_from_trace.py`
- `scripts/generate/export_citylearn_trace.py`
- `scripts/generate/build_citylearn_slot_qa.py`
- `scripts/eval/eval_medium_horizon_simqa_pilot.py`

Current tracker:
- `./.research/medium-horizon-simqa-experiment-tracker-20260512.md`

When adding real simulator support, prefer a schema-compatible adapter:

```text
real simulator trace
  -> export multivariate factual trace
  -> optionally export counterfactual trace or intervention metadata
  -> create records with:
       id, domain, horizon, variables, trace seed/path,
       event metadata, question, options, answer,
       oracle_evidence_caption, generic_caption, evidence dict
  -> run the same evaluator and sanity checks
```

Do not let real simulator integration change the evaluation protocol unless a
new contract or explicit plan update is written.

## Evaluation Rules

Ground truth rules:
- GT must be computed from program state, trace arrays, simulator logs, or
  factual/counterfactual differences.
- GPT/LLM may rewrite question wording, but must not decide the correct answer.
- Always keep answer-letter balance and report `meta_only`.

Minimum conditions:
- `meta_only`
- `generic_caption`
- `oracle_evidence_caption`
- `numbers_sampled_256`

Optional diagnostics:
- `numbers_full` on tiny subsets only
- tool-agent baselines after the benchmark is stable
- trained QCC model only after oracle and real-simulator gates pass

Critical metrics:
- accuracy by condition
- accuracy by horizon
- accuracy by task family
- prompt length / token-cost proxy
- meta-only leakage
- oracle-vs-generic gap
- oracle-vs-sampled-numbers gap at 4096/8192

## Existing Empirical Constraints

Existing cross-benchmark analysis found:
- OpenTSLM caption-only is not a stable evidence interface.
- ChatTS is better in some settings but not an oracle.
- caption+numbers does not guarantee monotonic improvement and can harm.
- FREDQA overall accuracy is heavily affected by meta-only / domain prior.
- Slot-level factuality audit shows systematic caption errors, especially
  OpenTSLM periodicity hallucination.

So avoid broad claims like:
- "caption is better than numbers"
- "caption is all you need"
- "current TS captioners understand long time series"

Use narrower claims:
- "question-conditioned evidence captions can be an efficient upper-bound
  interface"
- "generic captions are insufficient"
- "simulator-derived GT enables verifiable medium-horizon TS-QA"

## Engineering Rules

- Read this `AGENTS.md` before `CLAUDE.md`. `CLAUDE.md` is stale for this
  direction.
- Do not commit or revert unrelated dirty work. This repo has many historical
  untracked artifacts.
- Case-study reports for this project should be Chinese-first by default:
  write case titles, analysis text, figure titles/legends, question wording,
  option text, and conclusions in Chinese. Common technical terms may stay in
  English if followed by a Chinese gloss, e.g. `caption（说明文本）`,
  `prompt（提示文本）`, `ground truth（真值）`, `counterfactual（反事实）`.
  Keep reproducibility identifiers such as record IDs, task family names,
  method condition names, and file paths in their original English/code form,
  with Chinese explanations around them.
- Keep new pilot artifacts under `.research/<dated-dir>/`.
- Do not copy large datasets or simulator outputs into the local repo. Store
  large outputs on A100/3090 or keep only small manifests locally.
- Use `python3`, not `python`, on this machine.
- Local `grid2op` and `citylearn` were not installed when first checked on
  2026-05-12. `grid2op==1.12.4` is now installed in `.venv-simqa`.
  CityLearn local install was stopped because it pulled heavy torch/CUDA and
  openstudio dependencies. CityLearn 2.5.0 is available on the 3090 server at
  `/cluster/home/hulining/envs/citylearn`, with packaged data under
  `/cluster/home/hulining/.cache/citylearn/v2.5.0/`.
- LLM calls use the existing OpenAI-compatible proxy through
  `~/Research/gptapi/llm_client.py`; do not expose API keys.

## Next Action

The immediate next experiment is to move from validated simulator gates to
method training:

1. Define the exact QCC-v0 target format: slot extraction, evidence caption, or
   both.
2. Run QCC-v0 overfit/slot-prediction checks on the validated Grid2Op and
   CityLearn slot QA.
3. Only after QCC-v0 learns the oracle evidence target, move to SCL /
   hard-negative training.

Do not start SCL or broader training until QCC-v0 passes a small overfit gate.
