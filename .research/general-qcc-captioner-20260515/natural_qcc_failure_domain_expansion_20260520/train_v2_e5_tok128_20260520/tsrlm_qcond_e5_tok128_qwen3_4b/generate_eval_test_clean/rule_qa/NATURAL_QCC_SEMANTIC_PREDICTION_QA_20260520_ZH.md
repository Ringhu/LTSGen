# Natural QCC Semantic Prediction QA（2026-05-20）

本报告使用 deterministic semantic bridge 评估自然 evidence caption。它只作为 strict label bridge 的诊断补充，不改变 gold answer。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/train_v2_e5_tok128_20260520/tsrlm_qcond_e5_tok128_qwen3_4b/generate_eval_test_clean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl`
- caption field: `pred_caption`
- rows: `35`
- accuracy: `0.3143`
- empty answer rate: `0.4000`

## By Source

| source | n | accuracy |
| --- | ---: | ---: |
| `aiopslab_official_v3` | 5 | 0.0000 |
| `citylearn` | 2 | 0.5000 |
| `grid2op` | 10 | 0.3000 |
| `traffic` | 12 | 0.3333 |
| `water` | 6 | 0.5000 |

## Reason Distribution

`{'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}\\bsecond[- ]half\\b.*\\bhigher\\b': 1, 'ambiguous_label_list': 7, 'no_semantic_match': 7, 'semantic_plain_pattern:upward': 1, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}upward': 2, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}no\\ pronounced\\ spike': 1, 'semantic_numeric_first_half_higher': 2, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}there\\ is\\ no\\ clear\\ event\\ response': 2, 'semantic_numeric_zero_gap': 2, 'semantic_plain_pattern:late': 2, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}average\\ stress\\ is\\ higher\\ after\\ the\\ intervention': 1, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}there\\ is\\ no\\ stable\\ timing\\ lead': 2, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}moderate\\ congestion': 1, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}severe\\ congestion': 1, 'semantic_plain_pattern:early': 2, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}speed\\ is\\ more\\ strongly\\ coupled\\ with\\ occupancy\\ context': 1}`
