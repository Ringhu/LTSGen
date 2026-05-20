# Natural QCC Failure-Domain v2.1 完成审计（2026-05-20）

## Objective

按照规划，做一轮数据清洗和统一风格，然后再跑一次小实验，观察结果，并分析导致结果的原因。

## Prompt-to-Artifact Checklist

| requirement | status | evidence |
| --- | --- | --- |
| 做一轮数据清洗 | pass | `scripts/generate/build_natural_qcc_evidence_only_sft.py --style_repair` |
| 统一 evidence 风格 | pass | `sft_evidence_only_v21/`，target 为 `Evidence / Decision rule / Therefore` 结构 |
| 不改 gold answer | pass | v2.1 从 `merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl` 派生，只改 target/prompt |
| 目标 caption 质量 gate | pass | `sft_evidence_only_v21/target_caption_quality_audit.json`，evidence_shape=1.0 |
| 目标 semantic QA gate | pass | `sft_evidence_only_v21/target_semantic_qa/semantic_qa_metrics.json`，accuracy=1.0 |
| 同配置 qcond 小实验 | pass | `train_v21_style_repair_e5_tok128_20260520/tsrlm_qcond_e5_tok128_qwen3_4b/`，pipeline_complete=true |
| 同配置 no-question 对照 | pass | `train_v21_style_repair_e5_tok128_20260520/tsrlm_no_question_e5_tok128_qwen3_4b/`，pipeline_complete=true |
| 单 run audit | pass | 两个 run 的 `natural_qcc_gpu_smoke_result_audit.json` 均 audit_pass=true |
| qcond/no-question comparison | pass | `natural_qcc_failure_domain_expanded_v21_e5_tok128_qcond_vs_noquestion_audit.json`，gap=+0.2000 |
| generated caption quality audit | pass | qcond/no-question evidence_shape=1.0，answer_label_only=0.0 |
| 原因分析报告 | pass | `NATURAL_QCC_FAILURE_DOMAIN_V21_STYLE_REPAIR_TRAINING_REPORT_20260520_ZH.md` |
| 不同步模型权重 | pass | rsync 排除 `final_model/`，本地无模型权重或 >20MB 文件 |

## Completion Result

本轮完成。结论是：v2.1 清洗统一风格成功修复 generated caption 形态，但没有提升 qcond semantic QA。主要原因是模型开始稳定输出 evidence 模板，却仍会填错数值、窗口位置或反事实方向；Grid2Op 是最明显的受损域。

关键结果：

- qcond semantic QA：0.3143
- no-question semantic QA：0.1143
- qcond gap：+0.2000
- qcond evidence_shape_rate：1.0000
- qcond answer_label_only_rate：0.0000
- claim scope：cross-domain smoke only，不是完整方法成功。
