# Natural QCC v2.2 Numeric Grounding Repair 报告（2026-05-20）

## 结论

这一轮完成的是 **numeric grounding 修复的第一步**：把上一轮“看起来像证据但数字经常错”的问题，变成了一个可自动审计的 gate，并产出 v2.2 修复版 SFT 数据资产。

核心结论很直接：

- v2.1 target 本身是干净的：slot factuality 为 `1.0000`。
- v2.1 训练后生成 caption 的 grounding 很差：qcond overall slot factuality 只有 `0.1143`，Grid2Op 为 `0.0000`。
- v2.2 target 已修成更强的数值 grounding 格式：caption quality、semantic QA、slot factuality 三个 target gate 都是 `1.0000`。

这说明当前主要问题不是“问题是否自然”，也不是“target 是否能答题”，而是模型生成时没有稳定把当前 trace 的数值、窗口长度和方向复制到 evidence caption 里。

## 修了什么

### 1. 新增 slot factuality 审计

新增脚本：

`scripts/eval/audit_natural_qcc_slot_factuality.py`

它检查三类事实：

- **slot value**：caption 里写出的关键数字是否接近 support slots，例如 half mean、region std、extrema step/value、counterfactual diff。
- **direction**：caption 数字推出的方向是否和 gold answer 一致，例如 first/second half、early/middle/late、positive/negative intervention effect。
- **horizon**：caption 里提到的 local window length 是否和 support slots 一致，例如 256/512/2048 step。

这个审计不使用 LLM 判分，也不改变 gold answer，只把 deterministic support slots 变成可检查的事实约束。

### 2. 量化 v2.1 的 numeric grounding 问题

审计产物：

- `v21_target_slot_factuality_audit.json`
- `v21_qcond_slot_factuality_audit.json`
- `v21_no_question_slot_factuality_audit.json`

结果：

| run | overall slot factuality | slot value pass | slot value recall | direction pass | horizon pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| v2.1 target | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| v2.1 qcond generated | 0.1143 | 0.1143 | 0.1486 | 0.5357 | 0.7500 |
| v2.1 no-question generated | 0.1143 | 0.1143 | 0.0811 | 0.6154 | 0.8400 |

按域看，v2.1 qcond 的 Grid2Op 是最明显的失败：

| source | n | overall | slot value pass | direction pass | horizon pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| aiopslab_official_v3 | 5 | 0.4000 | 0.4000 | 0.6667 | n/a |
| citylearn | 2 | 0.0000 | 0.0000 | 1.0000 | 1.0000 |
| grid2op | 10 | 0.0000 | 0.0000 | 0.3750 | 0.3333 |
| traffic | 12 | 0.1667 | 0.1667 | 0.4545 | 1.0000 |
| water | 6 | 0.0000 | 0.0000 | 0.8000 | 1.0000 |

解释：v2.1 已经把 `Evidence / Decision rule / Therefore` 格式学得比较好，但模型经常把数值填错，尤其是 Grid2Op 的 local step、window length、counterfactual diff 和 stress direction。

### 3. 生成 v2.2 numeric-grounding repair 数据

修改入口：

`scripts/generate/build_natural_qcc_evidence_only_sft.py`

新增参数：

`--numeric_grounding_repair`

v2.2 做了两类修复：

1. **prompt 侧修复**：给 q-conditioned prompt 加 `Grounding checklist`，要求从当前 trace 计算数字，不复用其他样本数字；同时只说明“需要计算哪些字段”，不把 support slot 的答案值塞进 prompt。
2. **target 侧修复**：target 明确写出 local window length、关键数值、signed difference、relative difference、third/half/counterfactual direction，让训练目标更像可复制的 grounding trace。

输出目录：

`.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/sft_evidence_only_v22/`

规模：

| split | rows |
| --- | ---: |
| train + dev | 89 |
| test | 35 |
| all | 124 |

schema gate：

| gate | result |
| --- | ---: |
| schema_gate_pass | true |
| answer_label_suffix_count | 0 |
| option_letter_leak_count | 0 |
| missing_required_count | 0 |
| numeric_grounding_repair | true |

### 4. v2.2 target gate

v2.2 target 通过三个 gate：

| gate | result |
| --- | ---: |
| caption quality gate | true |
| evidence shape rate | 1.0000 |
| answer-label-only rate | 0.0000 |
| semantic QA accuracy | 1.0000 |
| slot factuality | 1.0000 |
| slot value pass | 1.0000 |
| slot value recall | 1.0000 |
| direction pass | 1.0000 |
| horizon pass | 1.0000 |

按域的 v2.2 target slot factuality 全部为 `1.0000`：

| source | n | overall slot factuality |
| --- | ---: | ---: |
| aiopslab_official_v3 | 5 | 1.0000 |
| citylearn | 2 | 1.0000 |
| grid2op | 10 | 1.0000 |
| traffic | 12 | 1.0000 |
| water | 6 | 1.0000 |

## 这轮没有声称什么

这轮没有声称 v2.2 模型已经变好，因为还没有跑 v2.2 训练。

目前能声称的是：

- 我们已经有了一个能抓 numeric grounding 错误的 deterministic gate。
- v2.1 的生成失败被量化了，特别是 Grid2Op 的数值/方向/window grounding。
- v2.2 数据资产已经完成，并且 target 在 quality、QA、slot factuality 三个层面都是干净的。

## 下一步

下一步应跑 v2.2 的同配置训练：

- qcond：`natural_qcc_failure_domain_expanded_v22_numeric_grounding_train_sft.jsonl`
- no-question：`natural_qcc_failure_domain_expanded_v22_numeric_grounding_no_question_train_sft.jsonl`
- 评估同时看 semantic QA、caption quality、slot factuality、qcond-vs-no-question gap。

如果 v2.2 的 generated slot factuality 仍然低，说明仅靠 prompt/target 风格不够，需要进一步做 value-copy auxiliary loss、slot-verbalization pretraining，或者 Grid2Op 专门的 numeric-copy curriculum。
