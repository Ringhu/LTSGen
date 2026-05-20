# Natural QCC Expansion Dataset（2026-05-19）

本目录把 GPT-5.5 reviewer gate 通过的扩展 natural TS-QA 样本转成 MultiSim/QCC 兼容数据和 split-specific SFT 资产。

## 输入输出

- natural rewrites: `.research/natural-tsqa-benchmark-20260520/rewrites20_including_seed_assets/natural_tsqa_rewrites20_including_seed_assets.jsonl`
- reviewer JSON: `.research/natural-tsqa-benchmark-20260520/reviews20_including_seed_assets/natural_tsqa_rewrites20_including_seed_assets_review.json`
- raw candidate JSONL: `.research/natural-tsqa-benchmark-20260520/candidates20_including_seed_assets/natural_tsqa_candidates20_including_seed_assets.jsonl`
- positive JSONL: `.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/natural_tsqa_candidates20_reviewed_positive.jsonl`
- excluded JSONL: `.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/natural_tsqa_candidates20_reviewed_excluded.jsonl`
- schema report: `.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/natural_tsqa_candidates20_reviewed_dataset_summary.json`

## Positive Summary

- positive rows: `75`
- excluded rows: `25`
- by source: `{'aiopslab_official_v3': 20, 'citylearn': 16, 'grid2op': 16, 'traffic': 13, 'water': 10}`
- by split: `{'dev': 11, 'test': 26, 'train': 38}`
- by value dim: `{'4': 20, '3': 55}`
- answer distribution: `{'D': 22, 'C': 20, 'A': 13, 'B': 20}`
- max answer share: `0.2933`
- schema gate pass: `True`

## SFT Files

| split | rows | raw | sft |
| --- | ---: | --- | --- |
| `dev` | 11 | `.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/sft/natural_tsqa_candidates20_reviewed_dev_raw.jsonl` | `.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/sft/natural_tsqa_candidates20_reviewed_dev_sft.jsonl` |
| `test` | 26 | `.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/sft/natural_tsqa_candidates20_reviewed_test_raw.jsonl` | `.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/sft/natural_tsqa_candidates20_reviewed_test_sft.jsonl` |
| `train` | 38 | `.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/sft/natural_tsqa_candidates20_reviewed_train_raw.jsonl` | `.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/sft/natural_tsqa_candidates20_reviewed_train_sft.jsonl` |

## 下一步

1. 对 positive JSONL 跑 `scripts/eval/run_natural_qcc_probe.py --data ...`，重做 `question_only/generic/statistical/natural_oracle` baseline。
2. 用 `sft/*_sft.jsonl` 在 A100/3090 上跑 TS-RLM/Qwen caption SFT。
3. 对 trained captioner 的 generated captions 跑 `scripts/eval/evaluate_natural_qcc_predictions.py`，再判断 QA 是否相比旧流程提升。
