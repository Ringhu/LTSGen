# Natural QCC Probe Results（2026-05-19）

本实验检查 reviewed natural QCC 数据是否能作为 evidence-caption/QA 接口运行。

## Data

- data: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl`
- rows: `124`
- by source: `{'aiopslab_official_v3': 12, 'citylearn': 9, 'grid2op': 31, 'traffic': 41, 'water': 31}`
- by split: `{'dev': 20, 'test': 35, 'train': 69}`
- train/eval probe split: `dev` -> `test` (`20` -> `35`)

## Baseline QA

| condition | n | accuracy | empty | mean chars |
| --- | ---: | ---: | ---: | ---: |
| `natural_oracle` | 124 | 1.0000 | 0.0000 | 218.2 |
| `natural_evidence_no_label` | 124 | 0.5968 | 0.1855 | 187.8 |
| `generic_caption` | 124 | 0.0323 | 0.8226 | 115.0 |
| `statistical_caption` | 124 | 0.0000 | 1.0000 | 152.8 |
| `question_only` | 124 | 0.0726 | 0.7581 | 101.9 |

## Trainable Caption Probe

| condition | train | eval | accuracy | empty |
| --- | ---: | ---: | ---: | ---: |
| `nearest_caption_question_conditioned` | 20 | 35 | 0.2286 | 0.4571 |
| `nearest_caption_no_question` | 20 | 35 | 0.1714 | 0.5143 |

## Interpretation

- `natural_oracle` 是上限检查：自然 evidence caption 被追加 exact answer label 后，应能被 rule-QA 稳定读取。
- `natural_evidence_no_label` 检查自然措辞本身是否已经包含评估器可识别的答案语义；如果低于 oracle，说明需要升级 QA evaluator 或统一自然 option label。
- `generic_caption` / `statistical_caption` / `question_only` 是接口对照。
- `nearest_caption_*` 是依赖 train split 的轻量 captioner 探针，不是最终 QCC 模型。`nearest_caption_question_conditioned` 高于 no-question (0.2286 vs 0.1714)，说明该弱探针中问题条件有增益。

## Caveats

- 该探针是最近邻 caption 诊断，不是 TS-RLM/Qwen 训练结果。
- 该探针验证的是数据接口和弱训练信号，不足以证明正式 QCC 训练收益。
- 若当前数据只覆盖单一 source 或少量重复场景，不能据此报告跨域方法收益。
- 下一步仍需要每域 50-100 条 reviewer-positive 样本，并在 GPU 上跑真正的 caption SFT 和 generated-caption QA。
