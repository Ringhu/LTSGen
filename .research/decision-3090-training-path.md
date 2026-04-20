# Decision: 3090 / A100-constrained CPR Training Path

**Date:** 2026-04-20
**Trigger:** R001 amber flag A1 — A100 GPU2 currently 60GB occupied by openpi-agilex (user wjc)
**Status:** FEASIBILITY CONFIRMED — implementation deferred to W1 (2026-05-07)

## Measured facts (R001 smoke on 3090 GPU1/2)

| Item | Value |
|---|---|
| OpenTSLM-Flamingo weights (Qwen3-4B + Chronos-2 + Flamingo cross-attn) | **8.28 GB** bf16 on 1× 3090 |
| Total params | 6.19 B |
| Naive trainable params (full Flamingo cross-attn + LoRA r=16 on q/v_proj) | **2.05 B** → does NOT fit 24GB with Adam |
| LoRA on Qwen3-4B only (q_proj/v_proj, r=16) | 5.9 M |
| Vars=1 ckpt load | 0 missing / 0 unexpected, val_loss 0.2026 ✓ |

The original mental model (Flamingo cross-attn ≈ 200M) was wrong; open_flamingo wraps EACH Qwen3 decoder layer with a new gated cross-attn block, so trainable cross-attn ≈ size of the LLM itself.

## Usable GPU inventory as of 2026-04-20

| Machine | Free VRAM | Notes |
|---|---|---|
| 3090 × 8 | 24 GB each, essentially all idle | Cluster totally available |
| A100 GPU0 | ~0 GB | Fully occupied by ocrvl user |
| A100 GPU1/2/3 | ~20 GB each | Each has 60 GB parked by openpi-agilex, 0% util |

**No GPU on either machine currently has > 24 GB free for training.**

## Three compatible training strategies

### Strategy X1 — LoRA everywhere (RECOMMENDED for W1)

- Freeze Chronos-2 (already frozen)
- Freeze Qwen3-4B base weights
- Freeze Flamingo cross-attn base weights
- Add LoRA r=16 to {q_proj, k_proj, v_proj, o_proj} of every Qwen3 decoder layer AND every Flamingo gated_cross_attn layer
- Expected trainable ≈ 20-40 M params (LoRA-only)
- Expected Adam state ≈ 80-160 MB
- Expected peak VRAM (fwd + bwd + Adam + activations w/ grad ckpt) ≈ **14-16 GB**
- Fits on 1× 3090 or 1× A100 (with 20GB free) comfortably
- Credibility: widely used in RLHF literature; reviewers will accept

### Strategy X2 — 8-bit Adam + full Flamingo trainable

- Freeze Chronos-2 + Qwen3-4B base
- Full training on Flamingo cross-attn (2.05B trainable)
- Use `bitsandbytes` 8-bit Adam → optimizer state ~4× smaller
- Expected peak ≈ 8 GB weights + 2 GB grads + 2 GB Adam (8-bit) + 4-6 GB activations (grad ckpt) = **~18 GB**
- Tighter than X1; 24GB 3090 should fit; A100-20GB MIGHT NOT fit
- More faithful to what CapRL did in vision (they trained full captioner)

### Strategy X3 — DeepSpeed Stage 2/3 across 2× 3090

- Shard optimizer state / gradients / params across GPUs
- Can fit ~2B trainable at full precision across 2 × 3090
- More complex to set up; more I/O between GPUs
- Only makes sense if X1 doesn't match baseline quality

## Decision

**Go with X1 (LoRA everywhere) as Stream 2 W1 default.** Fall back to X2 only if X1 underfits (i.e., CPR with X1 can't even match SFT baseline's QA). Stray to X3 only if X2 also fails.

GPU placement:
- **3090 cluster** primary home for CPR training
  - Judge (Qwen3-8B, ~16 GB) on one dedicated 3090
  - 3 captioner training seeds in parallel on 3 other 3090s
  - Keeps 4 GPUs in reserve for ablations / retries
- **A100 cluster** for baseline model inference / ChatTS-14B eval (no training) — can squeeze into 20GB per card since inference-only
- **Fallback**: if 3090 gets suddenly crowded, use A100 GPU1/2/3 with 20GB free each for X1 training (X1 fits in 20GB)

This change de-risks the A1 amber flag: we no longer depend on A100 GPU2 being freed.

## Updates to commit

- Experiment tracker R018/R020 updated to install `peft` + `bitsandbytes` in W1 on 3090 opentslm env
- Budget reminder: 3090 throughput is roughly 0.35× A100 for bf16 attention. 35 A100-hr per seed → ~100 3090-hr per seed = 4 days wall-clock if sequential, 1.5 days with 3 seeds parallel on 3 separate 3090s
- Contract does NOT need v2; this is strategy-level detail below the H3 threshold commitments

## Next actions

1. Nothing to do today beyond this memo. Smoke test will be repeated in W1 with X1 config and a real TS batch (vs today's fake LM-only forward).
2. Proceed to R002 transforms.py now.
