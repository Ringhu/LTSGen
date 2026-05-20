# Natural QCC Evidence-Only Repair Completion Audit（2026-05-20）

- status: `complete_positive_smoke_signal_with_limits`
- objective complete: `True`

## Checklist

| requirement | pass | evidence | note |
| --- | ---: | --- | --- |
| 保持当前 reviewer-positive 数据质量，不用低质量扩增样本 | `True` | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft_evidence_only/natural_qcc_crossdomain_evidence_only_summary.json` | positive=55, schema_gate_pass=True |
| 去掉 Answer label 捷径但保留可判定证据 | `True` | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft_evidence_only/target_semantic_qa/semantic_qa_metrics.json`<br>`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft_evidence_only/target_caption_quality_audit.json` | target semantic QA=1.0, answer-label-only=0 |
| 增加训练样本使用量 | `True` | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft_evidence_only/natural_qcc_crossdomain_evidence_only_summary.json` | train+dev=42, test=13 |
| 修复生成清洗问题并验证影响 | `True` | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/generate_eval_test_reclean/reclean_summary.json`<br>`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/generate_eval_test_reclean/caption_quality_audit.json` | 旧输出 re-clean changed_rate>0.9，质量门通过，但 QA 仍 0 |
| 跑 evidence-only 1 epoch qcond/no-question 对照 | `True` | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_evidence_only_smoke_qwen3_4b_20260520`<br>`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_evidence_only_no_question_smoke_qwen3_4b_20260520`<br>`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_evidence_only_qcond_vs_noquestion_audit_20260520.json` | 1 epoch 未提升 |
| 尝试更长训练和生成，观察是否提升训练效果 | `True` | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_evidence_only_e5_tok128_smoke_qwen3_4b_20260520`<br>`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_evidence_only_no_question_e5_tok128_smoke_qwen3_4b_20260520`<br>`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_evidence_only_e5_tok128_qcond_vs_noquestion_audit_20260520.json` | qcond=0.2308, noq=0.1538, gap=0.077 |
| 验证提升没有破坏 caption 质量 | `True` | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_evidence_only_e5_tok128_smoke_qwen3_4b_20260520/natural_qcc_caption_quality_audit.json`<br>`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_evidence_only_no_question_e5_tok128_smoke_qwen3_4b_20260520/natural_qcc_caption_quality_audit.json` | 两条 e5/tok128 run quality gate 都通过 |
| 检查 options-in-prompt 假设 | `True` | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft_evidence_only_options/natural_qcc_crossdomain_evidence_only_summary.json`<br>`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_evidence_only_options_e5_tok128_smoke_qwen3_4b_20260520`<br>`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_evidence_only_options_e5_tok128_qcond_vs_noquestion_audit_20260520.json` | target 质量保持，但 qcond options QA=0.0769，负向 |
| 所有远端结果不包含模型权重/检查点 | `True` | `find ... final_model/pytorch_model.bin/*.safetensors` | 已用 tar exclude，当前小结果目录未发现权重文件 |
| 中文报告存在并汇总结论 | `True` | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/NATURAL_QCC_EVIDENCE_ONLY_TRAINING_REPAIR_REPORT_20260520_ZH.md` | 报告已生成 |

## Final Result

在 reviewer-positive 55 条数据不扩增、不降低质量的前提下，evidence-only 目标和更长训练/生成把 qcond semantic QA 从 0.0000 提升到 0.2308，no-question 为 0.1538，q-conditioning gap 为 0.0770。结果是 smoke-level 正信号，但 test 只有 13 条，不能作为完整方法成功。

## Remaining Risk

- test 只有 13 条，不能作为完整方法成功
- Grid2Op/Traffic/Water 在最佳配置下仍为 0
- options-in-prompt 是负向消融，不建议作为下一步主线
