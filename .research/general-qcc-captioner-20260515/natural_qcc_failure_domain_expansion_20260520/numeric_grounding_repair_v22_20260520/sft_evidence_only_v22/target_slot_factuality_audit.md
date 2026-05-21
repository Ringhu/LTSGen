# Natural QCC Slot Factuality Audit（2026-05-20）

本审计只检查 generated/target caption 是否和 deterministic support slots 对齐；它不让 LLM 判答案，也不替代 downstream QA。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/sft_evidence_only_v22/natural_qcc_failure_domain_expanded_v22_numeric_grounding_test_raw.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/sft_evidence_only_v22/natural_qcc_failure_domain_expanded_v22_numeric_grounding_test_raw.jsonl`
- caption field: `target_caption`
- rows: `35`
- overall slot factuality: `1.0000`
- slot value pass rate: `1.0000`
- slot value recall: `1.0000`
- direction pass rate: `1.0000`
- horizon pass rate: `1.0000`

## By Source

| source | n | overall | value pass | value recall | direction | horizon | failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `aiopslab_official_v3` | 5 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | `{}` |
| `citylearn` | 2 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | `{}` |
| `grid2op` | 10 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | `{}` |
| `traffic` | 12 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | `{}` |
| `water` | 6 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | `{}` |

## Main Failure Reasons

`{}`

## Guardrail

如果 caption 形态 gate 通过但本审计低，说明模型学会了证据模板，但没有稳定从当前 trace 复制关键数值或方向。
