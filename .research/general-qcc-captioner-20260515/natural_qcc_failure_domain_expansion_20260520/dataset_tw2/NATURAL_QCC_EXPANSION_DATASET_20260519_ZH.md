# Natural QCC Expansion Dataset（2026-05-19）

本目录把 GPT-5.5 reviewer gate 通过的扩展 natural TS-QA 样本转成 MultiSim/QCC 兼容数据和 split-specific SFT 资产。

## 输入输出

- natural rewrites: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/rewrites_tw2/natural_qcc_failure_domain_tw2_rewrites.jsonl`
- reviewer JSON: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/rewrites_tw2/natural_qcc_failure_domain_tw2_rewrites_review.json`
- raw candidate JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/candidates_tw2/natural_qcc_failure_domain_tw2_candidates.jsonl`
- positive JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/dataset_tw2/natural_qcc_failure_domain_tw2_expansion_positive.jsonl`
- excluded JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/dataset_tw2/natural_qcc_failure_domain_tw2_expansion_excluded.jsonl`
- schema report: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/dataset_tw2/natural_qcc_failure_domain_tw2_expansion_dataset_summary.json`

## Positive Summary

- positive rows: `20`
- excluded rows: `12`
- by source: `{'traffic': 13, 'water': 7}`
- by split: `{'dev': 3, 'test': 6, 'train': 11}`
- by value dim: `{'3': 20}`
- answer distribution: `{'A': 7, 'D': 6, 'C': 3, 'B': 4}`
- max answer share: `0.35`
- schema gate pass: `True`

## SFT Files

| split | rows | raw | sft |
| --- | ---: | --- | --- |
| `dev` | 3 | `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/dataset_tw2/sft/natural_qcc_failure_domain_tw2_expansion_dev_raw.jsonl` | `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/dataset_tw2/sft/natural_qcc_failure_domain_tw2_expansion_dev_sft.jsonl` |
| `test` | 6 | `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/dataset_tw2/sft/natural_qcc_failure_domain_tw2_expansion_test_raw.jsonl` | `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/dataset_tw2/sft/natural_qcc_failure_domain_tw2_expansion_test_sft.jsonl` |
| `train` | 11 | `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/dataset_tw2/sft/natural_qcc_failure_domain_tw2_expansion_train_raw.jsonl` | `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/dataset_tw2/sft/natural_qcc_failure_domain_tw2_expansion_train_sft.jsonl` |

## 下一步

1. 对 positive JSONL 跑 `scripts/eval/run_natural_qcc_probe.py --data ...`，重做 `question_only/generic/statistical/natural_oracle` baseline。
2. 用 `sft/*_sft.jsonl` 在 A100/3090 上跑 TS-RLM/Qwen caption SFT。
3. 对 trained captioner 的 generated captions 跑 `scripts/eval/evaluate_natural_qcc_predictions.py`，再判断 QA 是否相比旧流程提升。
