# Natural QCC Caption Quality Audit（2026-05-20）

本审计检查 generated caption 是否具有基本 evidence-caption 形态。它不替代 downstream QA accuracy；QA 答对但只输出答案标签时，本审计会把它标为低质量 caption。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/probe_eval/natural_oracle_predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- caption field: `caption`
- rows: `55`
- quality gate pass: `True`
- evidence shape rate: `0.9091`
- numeric evidence rate: `0.9091`
- answer-label-only rate: `0.0000`

## By Source

| source | n | evidence shaped | answer-label-only | numeric evidence |
| --- | ---: | ---: | ---: | ---: |
| `aiopslab_official_v3` | 12 | 1.0000 | 0.0000 | 1.0000 |
| `citylearn` | 9 | 0.8889 | 0.0000 | 0.8889 |
| `grid2op` | 12 | 0.9167 | 0.0000 | 0.9167 |
| `traffic` | 11 | 0.8182 | 0.0000 | 0.8182 |
| `water` | 11 | 0.9091 | 0.0000 | 0.9091 |

## Failure Reasons

`{'no_numeric_evidence': 5}`

## Guardrail

只有该审计通过，才说明 generated captions 至少不像单纯答案标签投机；最终方法结论仍需同时看 QA accuracy、qcond-vs-no-question gap 和人工/LLM 细审。
