# Natural QCC Slot Factuality Audit（2026-05-20）

本审计只检查 generated/target caption 是否和 deterministic support slots 对齐；它不让 LLM 判答案，也不替代 downstream QA。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/train_v21_style_repair_e5_tok128_20260520/tsrlm_qcond_e5_tok128_qwen3_4b/generate_eval_test_clean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/sft_evidence_only_v21/natural_qcc_failure_domain_expanded_v21_evidence_only_test_raw.jsonl`
- caption field: `pred_caption`
- rows: `35`
- overall slot factuality: `0.1143`
- slot value pass rate: `0.1143`
- slot value recall: `0.1486`
- direction pass rate: `0.5357`
- horizon pass rate: `0.7500`

## By Source

| source | n | overall | value pass | value recall | direction | horizon | failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `aiopslab_official_v3` | 5 | 0.4000 | 0.4000 | 0.2857 | 0.6667 | 0.0000 | `{'slot_value_mismatch': 3, 'direction_mismatch': 1}` |
| `citylearn` | 2 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | `{'slot_value_mismatch': 2}` |
| `grid2op` | 10 | 0.0000 | 0.0000 | 0.0455 | 0.3750 | 0.3333 | `{'slot_value_mismatch': 10, 'direction_mismatch': 5, 'horizon_mismatch': 2}` |
| `traffic` | 12 | 0.1667 | 0.1667 | 0.1538 | 0.4545 | 1.0000 | `{'slot_value_mismatch': 10, 'direction_mismatch': 6}` |
| `water` | 6 | 0.0000 | 0.0000 | 0.2667 | 0.8000 | 1.0000 | `{'slot_value_mismatch': 6, 'direction_mismatch': 1}` |

## Main Failure Reasons

`{'slot_value_mismatch': 31, 'direction_mismatch': 13, 'horizon_mismatch': 2}`

## Guardrail

如果 caption 形态 gate 通过但本审计低，说明模型学会了证据模板，但没有稳定从当前 trace 复制关键数值或方向。
