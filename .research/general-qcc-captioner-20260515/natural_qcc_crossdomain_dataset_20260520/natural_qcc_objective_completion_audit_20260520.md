# Natural QCC Objective Completion Gate（2026-05-20）

- status: `complete_negative_signal`
- objective complete: `True`
- summary: 目标完成，但 q-conditioned generated-caption QA 没有证明优于基线或 no-question 对照。
- claim scope: `Completed smoke with negative result; report failure plainly.`

## Completion Checks

| check | pass |
| --- | ---: |
| `dataset_schema_gate_pass` | `True` |
| `positive_dataset_rows_present` | `True` |
| `sft_split_files_present` | `True` |
| `no_question_control_gate_pass` | `True` |
| `probe_results_present` | `True` |
| `oracle_evidence_baseline_present` | `True` |
| `non_oracle_baselines_present` | `True` |
| `oracle_caption_load_bearing` | `True` |
| `qcond_gpu_audit_pass` | `True` |
| `no_question_gpu_audit_pass` | `True` |
| `qcond_generated_metrics_present` | `True` |
| `no_question_generated_metrics_present` | `True` |
| `qcond_caption_quality_audit_present` | `True` |
| `no_question_caption_quality_audit_present` | `True` |
| `qcond_vs_no_question_comparison_complete` | `True` |
| `safe_result_manifest_pass` | `True` |
| `safe_result_manifest_has_no_unsafe_paths` | `True` |

## Result Checks

| item | value |
| --- | --- |
| `qcond_accuracy` | `0.0` |
| `no_question_accuracy` | `0.0` |
| `qcond_minus_no_question` | `0.0` |
| `min_gap` | `0.05` |
| `qcond_beats_all_non_oracle_baselines` | `False` |
| `qcond_beats_question_only` | `False` |
| `qcond_caption_quality_gate_pass` | `False` |
| `qcond_caption_evidence_shape_rate` | `0.3846` |
| `qcond_caption_answer_label_only_rate` | `0.5385` |
| `no_question_caption_quality_gate_pass` | `False` |
| `no_question_caption_evidence_shape_rate` | `0.4615` |
| `no_question_caption_answer_label_only_rate` | `0.3846` |
| `compare_status` | `no_qconditioning_gap` |

## Blockers

- None

## Remote Access Diagnostic

- any access pass: `True`
- `3090` reachable=`True`, access_pass=`True`, stderr=``

## Guardrail

该 gate 只在 q-conditioned 与 no-question 两条 GPU smoke 都完成、生成 caption 和 rule-QA 指标都存在、caption-quality 审计存在，并且安全 manifest 通过时，才会把 objective 标为 complete。
若 objective complete 但 QCC 没有超过 baselines/no-question，或 QA 提升但 caption-quality gate 失败，应按负结果或弱信号报告，而不是改写 claim。
