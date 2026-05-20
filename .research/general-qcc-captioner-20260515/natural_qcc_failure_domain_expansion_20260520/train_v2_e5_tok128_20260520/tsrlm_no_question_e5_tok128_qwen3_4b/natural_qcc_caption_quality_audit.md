# Natural QCC Caption Quality Audit（2026-05-20）

本审计检查 generated caption 是否具有基本 evidence-caption 形态。它不替代 downstream QA accuracy；QA 答对但只输出答案标签时，本审计会把它标为低质量 caption。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/train_v2_e5_tok128_20260520/tsrlm_no_question_e5_tok128_qwen3_4b/generate_eval_test_clean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl`
- caption field: `pred_caption`
- rows: `35`
- quality gate pass: `False`
- evidence shape rate: `0.3429`
- numeric evidence rate: `0.3429`
- answer-label-only rate: `0.3143`

## By Source

| source | n | evidence shaped | answer-label-only | numeric evidence |
| --- | ---: | ---: | ---: | ---: |
| `aiopslab_official_v3` | 5 | 1.0000 | 0.0000 | 1.0000 |
| `citylearn` | 2 | 1.0000 | 0.0000 | 1.0000 |
| `grid2op` | 10 | 0.4000 | 0.6000 | 0.4000 |
| `traffic` | 12 | 0.0000 | 0.0000 | 0.0000 |
| `water` | 6 | 0.1667 | 0.8333 | 0.1667 |

## Failure Reasons

`{'answer_label_only': 11, 'no_numeric_evidence': 23, 'too_short': 11}`

## Guardrail

只有该审计通过，才说明 generated captions 至少不像单纯答案标签投机；最终方法结论仍需同时看 QA accuracy、qcond-vs-no-question gap 和人工/LLM 细审。
