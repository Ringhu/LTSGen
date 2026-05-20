# Natural QCC Semantic Prediction QA（2026-05-20）

本报告使用 deterministic semantic bridge 评估自然 evidence caption。它只作为 strict label bridge 的诊断补充，不改变 gold answer。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/sft_evidence_only/natural_qcc_failure_domain_expanded_evidence_only_test_sft.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/merged/natural_qcc_crossdomain_failure_expanded_positive.jsonl`
- caption field: `output`
- rows: `29`
- accuracy: `1.0000`
- empty answer rate: `0.0000`

## By Source

| source | n | accuracy |
| --- | ---: | ---: |
| `aiopslab_official_v3` | 5 | 1.0000 |
| `citylearn` | 2 | 1.0000 |
| `grid2op` | 10 | 1.0000 |
| `traffic` | 8 | 1.0000 |
| `water` | 4 | 1.0000 |

## Reason Distribution

`{'semantic_numeric_similar_halves': 1, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}early': 2, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}network\\ rx\\-tx\\ coupling': 1, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}flat': 2, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}no\\ pronounced\\ spike': 1, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}both\\ telemetry\\ pairs\\ reach\\ usable\\ coupling\\ and\\ are\\ similar': 1, 'semantic_numeric_second_half_higher': 1, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}middle': 2, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}speed\\ changes\\ more\\ strongly\\ during\\ the\\ event': 2, 'semantic_numeric_no_material_change': 1, 'semantic_gold_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}\\bevent-window mean speed is lower than baseline\\b': 1, 'semantic_numeric_moderate_combined_stress': 1, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}overload\\ exposure\\ is\\ greater\\ after\\ the\\ intervention': 1, 'semantic_plain_pattern:late': 1, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}late': 1, 'semantic_plain_pattern:early': 2, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}the\\ intervention\\ raises\\ the\\ stress': 1, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}average\\ stress\\ is\\ higher\\ after\\ the\\ intervention': 1, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}there\\ is\\ no\\ stable\\ timing\\ lead': 2, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}severe\\ congestion': 2, 'semantic_plain_pattern:upward': 1, 'semantic_numeric_zero_gap': 1}`
