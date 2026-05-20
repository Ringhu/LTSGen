# Natural QCC Slot Factuality Audit（2026-05-20）

本审计只检查 generated/target caption 是否和 deterministic support slots 对齐；它不让 LLM 判答案，也不替代 downstream QA。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/token_budget_fix_diagnostics_20260520/qcond_overfit5_maxtext768_qwen3_4b/generate_eval_test_clean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/sft_evidence_only_v22/natural_qcc_failure_domain_expanded_v22_numeric_grounding_train_raw.jsonl`
- caption field: `pred_caption`
- rows: `5`
- overall slot factuality: `0.2000`
- slot value pass rate: `0.2000`
- slot value recall: `0.6000`
- direction pass rate: `0.7500`
- horizon pass rate: `1.0000`

## By Source

| source | n | overall | value pass | value recall | direction | horizon | failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `aiopslab_official_v3` | 5 | 0.2000 | 0.2000 | 0.6000 | 0.7500 | 1.0000 | `{'slot_value_mismatch': 4, 'direction_mismatch': 1}` |

## Main Failure Reasons

`{'slot_value_mismatch': 4, 'direction_mismatch': 1}`

## Guardrail

如果 caption 形态 gate 通过但本审计低，说明模型学会了证据模板，但没有稳定从当前 trace 复制关键数值或方向。
