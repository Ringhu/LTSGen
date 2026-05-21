# MultiSim v5 AIOpsLab v3 Completion Audit（2026-05-18）

## Goal

用户目标：先做 dataloader 和 training smoke，确认后扩 AIOpsLab 并修改模型，然后做训练和测试，给出扩充数据后的训练模型评估报告。

## Deliverable Audit

| 要求 | 状态 | 证据 |
| --- | --- | --- |
| dataloader smoke | done | `multisim_qcc_v5_aiops_v3/dataloader_smoke_balanced_20260518.json`, `smoke_pass=true` |
| training smoke / bounded training | done | 144-step one-epoch A100 run, train report under `tsrlm_multisim_v5_aiops_v3_balanced24_qwen3_4b_20260518/` |
| 扩 AIOpsLab | done | `aiopslab_official_v3`: 60 rows, 5 usable cases; 2 revoke_auth cases skipped because exported CSV=0 |
| 修改模型/训练路径 | done | dedicated MultiSim v5 4-channel collator/training/generation path; 3D data zero-padded to 4D |
| 扩充数据后训练 | done | balanced train: 144 rows, 24/source, 1 epoch |
| 扩充数据后测试 | done | bounded eval: 48 rows, 8/source, generated captions + rule QA |
| 评估报告 | done | `MULTISIM_V5_AIOPS_V3_TRAINING_EVAL_REPORT_ZH_20260518.md` |
| GitHub-ready figure | done | `figures/multisim-v5-aiops-v3-flow.{mmd,md}` |

## Key Numbers

| Metric | Value |
| --- | ---: |
| merged rows | 1980 |
| sources | 6 |
| AIOpsLab v3 rows | 60 |
| dataloader smoke pass | true |
| train rows | 144 |
| eval rows for loss | 144 |
| bounded QA rows | 48 |
| oracle QA accuracy | 1.0000 |
| generic QA accuracy | 0.0208 |
| statistical QA accuracy | 0.1250 |
| trained model QA accuracy | 0.1250 |
| trained model empty answer rate | 0.5208 |

## Important Caveats

- This is not a method success. The trained model did not beat the statistical caption baseline.
- The bounded QA test uses 48 rows because full 144-row generation with 48 tokens was too slow and had no streaming output.
- Large JSONL files and checkpoints remain on A100. Local/GitHub only keep small reports, scripts, and evaluation artifacts.
- Mermaid PNG rendering failed locally because Chromium sandbox was unavailable; the `.mmd` and `.md` Mermaid sources are kept and render on GitHub-compatible Markdown.

## Recommended Next Step

Do not start larger multi-simulator training yet. First add a streaming generation writer and run a per-source overfit gate plus constrained output template to reduce hallucination and empty-answer failures.
