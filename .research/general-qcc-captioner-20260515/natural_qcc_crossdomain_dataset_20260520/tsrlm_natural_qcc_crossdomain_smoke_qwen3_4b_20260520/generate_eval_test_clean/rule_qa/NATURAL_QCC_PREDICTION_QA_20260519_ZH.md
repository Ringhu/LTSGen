# Natural QCC Prediction QA（2026-05-19）

本报告把 generated evidence captions 转成下游 QA accuracy，用于训练后快速判断 natural QCC caption 是否真的支持答题。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/generate_eval_test_clean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- caption field: `pred_caption`
- rows: `13`
- accuracy: `0.0000`
- empty answer rate: `1.0000`

## By Source

| source | n | accuracy | empty |
| --- | ---: | ---: | ---: |
| `aiopslab_official_v3` | 5 | 0.0000 | 1.0000 |
| `citylearn` | 2 | 0.0000 | 1.0000 |
| `grid2op` | 2 | 0.0000 | 1.0000 |
| `traffic` | 3 | 0.0000 | 1.0000 |
| `water` | 1 | 0.0000 | 1.0000 |

## Reason Distribution

`{'no_label_match': 13}`
