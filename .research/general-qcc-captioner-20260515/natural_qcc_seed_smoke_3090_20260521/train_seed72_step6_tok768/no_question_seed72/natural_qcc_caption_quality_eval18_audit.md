# Natural QCC Caption Quality Audit（2026-05-20）

本审计检查 generated caption 是否具有基本 evidence-caption 形态。它不替代 downstream QA accuracy；QA 答对但只输出答案标签时，本审计会把它标为低质量 caption。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_seed_smoke_3090_20260521/train_seed72_step6_tok768/no_question_seed72/generate_eval18_clean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_seed_smoke_3090_20260521/gpu_bundle/seed_gold_smoke_eval18.jsonl`
- caption field: `pred_caption`
- rows: `18`
- quality gate pass: `False`
- evidence shape rate: `0.3333`
- numeric evidence rate: `0.6667`
- answer-label-only rate: `0.3333`

## By Source

| source | n | evidence shaped | answer-label-only | numeric evidence |
| --- | ---: | ---: | ---: | ---: |
| `aiopslab` | 3 | 0.0000 | 1.0000 | 0.0000 |
| `citylearn` | 3 | 1.0000 | 0.0000 | 1.0000 |
| `finrl` | 3 | 0.0000 | 0.0000 | 1.0000 |
| `grid2op` | 3 | 0.0000 | 1.0000 | 0.0000 |
| `traffic` | 3 | 0.0000 | 0.0000 | 1.0000 |
| `water` | 3 | 1.0000 | 0.0000 | 1.0000 |

## Failure Reasons

`{'answer_label_only': 6, 'no_numeric_evidence': 6, 'too_short': 12}`

## Guardrail

只有该审计通过，才说明 generated captions 至少不像单纯答案标签投机；最终方法结论仍需同时看 QA accuracy、qcond-vs-no-question gap 和人工/LLM 细审。
