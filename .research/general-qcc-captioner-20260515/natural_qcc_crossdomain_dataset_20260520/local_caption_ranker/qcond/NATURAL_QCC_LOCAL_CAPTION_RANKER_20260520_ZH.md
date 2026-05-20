# Natural QCC Local Caption Ranker（2026-05-20）

本诊断在无 GPU / 无 torch 环境下训练一个轻量 option-ranker，并把预测选项写成 generated caption 后用同一 rule-QA 评估。它不是 TS-RLM/Qwen SFT，也不验证 evidence factuality，只用于判断 reviewed natural QCC 数据是否存在可训练的弱监督信号。

## Setup

- data: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- train split: `train` (`31` rows)
- eval split: `test` (`13` rows)
- epochs: `30`
- no_question: `False`
- use_task_feature: `False`

## QA Metrics

| condition | rows | accuracy | empty |
| --- | ---: | ---: | ---: |
| `local_ranker_train` | 31 | 0.9677 | 0.0000 |
| `local_ranker_eval` | 13 | 0.6154 | 0.0000 |

## Baseline Comparison

| baseline | accuracy |
| --- | ---: |
| `natural_oracle` | `1.0` |
| `generic_caption` | `0.0182` |
| `statistical_caption` | `0.0` |
| `question_only` | `0.1273` |
| `nearest_caption_question_conditioned` | `0.4615` |
| `nearest_caption_no_question` | `0.2308` |
| `local_ranker_eval` | `0.6154` |

## Interpretation

- local ranker vs question-only: `0.6154` vs `0.1273`.
- 该结果只能作为本地弱训练诊断；正式结论仍需要 GPU 上的 TS-RLM/Qwen caption SFT、generated captions 和审计通过。
