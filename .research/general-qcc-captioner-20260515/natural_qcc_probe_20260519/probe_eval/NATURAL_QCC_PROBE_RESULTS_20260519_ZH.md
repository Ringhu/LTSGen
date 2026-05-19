# Natural QCC Probe Results（2026-05-19）

本实验是 reviewed natural balanced8 的首轮闭环验证：检查新构造的数据是否能作为 QCC evidence-caption/QA 接口运行。

## Baseline QA

| condition | n | accuracy | empty | mean chars |
| --- | ---: | ---: | ---: | ---: |
| `natural_oracle` | 43 | 1.0000 | 0.0000 | 180.4 |
| `natural_evidence_no_label` | 43 | 0.6279 | 0.3023 | 152.4 |
| `generic_caption` | 43 | 0.0233 | 0.8837 | 114.8 |
| `statistical_caption` | 43 | 0.0465 | 0.9535 | 204.9 |
| `question_only` | 43 | 0.0000 | 0.8605 | 93.3 |

## Trainable Caption Probe

| condition | train | eval | accuracy | empty |
| --- | ---: | ---: | ---: | ---: |
| `nearest_caption_question_conditioned` | 19 | 24 | 0.1250 | 0.7500 |
| `nearest_caption_no_question` | 19 | 24 | 0.1250 | 0.7500 |

## Interpretation

- `natural_oracle` 是上限检查：自然 evidence caption 被追加 exact answer label 后，应能被 rule-QA 稳定读取。
- `natural_evidence_no_label` 检查自然措辞本身是否已经包含评估器可识别的答案语义；如果低于 oracle，说明需要升级 QA evaluator 或统一自然 option label。
- `generic_caption` / `statistical_caption` / `question_only` 是接口对照。
- `nearest_caption_*` 是依赖 train split 的轻量 captioner 探针，不是最终 QCC 模型。当前 balanced8 没有 train split，只能做 dev->test 小样本 sanity check。

## Caveats

- 样本只有 43 条 reviewer-positive，且 split 不均衡；AIOpsLab 正例只有 test，没有 dev 训练样本。
- 该探针验证的是数据接口和弱训练信号，不足以证明正式 QCC 训练收益。
- 下一步需要每域 50-100 条 reviewer-positive 样本，形成 train/dev/test 后再跑 TSLLM/Qwen caption SFT。
