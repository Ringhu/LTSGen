# Natural QCC Caption Quality Audit（2026-05-20）

本审计检查 generated caption 是否具有基本 evidence-caption 形态。它不替代 downstream QA accuracy；QA 答对但只输出答案标签时，本审计会把它标为低质量 caption。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520/generate_eval_test_reclean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- caption field: `pred_caption`
- rows: `13`
- quality gate pass: `False`
- evidence shape rate: `0.6154`
- numeric evidence rate: `1.0000`
- answer-label-only rate: `0.0000`

## By Source

| source | n | evidence shaped | answer-label-only | numeric evidence |
| --- | ---: | ---: | ---: | ---: |
| `aiopslab_official_v3` | 5 | 0.0000 | 0.0000 | 1.0000 |
| `citylearn` | 2 | 1.0000 | 0.0000 | 1.0000 |
| `grid2op` | 2 | 1.0000 | 0.0000 | 1.0000 |
| `traffic` | 3 | 1.0000 | 0.0000 | 1.0000 |
| `water` | 1 | 1.0000 | 0.0000 | 1.0000 |

## Failure Reasons

`{'too_short': 5}`

## Guardrail

只有该审计通过，才说明 generated captions 至少不像单纯答案标签投机；最终方法结论仍需同时看 QA accuracy、qcond-vs-no-question gap 和人工/LLM 细审。
