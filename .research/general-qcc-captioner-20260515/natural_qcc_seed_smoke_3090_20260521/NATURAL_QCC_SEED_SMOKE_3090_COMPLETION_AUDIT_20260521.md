# Natural QCC Seed 3090 Smoke Completion Audit（2026-05-21）

## Objective

用户要求：把当前 Natural QCC seed 放到 3090 服务器上，开始一次 smoke 训练，并写一份图文并茂、通俗易懂的结果报告，同步到 GitHub。

## Prompt-to-Artifact Checklist

| Requirement | Evidence | Status |
| --- | --- | --- |
| 使用 3090 服务器 | `remote_access_check_backup_config.json` shows `access_pass=true`, host `head2`, `torch_cuda_device_count=8`; report records the 3090 route without exposing private SSH details. | complete |
| 训练数据放到 3090 | Remote archive path used in report: `/cluster/home/hulining/LTSGEN_caption_model_longline_seed_smoke_20260521_164648`; GPU bundle summary copied back under `gpu_bundle/seed_gpu_smoke_bundle_summary.json`. | complete |
| 每个域进入 smoke | `gpu_bundle/seed_gpu_smoke_bundle_summary.json`: 72 rows, `grid2op/citylearn/traffic/water/aiopslab/finrl = 12` each. | complete |
| qcond/no-question smoke inputs | `gpu_bundle/seed_qcond_smoke.jsonl` and `gpu_bundle/seed_no_question_smoke.jsonl`, 72 rows each. | complete |
| Token-budget preflight | `train_seed72_ep1_tok768/qcond_seed72/preflight.json`: `preflight_pass=true`, zero output truncation, zero prompt truncation, max needed tokens 408 under 768. | complete |
| Full smoke attempt | `train_seed72_ep1_tok768/qcond_seed72/natural_qcc_smoke_pipeline_summary.json`: preflight passed; train stopped with `returncode=-11`. | complete, negative result |
| Recovery diagnostics | `diagnostics/qcond_min2_bf16/multisim_v5_train_smoke_report.json` and `diagnostics/qcond_72_maxstep1_bf16/multisim_v5_train_smoke_report.json` show small/1-step training succeeded. | complete |
| Completed bounded smoke | `train_seed72_step6_tok768/qcond_seed72/multisim_v5_train_smoke_report.json` and `train_seed72_step6_tok768/no_question_seed72/multisim_v5_train_smoke_report.json`: both trained with 72 rows, `max_steps=6`. | complete |
| Generated captions | qcond/no-question prediction files under `train_seed72_step6_tok768/*/generate_eval18_clean/predictions.jsonl`; each has 18 rows, 3 per domain. | complete |
| QA and caption-quality metrics | `semantic_qa_metrics.json` and `natural_qcc_caption_quality_eval18_audit.json` exist for both qcond and no-question. | complete |
| 图文并茂报告 | `NATURAL_QCC_SEED_SMOKE_3090_REPORT_20260521_ZH.md` includes SVG figures under `figures/`. | complete |
| 通俗解释 | Report sections `一句话结论`, `通俗解释`, and `本轮结论` explain results in non-technical language. | complete |
| No large checkpoints committed | Local artifact check found no `final_model/*` files and no files larger than 5MB in this result directory. | complete |
| Reproducible runner | `scripts/remote/run_natural_qcc_seed_smoke_3090.sh` and `scripts/generate/build_natural_qcc_seed_smoke_gpu_bundle.py`. | complete |
| GitHub sync | Pending until commit and push finish. | pending |

## Result Summary

The real 3090 route is usable and the data/training preflight is healthy. A full 1-epoch qcond run hit a lower-level Python/PyTorch/CUDA segfault after model loading, so this is not a complete successful training run. A bounded 6-step smoke did complete for both qcond and no-question, including save/load/generation/evaluation.

The bounded result shows qcond generates more evidence-shaped captions than no-question, but semantic QA remains 0. This should be reported as a useful infrastructure and diagnostic milestone, not as Natural QCC method success.
