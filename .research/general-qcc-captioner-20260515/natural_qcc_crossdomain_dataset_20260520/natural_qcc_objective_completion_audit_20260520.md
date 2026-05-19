# Natural QCC Objective Completion Gate（2026-05-20）

- status: `incomplete_or_blocked`
- objective complete: `False`
- summary: 目标尚未完成：真实 QCC/no-question 训练、生成 caption、caption 质量审计、QA 或安全同步证据仍缺失。
- claim scope: `No generated-caption training claim allowed.`

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
| `qcond_gpu_audit_pass` | `False` |
| `no_question_gpu_audit_pass` | `False` |
| `qcond_generated_metrics_present` | `False` |
| `no_question_generated_metrics_present` | `False` |
| `qcond_caption_quality_audit_present` | `False` |
| `no_question_caption_quality_audit_present` | `False` |
| `qcond_vs_no_question_comparison_complete` | `False` |
| `safe_result_manifest_pass` | `False` |
| `safe_result_manifest_has_no_unsafe_paths` | `True` |

## Result Checks

| item | value |
| --- | --- |
| `qcond_accuracy` | `None` |
| `no_question_accuracy` | `None` |
| `qcond_minus_no_question` | `None` |
| `min_gap` | `0.05` |
| `qcond_beats_all_non_oracle_baselines` | `False` |
| `qcond_beats_question_only` | `False` |
| `qcond_caption_quality_gate_pass` | `False` |
| `qcond_caption_evidence_shape_rate` | `None` |
| `qcond_caption_answer_label_only_rate` | `None` |
| `no_question_caption_quality_gate_pass` | `False` |
| `no_question_caption_evidence_shape_rate` | `None` |
| `no_question_caption_answer_label_only_rate` | `None` |
| `compare_status` | `incomplete_or_blocked` |

## Blockers

- `qcond_gpu_audit_pass`
- `no_question_gpu_audit_pass`
- `qcond_generated_metrics_present`
- `no_question_generated_metrics_present`
- `qcond_caption_quality_audit_present`
- `no_question_caption_quality_audit_present`
- `qcond_vs_no_question_comparison_complete`
- `safe_result_manifest_pass`

## Remote Access Diagnostic

- any access pass: `False`
- `a100` reachable=`False`, access_pass=`False`, stderr=`ssh: Could not resolve hostname a100: Temporary failure in name resolution`
- `3090` reachable=`False`, access_pass=`False`, stderr=`Connection closed by 0.0.12.18 port 22`

## Guardrail

该 gate 只在 q-conditioned 与 no-question 两条 GPU smoke 都完成、生成 caption 和 rule-QA 指标都存在、caption-quality 审计存在，并且安全 manifest 通过时，才会把 objective 标为 complete。
若 objective complete 但 QCC 没有超过 baselines/no-question，或 QA 提升但 caption-quality gate 失败，应按负结果或弱信号报告，而不是改写 claim。
