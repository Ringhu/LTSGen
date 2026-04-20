# Research Contract — ShapeShift

**Project:** LTSGEN — Counterfactual-grounded TS-LLM captioning for shape QA
**Date locked:** 2026-04-19
**Status:** ACTIVE (locked on git commit — see §9)
**Baseline paper:** OpenTSLM (arXiv 2510.02410)

---

## 1. Hypothesis (falsifiable)

**H1 (Diagnosis)** — The input-agnostic captioning failure observed on our
retrained OpenTSLM-Flamingo (CFR = 2.78%, n=36) is **not** an
implementation artifact; the same pathology will replicate across other
synthetic-caption-SFT TS-LLMs (ChatTS-14B, OpenTSLM-SoftPrompt, a second
OpenTSLM-Flamingo seed) with CFR ≤ 10% on ≥ 3 of 4 tested systems under
at least 3 semantics-altering transforms.

**H2 (Benchmark)** — A counterfactual-paired "consistency rate" metric
on ShapeShift-TS is a **strictly stronger** test of TS-LLM input
conditioning than absolute QA accuracy: consistency rate will correlate
with held-out shape-sensitive QA on real OOD data (Time-MMD,
exchange_rate) with Spearman ρ ≥ 0.5, while absolute single-question
accuracy on the same models will correlate ρ < 0.3.

**H3 (Method)** — Adding a paired-counterfactual consistency reward on
top of a CapRL-style QA-accuracy reward (together = **CPR**) will raise
CFR from ~3% to ≥ 60% and raise downstream shape-QA accuracy from ~36%
to ≥ 70%, while a **CapRL-pure baseline with no pair term** will plateau
at CFR ≤ 30% and QA ≤ 55%.

All three hypotheses are conjunctive — the paper's core claim is that
all three hold together. If H1 fails the paper has no motivation; if H2
fails the benchmark is not publishable; if H3 fails the method section
collapses (but diagnosis + benchmark may still publish at D&B track).

---

## 2. Success / Failure Signals (per claim)

### 2.1 Diagnosis (H1)

| Metric | Dataset | Success | Failure | Ambiguous |
|---|---|---|---|---|
| CFR (correct-flip rate) | TSShapeQA-v2 OOD (n = 800) | ≤ 10% on ≥ 3 of {OpenTSLM-Flamingo-seed1, OpenTSLM-Flamingo-seed2, OpenTSLM-SoftPrompt, ChatTS-14B} under ≥ 4 of {T_rev, T_var, T_peak, T_amp, T_phase, T_changept} | Any model achieves CFR ≥ 30% on > 50% of transforms | One model at 15-30% OR fewer than 4 transforms with CFR ≤ 10% |

**Test-set construction**: TSShapeQA-v2 must use sources strictly disjoint
from LTSGen synthetic training distribution (Time-MMD, exchange_rate,
illness only; no electricity/weather/traffic that leak into LTSGen).

### 2.2 Benchmark (H2)

| Metric | Dataset | Success | Failure | Ambiguous |
|---|---|---|---|---|
| Spearman ρ between consistency rate and held-out shape-QA accuracy on real-OOD data | TSShapeQA-v2 OOD split × 6 models (our 4 + GPT-4o + oracle) | ρ ≥ 0.5 AND ρ_consistency > ρ_single_accuracy by ≥ 0.2 | ρ_consistency < 0.3 OR ρ_consistency ≤ ρ_single_accuracy | 0.3 ≤ ρ < 0.5 AND ρ_consistency > ρ_single_accuracy |
| Meta-only leakage on v2 | TSShapeQA-v2 | Meta-only ≤ blended-random + 0.12 per qa_type | Any qa_type has meta-only > random + 0.15 | within 0.12-0.15 of random |
| Sanity gap | TSShapeQA-v2 | numbers − meta_only ≥ +10pp overall | numbers − meta_only < +5pp | 5-10pp |

### 2.3 Method — CPR (H3) — **THE CENTRAL BET**

Evaluated on TSShapeQA-v2 OOD held-out (n = 800) after 2-week A100 GPU2 pilot.

| Arm | Primary metric = Overall shape-QA acc | Secondary = CFR | Success | Failure |
|---|---|---|---|---|
| A: Baseline SFT-only (frozen OpenTSLM-vars=1) | ~0.36 (known) | ~0.03 (known) | n/a | n/a |
| B: CapRL-pure (QA-accuracy reward only) | **≤ 0.55** | **≤ 0.30** | differentiation from C ≥ 15pp on QA OR ≥ 30pp on CFR | B ≥ C on either metric |
| C: CPR (ours, α·QA_acc + β·pair_consistency) | **≥ 0.70** | **≥ 0.60** | both QA ≥ 0.70 AND CFR ≥ 0.60 | QA < 0.55 OR CFR < 0.30 |
| D: Pair-only (no QA_acc reward) | expected ~0.30 | expected ~0.40 | sanity: D < C on QA | D ≥ C on QA ⇒ pair-term is hacking, not perceiving |
| E (upper-bound): Oracle caption | 0.96 (measured) | 0.90 (est) | n/a | n/a |

**Three possible method outcomes (locked before runs):**

| Outcome | Definition | Routing |
|---|---|---|
| **A-success** | C achieves QA ≥ 0.70 AND CFR ≥ 0.60, AND C − B ≥ 15pp on QA OR ≥ 30pp on CFR | Full 3-contribution paper → ICLR 2027 main |
| **B-partial** | C achieves QA ∈ [0.45, 0.70) OR CFR ∈ [0.20, 0.60), AND C − B ≥ 5pp on either | Diagnosis + Benchmark main contribution, Method section reframed as "progress but open problem" → NeurIPS 2026 D&B + preprint by 2026-06-15 |
| **C-failure** | C ≤ B on both metrics, OR C achieves CFR < 0.15 | Drop method, pure Diagnosis + Benchmark paper → NeurIPS 2026 D&B; CPR becomes "tried, didn't solve it" negative result in appendix |

**Hard rule**: The routing table is locked. Outcome B does NOT escalate to
A by adding more transforms, more seeds, more hyperparameter sweeps
*after* seeing results. Scope expansion post-result is forbidden.

---

## 3. Per-Ablation Expectations

Every ablation predicted **before** runs. Surprise = learning signal,
not a license for reframing.

| # | Ablation | Predicted QA / CFR | Mental model | Surprise interpretation |
|---|---|---|---|---|
| 1 | Baseline frozen (SFT-only) | 0.36 / 0.03 | Known kill-test result | Deviation > ±0.05 means seed instability — rerun before trusting |
| 2 | CapRL-pure (QA-acc reward, no pair) | 0.52 / 0.22 | QA reward encourages some grounding but captioner can still template-match on popular labels | If CapRL-pure ≥ C → CPR pair term adds nothing, H3 falsified |
| 3 | CPR full (α=1, β=1) | 0.73 / 0.65 | Pair term explicitly punishes input-agnostic captions | If CPR < CapRL-pure → pair term is toxic, β sweep required |
| 4 | Pair-only (α=0, β=1) | 0.28 / 0.42 | Captioner can achieve high pair-contrast by writing garbage that happens to flip, but is not QA-useful | If Pair-only ≥ CPR → implies QA reward is redundant (suspicious, check reward-hacking) |
| 5 | α/β sweep (α∈{1}, β∈{0.3, 1, 3, 10}) | monotonic CFR ↑ with β, QA ∩-shaped peaking at β≈1 | Pair reward over-weighted → captioner optimizes contrast at cost of usefulness | If β=3 or β=10 wins on both → our mental model wrong, pair term is underweighted not overweighted |
| 6 | Transform ablation — CPR trained only on T_rev, test on T_var, T_peak | QA ≥ 0.60, CFR ≥ 0.45 on held-out transforms | Transforms are correlated via "input-conditioning" invariant; training on one should transfer | If no transfer → CFR is per-transform-hacking, not real grounding; paper must add "transform-generalization gap" section |
| 7 | Length ablation (128 / 256 / 512 / 1024) | monotonic QA ↑ with length up to 512, plateau or dip at 1024 | Longer TS has more shape information but also more context budget for template hallucination | Non-monotonic → encoder capacity issue in Chronos-2, not caption problem |
| 8 | Downstream-LLM swap (gpt-5.4 ↔ gpt-5.4-mini ↔ Qwen-2.5-7B-local) | CFR ± 5pp, QA ± 8pp | Reward model generalizes across frozen readers | Swap-gap > 15pp → CPR is overfit to the judge |
| 9 | In-dist (LTSGen held-out) vs OOD (Time-MMD) gap | in-dist QA − OOD QA ≤ 8pp with CPR, vs 26pp with baseline (measured) | CPR closes the OOD gap because it teaches grounded description | Gap widens with CPR → CPR overfits to synthetic distribution, H3 falsified on OOD |

---

## 4. Stop Conditions (abandon mid-experiment)

Triggered = stop, escalate to user, do NOT continue to next ablation.

- **S1 (Reward-hacking)**: CPR training curve shows CFR → 90%+ on train within 50 steps but OOD QA ≤ baseline. Means captioner is gaming the pair term.
- **S2 (Training instability)**: CPR loss diverges > 3× initial within 200 GRPO steps across ≥ 2 of 3 seeds.
- **S3 (Compute overrun)**: Full CPR run > 96 A100-hours without reaching any held-out CFR > 0.15. Means signal is too sparse; reward shaping needed before scaling.
- **S4 (Judge-shortcut)**: gpt-5.4-mini answers correctly from empty-caption (meta-only) at ≥ 0.55 on new transforms added to v2 → benchmark leakage, stop and redesign QA pairs.
- **S5 (Paper scoop)**: Any arXiv preprint appears (by 2026-06-01) that independently couples (counterfactual-pair reward OR CapRL) × (time-series captioner). Escalate to user same day for scope-cut decision.
- **S6a (Stream 1 deadline)**: If TSShapeQA-v2 build (800 OOD + 300 in-dist) or diagnosis runs across 4 models × 6 transforms are not complete by **2026-05-02** (end-of-day), drop NeurIPS D&B submission, fall back to preprint-first track.
- **S6b (Stream 2 deadline)**: If H3 pilot has not produced a decisive A/B/C outcome by **2026-06-08**, scope cuts to Outcome-B or Outcome-C routing regardless of projections.
- **S7 (Judge drift)**: If Qwen2.5-7B-Instruct vs gpt-5.4-mini evaluation on the same held-out test set show > 15pp gap on any method arm's QA score, pause, investigate whether reward model mismatch invalidates training signal.

---

## 5. Forbidden post-hoc rationalizations

These narratives are explicitly banned. If observed, revisit contract,
do NOT re-narrate.

- ❌ "CPR didn't beat CapRL-pure but reveals an interesting reward-hacking phenomenon we should publish." → If C ≤ B, route to **C-failure**. Not a new story.
- ❌ "The OOD gap is larger than expected but that just proves OOD is harder." → Contract predicts ≤ 8pp with CPR. > 8pp is H3 falsification.
- ❌ "Meta-only on v2 beats random by 0.16 but still allows us to measure differential effect." → H2 failure, benchmark needs redesign.
- ❌ "Our method gains 3pp on QA, which in TS is a big deal." → Below ambiguous-zone floor of +5pp (B vs C delta). Not a success.
- ❌ "Pair-term-only (arm D) beats CPR, which means the pair term alone is the key insight." → Per contract, D ≥ C means reward-hacking suspected; trigger S1 investigation, not narrative reframing.
- ❌ "Transforms don't generalize but per-transform training is still a contribution." → Not the paper we committed to; escalate as scope change.

---

## 6. Publication Routing (locked)

**Two parallel streams** — dictated by the 2026-05-06 NeurIPS D&B hard
deadline (17 days from contract lock) being too tight for a full 3-seed
× 4-arm method pilot.

### Stream 1 — Diagnosis + Benchmark only → NeurIPS 2026 D&B
- **Deadline: 2026-05-06** (17 days)
- **Scope: Contributions 1 (Diagnosis §2.1) + 2 (Benchmark §2.2) only**
- Method (CPR) NOT included; even an A-success method pilot cannot
  finish cleanly in 17 days
- Feasibility gate: TSShapeQA-v2 build must finish by 2026-04-26 (7d);
  diagnosis runs across 4 models × 6 transforms by 2026-05-01 (12d);
  writing + polish 2026-05-02 to 05-06 (4d)
- Failure fallback for Stream 1: miss 2026-05-06 → paper goes to
  preprint 2026-06-15 + resubmit at next D&B-style venue

### Stream 2 — CPR method paper → preprint 2026-06-15 + ICLR 2027
- **Priority arXiv preprint: 2026-06-15** (57 days)
- **Main submission: ICLR 2027 main, 2026-10**
- **Scope: 3-contribution composite (D + B + CPR)**
- The D&B paper (Stream 1) becomes Section 3-4 of this longer paper;
  cite Stream 1 as parallel work if accepted, or absorb outright if
  rejected

### Routing by method outcome (same as §2.3)

| Outcome of CPR pilot | Stream 2 action |
|---|---|
| A-success | Full 3-contribution ICLR 2027 paper, preprint on schedule |
| B-partial | Preprint includes "partial-fix + open problem" framing; ICLR 2027 submission contingent on whether B-partial holds up under scale-up to full ablation suite |
| C-failure | Stream 2 downgrades to extended Stream 1 (CPR in appendix as negative result), submit to EMNLP 2026 short / ICLR 2027 D&B-style |

Priority preprint at arXiv by **2026-06-15** regardless of outcome —
establishes timestamp priority against scoop risk (S5).

---

## 7. Dataset and sample-size commitments

- **TSShapeQA-v2 OOD split**: n = 800. Sources = Time-MMD + exchange_rate + illness only. Per qa_type balanced.
- **TSShapeQA-v2 in-dist split**: n = 300. For sanity, not primary evaluation.
- **Counterfactual pairs per test instance**: all 6 transforms {T_rev, T_var, T_peak, T_amp, T_phase, T_changept} per sample where GT-flip is well-defined ⇒ up to 800 × 6 = 4800 pair-evaluations on OOD alone. Every transform must have a **deterministic GT-flipping rule documented in `scripts/generate/transforms.py`** before data build.
- **Seeds**: 3 per method arm (B, C, D). Report mean ± std.
- **Training batch size / steps**: CPR GRPO, 4 × A100 GPU2-equiv, ≤ 2 weeks wall-clock, ≤ 96 A100-hours per seed.
- **Frozen judge — hybrid policy**:
  - **Training (inner RL loop)**: local `Qwen2.5-7B-Instruct` hosted on 3090 via vLLM. Zero API cost, reproducible, same judge across all arms.
  - **Evaluation (final reported numbers)**: primary = Qwen2.5-7B-Instruct (same as training, measures method improvement); secondary = `gpt-5.4-mini` via crisinsjtu proxy on 10-20% test subsample, to prove **judge-transfer robustness** (CPR gains not a reward-hacking artifact of the specific judge).
  - **Ablation #8 (judge swap)**: report {Qwen2.5-7B, gpt-5.4-mini, gpt-5.4} for the central C-arm (CPR) only — 3 values, small subsample each.

---

## 8. Claim-to-Signal Map (fill during writing)

| Paper claim | Contract signal | Evidence |
|---|---|---|
| "Synthetic-caption SFT collapses to templates" | H1 Diagnosis CFR table §2.1 | Table 1 (models × transforms) |
| "Consistency rate is a stronger diagnostic than accuracy" | H2 Benchmark ρ gap §2.2 | Table 2 (correlation comparison) |
| "CPR fixes counterfactual grounding" | H3 CPR vs CapRL-pure §2.3 | Table 3 (main results), Fig 2 (training curves) |
| "Pair term is load-bearing" | Ablation #4 (Pair-only), #5 (β sweep) | Table 4 |
| "Transform-transfer generalizes" | Ablation #6 | Table 5 |

---

## 9. Immutability clause

Status flips to ACTIVE on git commit of this file. From that point:
- This file is not edited. Revisions = new `research-contract-v2.md` with changelog.
- Any change that weakens success criteria or redefines failure after seeing results is forbidden.
- The user (Cris) and Claude Code both bound by this contract.

Signed timestamp: git commit hash (to be inserted on commit).

---

## 10. Resolution of [需你确认] items (as of 2026-04-19)

| Item | User decision |
|---|---|
| TSShapeQA-v2 size | 800 OOD + 300 in-dist |
| Transforms in eval suite | All 6: T_rev, T_var, T_peak, T_amp, T_phase, T_changept |
| Frozen judge | **Hybrid**: Qwen2.5-7B-Instruct local (training + primary eval); gpt-5.4-mini closed (subsample eval for judge-transfer verification); judge swap ablation for CPR arm only |
| NeurIPS D&B 2026 deadline | 2026-05-06 (17 days from lock) → triggers Stream 1 / Stream 2 split per §6 |
