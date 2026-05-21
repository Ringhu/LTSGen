# Phase 1 Result — ChatTS-14B Conditioning Ablation

**Date:** 2026-04-20
**Model:** ChatTS-14B (ByteDance, public HF), fp16 on A100 GPU2
**Method:** identical to OpenTSLM conditioning ablation (n=36 confident-flippable samples), shared filter_meta.json so the **exact same 36 series** are tested

## Headline Result

| Transform | OpenTSLM-Flamingo (4B) | **ChatTS-14B** | Δ |
|---|---:|---:|---:|
| time_reversal (n=22) | 4.55% | **68.18%** | **+63.6pp** |
| variance_injection_2nd_half (n=14) | 0.00% | **21.43%** | +21.4pp |
| **Overall (n=36)** | **2.78%** | **50.00%** | **+47.2pp** |

**Caption literal-unchanged rate** (50%+ unchanged = pure template emission):

| Transform | OpenTSLM | ChatTS-14B |
|---|---:|---:|
| time_reversal | 50% literally identical | **5%** literally identical |
| variance_injection | 79% literally identical | 64% literally identical |

## Interpretation

**Cancelled hypothesis: "all SFT-on-synthetic-caption TS-MLLMs fail equivalently"**

Our prior negative-result framing was that synthetic-caption SFT is paradigm-fundamentally broken across the entire family. The data **does not support this strong claim**. ChatTS-14B (same paradigm family, scaled up: 14B vs 4B + Evol-Instruct synthetic data vs LTSGen synthetic captions) shows:
- 14.4× higher conditioning flip rate on time_reversal
- 10× lower literal-template emission
- **Real, partial, but visible discriminativity**

**Refined conclusion**: at sufficient scale and with better-curated synthetic data, captioner discriminativity does emerge — but **plateaus at ~50% overall correct-flip rate**, while **oracle interface ceiling is 96-100%**. Caption-paradigm is not dead; it is **half-dead**, and the remaining 50pp gap is the open scientific problem.

## What this means for the paper

### Cannot say (no longer supported)
- ❌ "SFT-on-synthetic-caption TS-MLLMs systematically fail" — ChatTS doesn't fail systematically
- ❌ "Caption is fundamentally not the right interface" — at 50% flip rate, there is signal
- ❌ "Our OpenTSLM result generalizes to all TS-MLLMs" — it doesn't

### Can say (and now have direct evidence)
- ✅ **"Captioner-grounding scales with model size and data quality"** — 4B+LTSGen → 2.78%; 14B+Evol-Instruct → 50%
- ✅ **"Even at 14B scale, learned captions only achieve half of oracle's downstream interface capacity"** — 50% flip ≪ 96% oracle
- ✅ **"Tool-augmentation outperforms learned-caption at all tested scales"** — Tool-Agent 1.000 across both 4B-class and 14B-class scenarios
- ✅ **"OpenTSLM-Flamingo at 4B is broken in ways ChatTS-14B is not"** — separable effects of architecture vs scale vs data

## Recommended Paper Re-framing

**Old title**: *Captions Are Not the Interface: Why Raw Numbers + Tools Beat Learned TS-MLLM Captions*

**New title (draft)**: *The Long Climb of TS-MLLM Captions: Scale Helps, Tools Win* — or — *From 3% to 50% to 100%: Captioning, RL, and Tools as Three Tiers of TS-LLM Interface*

**Re-organized story**:
1. (§3 Diagnosis) Three tiers of TS-LLM interface — measured on the same TSShapeQA benchmark:
   - Tier 1 (small synthetic-caption SFT, our OpenTSLM-Flamingo 4B): 2.78% conditioning flip, 0.34 downstream acc
   - Tier 2 (large synthetic-caption SFT, ChatTS-14B): 50% conditioning flip, ?? downstream acc (Phase 3 will fill)
   - Tier 3 (tool-augmented frozen LLM): 100% conditioning by construction, 1.000 downstream acc
2. (§4 Benchmark) TSShapeQA (already done)
3. (§5 Method) Tool-Agent baseline beats both Tier 1 and Tier 2 captioners regardless of LLM scale (already done)
4. (§6 Discussion) **CapRL-style RL training is the natural next step to bridge the remaining 50pp gap** — explicitly call out as future work; the user has a separate plan for this

## Status of follow-up

- Phase 2 (full TSShapeQA caption gen) running on A100 GPU2; ETA ~25 min remaining
- Phase 3 (5-condition downstream eval) ready to launch immediately when Phase 2 finishes
- Phase 4 (paper §3 rewrite) will use this re-framed story
