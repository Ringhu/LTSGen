# Natural QCC Prediction QA（2026-05-19）

本报告把 generated evidence captions 转成下游 QA accuracy，用于训练后快速判断 natural QCC caption 是否真的支持答题。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/local_caption_ranker/qcond/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- caption field: `pred_caption`
- rows: `13`
- accuracy: `0.6154`
- empty answer rate: `0.0000`

## By Source

| source | n | accuracy | empty |
| --- | ---: | ---: | ---: |
| `aiopslab_official_v3` | 5 | 1.0000 | 0.0000 |
| `citylearn` | 2 | 0.5000 | 0.0000 |
| `grid2op` | 2 | 0.0000 | 0.0000 |
| `traffic` | 3 | 0.6667 | 0.0000 |
| `water` | 1 | 0.0000 | 0.0000 |

## Reason Distribution

`{'explicit_answer_label': 13}`
