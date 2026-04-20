# Experiment Plan — ShapeShift

**Project:** LTSGEN — Counterfactual-grounded TS-LLM captioning
**Contract:** `.research/research-contract-20260419.md` (git `bd1a18b`, IMMUTABLE)
**Plan locked:** 2026-04-19
**Status:** ACTIVE
**Plan thesis:** Three hypotheses (H1 Diagnosis, H2 Benchmark, H3 Method). Stream 1 ships H1+H2 to NeurIPS D&B 2026-05-06 in 17 days; Stream 2 extends with H3 CPR method to arXiv preprint 2026-06-15 + ICLR 2027 main. User is solo PhD student, so Streams are sequential in human-hours, partially overlappable in GPU-hours (training starts before writing finishes).

---

## 1. Claim Map

| Claim | Linked hypothesis | Linked blocks | Load-bearing evidence | Minimum convincing result |
|---|---|---|---|---|
| C1: "Synthetic-caption SFT TS-LLMs fail to condition on input shape" | H1 | B1 | CFR table across 4 models × 6 transforms | CFR ≤ 10% on ≥ 3 of 4 models on ≥ 4 of 6 transforms |
| C2: "Consistency rate is a strictly stronger diagnostic than raw accuracy for TS-LLM faithfulness" | H2 | B2 | Spearman ρ gap on ShapeShift-TS vs shape-sensitive QA held-out | ρ_consistency ≥ 0.5 AND ρ_consistency − ρ_accuracy ≥ 0.2 |
| C3: "CPR training raises CFR from ~3% to ≥ 60% while CapRL-pure plateaus" | H3 | B3, B4, B5 | 4-arm comparison table; load-bearing delta = C-arm vs B-arm | C: QA ≥ 0.70 AND CFR ≥ 0.60, AND C−B ≥ 15pp QA or ≥ 30pp CFR |
| C4 (anti-claim to rule out): "Gains come from reward hacking / judge-specific overfitting, not from real TS grounding" | H3 | B6 (judge swap), B7 (transform transfer) | Gains persist across 3 judges; gains transfer across transforms | Judge-swap gap ≤ 15pp; transform-transfer CFR ≥ 45 on held-out transform |

---

## 2. Paper Storyline

**Stream 1 (NeurIPS D&B, 2026-05-06)** main paper must prove: C1 + C2. Method (CPR) mentioned as "future work" in discussion.

**Stream 2 (arXiv 2026-06-15 + ICLR 2027)** main paper must prove: C1 + C2 + C3 + C4. Stream 1 material becomes §3 (Diagnosis) + §4 (Benchmark). Stream 2 adds §5 (CPR Method) + §6 (Ablations).

**Intentionally cut:**
- Alternative methods (neurosymbolic concept bottleneck, contrastive decoding, debate) — all dropped in idea-generation stage as weaker than CPR
- TSShapeQA v1 is abandoned in favor of v2. Only v2 is reported.
- Medical TS benchmarks (HAR, Sleep, ECG) — OpenTSLM's home turf, not ours
- Multivariate TS — vars=1 is already the user's best checkpoint; do not relitigate

---

## 3. Experiment Blocks

### Block B1 — Diagnosis: cross-family CFR audit

- **Claim tested:** C1 (H1)
- **Why:** Establishes the problem exists beyond our own retrained model — motivates benchmark and method.
- **Dataset:** ShapeShift-TS-v2 OOD split (n = 800, sources = Time-MMD + exchange_rate + illness)
- **Compared systems:**
  1. OpenTSLM-Flamingo-vars1 seed1 (user's existing checkpoint `ablation_vars1_mixed`)
  2. OpenTSLM-Flamingo-vars1 seed2 (retrain or distill, see R005)
  3. OpenTSLM-SoftPrompt (pretrained checkpoint from Stanford release, if released; else skip and drop to 3-of-3)
  4. ChatTS-14B (ByteDance HF weights `bytedance-research/ChatTS-14B`, zero-shot)
- **Transforms applied:** all 6 {T_rev, T_var, T_peak, T_amp, T_phase, T_changept}, each with deterministic GT-flip rule in `scripts/generate/transforms.py`
- **Metrics:**
  - Primary: CFR per (model × transform) cell — % of (x, T(x)) pairs where generated caption causes downstream-LLM answer to flip in the GT-correct direction
  - Secondary: caption-diff-rate = % of pairs where caption *text* differs at all (sanity: if this is also low, caption is literally unchanged → not a reward issue)
  - Meta: in-dist CFR for the same 4 models on v2 in-dist split (n = 300)
- **Judge:** Qwen2.5-7B-Instruct (primary); gpt-5.4-mini on 20% subsample (judge-transfer)
- **Setup:** batch inference via vLLM; 3090 for judge, A100 GPU2 for OpenTSLM inference; ChatTS-14B on 2×3090 or 1×A100
- **Success:** CFR ≤ 10% on ≥ 3 of 4 models × ≥ 4 of 6 transforms
- **Failure interpretation:** Any model achieves CFR ≥ 30% on > 50% of transforms → H1 falsified, our diagnosis was model-specific. Paper pivots to model-specific story (much weaker).
- **Table target:** Table 1 (Stream 1 main result)
- **Priority:** MUST-RUN

### Block B2 — Benchmark validity: consistency rate vs accuracy correlation

- **Claim tested:** C2 (H2)
- **Why:** A benchmark paper must show the metric measures something new — otherwise it's just another TSQA.
- **Dataset:** ShapeShift-TS-v2 OOD; shape-sensitive held-out QA set (constructed from Time-MMD + exchange_rate segments NOT in v2's 800) as correlation target
- **Compared systems:** 6 evaluees — 4 models from B1 + GPT-4o (zero-shot on plotted TS) + oracle caption (GPT-5.4 with GT features) as anchors
- **Metrics:**
  - Per system: consistency rate on v2 (primary metric of our benchmark)
  - Per system: single-question accuracy on shape-sensitive held-out QA
  - Spearman ρ_consistency between consistency and held-out accuracy
  - Spearman ρ_accuracy between v2 single-question accuracy and held-out accuracy
  - Target: ρ_consistency ≥ 0.5 AND ρ_consistency − ρ_accuracy ≥ 0.2
- **Sanity (required before primary result):**
  - Meta-only on v2 ≤ blended-random + 0.12 per qa_type
  - Numbers − meta-only ≥ +10pp overall
- **Success:** Both sanity conditions hold AND primary ρ targets met
- **Failure interpretation:** If consistency does not correlate, the metric does not measure grounding — benchmark paper does not ship. Fall back to Stream 1 dropping to only the diagnosis claim (much weaker).
- **Table target:** Table 2 + Figure 1 (scatter of consistency vs held-out accuracy)
- **Priority:** MUST-RUN

### Block B3 — Method main result: 4-arm comparison

- **Claim tested:** C3 (H3) main
- **Why:** The central bet of the paper.
- **Dataset:** ShapeShift-TS-v2 OOD (n = 800) for evaluation; training on LTSGen paired-counterfactual training split (new, n ≈ 5000 pairs)
- **Compared systems:**
  - A: Frozen OpenTSLM-Flamingo-vars1 (no RL; sanity anchor)
  - B: OpenTSLM + CapRL-pure (QA-accuracy reward only, no pair term)
  - C: OpenTSLM + CPR (QA-accuracy + counterfactual-pair consistency, ours)
  - D: OpenTSLM + Pair-only (counterfactual-pair reward only, no QA reward; sanity)
  - E: Oracle caption (GPT-5.4 with GT features, fixed upper bound)
- **Seeds:** 3 per arm for B/C/D; 1 for A (existing) and E (deterministic)
- **Metrics:** CFR (primary), overall shape-QA accuracy (secondary), caption-diff-rate, per-transform CFR
- **Setup:**
  - Backbone frozen: Chronos-2 encoder (frozen); Qwen3-4B LLM (frozen except LoRA r=16 on attention layers); Flamingo cross-attn (trainable)
  - Training: GRPO with 8 rollouts/step, 3 counterfactual pairs/batch, lr 1e-5, 5000 steps
  - Wall-clock estimate: ~35 A100-hr per seed
  - Judge (reward): Qwen2.5-7B-Instruct via vLLM on 3090 (1 GPU dedicated)
- **Success:** C achieves QA ≥ 0.70 AND CFR ≥ 0.60, AND C − B ≥ 15pp QA or ≥ 30pp CFR
- **Failure interpretation:** See contract §2.3 routing table. B-partial → preprint with open-problem framing. C-failure → drop method, pure D&B paper.
- **Table target:** Table 3 (Stream 2 main result)
- **Priority:** MUST-RUN

### Block B4 — Reward-component ablation

- **Claim tested:** C3 load-bearing piece: "The pair term is necessary"
- **Why:** Distinguishes CPR from vanilla CapRL port.
- **Compared systems:** {C: CPR (α=1, β=1), C-β0.3, C-β3, C-β10, D: Pair-only}
- **Seeds:** 3 per β value
- **Setup:** same as B3, sweep β only
- **Success:** β=1 ∩-shaped peak on QA (monotonic CFR ↑ with β acceptable); extreme β (0.3 or 10) clearly worse on QA
- **Failure interpretation:** If β=0.3 wins → pair term hurts → C3 mechanism wrong; if β=10 wins → our mental model wrong → paper must add "pair-heavy regime" story
- **Table target:** Table 4
- **Priority:** MUST-RUN

### Block B5 — Transform transfer (generalization)

- **Claim tested:** C3 + anti-claim C4 piece: "CPR teaches generic grounding, not per-transform hacking"
- **Why:** If CFR is transform-specific, CPR is just memorizing the reward channel.
- **Setup:** Train CPR using ONLY T_rev pairs; eval CFR on {T_var, T_peak, T_amp, T_phase, T_changept} held out
- **Seeds:** 3
- **Success:** held-out-transform CFR ≥ 0.45; QA ≥ 0.60
- **Failure interpretation:** held-out CFR < 0.20 → CPR is per-transform hacking → paper must scope to "CPR works when train-time transforms cover test-time transforms"
- **Table target:** Table 5
- **Priority:** MUST-RUN

### Block B6 — Judge swap (reward-hacking check)

- **Claim tested:** C4 — rule out "CPR overfits to Qwen-2.5-7B judge"
- **Why:** Reviewers will ask.
- **Setup:** C-arm (CPR) final checkpoint, 3 seeds. Eval on v2 OOD subsample (n=200) with 3 judges:
  - Qwen-2.5-7B-Instruct (training judge, reference)
  - gpt-5.4-mini (closed, strong)
  - gpt-5.4 (closed, strongest)
- **Success:** max judge-swap gap ≤ 15pp on QA
- **Failure interpretation:** gap > 15pp → CPR is partially judge-specific; paper must report both and position as "limitation: judge calibration required per domain"
- **Table target:** Table 6
- **Priority:** MUST-RUN

### Block B7 — Length generalization

- **Claim tested:** Supporting — CPR works across TS lengths
- **Why:** Reviewer concern; benchmark claims length control.
- **Setup:** Train C-arm on length-256 only; eval at {128, 256, 512, 1024}
- **Seeds:** 1 per length (compute-bounded)
- **Success:** monotonic QA ↑ with length up to 512; no collapse at 1024
- **Failure interpretation:** Non-monotonic → encoder capacity issue, not caption problem; paper must add "length limitation" figure
- **Table target:** Appendix Figure A1
- **Priority:** NICE-TO-HAVE (drop if compute tight)

### Block B8 — In-dist vs OOD gap

- **Claim tested:** C3 supporting — CPR closes the OOD gap
- **Why:** If CPR only works in-dist, it's not closing the real-world gap that motivates caption work.
- **Setup:** All existing runs, split results by in-dist (LTSGen held-out, n = 300) vs OOD (n = 800)
- **No new training runs.** Evaluation-only.
- **Success:** CPR gap in-dist − OOD ≤ 8pp on QA (baseline measured at 26pp)
- **Failure interpretation:** CPR widens gap → overfits synthetic training distribution; H3 falsified on OOD
- **Table target:** Appendix Table A1
- **Priority:** MUST-RUN (free; reuses runs)

### Block B9 — Qualitative failure analysis

- **Claim tested:** None directly; scientific honesty
- **Why:** Referees like qualitative examples; gives us reframe-free discussion of what CPR doesn't fix.
- **Setup:** Hand-pick 20 CPR failures + 20 CPR successes; manual analysis
- **Priority:** NICE-TO-HAVE

---

## 4. Run Order and Milestones

### Stream 1 — Day-by-Day (17 days, 2026-04-19 → 2026-05-06)

User is solo operator. "Owner" column records the actor: CC = Claude Code session, User = human decision, Codex = autonomous coding on A100.

| Date | Day | Goal | Deliverable | Owner | Dependency | Stop-gate |
|---|---|---|---|---|---|---|
| 04-19 Sun | D0 | Contract locked. Infra smoke test. Spin up vLLM on 3090 with Qwen2.5-7B-Instruct; verify A100 GPU2 access; verify ChatTS-14B HF download to A100. | `infra-ok.txt` note | CC + User | — | — |
| 04-20 Mon | D1 | Implement `scripts/generate/transforms.py` with all 6 transforms + deterministic GT-flip rules + unit tests (20 canonical examples per transform, assert GT flips). | `transforms.py` + pytest 100% green | CC | D0 | if unit tests fail → debug on D1, no slip |
| 04-21 Tue | D2 | Extend `build_tsshapeqa.py` → `build_tsshapeqa_v2.py`. Smoke test: generate n=40 OOD with 3 transforms. Verify pipeline end-to-end. | smoke v2 jsonl | CC | D1 | pipeline hang → escalate |
| 04-22 Wed | D3 | Full v2 OOD generation: 800 samples × 6 transforms × pair MCQ via gpt-5.4 (~6600 API calls). Parallelize via async. | `v2_ood.jsonl` complete | CC | D2 | API quota → fall back to gpt-5.4-mini |
| 04-23 Thu | D4 | Full v2 in-dist generation (300 samples × 6 transforms). Sanity script: meta-only leakage + numbers gap + per-qa-type balance. | `v2_indist.jsonl` + `sanity.md` | CC | D3 | sanity FAIL (meta-only ≥ random + 0.15) → redesign MCQ prompts, cost 2 days |
| 04-24 Fri | D5 | Retrain OpenTSLM-Flamingo seed2 (5-8 hr on A100 GPU2). Meanwhile generate captions from seed1 on all v2 (inference only, ~2 hr). | seed2 checkpoint + seed1 captions | Codex (overnight) + CC | D4 | seed2 training diverges → use OpenTSLM-SoftPrompt as seed2 substitute |
| 04-25 Sat | D6 | Generate captions from seed2, SoftPrompt (if usable), ChatTS-14B on all v2. | 4-model captions jsonl | Codex + CC | D5 | ChatTS too big for 1×A100 → use 2×A100 or shard |
| 04-26 Sun | D7 | **S6a HARD GATE.** v2 build must be complete + sanity-passed + 4 models' captions generated. If NOT → drop NeurIPS D&B, pivot to preprint-first. If YES → proceed. | GATE decision note | User | D6 | HARD: miss → Stream 1 aborted |
| 04-27 Mon | D8 | Diagnosis eval (B1): Qwen2.5-7B judge answers MCQ pairs for 4 models × 6 transforms × 800 samples = 19,200 pair evals. Parallelize via vLLM batch inference. | `diagnosis_results.jsonl` | CC + Codex | D7 GATE = YES | judge inference > 24 hr → add 3090 GPUs |
| 04-28 Tue | D9 | Judge-transfer subsample: gpt-5.4-mini on 20% of pairs. Aggregate CFR table. | Table 1 data | CC | D8 | — |
| 04-29 Wed | D10 | Benchmark validity (B2): compute Spearman ρ across 6 evaluees. Shape-sensitive held-out QA generation from Time-MMD held-out. | Table 2 + Fig 1 data | CC | D8 | ρ < 0.3 → H2 falsified; Stream 1 degrades to diagnosis-only |
| 04-30 Thu | D11 | Paper draft: Intro + Related Work. NeurIPS D&B template setup. | `paper/intro.tex` + `paper/related.tex` | CC | D9, D10 | — |
| 05-01 Fri | D12 | Paper draft: §3 Diagnosis + §4 Benchmark. All figures imported. | `paper/diagnosis.tex` + `paper/benchmark.tex` | CC | D11 | — |
| 05-02 Sat | D13 | Paper draft: §2 ShapeShift-TS construction + §5 Discussion + abstract. | `paper/shapeshiftts.tex` + `abstract.tex` | CC | D12 | — |
| 05-03 Sun | D14 | Full edit pass. Figures polish (paper-figure skill). Table formatting. | compilable PDF v0 | CC | D13 | LaTeX build fails → debug D14-D15 |
| 05-04 Mon | D15 | Internal review (research-review skill via Codex MCP). Apply fixes. | review-round1.md + v1 PDF | CC + User | D14 | major content rewrite → slip into D16 |
| 05-05 Tue | D16 | Reserved: last-minute fix / one reworked figure. Final proofread. | final PDF | CC + User | D15 | — |
| 05-06 Wed | D17 | **SUBMIT NeurIPS 2026 D&B.** Also push priority arXiv v0 simultaneously. | submission receipt + arXiv ID | User | D16 | — |

### Stream 2 — Week-by-Week (40 days post-submission, 2026-05-07 → 2026-06-15)

| Week | Dates | Goal | Deliverable | GPU usage | Stop-gate |
|---|---|---|---|---|---|
| W1 | 05-07 ~ 05-13 | Implement CPR training loop on OpenTSLM repo. GRPO rollout + pair sampler + judge reward integration. | `opentslm/rl/cpr_trainer.py` + smoke test (1 seed, 200 steps) | A100 GPU2 + 3090 judge host | implementation overrun > 7d → cut ablation scope B7 and B9 first |
| W2 | 05-14 ~ 05-20 | Launch B3 main runs (A/B/C/D × 3 seeds = 12 runs). Parallelize 2-3 seeds across 2 A100s. | 12 checkpoints + WandB dashboards | 2× A100 full-time, ~10 d of compute parallel | S1 (reward-hacking), S2 (divergence), S3 (compute overrun) — see §5 |
| W3 | 05-21 ~ 05-27 | Complete B3. Eval on v2 OOD. Start B4 (α/β sweep, 12 runs) and B5 (transform transfer, 3 runs). | B3 Table 3 data; B4 runs in progress | 2× A100 | B3 decisive outcome not by 05-27 → extend to 05-31 at latest (eats buffer) |
| W4 | 05-28 ~ 06-03 | Complete B4 + B5. B6 judge-swap (eval only, no training). | Tables 4-6 data | 1× A100 + 3090 judges | — |
| W5 | 06-04 ~ 06-10 | B7 (length, NICE-TO-HAVE; drop if W3 slipped) + B8 (free, eval split) + B9 (qualitative). **S6b HARD GATE 06-08**: decisive A/B/C outcome required. | all tables ready | 1× A100 | S6b fires → route per contract §2.3 |
| W6 | 06-11 ~ 06-15 | Write §5 Method + §6 Ablations. Update arXiv v1 preprint. | PDF v1 on arXiv 2026-06-15 | 0 GPU | — |

---

## 5. Stop-Condition Monitoring

All thresholds from contract §4. Every condition has a concrete metric + source + whether it's auto-monitored or human-checked.

| ID | Condition | Metric / source | Auto? | Action |
|---|---|---|---|---|
| S1 | Reward-hacking | WandB: `train/CFR` > 0.9 within 200 steps AND `eval_ood/QA` ≤ baseline 0.36 | Manual daily W2-W4 | PAUSE run, investigate pair-term exploit; patch reward, restart |
| S2 | Training instability | WandB: `train/loss` > 3× initial for ≥ 50 steps on 2+ seeds | Auto alert via wandb-alert plugin or daily `training-check` skill | STOP all seeds, check data loader / lr schedule |
| S3 | Compute overrun | WandB: cumulative A100-hr/run > 96 AND `eval/CFR` < 0.15 | Manual daily | STOP run, reward shaping / lr adjustment |
| S4 | Benchmark leakage | v2 sanity script: any qa_type meta-only > random + 0.15 | Auto in sanity script on D4 | REBUILD MCQ prompts; cost: 2 days out of Stream 1 budget |
| S5 | Scoop | Weekly arXiv scan for {"time series" + "counterfactual" + "reward" + "captioning"} via `arxiv` skill Mondays | Manual weekly | Same-day escalation to User; decide scope-cut |
| S6a | TSShapeQA-v2 build miss | D7 (2026-04-26) gate: v2 jsonl + 4 models' captions on disk | Manual D7 EOD | Drop NeurIPS D&B, pivot to preprint-first (Stream 2 only) |
| S6b | H3 pilot not decisive by 2026-06-08 | B3 Table 3 aggregated with 3 seeds per arm | Manual 2026-06-08 EOD | Route per contract §2.3 — B-partial or C-failure |
| S7 | Judge drift | B6 Table 6: max (Qwen vs gpt-5.4-mini) gap on QA > 15pp | Manual in W4 | PAUSE, investigate; may require retraining with gpt-5.4-mini as judge |

**Monitoring cadence during Stream 2 training:**
- Daily: 09:00 CST — spot-check WandB dashboards for all active runs (15 min)
- Daily: 21:00 CST — run `training-check` skill, auto-flag S1/S2/S3
- Weekly Mondays: run arxiv scoop check (S5)

---

## 6. Compute & Data Budget

### GPU hours (A100-equiv)

| Block | Runs | A100-hr/run | Total |
|---|---|---|---|
| D5 seed2 retrain | 1 | 6 | 6 |
| B1 diagnosis eval (inference only) | 4 models, batched | — | ~5 |
| B3 main method | 12 (4 arms × 3 seeds) | 35 | 420 |
| B4 α/β sweep | 12 (4 β × 3 seeds) | 35 | 420 |
| B5 transform transfer | 3 | 35 | 105 |
| B7 length | 4 (cut to MUST single-seed) | 35 | 140 |
| B6 judge swap | 0 train, 3 judges × eval | — | 0 |
| B8 in-dist/OOD split | 0 (free reuse) | — | 0 |
| **Total** | — | — | **~1100 A100-hr** |

Assuming 2 A100 GPUs available on average (GPU2 full-time + GPU0 or 3 when idle):
- 1100 A100-hr / 2 GPUs = 550 wall-hours = **~23 days of 24/7 compute**

Fits in 40 days of Stream 2 with margin, but NO compute-slippage tolerance.

### 3090 hours

- Qwen2.5-7B judge via vLLM: 1 GPU dedicated full-time during W2-W5 training = 28 × 24 = 672 3090-hours. Plentiful.
- Eval inference for Stream 1 D8-D9: 2-3 days × 2 GPUs = ~144 3090-hr.

### Data / API budget

- Gpt-5.4 for v2 MCQ generation (D3-D4): ~6600 calls × ~500 in-tok + 200 out-tok. Small in proxy terms.
- Gpt-5.4-mini for judge-transfer B1 subsample (D9): ~19,200 × 0.2 = ~3,840 calls.
- Gpt-5.4-mini for B6 judge-swap eval: ~200 × 3 = 600 calls.
- Gpt-5.4 for B6 strongest-judge subsample: ~200 calls.
- Total API: ~11,200 calls across 40 days. Well within crisinsjtu proxy practical limits.

### Biggest bottleneck

**CPR 3-seeds × 4-arms = 12 runs over 10-14 days of parallel A100 compute (W2-W3).** Any training instability or reward-hacking (S1/S2) burns days. Mitigation: W1 smoke test MUST catch bugs before W2 launch.

---

## 7. Critical-Path GANTT (Stream 1)

```
04-19  infra
04-20  transforms.py        [CRIT]
04-21  v2 smoke
04-22  v2 OOD gen           [CRIT]
04-23  v2 indist + sanity   [CRIT]
04-24  seed2 retrain || seed1 captions
04-25  4-model caption gen  [CRIT]
04-26  ◆ S6a GATE           [HARD]
04-27  diagnosis eval       [CRIT]
04-28  judge-transfer + CFR table
04-29  benchmark validity ρ [CRIT — H2 gate]
04-30  paper intro+related
05-01  paper diagnosis+benchmark
05-02  paper ShapeShiftTS+discussion
05-03  edit pass v0 PDF
05-04  internal review
05-05  buffer
05-06  ◆ SUBMIT
```

**Bottlenecks explicit:**
- D1 transforms.py — blocks everything downstream
- D3-D4 v2 generation — blocks diagnosis
- D7 S6a GATE — single point of failure; if fails, all Stream 1 writing work is wasted
- D10 H2 ρ computation — second H2 gate; if fails, Stream 1 degrades to weak diagnosis-only paper

**Bottlenecks for Stream 2:**
- W1 CPR implementation — must-finish by W2 start or all downstream training delays
- W2-W3 main 12 runs — consumes ~280 GPU-hr; ONE divergent seed can cost 3 days

---

## 8. Fallback Routing

### If S6a fires (TSShapeQA-v2 not ready 2026-04-26 EOD)

→ **Abandon NeurIPS D&B 2026-05-06.** Merge timeline into Stream 2 only:
- Take 2 extra days to recover v2 build
- Proceed with Stream 2 W1 starting 2026-05-05 instead of 05-07 (tiny delay)
- Diagnosis + Benchmark + Method all land in 2026-06-15 preprint together
- This loses the NeurIPS D&B priority but preserves the ICLR 2027 submission

### If H2 (ρ target) fails on D10 2026-04-29

→ **Stream 1 downgrade** to diagnosis-only paper. Submit to NeurIPS D&B as narrower scope: "CFR metric + diagnosis", drop the "consistency rate is a stronger metric" framing. Paper becomes **3 pages shorter**; content from H2 §4 replaced by extended qualitative analysis from B9.

### If S6b fires (H3 not decisive 2026-06-08)

→ Per contract §2.3:
- **B-partial outcome** (C between baseline and 0.70): preprint 2026-06-15 with "open problem" framing; §5 Method titled "Towards Counterfactual-Pair Reward: A Partial Solution"; resubmit NeurIPS 2027 main
- **C-failure outcome** (C ≤ B on both metrics): DROP §5 Method from preprint; preprint becomes extended Stream 1 paper; CPR goes to appendix as negative result; EMNLP 2026 short track consideration

### If W2 12-run launch hits S1/S2/S3

→ PAUSE all 12 seeds. Drill down on 1 seed of C-arm to reproduce failure. Expected recovery cost: 3-5 days. Budget absorbs if within W3; otherwise B7 (length) and B9 (qualitative) cut.

### If arxiv scoop (S5) fires

User decision required. Options:
1. **Accelerate submission**: preprint NOW with whatever is ready (even B3 only)
2. **Differentiate**: sharpen positioning against the scoop paper; redo Section 2 Related Work and proceed as planned
3. **Pivot**: if scoop paper is exactly CPR-for-TS with our design, emergency idea-generation round to find adjacent angle (e.g., tool-augmented CPR, or contrastive CPR)

---

## 9. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| TSShapeQA-v2 sanity fails (meta-only leakage) | Medium | High — burns 2 days of Stream 1 | Use v1 pilot's balancing recipe as starting point; D4 has sanity script auto-run |
| OpenTSLM-SoftPrompt weights not publicly released | High | Medium — drops H1 to 3-model claim | Pre-check on D0; fall back to 3-of-3 threshold in H1 spec |
| ChatTS-14B too slow on 1×A100 | Medium | Medium | Shard across 2 A100s; budget extra time on D6 |
| GRPO instability on OpenTSLM | High | High — blocks all of Stream 2 W2 | W1 smoke test with 1 seed × 200 steps BEFORE W2 launch; if smoke fails, W1 extends and W3 ablations compress |
| Scoop (CapRL-for-TS published by competitor) | Medium-high | Variable | Daily arxiv scan + weekly scheduled check via `arxiv` skill |
| API quota (gpt-5.4) during v2 gen or judge eval | Medium | Low | Batch async + retry with backoff; fall back to gpt-5.4-mini if needed |
| User unavailability / sick days | Always possible | Depends on timing | Stream 1 has 1 buffer day (D16); Stream 2 has no real buffer — sickness in W1-W2 is critical |

---

## 10. First 3 Runs to Launch (next 48h)

1. **R001 — Infra smoke test.** Start vLLM + Qwen2.5-7B-Instruct on 3090, verify API endpoint, verify ChatTS-14B downloadable to A100, verify OpenTSLM vars=1 checkpoint loads. ETA: 2 hours. Owner: CC session after this plan locks.
2. **R002 — `transforms.py` + unit tests (D1).** 6 transforms × 20 canonical examples; all assert GT flips in the correct direction. ETA: 1 work-day 2026-04-20. Owner: CC.
3. **R003 — v2 build smoke (D2).** 40 OOD samples × 3 transforms, full pipeline. Verify output jsonl + sanity + no 502 API errors. ETA: half work-day 2026-04-21. Owner: CC.

**These 3 unblock everything. R002 is the hard dependency for all of Stream 1.**

---

## 11. Final Checklist

- [x] Every experiment block is tied to a contract hypothesis
- [x] Main-paper tables are covered (Tables 1-6) with 1 figure (Fig 1 scatter)
- [x] Novelty isolated (B4 α/β sweep shows pair term is load-bearing)
- [x] Simplicity defended (B3 arm D Pair-only vs C CPR shows QA reward also needed)
- [x] Frontier component (GRPO RL) justified (B3 A vs B vs C shows SFT-only and CapRL-pure both inadequate)
- [x] MUST-RUN (B1, B2, B3, B4, B5, B6, B8) separated from NICE-TO-HAVE (B7, B9)
- [x] Run order is topologically valid — every run has explicit dependencies
- [x] All stop conditions have concrete monitoring + thresholds
- [x] Fallback routes defined for every foreseeable failure

---

**Plan ACTIVE. Next concrete action: R001 infra smoke test (~2 hours today).**
