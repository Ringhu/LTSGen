# Experiment Tracker — ShapeShift

Contract: `.research/research-contract-20260419.md` (IMMUTABLE, git `bd1a18b`)
Plan: `.research/experiment-plan-20260419.md`
Status: ACTIVE from 2026-04-19

Legend: **TODO** · **IP** (in progress) · **DONE** · **BLOCKED** · **CUT**

## Stream 1 — NeurIPS D&B 2026-05-06

| RunID | Date | Block | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| R001 | 04-19 | infra | Smoke test vLLM + Qwen judge, ChatTS-14B DL, OpenTSLM ckpt load | — | — | infra-ok | MUST | TODO | First action |
| R002 | 04-20 | B1 infra | `transforms.py` + unit tests for all 6 transforms | — | canonical 20/transform | pytest pass | MUST | TODO | R001 dep |
| R003 | 04-21 | B1 data | v2 smoke build n=40 × 3 transforms | `build_tsshapeqa_v2.py` | OOD smoke | pipeline ok | MUST | TODO | R002 dep |
| R004 | 04-22 | B1 data | Full v2 OOD n=800 × 6 transforms | gpt-5.4 generator | OOD | 800 jsonl | MUST | TODO | R003 dep |
| R005 | 04-23 | B1 data | Full v2 in-dist n=300 × 6 transforms + sanity | gpt-5.4 + sanity script | in-dist | 300 jsonl + sanity md | MUST | TODO | R004 dep; S4 sanity gate |
| R006 | 04-24 | B1 models | OpenTSLM-Flamingo seed2 retrain (5-8 hr) | same arch, diff seed | LTSGen train | val loss | MUST | TODO | Can run overnight via Codex on A100 |
| R007 | 04-24 | B1 models | OpenTSLM-Flamingo seed1 caption gen on v2 | existing ckpt | v2 OOD + in-dist | captions jsonl | MUST | TODO | parallel with R006 |
| R008 | 04-25 | B1 models | Caption gen: seed2 + SoftPrompt (if available) + ChatTS-14B | 3 systems | v2 OOD + in-dist | captions jsonl | MUST | TODO | R006+R007 dep |
| R009 | 04-26 | GATE | **S6a hard gate**: v2 + 4-model captions ready? | — | — | GO/NO-GO | MUST | TODO | If NO-GO: fallback to §8.1 |
| R010 | 04-27 | B1 eval | Diagnosis CFR: 4 models × 6 transforms × 800 pairs via Qwen judge | Qwen3-8B-Instruct | v2 OOD | CFR table | MUST | TODO | R009=GO dep |
| R011 | 04-28 | B1 eval | Judge-transfer subsample: gpt-5.4-mini on 20% | gpt-5.4-mini | v2 OOD subset | CFR gap | MUST | TODO | R010 dep |
| R012 | 04-29 | B2 eval | H2 ρ: consistency vs held-out shape-QA; 6 evaluees | Qwen + oracle + GPT-4o | v2 OOD + held-out QA | Spearman ρ | MUST | TODO | R010 dep; H2 gate |
| R013 | 04-30 ~ 05-02 | paper | Stream 1 paper draft §1-§5 | NeurIPS D&B template | — | compilable PDF | MUST | TODO | R012 dep |
| R014 | 05-03 | paper | Figure polish + table formatting | paper-figure skill | — | v0 PDF | MUST | TODO | R013 dep |
| R015 | 05-04 | paper | Internal review via Codex MCP | research-review skill | — | review-round1.md | MUST | TODO | R014 dep |
| R016 | 05-05 | paper | Apply review fixes + final proofread | — | — | final PDF | MUST | TODO | R015 dep; buffer day |
| R017 | 05-06 | submit | **SUBMIT NeurIPS D&B + arXiv v0** | — | — | submission receipt + arXiv ID | MUST | TODO | HARD deadline |

## Stream 2 — arXiv 2026-06-15 + ICLR 2027

### Week 1 (05-07 ~ 05-13) CPR implementation

| RunID | Block | Purpose | System | Status | Notes |
|---|---|---|---|---|---|
| R018 | impl | CPR GRPO trainer on OpenTSLM | `rl/cpr_trainer.py` | TODO | — |
| R019 | impl | Pair-batch sampler | `rl/pair_sampler.py` | TODO | R018 dep |
| R020 | impl | Qwen judge vLLM integration for reward loop | `rl/judge_vllm.py` | TODO | R018 dep |
| R021 | impl | Smoke test: 1 seed × 200 steps, 1 arm (C-full) | — | TODO | R018+R019+R020 dep; MUST catch bugs before W2 |

### Week 2-3 (05-14 ~ 05-27) B3 main 4-arm runs

| RunID | Block | Purpose | System | GPU-hr | Status | Notes |
|---|---|---|---|---|---|---|
| R022-R024 | B3 | Arm B CapRL-pure × 3 seeds | captioner + QA reward only | 105 | TODO | Launch parallel on 2× A100 |
| R025-R027 | B3 | Arm C CPR × 3 seeds | captioner + QA + pair reward | 105 | TODO | The central bet |
| R028-R030 | B3 | Arm D Pair-only × 3 seeds | captioner + pair reward only | 105 | TODO | Sanity anchor |
| R031 | B3 | Arm A SFT baseline eval (no training) | frozen vars=1 ckpt | 0 | TODO | Use existing checkpoint |
| R032 | B3 | Arm E oracle eval (no training) | GPT-5.4 oracle captioning | 0 API | TODO | Upper bound |

### Week 3-4 (05-21 ~ 06-03) B4 β-sweep + B5 transfer

| RunID | Block | Purpose | System | GPU-hr | Status | Notes |
|---|---|---|---|---|---|---|
| R033-R035 | B4 | CPR β=0.3 × 3 seeds | — | 105 | TODO | — |
| R036-R038 | B4 | CPR β=3 × 3 seeds | — | 105 | TODO | — |
| R039-R041 | B4 | CPR β=10 × 3 seeds | — | 105 | TODO | — |
| R042-R044 | B5 | Transform transfer: train T_rev only × 3 seeds | — | 105 | TODO | Held-out: T_var/T_peak/T_amp/T_phase/T_changept |

### Week 4 (05-28 ~ 06-03) B6 judge-swap (eval only)

| RunID | Block | Purpose | System | GPU-hr | Status | Notes |
|---|---|---|---|---|---|---|
| R045 | B6 | C-arm eval with Qwen judge | Qwen3-8B | 0 train | TODO | 3-seed mean ± std |
| R046 | B6 | C-arm eval with gpt-5.4-mini judge | closed API | 0 train | TODO | 200 samples subset |
| R047 | B6 | C-arm eval with gpt-5.4 judge | closed API | 0 train | TODO | 200 samples subset |

### Week 5 (06-04 ~ 06-10) B7 length + B8 in-dist/OOD + B9 qualitative

| RunID | Block | Purpose | System | GPU-hr | Status | Notes |
|---|---|---|---|---|---|---|
| R048 | B7 | CPR trained length=128 | — | 35 | TODO | NICE-TO-HAVE |
| R049 | B7 | CPR trained length=256 (canonical) | — | 0 (reuses R025) | TODO | — |
| R050 | B7 | CPR trained length=512 | — | 35 | TODO | NICE-TO-HAVE |
| R051 | B7 | CPR trained length=1024 | — | 35 | TODO | NICE-TO-HAVE |
| R052 | B8 | Split existing results by in-dist/OOD | eval only | 0 | TODO | Free |
| R053 | B9 | Qualitative 20+20 analysis | manual | 0 | TODO | NICE-TO-HAVE |
| R054 | GATE | **S6b hard gate 06-08** | — | 0 | TODO | Route per contract §2.3 |

### Week 6 (06-11 ~ 06-15) preprint write-up

| RunID | Block | Purpose | Deliverable | Status | Notes |
|---|---|---|---|---|---|
| R055 | paper | Stream 2 Method §5 + Ablations §6 | LaTeX sections | TODO | — |
| R056 | paper | arXiv v1 full paper | preprint PDF | TODO | — |
| R057 | submit | **SUBMIT arXiv 2026-06-15** | arXiv ID + tweet | TODO | HARD deadline |

---

## Cumulative GPU budget tracker

| Week | Allocated A100-hr | Used A100-hr | Remaining |
|---|---|---|---|
| Stream 1 (04-19 ~ 05-06) | ~20 | 0 | 20 |
| W1 (05-07 ~ 05-13) smoke | ~20 | 0 | 20 |
| W2-W3 (05-14 ~ 05-27) B3 | 315 | 0 | 315 |
| W3-W4 (05-21 ~ 06-03) B4/B5 | 525 | 0 | 525 |
| W4 (05-28 ~ 06-03) B6 | 0 | 0 | 0 |
| W5 (06-04 ~ 06-10) B7/B8/B9 | 105 | 0 | 105 |
| W6 (06-11 ~ 06-15) writing | 0 | 0 | 0 |
| **Total** | **985** | **0** | **985** |

Budget vs contract cap (96 A100-hr × 12 runs = 1152 A100-hr): under budget by 14%. Cushion = ~167 A100-hr for debugging / rerun.
