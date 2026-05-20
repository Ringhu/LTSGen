# Natural QCC Semantic Prediction QA（2026-05-20）

本报告使用 deterministic semantic bridge 评估自然 evidence caption。它只作为 strict label bridge 的诊断补充，不改变 gold answer。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/token_budget_fix_diagnostics_20260520/qcond_overfit5_maxtext768_qwen3_4b/generate_eval_test_clean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl`
- caption field: `pred_caption`
- rows: `5`
- accuracy: `0.8000`
- empty answer rate: `0.0000`

## By Source

| source | n | accuracy |
| --- | ---: | ---: |
| `aiopslab_official_v3` | 5 | 0.8000 |

## Reason Distribution

`{'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}network\\ rx\\-tx\\ coupling': 2, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}early': 2, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}similar\\ halves': 1}`
