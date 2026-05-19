# Natural QCC Expansion Dataset（2026-05-19）

本目录把 GPT-5.5 reviewer gate 通过的扩展 natural TS-QA 样本转成 MultiSim/QCC 兼容数据和 split-specific SFT 资产。

## 输入输出

- natural rewrites: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/natural_qcc_crossdomain_rewrites.jsonl`
- reviewer JSON: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/natural_qcc_crossdomain_rewrites_review.json`
- raw candidate JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_candidates_20260520/natural_qcc_crossdomain_candidates.jsonl`
- positive JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- excluded JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_excluded.jsonl`
- schema report: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_dataset_summary.json`

## Positive Summary

- positive rows: `33`
- excluded rows: `27`
- by source: `{'aiopslab_official_v3': 12, 'citylearn': 7, 'grid2op': 6, 'traffic': 4, 'water': 4}`
- by split: `{'dev': 6, 'test': 9, 'train': 18}`
- by value dim: `{'4': 12, '3': 21}`
- answer distribution: `{'B': 11, 'D': 8, 'A': 9, 'C': 5}`
- max answer share: `0.3333`
- schema gate pass: `True`

## SFT Files

| split | rows | raw | sft |
| --- | ---: | --- | --- |
| `dev` | 6 | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft/natural_qcc_crossdomain_dev_raw.jsonl` | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft/natural_qcc_crossdomain_dev_sft.jsonl` |
| `test` | 9 | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft/natural_qcc_crossdomain_test_raw.jsonl` | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft/natural_qcc_crossdomain_test_sft.jsonl` |
| `train` | 18 | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft/natural_qcc_crossdomain_train_raw.jsonl` | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft/natural_qcc_crossdomain_train_sft.jsonl` |

## 下一步

1. 对 positive JSONL 跑 `scripts/eval/run_natural_qcc_probe.py --data ...`，重做 `question_only/generic/statistical/natural_oracle` baseline。
2. 用 `sft/*_sft.jsonl` 在 A100/3090 上跑 TS-RLM/Qwen caption SFT。
3. 对 trained captioner 的 generated captions 跑 `scripts/eval/evaluate_natural_qcc_predictions.py`，再判断 QA 是否相比旧流程提升。
