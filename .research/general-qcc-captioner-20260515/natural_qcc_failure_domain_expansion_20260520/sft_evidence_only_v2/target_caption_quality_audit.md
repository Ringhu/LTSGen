# Natural QCC Caption Quality Audit（2026-05-20）

本审计检查 generated caption 是否具有基本 evidence-caption 形态。它不替代 downstream QA accuracy；QA 答对但只输出答案标签时，本审计会把它标为低质量 caption。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/sft_evidence_only_v2/natural_qcc_failure_domain_expanded_v2_evidence_only_test_sft.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl`
- caption field: `output`
- rows: `35`
- quality gate pass: `True`
- evidence shape rate: `0.8857`
- numeric evidence rate: `0.8857`
- answer-label-only rate: `0.0000`

## By Source

| source | n | evidence shaped | answer-label-only | numeric evidence |
| --- | ---: | ---: | ---: | ---: |
| `aiopslab_official_v3` | 5 | 1.0000 | 0.0000 | 1.0000 |
| `citylearn` | 2 | 1.0000 | 0.0000 | 1.0000 |
| `grid2op` | 10 | 0.8000 | 0.0000 | 0.8000 |
| `traffic` | 12 | 1.0000 | 0.0000 | 1.0000 |
| `water` | 6 | 0.6667 | 0.0000 | 0.6667 |

## Failure Reasons

`{'no_numeric_evidence': 4}`

## Guardrail

只有该审计通过，才说明 generated captions 至少不像单纯答案标签投机；最终方法结论仍需同时看 QA accuracy、qcond-vs-no-question gap 和人工/LLM 细审。
