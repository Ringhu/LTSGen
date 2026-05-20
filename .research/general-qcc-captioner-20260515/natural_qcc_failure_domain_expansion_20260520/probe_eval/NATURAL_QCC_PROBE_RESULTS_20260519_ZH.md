# Natural QCC Probe Results（2026-05-19）

本实验检查 reviewed natural QCC 数据是否能作为 evidence-caption/QA 接口运行。

## Data

- data: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/merged/natural_qcc_crossdomain_failure_expanded_positive.jsonl`
- rows: `104`
- by source: `{'aiopslab_official_v3': 12, 'citylearn': 9, 'grid2op': 31, 'traffic': 28, 'water': 24}`
- by split: `{'dev': 17, 'test': 29, 'train': 58}`
- train/eval probe split: `dev` -> `test` (`17` -> `29`)

## Baseline QA

| condition | n | accuracy | empty | mean chars |
| --- | ---: | ---: | ---: | ---: |
| `natural_oracle` | 104 | 1.0000 | 0.0000 | 218.7 |
| `natural_evidence_no_label` | 104 | 0.6346 | 0.1635 | 188.7 |
| `generic_caption` | 104 | 0.0192 | 0.8462 | 117.6 |
| `statistical_caption` | 104 | 0.0000 | 1.0000 | 141.8 |
| `question_only` | 104 | 0.0865 | 0.7500 | 103.2 |

## Trainable Caption Probe

| condition | train | eval | accuracy | empty |
| --- | ---: | ---: | ---: | ---: |
| `nearest_caption_question_conditioned` | 17 | 29 | 0.2069 | 0.5172 |
| `nearest_caption_no_question` | 17 | 29 | 0.1379 | 0.5862 |

## Interpretation

- `natural_oracle` 是上限检查：自然 evidence caption 被追加 exact answer label 后，应能被 rule-QA 稳定读取。
- `natural_evidence_no_label` 检查自然措辞本身是否已经包含评估器可识别的答案语义；如果低于 oracle，说明需要升级 QA evaluator 或统一自然 option label。
- `generic_caption` / `statistical_caption` / `question_only` 是接口对照。
- `nearest_caption_*` 是依赖 train split 的轻量 captioner 探针，不是最终 QCC 模型。`nearest_caption_question_conditioned` 高于 no-question (0.2069 vs 0.1379)，说明该弱探针中问题条件有增益。

## Caveats

- 该探针是最近邻 caption 诊断，不是 TS-RLM/Qwen 训练结果。
- 该探针验证的是数据接口和弱训练信号，不足以证明正式 QCC 训练收益。
- 若当前数据只覆盖单一 source 或少量重复场景，不能据此报告跨域方法收益。
- 下一步仍需要每域 50-100 条 reviewer-positive 样本，并在 GPU 上跑真正的 caption SFT 和 generated-caption QA。
