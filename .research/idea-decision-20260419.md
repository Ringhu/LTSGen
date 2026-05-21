# Idea Decision — 2026-04-19

## Ranking Table

| # | Title | Nov | Feas | BaseCompat | ImplCplx | Improv | Scoop | Verdict | One-line killer |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|---|---|
| 1 | TimeCapRL (CapRL → TS) | 2 | 3 | 4 | 4 | 3 | 4 | REVISE | "Mechanical CapRL domain transfer" |
| 2 | Illusion of Grounding (diagnosis) | 3 | 4 | 5 | 2 | 1 | 4 | REVISE | "Narrow attack on one baseline; needs multi-model + comparator" |
| 3 | ShapeShift-TS (counterfactual benchmark) | 3 | 5 | 5 | 2 | 2 | 4 | REVISE | "Toy synthetic sanity check unless taxonomy + predictive validity proven" |
| 4 | PRM for TS shape CoT | 3 | 3 | 4 | 4 | 2 | 4 | REVISE | "May solve wrong problem; grounding failure, not sparsity" |
| 5 | VIB anti-prior regularizer | 2 | 3 | 4 | 3 | 2 | 4 | REVISE | "KL-to-prior ≠ correct TS dependence; objective mismatch" |
| 6 | Label-shuffled oracle diagnostic | 2 | 5 | 5 | 2 | 2 | 4 | REVISE | "Narrow ablation note — needs multi-family faithfulness protocol" |
| 7 | Contrastive Decoding on frozen CKPT | 2 | 4 | 5 | 2 | 2 | 4 | **KILL** | "2.78% flip-rate contradicts 'grounding is present but suppressed' premise" |
| 8 | Adversarial LLM Debate | 2 | 4 | 5 | 2 | 2 | 5 | **KILL** | "Inference-time patch for a training-time grounding failure" |
| 9 | RAG-TS retrieval anchors | 2 | 4 | 4 | 2 | 2 | 4 | REVISE | "Template copying → nearest-neighbor template copying; datastore becomes lookup table" |
| 10 | Neurosymbolic Concept Bottleneck | 3 | 4 | 4 | 3 | 2 | 4 | REVISE | "'Formal guarantee' claim mathematically unjustified; ontology leakage risk" |

## Cross-cutting observations

Every single review converges on two points:

1. **The load-bearing result is not task accuracy — it is the counterfactual correct-flip rate**, and secondarily the oracle-gap closure and wrong-caption separation. This is what the user's own kill-test discovered and it is what the field will demand proof of.
2. **CapRL (ICLR 2026) is the most dangerous prior-art for every idea**, because any story that says "force captions to be useful to a downstream LLM" gets mapped onto CapRL's paradigm. To differentiate, we need a contribution that is uniquely TS and uniquely counterfactual-aware.

A third unstated convergence: **single-thread papers (only diagnosis, only benchmark, only method) are all REVISEs at top venues** because each alone is vulnerable to one reviewer path. Any composite of diagnosis + benchmark + method is more defensible precisely because rejecting it requires rejecting multiple contributions.

## Decision: Primary candidate

**Chosen direction: Composite paper titled**

> **"ShapeShift: Diagnosing, Benchmarking, and Fixing Counterfactual Collapse in Time-Series Language Models"**

### Contribution synthesis (integrating ideas 2 + 3 + counterfactual-pair extension of 1)

1. **Diagnosis (from Idea 2, hardened).** Formal definition of "caption collapse": for a captioner C and a semantic-altering transform T on TS x, the correct-flip rate CFR(C, T) is the fraction of paired (x, T(x)) on which C's output correctly changes ground-truth-wise. Empirically measure CFR across **OpenTSLM-SoftPrompt, OpenTSLM-Flamingo (our retrained vars=1 checkpoint), ChatTS-14B, and a TS-CLIP-based probing control** on a taxonomy of 6-8 transforms (time reversal, variance injection, amplitude scale, phase shift, local permutation, spike insert / remove, trend inversion, monotonic → non-monotonic). Show **< 10% CFR is the rule, not the exception**, across all synthetic-SFT TS-LLMs.

2. **Benchmark (from Idea 3, hardened).** Release **ShapeShift-TS**: length-controlled (128 / 256 / 512 / 1024), paired-counterfactual TS-QA dataset with 6-8 transforms × 4-5 primitives (trend / extrema / volatility / periodicity / changepoint). Key metric is **consistency rate** (both-original-correct AND counterfactual-correct), not absolute accuracy. Predictive validity check: consistency rate must correlate with held-out shape-sensitive QA on real OOD data (Time-MMD, exchange_rate).

3. **Method (novel piece, the core contribution).** Introduce **Counterfactual-Pair Reward (CPR)**: on top of CapRL-style accuracy reward, add a pairwise consistency reward that the captioner must produce outputs whose downstream MCQ answer distributions flip correctly between (x, T(x)) under known-transform pairs. Loss = α · QA_accuracy_reward(x) + β · counterfactual_consistency_reward(x, T(x)). Show that **vanilla CapRL transplant does NOT raise CFR meaningfully (+~15pp absolute), while CapRL + CPR raises CFR from ~3% to ~55-70% absolute** in a 2-week pilot on 3090.

### Why this is the right choice

- **Differentiates from CapRL**: CapRL uses only positive QA-accuracy reward. CPR's counterfactual-pair consistency reward is a specifically TS-motivated extension (vision doesn't naturally admit label-flipping transforms the way TS does with time reversal / variance injection). We explicitly predict and show that vanilla CapRL transplant fails.
- **Differentiates from TimeMaster**: TimeMaster rewards classification + LLM-judged "insight quality". Neither is counterfactual-pair consistency.
- **Differentiates from OpenTSLM / ChatTS**: they have no counterfactual probe, no benchmark, and no RL.
- **Differentiates from TRQA**: TRQA tests task completion; ShapeShift-TS tests causal input conditioning, a strictly different axis.
- **Uses the user's existing artifacts**: TSShapeQA v1, kill-test probe code, retrained OpenTSLM-vars=1 checkpoint, LTSGen pipeline, gpt-5.4 proxy. Avoids large-scale new pretraining.
- **Three contributions survive one reviewer kill**: if a reviewer attacks the diagnosis as narrow, the benchmark and method still stand; attacks on benchmark breadth leave the method intact; attacks on method novelty still leave a benchmark-and-diagnostic paper.

### Explicit revisions applied from Codex feedback

- Idea 2 reviewer demanded multi-model + multiple transforms + metric validation → absorbed into Diagnosis section.
- Idea 3 reviewer demanded principled taxonomy + semantically-valid counterfactuals + predictive-validity correlation → absorbed into Benchmark section.
- Idea 1 reviewer demanded "not just TS port of CapRL" → addressed by making CPR (not QA-accuracy RL) the main novelty.
- Idea 5/10 reviewers demanded that the loss actually force correct TS dependence, not just difference from prior → CPR directly enforces semantic direction under known transforms, not just divergence.

### Compute budget (rough)

- Diagnosis + Benchmark construction: 1 week, local + 3090 small, essentially CPU-bound.
- Method pilot (CapRL vs CapRL+CPR, vars=1 checkpoint init, n=36 counterfactual test set, batch-of-8 GRPO): 2 weeks on 1 × A100 (CUDA_VISIBLE_DEVICES=2).
- Full training (5 transforms × 3 seeds × 3 baseline methods): 4 weeks on 2 × A100.
- Writing + polish: 3 weeks overlapping with runs.

### Venue target

- **Primary**: ICLR 2027 main (deadline ~2026-10, 5-6 months away — comfortable).
- **Secondary**: NeurIPS 2026 main (deadline ~2026-05, ~1 month — too tight for full method; possible to submit Diagnosis + Benchmark as Datasets & Benchmarks track standalone if method pilot is slow).
- **Fallback**: EMNLP 2026 short (~2026-06) for Diagnosis-only negative-result paper if method pilot shows <30% CFR improvement by week 3.

## Decision: Backup candidate

If Stage-4 prior-art recheck surfaces someone already doing CPR-style counterfactual-pair training on TS-LLMs (plausible — the idea is not absurdly original), the fallback is:

**"ShapeShift-TS: A Counterfactual-Faithfulness Benchmark for Time-Series Language Models"** — pure benchmark paper from Idea 3, targeting **NeurIPS 2026 Datasets & Benchmarks Track** (~2026-06 deadline).

- Lower novelty ceiling but much higher acceptance probability
- Uses only infrastructure the user already has (LTSGen + TSShapeQA harness + kill-test probe)
- The paper's value is the benchmark + a leaderboard showing that OpenTSLM / ChatTS / TimeMaster all fail it
- Ablation of a CapRL-style baseline (not the user's main novelty) included as an oracle-caption-style probe

## Decision: What is killed

- Idea 7 (Contrastive Decoding) and Idea 8 (Debate) are explicitly killed; the pilot data (2.78% CFR) says the grounding is not latently present to rescue at inference time.
- Ideas 4 (PRM), 5 (VIB), 9 (RAG), 10 (Concept Bottleneck) are kept **available as ablations or alternate-method arms in Section 3**, but not as standalone papers. If CPR alone is insufficient in the pilot, the next method to try is a concept-bottleneck variant of CPR (Idea 10 absorbed).

## Next step (mandated by idea-generation skill)

Stage 4: **Gemini aggressive prior-art recheck specifically on the CPR (counterfactual-pair reward) claim and the ShapeShift-TS composite paper**. After that: handoff to `research-contract`.
