# Natural QCC GPU Smoke Result Audit（2026-05-20）

- run_dir: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/train_v2_e5_tok128_20260520/tsrlm_no_question_e5_tok128_qwen3_4b`
- audit_pass: `True`
- status: `smoke_improves_over_local_non_oracle_baselines`
- generated QA accuracy: `0.1429`
- generated QA rows: `35`
- summary: generated caption 在当前 AIOps smoke 子集上超过所有本地非 oracle 基线。
- next action: 把结果作为单源 smoke 证据记录；下一步扩到跨域 reviewer-positive 数据后复验。

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
| `generated_caption` | `0.1429` |

## Decision Fields

- baseline max non-oracle: `0.0726`
- beats all non-oracle baselines: `True`
- beats question-only: `True`
- oracle gap: `0.8571`
- claim scope: `Smoke-level training result only; not a full method claim.`

## Interpretation Guardrail

只有 `audit_pass=true` 时，才能把该 run 当作 generated-caption QA 结果；否则只能作为失败/阻塞记录。
若 generated-caption QA 未超过 `question_only`，应报告为 training/interface failure，而不是 QCC 成功。
