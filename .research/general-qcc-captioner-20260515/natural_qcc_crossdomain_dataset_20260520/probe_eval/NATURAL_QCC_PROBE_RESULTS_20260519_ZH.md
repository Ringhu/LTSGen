# Natural QCC Probe Results（2026-05-19）

本实验检查 reviewed natural QCC 数据是否能作为 evidence-caption/QA 接口运行。

## Data

- data: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- rows: `55`
- by source: `{'aiopslab_official_v3': 12, 'citylearn': 9, 'grid2op': 12, 'traffic': 11, 'water': 11}`
- by split: `{'dev': 11, 'test': 13, 'train': 31}`
- train/eval probe split: `train` -> `test` (`31` -> `13`)

## Baseline QA

| condition | n | accuracy | empty | mean chars |
| --- | ---: | ---: | ---: | ---: |
| `natural_oracle` | 55 | 1.0000 | 0.0000 | 222.5 |
| `natural_evidence_no_label` | 55 | 0.6545 | 0.1636 | 192.7 |
| `generic_caption` | 55 | 0.0182 | 0.8909 | 118.7 |
| `statistical_caption` | 55 | 0.0000 | 1.0000 | 152.8 |
| `question_only` | 55 | 0.1273 | 0.7091 | 105.6 |

## Trainable Caption Probe

| condition | train | eval | accuracy | empty |
| --- | ---: | ---: | ---: | ---: |
| `nearest_caption_question_conditioned` | 31 | 13 | 0.4615 | 0.3846 |
| `nearest_caption_no_question` | 31 | 13 | 0.2308 | 0.6154 |

## Interpretation

- `natural_oracle` 是上限检查：自然 evidence caption 被追加 exact answer label 后，应能被 rule-QA 稳定读取。
- `natural_evidence_no_label` 检查自然措辞本身是否已经包含评估器可识别的答案语义；如果低于 oracle，说明需要升级 QA evaluator 或统一自然 option label。
- `generic_caption` / `statistical_caption` / `question_only` 是接口对照。
- `nearest_caption_*` 是依赖 train split 的轻量 captioner 探针，不是最终 QCC 模型。`nearest_caption_question_conditioned` 高于 no-question (0.4615 vs 0.2308)，说明该弱探针中问题条件有增益。

## Caveats

- 该探针是最近邻 caption 诊断，不是 TS-RLM/Qwen 训练结果。
- 该探针验证的是数据接口和弱训练信号，不足以证明正式 QCC 训练收益。
- 若当前数据只覆盖单一 source 或少量重复场景，不能据此报告跨域方法收益。
- 下一步仍需要每域 50-100 条 reviewer-positive 样本，并在 GPU 上跑真正的 caption SFT 和 generated-caption QA。
