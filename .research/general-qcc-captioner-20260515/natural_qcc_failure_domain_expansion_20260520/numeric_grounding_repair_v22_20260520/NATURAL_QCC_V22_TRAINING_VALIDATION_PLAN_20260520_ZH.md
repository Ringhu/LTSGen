# Natural QCC v2.2 Numeric Grounding 训练验证计划（2026-05-20）

## 目标

验证 v2.2 numeric-grounding repair 是否不仅修好了 target，也能让训练后的 generated evidence caption 更可靠。

本轮不改变 gold answer，不引入 LLM 判分。训练后只用 deterministic evaluator 和 support-slot audit 判断效果。

## 要跑的对照

保持 v2.1 可比配置：

| item | value |
| --- | --- |
| model | `Qwen/Qwen3-4B` |
| bridge | `prefix` |
| train epochs | `5` |
| gradient accumulation | `2` |
| max new tokens | `128` |
| clean max sentences | `3` |
| QA evaluator | `semantic` |
| train rows | `89` |
| test rows | `35` |

两条 run：

| run | train SFT | eval raw |
| --- | --- | --- |
| qcond | `sft_evidence_only_v22/natural_qcc_failure_domain_expanded_v22_numeric_grounding_train_sft.jsonl` | `sft_evidence_only_v22/natural_qcc_failure_domain_expanded_v22_numeric_grounding_test_raw.jsonl` |
| no-question | `sft_evidence_only_v22/natural_qcc_failure_domain_expanded_v22_numeric_grounding_no_question_train_sft.jsonl` | `sft_evidence_only_v22/natural_qcc_failure_domain_expanded_v22_numeric_grounding_no_question_test_raw.jsonl` |

输出目录：

`.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/train_v22_e5_tok128_20260520/`

## 必跑评估

每条 run 完成后产出：

| evidence | command family | purpose |
| --- | --- | --- |
| pipeline summary | `scripts/train/run_natural_qcc_gpu_smoke.py` | 确认 preflight、训练、生成、semantic QA 全链路完成 |
| smoke result audit | `scripts/eval/audit_natural_qcc_gpu_smoke_result.py` | 确认结果不是缺文件或空评估 |
| generated semantic QA | `evaluate_natural_qcc_semantic_predictions.py` | 看 generated caption 能否支持答题 |
| caption quality audit | `scripts/eval/audit_natural_qcc_caption_quality.py` | 看输出是否像 evidence caption，而不是答案标签 |
| slot factuality audit | `scripts/eval/audit_natural_qcc_slot_factuality.py` | 看关键数值、方向、horizon 是否和 support slots 对齐 |
| qcond-vs-no-question | `scripts/eval/audit_natural_qcc_gpu_qcond_vs_noquestion.py` | 判断 question conditioning 是否带来有效增益 |

## 判定标准

### Strong effective

满足所有条件：

- qcond pipeline 和 no-question pipeline 都 `audit_pass=true`；
- qcond generated caption quality gate 为 `true`；
- qcond semantic QA 高于 v2.1 qcond baseline `0.3143`；
- qcond overall slot factuality 高于 v2.1 qcond baseline `0.1143`，且至少达到 `0.25`；
- qcond Grid2Op slot factuality 高于 v2.1 Grid2Op baseline `0.0000`；
- qcond slot factuality 比 no-question 高至少 `0.05`。

解释：可以说 v2.2 numeric-grounding repair 对模型生成产生了明确正效果，但仍只是 124-row failure-domain smoke，不是 full method claim。

### Mixed effective

满足以下任一情况：

- qcond slot factuality 高于 v2.1 baseline，但 semantic QA 没有提升；
- qcond semantic QA 提升，但 slot factuality 没有达到 `0.25`；
- qcond 有提升，但没有超过 no-question 对照。

解释：说明数据修复方向有信号，但生成端仍没有稳定学会 trace-to-evidence grounding。

### Not effective

满足以下任一情况：

- qcond pipeline 不完整或 audit 不通过；
- qcond slot factuality 未超过 v2.1 qcond baseline `0.1143`；
- qcond Grid2Op slot factuality 仍为 `0.0000`；
- caption quality gate 退化为 `false`。

解释：说明 v2.2 的 target 修复没有转化为模型生成能力，下一步应转向 value-copy auxiliary loss、slot-verbalization pretraining、Grid2Op curriculum，或更强的数值复制机制。

## 预期结论格式

最终报告必须同时给出：

- target gate：v2.2 target quality / semantic QA / slot factuality；
- generated gate：qcond 和 no-question 的 semantic QA、caption quality、slot factuality；
- v2.1 baseline 对比；
- Grid2Op 单独结论；
- 是否满足 `strong effective`、`mixed effective` 或 `not effective`；
- 下一步建议。

