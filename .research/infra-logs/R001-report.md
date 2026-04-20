# R001 Infra Smoke Test — Report

**Date:** 2026-04-19 22:50 CST
**Status:** ✅ PASS (with 2 amber flags)

## Summary

All 4 sub-checks passed. Infrastructure is ready to proceed to R002 (`transforms.py`).
Two non-blocking issues logged for scheduling awareness.

## Sub-check results

### R001-A — 3090 GPU + Qwen3-8B judge — ✅ PASS

- 8× RTX 3090 24GB all essentially idle (GPU0: 366 MiB used by someone's small python process; GPU1-7: fully free)
- Conda env `opentslm` at `/cluster/home/hulining/anaconda3/envs/opentslm` has torch 2.5.1+cu121 and transformers 5.4.0
- **Qwen3-8B downloaded** at `~/.cache/huggingface/hub/models--Qwen--Qwen3-8B` (5 safetensors shards, complete)
- **Qwen3-4B also cached** (captioner base, no redownload needed)
- **Smoke generation**: loaded via `transformers` in bf16 on GPU1 in 66.5s (cold cache), generated 20 tokens in 4.18s, peak VRAM **16.4 GB** (fits 24GB single 3090 with ~8GB headroom for batching)
- Output coherent: `"A stop sign is an octagon. Q:..."`
- **vLLM NOT installed.** Decision: use `transformers` + batched generate for R001 smoke and for diagnosis eval (B1); defer vLLM install to W1 (Stream 2 CPR training start, 2026-05-07) when throughput matters for inner RL loop

### R001-B — A100 GPU + OpenTSLM ckpt — ✅ PASS (1 amber)

- 4× A100 80GB; **GPU 0 busy 65% util** (ocrvl env, it_stu100 user, 53 GB used); **GPU 1/2/3 each have 60GB used by `openpi-agilex` job (user wjc), 0% util but parked memory**
- **Amber flag A1**: A100 GPU2 (user's default per CLAUDE.md) currently has only ~20GB free. Not blocking R001 (no training yet) but W2 CPR launch 2026-05-14 needs GPU2 to be freed or OpenTSLM inference squeezed into 20GB
- Conda env `opentslm` at `/cluster/home/user1/anaconda3/envs/opentslm` has torch 2.6.0+cu124, transformers 5.4.0
- Other relevant envs confirmed: `chatts`, `tsgen`, `tsrl`, `tsci`, `ptst`
- **OpenTSLM vars=1 ckpt LOCATION CORRECTED**: actual path is `/cluster1/user1/hulining/opentslm_checkpoints/Qwen3_4B/OpenTSLMFlamingo/ablation_vars1_mixed/stage2_captioning/checkpoints/best_model.pt` (22 GB). EXPERIMENT_PROGRESS.md had the shortened incorrect path. **Contract + plan + tracker must be updated** (amber flag A2, fix in next commit)
- Ckpt loads on CPU in 28.3s, `val_loss=0.2026` ✓ matches contract
- Model state dict has 2860 tensors

### R001-C — ChatTS-14B — ✅ PASS

- Weights already cached on A100 at `~/.cache/huggingface/hub/models--bytedance-research--ChatTS-14B`
- ChatTS source repo cloned at `/cluster/home/user1/hulining/ChatTS` and `TSModel/ChatTS`
- HF cache total 211 GB (fine)
- No download needed

### R001-D — crisinsjtu proxy — ✅ PASS

- `gpt-5.4-mini` ping returned `PONG` in < 3s via `llm_client.py` helper
- `OPENAI_BASE_URL` and `OPENAI_API_KEY` loadable from `~/.bashrc`

## Amber flags (non-blocking, track)

**A1 — A100 GPU2 occupancy.** openpi-agilex job (user wjc) uses 61GB on GPUs 1/2/3. Impact: when W2 CPR training starts 2026-05-14, if this job is still running, we can only use ~20GB per A100 which limits batch size. Mitigation:
- Check occupancy weekly during Stream 1
- If still occupied by 2026-05-10, escalate to get GPU access or redirect training to 3090 (OpenTSLM-vars=1 + Qwen3-4B bf16 might fit in 24GB 3090 tight; would need 2× 3090 for reasonable batch)

**A2 — Ckpt path correction.** The contract §1 and plan §3 and CLAUDE.md reference `/cluster1/user1/hulining/opentslm_checkpoints/ablation_vars1_mixed/` which does NOT exist. Real path: `/cluster1/user1/hulining/opentslm_checkpoints/Qwen3_4B/OpenTSLMFlamingo/ablation_vars1_mixed/stage2_captioning/checkpoints/best_model.pt`. Plan allows pre-experiment amendment log since no experiments have begun. Fix before R002 proceeds.

## Decisions locked by R001

- **Judge runtime = transformers (not vLLM) for Stream 1 eval**. vLLM install deferred to W1 2026-05-07 pre-CPR.
- **Judge GPU placement**: 3090 GPU1 (or any free slot 1-7). Dedicated during B1 diagnosis eval runs.
- **Captioner runtime = transformers + device_map auto**. Will use A100 GPU1 (or 2/3 depending on openpi-agilex job end-time) for OpenTSLM inference.

## Next action

R002 — `scripts/generate/transforms.py` implementation. Dependencies from R001 met. Expected start: 2026-04-20 (tomorrow).
