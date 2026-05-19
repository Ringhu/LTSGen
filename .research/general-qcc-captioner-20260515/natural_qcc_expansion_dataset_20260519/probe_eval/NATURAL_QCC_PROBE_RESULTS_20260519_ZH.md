# Natural QCC Probe Results（2026-05-19）

本实验检查 reviewed natural QCC 数据是否能作为 evidence-caption/QA 接口运行。

## Data

- data: `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/natural_qcc_expansion_positive.jsonl`
- rows: `25`
- by source: `{'aiopslab_official_v3': 25}`
- by split: `{'dev': 5, 'test': 10, 'train': 10}`
- train/eval probe split: `train` -> `test` (`10` -> `10`)

## Baseline QA

| condition | n | accuracy | empty | mean chars |
| --- | ---: | ---: | ---: | ---: |
| `natural_oracle` | 25 | 1.0000 | 0.0000 | 193.8 |
| `natural_evidence_no_label` | 25 | 0.6000 | 0.2000 | 167.4 |
| `generic_caption` | 25 | 0.0000 | 1.0000 | 126.0 |
| `statistical_caption` | 25 | 0.0000 | 1.0000 | 311.6 |
| `question_only` | 25 | 0.2000 | 0.6000 | 117.8 |

## Trainable Caption Probe

| condition | train | eval | accuracy | empty |
| --- | ---: | ---: | ---: | ---: |
| `nearest_caption_question_conditioned` | 10 | 10 | 1.0000 | 0.0000 |
| `nearest_caption_no_question` | 10 | 10 | 1.0000 | 0.0000 |

## Interpretation

- `natural_oracle` 是上限检查：自然 evidence caption 被追加 exact answer label 后，应能被 rule-QA 稳定读取。
- `natural_evidence_no_label` 检查自然措辞本身是否已经包含评估器可识别的答案语义；如果低于 oracle，说明需要升级 QA evaluator 或统一自然 option label。
- `generic_caption` / `statistical_caption` / `question_only` 是接口对照。
- `nearest_caption_*` 是依赖 train split 的轻量 captioner 探针，不是最终 QCC 模型。`nearest_caption_question_conditioned` 与 no-question 持平 (1.0000)；这通常表示当前子集可由 source/task/数值近邻记忆解决，不能作为 QCC 问题条件收益证据。

## Caveats

- 该探针是最近邻 caption 诊断，不是 TS-RLM/Qwen 训练结果。
- 该探针验证的是数据接口和弱训练信号，不足以证明正式 QCC 训练收益。
- 若当前数据只覆盖单一 source 或少量重复场景，不能据此报告跨域方法收益。
- 下一步仍需要每域 50-100 条 reviewer-positive 样本，并在 GPU 上跑真正的 caption SFT 和 generated-caption QA。
