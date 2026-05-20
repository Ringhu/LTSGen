# Natural QCC v2.2 Training Validation Completion Audit（2026-05-20）

## Objective

用户要求：先规划如何做训练进行验证，然后走训练流程，验证 v2.2 numeric-grounding 修复是否有效。

Concrete deliverables:

1. 写出训练验证计划和成功/失败判定标准。
2. 真实跑 v2.2 qcond/no-question paired training。
3. 收集 semantic QA、caption quality、slot factuality、qcond-vs-no-question 结果。
4. 写中文训练验证报告，给出“修复是否有效”的结论。
5. 同步到 GitHub。

## Prompt-to-Artifact Checklist

| requirement | evidence | status |
| --- | --- | --- |
| 训练验证计划 | `NATURAL_QCC_V22_TRAINING_VALIDATION_PLAN_20260520_ZH.md` | complete |
| 预设判定标准 | plan 中定义 `strong effective` / `mixed effective` / `not effective` | complete |
| 可复现训练脚本 | `scripts/remote/run_natural_qcc_failure_domain_v22_pair_3090.sh` | complete |
| 远程 GPU access | `train_v22_e5_tok128_20260520/remote_gpu_access_check.json`, `any_access_pass=true` | complete |
| qcond 训练完成 | `tsrlm_qcond_e5_tok128_qwen3_4b/natural_qcc_smoke_pipeline_summary.json`, `complete=true` | complete |
| no-question 训练完成 | `tsrlm_no_question_e5_tok128_qwen3_4b/natural_qcc_smoke_pipeline_summary.json`, `complete=true` | complete |
| qcond smoke audit | `tsrlm_qcond_e5_tok128_qwen3_4b/natural_qcc_gpu_smoke_result_audit.json`, `audit_pass=true` | complete |
| no-question smoke audit | `tsrlm_no_question_e5_tok128_qwen3_4b/natural_qcc_gpu_smoke_result_audit.json`, `audit_pass=true` | complete |
| semantic QA | both `generate_eval_test_clean/rule_qa/semantic_qa_metrics.json` | complete |
| caption quality | both `natural_qcc_caption_quality_audit.json` | complete |
| slot factuality | both `natural_qcc_slot_factuality_audit.json` | complete |
| qcond-vs-no-question | `natural_qcc_failure_domain_expanded_v22_e5_tok128_qcond_vs_noquestion_audit.json` | complete |
| result summary | `natural_qcc_failure_domain_v22_training_validation_result_summary_20260520.json` | complete |
| Chinese report | `NATURAL_QCC_V22_TRAINING_VALIDATION_REPORT_20260520_ZH.md` | complete |

## Verification Evidence

Target gates:

- target semantic QA: `1.0000`
- target caption quality gate: `true`
- target evidence shape rate: `1.0000`
- target slot factuality: `1.0000`

Generated qcond:

- pipeline audit pass: `true`
- semantic QA: `0.0000`
- empty answer rate: `1.0000`
- empty caption rate: `1.0000`
- caption quality gate: `false`
- overall slot factuality: `0.0857`
- Grid2Op slot factuality: `0.0000`

Generated no-question:

- pipeline audit pass: `true`
- semantic QA: `0.0000`
- empty answer rate: `1.0000`
- caption quality gate: `true`
- evidence shape rate: `0.8571`
- overall slot factuality: `0.0857`
- Grid2Op slot factuality: `0.0000`

Comparison:

- qcond-minus-no-question semantic QA: `0.0000`
- qcond-vs-no-question status: `no_qconditioning_gap`
- effectiveness decision: `not_effective`

## Coverage Check

This audit does not rely on proxy signals alone:

- Passing target gates is not treated as training success.
- Passing smoke audit is not treated as model success; it only proves the pipeline completed and metrics exist.
- The conclusion uses generated semantic QA, caption quality, slot factuality, and qcond-vs-no-question together.
- The report explicitly distinguishes target cleanliness from model generation failure.

## Missing Or Weak Points

No required objective item remains missing.

Residual risk:

- The run used a copied remote work directory rather than remote `git pull` because the remote host's GitHub proxy was unavailable. The local branch commit was already pushed before copying, and the copied runner was the same code plus the local `PYTHONPATH` fix now tracked in this branch.
- Model weights were not synced back or committed; only JSON/JSONL/MD result evidence was retained locally.

## Completion Decision

The objective is complete: a training plan was written, qcond/no-question training was run on 3090, all planned evaluation gates were collected, and the result was reported.

Conclusion: v2.2 numeric-grounding target repair is data-clean, but training validation failed; the repair is **not effective** under the current TS-RLM/Qwen generation recipe.

