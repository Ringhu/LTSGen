# Natural QCC v2.2 Numeric Grounding 训练验证报告（2026-05-20）

## 结论

这轮训练验证的结论是：**v2.2 数据修复有效，但没有转化成模型生成能力；按预先计划，本轮判定为 `not_effective`。**

更具体地说：

- v2.2 target 仍然是干净的：caption quality、semantic QA、slot factuality 都是 `1.0000`。
- 真实 3090 上的 qcond/no-question paired training 已完整跑完，pipeline audit 都通过。
- 但是 generated caption 失败了：qcond 35 条测试样本全部生成空 caption，semantic QA 为 `0.0000`。
- no-question 虽然生成了一些 evidence-like 短句，但大多是重复模板或错任务证据，semantic QA 也是 `0.0000`。
- Grid2Op 仍然没有改善：qcond 和 no-question 的 Grid2Op slot factuality 都是 `0.0000`。

所以不能说“v2.2 numeric-grounding repair 有效”。现在能说的是：**target 修好了；训练/生成接口或 prompt-target 协议出现了新的失败，必须先诊断生成空输出和模板坍缩，再继续扩训练。**

## 运行设置

运行位置：

`/cluster/home/hulining/LTSGEN_v22_numeric_grounding_20260520`

本地结果目录：

`.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/numeric_grounding_repair_v22_20260520/train_v22_e5_tok128_20260520/`

配置保持和 v2.1 可比：

| item | value |
| --- | --- |
| GPU | RTX 3090, `CUDA_VISIBLE_DEVICES=1` |
| model | `Qwen/Qwen3-4B` |
| bridge | `prefix` |
| train epochs | `5` |
| gradient accumulation | `2` |
| max new tokens | `128` |
| clean max sentences | `3` |
| QA evaluator | `semantic` |
| train/test rows | `89 / 35` |

可复现 runner：

`scripts/remote/run_natural_qcc_failure_domain_v22_pair_3090.sh`

## Target Gate

v2.2 target 本身继续通过全部 gate：

| gate | result |
| --- | ---: |
| target caption quality gate | `true` |
| target evidence shape rate | `1.0000` |
| target answer-label-only rate | `0.0000` |
| target semantic QA | `1.0000` |
| target overall slot factuality | `1.0000` |
| target Grid2Op slot factuality | `1.0000` |

这说明数据资产不是直接坏掉的：如果把 target caption 当证据输入，答案可由 deterministic evaluator 验证。

## Generated 结果

| run | audit pass | semantic QA | empty answer | caption quality | evidence shape | slot factuality | Grid2Op slot factuality |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v2.1 qcond baseline | `true` | `0.3143` | `0.2857` | `true` | `1.0000` | `0.1143` | `0.0000` |
| v2.2 qcond | `true` | `0.0000` | `1.0000` | `false` | `0.0000` | `0.0857` | `0.0000` |
| v2.2 no-question | `true` | `0.0000` | `1.0000` | `true` | `0.8571` | `0.0857` | `0.0000` |

qcond-vs-no-question：

| metric | value |
| --- | ---: |
| qcond semantic QA | `0.0000` |
| no-question semantic QA | `0.0000` |
| gap | `0.0000` |
| decision | `no_qconditioning_gap` |

按照预先计划，v2.2 至少需要 qcond semantic QA 超过 v2.1 的 `0.3143`，qcond slot factuality 超过 `0.1143` 且最好达到 `0.25`，并且 Grid2Op slot factuality 从 `0.0000` 起跳。本轮这些都没有满足。

## 失败形态

### qcond：空输出

qcond 的 `generate_eval_test_clean/metrics.json` 显示：

| metric | value |
| --- | ---: |
| rows | `35` |
| empty caption rate | `1.0000` |
| mean caption chars | `0.0` |

抽查 `predictions.jsonl` 可见 `pred_caption` 和 `pred_caption_raw` 都是空字符串。例如第一条 AIOps test row：

```text
target_caption: Evidence: in the 64-step local window, first-half mean is 797,644.80, ...
pred_caption: ""
pred_caption_raw: ""
```

这不是审计脚本漏读字段，而是生成阶段真的没有产生有效 caption。

### no-question：有形态但错证据

no-question 的 caption quality gate 反而通过：

| metric | value |
| --- | ---: |
| evidence shape rate | `0.8571` |
| numeric evidence rate | `0.8571` |
| mean caption chars | `86.6` |

但这些句子大多是重复模板或错任务证据。例如多条不同 AIOps 问题都生成：

```text
Evidence: in the 64-step local window, CPU-memory correlation is 0.000, and network receive
```

它看起来像证据，但不能回答对应问题，所以 semantic QA 仍是 `0.0000`，slot factuality 也只有 `0.0857`。

## 和 v2.1 的关系

v2.1 的主要问题是：caption 形态过了，但数值 grounding 很差。

v2.2 原本想解决这个问题：target 加强 local window、关键数值、signed difference、relative difference、direction/horizon。target gate 证明这部分是成立的。

但训练后出现了更底层的问题：

- qcond 完全空输出；
- no-question 模板坍缩；
- semantic QA 从 v2.1 qcond 的 `0.3143` 掉到 `0.0000`；
- slot factuality 从 v2.1 qcond 的 `0.1143` 掉到 `0.0857`；
- Grid2Op 继续是 `0.0000`。

所以这轮不是“numeric grounding 仍差一点”，而是 **v2.2 prompt/target 和当前 TS-RLM generation recipe 不匹配**。

## 判定

按训练验证计划，本轮触发 `not_effective`：

- qcond caption quality gate 为 `false`；
- qcond semantic QA 未超过 v2.1 baseline `0.3143`；
- qcond slot factuality 未超过 v2.1 baseline `0.1143`；
- qcond Grid2Op slot factuality 仍为 `0.0000`；
- qcond-vs-no-question gap 为 `0.0000`。

## 下一步

不要扩数据，也不要直接换大训练。先做生成协议诊断：

1. 对 v2.2 qcond checkpoint 跑 train-set generation，看是否训练样本也空输出。
2. 比较 v2.1 和 v2.2 的 qcond prompt/target token length、label mask、EOS 分布；qcond train loss 接近 0 但 decode 为空，很像 label/generation protocol 问题。
3. 跑 `max_new_tokens`、`min_new_tokens`、禁用/放宽清洗的 raw generation probe，确认是模型直接 EOS，还是清洗规则把内容删掉。
4. 做 5-example overfit：如果训练集也无法生成 target，先修训练/生成代码；如果训练集能生成但 test 空，才回到数据泛化问题。
5. 在上述诊断通过前，不继续做 v2.3 数据扩容或 Grid2Op 专门 curriculum。

