# LTSGEN — Project CLAUDE.md

## Active Research Contract

**`./.research/research-contract-20260419.md` is ACTIVE.** All experimental
code, experiment design, and paper writing must respect:

- Hypothesis H1/H2/H3, success signals, and failure signals as locked
- The routing table in §2.3 (A-success / B-partial / C-failure) is locked —
  no post-hoc reinterpretation
- The forbidden-rationalization list in §5 is binding
- Every paper claim must map back to a contract signal (§8)

Revisions require a new file `research-contract-v2.md` with explicit
changelog. Changes that weaken success criteria or redefine failure after
seeing results are forbidden.

## Key paths

| Artifact | Path |
|---|---|
| Research contract (active) | `./.research/research-contract-20260419.md` |
| **Experiment plan (active)** | `./.research/experiment-plan-20260419.md` |
| **Experiment tracker** | `./.research/experiment-tracker-20260419.md` |
| Lit review | `./.research/lit-review-20260419.md` |
| Idea decision | `./.research/idea-decision-20260419.md` |
| Prior-art check | `./.research/prior-art-check-20260419.md` |
| Experiment progress log | `./EXPERIMENT_PROGRESS.md` (historical, pre-contract) |
| TSShapeQA v1 data | `./LTSGEN-ext-a/data/tsshapeqa/` |
| OpenTSLM-vars1 checkpoint (A100) | `/cluster1/user1/hulining/opentslm_checkpoints/Qwen3_4B/OpenTSLMFlamingo/ablation_vars1_mixed/stage2_captioning/checkpoints/best_model.pt` |
| OpenTSLM codebase (A100) | `/cluster/home/user1/hulining/TSModel/OpenTSLM/` |

## Two-stream publication plan (locked)

| Stream | Deadline | Scope | Venue |
|---|---|---|---|
| **Stream 1** | 2026-05-06 (hard) | Diagnosis (H1) + Benchmark (H2) only | NeurIPS 2026 D&B |
| **Stream 2** | 2026-06-15 preprint, 2026-10 camera-ready | 3-contribution (H1+H2+H3) | ICLR 2027 main |

Stream 1 deadline is tight (17 days from contract lock). Falling off
Stream 1 defaults to preprint-first Stream 2 per §6 of the contract.

## Infrastructure recap (global CLAUDE.md has full details)

- **Local**: Claude Code CLI + SSHFS mount of A100 via `~/mnt/a100`
- **A100 (ssh a100)**: 4× A100 80GB, default GPU2, code at `/cluster/home/user1/hulining/`
- **3090 (ssh 3090)**: 8× RTX 3090 24GB, code at `/cluster/home/hulining/`
- **LLM proxy**: `OPENAI_BASE_URL=https://ai.crisinsjtu.top/v1`, models: gpt-5.4 / gpt-5.4-mini / gpt-5.2-pro
- **Local LLM for RL reward (new for ShapeShift)**: Qwen2.5-7B-Instruct via vLLM on 3090

## Current phase

**Phase: plan locked → R001 infra smoke test.**
Contract + experiment-plan + tracker all locked 2026-04-19.

**Next concrete action: R001** — infrastructure smoke test (~2 hours):
spin up vLLM + Qwen2.5-7B-Instruct on 3090, verify A100 GPU2 access,
confirm ChatTS-14B HF download, verify OpenTSLM vars=1 ckpt loads.

**R001 unblocks R002 (transforms.py implementation 2026-04-20), which
is the single hard dependency of all Stream 1 work.**

Stream 1 S6a gate: **2026-04-26 EOD** — TSShapeQA-v2 build must be
complete + sanity-passed + 4-model captions generated. Miss = Stream 1
aborted, pivot to Stream 2 preprint-first.
