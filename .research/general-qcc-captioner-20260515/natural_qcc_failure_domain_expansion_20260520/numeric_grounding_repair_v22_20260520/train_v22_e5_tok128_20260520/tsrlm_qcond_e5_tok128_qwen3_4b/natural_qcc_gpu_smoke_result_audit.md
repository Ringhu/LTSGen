# Natural QCC GPU Smoke Result Audit（2026-05-20）

- run_dir: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/train_v22_e5_tok128_20260520/tsrlm_qcond_e5_tok128_qwen3_4b`
- audit_pass: `True`
- status: `smoke_no_improvement_over_local_non_oracle_baselines`
- generated QA accuracy: `0.0`
- generated QA rows: `35`
- summary: generated caption 没有超过当前最强非 oracle 基线，不能作为 QCC 训练成功。
- next action: 检查训练日志、caption 空答率和输出格式；必要时调整训练数据或目标格式。

## Checks

| check | pass |
| --- | ---: |
| `preflight_exists` | `True` |
| `preflight_pass` | `True` |
| `pipeline_summary_exists` | `True` |
| `pipeline_complete` | `True` |
| `predictions_exist` | `True` |
| `prediction_rows_positive` | `True` |
| `qa_metrics_exists` | `True` |
| `qa_rows_positive` | `True` |
| `baseline_probe_exists` | `True` |
| `baseline_has_question_only` | `True` |

## Baseline Comparison

| condition | accuracy |
| --- | ---: |
| `natural_oracle` | `1.0` |
| `generic_caption` | `0.0323` |
| `statistical_caption` | `0.0` |
| `question_only` | `0.0726` |
| `generated_caption` | `0.0` |

## Decision Fields

- baseline max non-oracle: `0.0726`
- beats all non-oracle baselines: `False`
- beats question-only: `False`
- oracle gap: `1.0`
- claim scope: `Smoke-level training result only; not a full method claim.`

## Interpretation Guardrail

只有 `audit_pass=true` 时，才能把该 run 当作 generated-caption QA 结果；否则只能作为失败/阻塞记录。
若 generated-caption QA 未超过 `question_only`，应报告为 training/interface failure，而不是 QCC 成功。
