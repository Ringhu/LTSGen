# Natural QCC Semantic Prediction QA（2026-05-20）

本报告使用 deterministic semantic bridge 评估自然 evidence caption。它只作为 strict label bridge 的诊断补充，不改变 gold answer。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/generate_eval_test_reclean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- caption field: `pred_caption`
- rows: `13`
- accuracy: `0.0000`
- empty answer rate: `0.9231`

## By Source

| source | n | accuracy |
| --- | ---: | ---: |
| `aiopslab_official_v3` | 5 | 0.0000 |
| `citylearn` | 2 | 0.0000 |
| `grid2op` | 2 | 0.0000 |
| `traffic` | 3 | 0.0000 |
| `water` | 1 | 0.0000 |

## Reason Distribution

`{'no_semantic_match': 11, 'ambiguous_label_list': 1, 'semantic_plain_pattern:\\bfirst[- ]half\\b.*\\bhigher\\b': 1}`
