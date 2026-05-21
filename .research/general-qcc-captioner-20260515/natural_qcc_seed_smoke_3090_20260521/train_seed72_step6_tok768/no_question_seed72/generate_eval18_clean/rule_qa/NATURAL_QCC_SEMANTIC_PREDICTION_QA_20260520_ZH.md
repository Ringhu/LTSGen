# Natural QCC Semantic Prediction QA（2026-05-20）

本报告使用 deterministic semantic bridge 评估自然 evidence caption。它只作为 strict label bridge 的诊断补充，不改变 gold answer。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_seed_smoke_3090_20260521/train_seed72_step6_tok768/no_question_seed72/generate_eval18_clean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_seed_smoke_3090_20260521/gpu_bundle/seed_gold_smoke_eval18.jsonl`
- caption field: `pred_caption`
- rows: `18`
- accuracy: `0.0000`
- empty answer rate: `1.0000`

## By Source

| source | n | accuracy |
| --- | ---: | ---: |
| `aiopslab` | 3 | 0.0000 |
| `citylearn` | 3 | 0.0000 |
| `finrl` | 3 | 0.0000 |
| `grid2op` | 3 | 0.0000 |
| `traffic` | 3 | 0.0000 |
| `water` | 3 | 0.0000 |

## Reason Distribution

`{'no_semantic_match': 18}`
