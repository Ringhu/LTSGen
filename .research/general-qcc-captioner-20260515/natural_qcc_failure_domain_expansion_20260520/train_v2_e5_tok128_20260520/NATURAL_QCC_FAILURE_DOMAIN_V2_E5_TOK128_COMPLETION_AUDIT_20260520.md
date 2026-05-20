# Natural QCC Failure-Domain v2 同配置训练完成审计（2026-05-20）

## Objective

基于当前 v2 扩容数据，做一次同配置训练，观察结果，并分析哪里可以优化。

## Deliverables

| requirement | status | evidence |
| --- | --- | --- |
| 使用当前扩容数据 | pass | `merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl`, n=124 |
| 使用同配置训练 | pass | e5/tok128：epochs=5, max_new_tokens=128, clean_max_sentences=3, gradient_accumulation_steps=2 |
| 跑 q-conditioned | pass | `tsrlm_qcond_e5_tok128_qwen3_4b/natural_qcc_smoke_pipeline_summary.json`, complete=true |
| 跑 no-question 对照 | pass | `tsrlm_no_question_e5_tok128_qwen3_4b/natural_qcc_smoke_pipeline_summary.json`, complete=true |
| semantic QA 评估 | pass | qcond=0.3143, no-question=0.1429 |
| qcond/no-question comparison | pass | `natural_qcc_failure_domain_expanded_v2_e5_tok128_qcond_vs_noquestion_audit.json`, gap=+0.1714 |
| caption quality audit | pass | 两条 run 都有 `natural_qcc_caption_quality_audit.json` |
| 优化分析 | pass | `NATURAL_QCC_FAILURE_DOMAIN_V2_E5_TOK128_TRAINING_REPORT_20260520_ZH.md` |
| 不提交模型权重 | pass | 本地同步排除了 `final_model/` |

## Completion Result

训练和分析已完成。结果是 smoke-level 正信号，但不是完整方法成功：

- qcond semantic QA：0.3143
- no-question semantic QA：0.1429
- gap：+0.1714
- qcond caption quality gate：false
- no-question caption quality gate：false

下一步应先修 caption quality 和 Grid2Op/Water 失败模式，再继续扩容或做模型结构搜索。
