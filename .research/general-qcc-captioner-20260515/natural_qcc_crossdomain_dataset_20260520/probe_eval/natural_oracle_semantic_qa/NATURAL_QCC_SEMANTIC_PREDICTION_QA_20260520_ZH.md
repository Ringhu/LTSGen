# Natural QCC Semantic Prediction QA（2026-05-20）

本报告使用 deterministic semantic bridge 评估自然 evidence caption。它只作为 strict label bridge 的诊断补充，不改变 gold answer。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/probe_eval/natural_oracle_predictions.jsonl`
- gold: `/tmp/ltsgen-question-repair-20260519/.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- caption field: `caption`
- rows: `55`
- accuracy: `1.0000`
- empty answer rate: `0.0000`

## By Source

| source | n | accuracy |
| --- | ---: | ---: |
| `aiopslab_official_v3` | 12 | 1.0000 |
| `citylearn` | 9 | 1.0000 |
| `grid2op` | 12 | 1.0000 |
| `traffic` | 11 | 1.0000 |
| `water` | 11 | 1.0000 |

## Reason Distribution

`{'explicit_gold_answer_label': 16, 'explicit_answer_label': 39}`
