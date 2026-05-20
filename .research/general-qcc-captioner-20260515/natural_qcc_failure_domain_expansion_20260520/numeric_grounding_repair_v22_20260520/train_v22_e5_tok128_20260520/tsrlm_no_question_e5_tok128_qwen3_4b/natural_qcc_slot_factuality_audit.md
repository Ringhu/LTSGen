# Natural QCC Slot Factuality Audit（2026-05-20）

本审计只检查 generated/target caption 是否和 deterministic support slots 对齐；它不让 LLM 判答案，也不替代 downstream QA。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/train_v22_e5_tok128_20260520/tsrlm_no_question_e5_tok128_qwen3_4b/generate_eval_test_clean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/sft_evidence_only_v22/natural_qcc_failure_domain_expanded_v22_numeric_grounding_no_question_test_raw.jsonl`
- caption field: `pred_caption`
- rows: `35`
- overall slot factuality: `0.0857`
- slot value pass rate: `0.0857`
- slot value recall: `0.0135`
- direction pass rate: `0.2857`
- horizon pass rate: `1.0000`

## By Source

| source | n | overall | value pass | value recall | direction | horizon | failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `aiopslab_official_v3` | 5 | 0.4000 | 0.4000 | 0.1429 | 0.0000 | 1.0000 | `{'slot_value_mismatch': 3}` |
| `citylearn` | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | `{'slot_value_mismatch': 2, 'direction_mismatch': 1}` |
| `grid2op` | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | `{'slot_value_mismatch': 10, 'direction_mismatch': 3}` |
| `traffic` | 12 | 0.0833 | 0.0833 | 0.0000 | 0.5000 | 1.0000 | `{'slot_value_mismatch': 11, 'direction_mismatch': 1}` |
| `water` | 6 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | `{'slot_value_mismatch': 6}` |

## Main Failure Reasons

`{'slot_value_mismatch': 32, 'direction_mismatch': 5}`

## Guardrail

如果 caption 形态 gate 通过但本审计低，说明模型学会了证据模板，但没有稳定从当前 trace 复制关键数值或方向。
