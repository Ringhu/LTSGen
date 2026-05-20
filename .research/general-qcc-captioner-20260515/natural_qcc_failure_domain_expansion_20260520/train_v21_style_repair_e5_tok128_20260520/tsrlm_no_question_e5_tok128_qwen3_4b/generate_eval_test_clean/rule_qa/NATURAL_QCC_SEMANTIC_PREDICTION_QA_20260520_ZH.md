# Natural QCC Semantic Prediction QA（2026-05-20）

本报告使用 deterministic semantic bridge 评估自然 evidence caption。它只作为 strict label bridge 的诊断补充，不改变 gold answer。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/train_v21_style_repair_e5_tok128_20260520/tsrlm_no_question_e5_tok128_qwen3_4b/generate_eval_test_clean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl`
- caption field: `pred_caption`
- rows: `35`
- accuracy: `0.1143`
- empty answer rate: `0.6571`

## By Source

| source | n | accuracy |
| --- | ---: | ---: |
| `aiopslab_official_v3` | 5 | 0.2000 |
| `citylearn` | 2 | 0.0000 |
| `grid2op` | 10 | 0.2000 |
| `traffic` | 12 | 0.0833 |
| `water` | 6 | 0.0000 |

## Reason Distribution

`{'no_semantic_match': 23, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}network\\ rx\\-tx\\ coupling': 1, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}late': 9, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}early': 2}`
