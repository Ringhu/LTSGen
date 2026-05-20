# Natural QCC Semantic Prediction QA（2026-05-20）

本报告使用 deterministic semantic bridge 评估自然 evidence caption。它只作为 strict label bridge 的诊断补充，不改变 gold answer。

- predictions: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/train_v22_e5_tok128_20260520/tsrlm_qcond_e5_tok128_qwen3_4b/generate_eval_test_clean/predictions.jsonl`
- gold: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl`
- caption field: `pred_caption`
- rows: `35`
- accuracy: `0.0000`
- empty answer rate: `1.0000`

## By Source

| source | n | accuracy |
| --- | ---: | ---: |
| `aiopslab_official_v3` | 5 | 0.0000 |
| `citylearn` | 2 | 0.0000 |
| `grid2op` | 10 | 0.0000 |
| `traffic` | 12 | 0.0000 |
| `water` | 6 | 0.0000 |

## Reason Distribution

`{'no_semantic_match': 35}`
