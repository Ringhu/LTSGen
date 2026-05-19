# Natural QCC Prediction QA（2026-05-19）

本报告把 generated evidence captions 转成下游 QA accuracy，用于训练后快速判断 natural QCC caption 是否真的支持答题。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/natural_qcc_probe_positive.jsonl`
- gold: `/tmp/ltsgen-question-repair-20260519/.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/natural_qcc_probe_positive.jsonl`
- caption field: `generic_caption`
- rows: `43`
- accuracy: `0.0233`
- empty answer rate: `0.8837`

## By Source

| source | n | accuracy | empty |
| --- | ---: | ---: | ---: |
| `aiopslab_official_v3` | 3 | 0.0000 | 1.0000 |
| `citylearn` | 8 | 0.0000 | 1.0000 |
| `finrl_scaled` | 8 | 0.0000 | 1.0000 |
| `grid2op` | 8 | 0.0000 | 1.0000 |
| `traffic` | 8 | 0.1250 | 0.6250 |
| `water` | 8 | 0.0000 | 0.7500 |

## Reason Distribution

`{'no_label_match': 38, 'option_label_text': 5}`
