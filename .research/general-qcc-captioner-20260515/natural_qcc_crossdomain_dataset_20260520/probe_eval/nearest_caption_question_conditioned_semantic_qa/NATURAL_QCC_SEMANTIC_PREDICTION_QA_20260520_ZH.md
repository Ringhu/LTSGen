# Natural QCC Semantic Prediction QA（2026-05-20）

本报告使用 deterministic semantic bridge 评估自然 evidence caption。它只作为 strict label bridge 的诊断补充，不改变 gold answer。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/probe_eval/nearest_caption_question_conditioned_predictions.jsonl`
- gold: `/tmp/ltsgen-question-repair-20260519/.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- caption field: `caption`
- rows: `13`
- accuracy: `0.4615`
- empty answer rate: `0.3077`

## By Source

| source | n | accuracy |
| --- | ---: | ---: |
| `aiopslab_official_v3` | 5 | 1.0000 |
| `citylearn` | 2 | 0.5000 |
| `grid2op` | 2 | 0.0000 |
| `traffic` | 3 | 0.0000 |
| `water` | 1 | 0.0000 |

## Reason Distribution

`{'explicit_answer_label': 8, 'semantic_context_pattern:(?:\\b(?:supporting|supports|indicating|indicates|therefore|so|falls\\s+in|places)\\b|\\bthis\\s+supports\\b)[^.\\n]{0,120}neither\\ telemetry\\ pair\\ reaches\\ usable\\ coupling': 1, 'no_semantic_match': 4}`
