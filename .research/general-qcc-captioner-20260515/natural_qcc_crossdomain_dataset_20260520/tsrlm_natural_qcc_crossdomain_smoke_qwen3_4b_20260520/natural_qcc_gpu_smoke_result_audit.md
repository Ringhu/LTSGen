# Natural QCC GPU Smoke Result Audit（2026-05-20）

- run_dir: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520`
- audit_pass: `False`
- status: `incomplete_or_blocked`
- generated QA accuracy: `None`
- generated QA rows: `None`
- summary: GPU smoke run 尚未完整完成，不能解释 generated-caption QA。
- next action: 先完成远程 preflight、训练、生成和 rule-QA，再重新运行本审计。

## Checks

| check | pass |
| --- | ---: |
| `preflight_exists` | `False` |
| `preflight_pass` | `False` |
| `pipeline_summary_exists` | `True` |
| `pipeline_complete` | `False` |
| `predictions_exist` | `False` |
| `prediction_rows_positive` | `False` |
| `qa_metrics_exists` | `False` |
| `qa_rows_positive` | `False` |
| `baseline_probe_exists` | `True` |
| `baseline_has_question_only` | `True` |

## Baseline Comparison

| condition | accuracy |
| --- | ---: |
| `natural_oracle` | `1.0` |
| `generic_caption` | `0.0182` |
| `statistical_caption` | `0.0` |
| `question_only` | `0.1273` |
| `generated_caption` | `None` |

## Decision Fields

- baseline max non-oracle: `0.1273`
- beats all non-oracle baselines: `False`
- beats question-only: `False`
- oracle gap: `None`
- claim scope: `No training-result claim allowed.`

## Interpretation Guardrail

只有 `audit_pass=true` 时，才能把该 run 当作 generated-caption QA 结果；否则只能作为失败/阻塞记录。
若 generated-caption QA 未超过 `question_only`，应报告为 training/interface failure，而不是 QCC 成功。
