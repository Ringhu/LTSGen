# Natural QCC Expansion Dataset（2026-05-19）

本目录把 GPT-5.5 reviewer gate 通过的扩展 natural TS-QA 样本转成 MultiSim/QCC 兼容数据和 split-specific SFT 资产。

## 输入输出

- natural rewrites: `.research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites.jsonl`
- reviewer JSON: `.research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites_review.json`
- raw candidate JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates.jsonl`
- positive JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/natural_qcc_expansion_positive.jsonl`
- excluded JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/natural_qcc_expansion_excluded.jsonl`
- schema report: `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/natural_qcc_expansion_dataset_summary.json`

## Positive Summary

- positive rows: `25`
- excluded rows: `0`
- by source: `{'aiopslab_official_v3': 25}`
- by split: `{'dev': 5, 'test': 10, 'train': 10}`
- by value dim: `{'4': 25}`
- answer distribution: `{'B': 6, 'D': 9, 'C': 6, 'A': 4}`
- max answer share: `0.36`
- schema gate pass: `True`

## SFT Files

| split | rows | raw | sft |
| --- | ---: | --- | --- |
| `dev` | 5 | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/sft/natural_qcc_expansion_dev_raw.jsonl` | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/sft/natural_qcc_expansion_dev_sft.jsonl` |
| `test` | 10 | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/sft/natural_qcc_expansion_test_raw.jsonl` | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/sft/natural_qcc_expansion_test_sft.jsonl` |
| `train` | 10 | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/sft/natural_qcc_expansion_train_raw.jsonl` | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/sft/natural_qcc_expansion_train_sft.jsonl` |

## 下一步

1. 对 positive JSONL 跑 `scripts/eval/run_natural_qcc_probe.py --data ...`，重做 `question_only/generic/statistical/natural_oracle` baseline。
2. 用 `sft/*_sft.jsonl` 在 A100/3090 上跑 TS-RLM/Qwen caption SFT。
3. 对 trained captioner 的 generated captions 跑 `scripts/eval/evaluate_natural_qcc_predictions.py`，再判断 QA 是否相比旧流程提升。
