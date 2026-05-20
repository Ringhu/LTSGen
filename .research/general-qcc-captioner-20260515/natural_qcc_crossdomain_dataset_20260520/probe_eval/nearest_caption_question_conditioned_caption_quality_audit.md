# Natural QCC Caption Quality Audit（2026-05-20）

本审计检查 generated caption 是否具有基本 evidence-caption 形态。它不替代 downstream QA accuracy；QA 答对但只输出答案标签时，本审计会把它标为低质量 caption。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/probe_eval/nearest_caption_question_conditioned_predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- caption field: `caption`
- rows: `13`
- quality gate pass: `False`
- evidence shape rate: `0.7692`
- numeric evidence rate: `0.7692`
- answer-label-only rate: `0.0000`

## By Source

| source | n | evidence shaped | answer-label-only | numeric evidence |
| --- | ---: | ---: | ---: | ---: |
| `aiopslab_official_v3` | 5 | 1.0000 | 0.0000 | 1.0000 |
| `citylearn` | 2 | 1.0000 | 0.0000 | 1.0000 |
| `grid2op` | 2 | 0.5000 | 0.0000 | 0.5000 |
| `traffic` | 3 | 0.3333 | 0.0000 | 0.3333 |
| `water` | 1 | 1.0000 | 0.0000 | 1.0000 |

## Failure Reasons

`{'no_numeric_evidence': 3}`

## Guardrail

只有该审计通过，才说明 generated captions 至少不像单纯答案标签投机；最终方法结论仍需同时看 QA accuracy、qcond-vs-no-question gap 和人工/LLM 细审。
