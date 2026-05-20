# Natural QCC v2.2 训练失败诊断（2026-05-20）

## 结论

目前最可能的问题不是 v2.2 target 数据坏了，也不是 3090 训练没跑通，而是 **训练文本长度预算把 qcond 的 target caption 全部截掉了**。

当前 `train_multisim_v5_smoke.py` 的 collator 默认使用：

| 参数 | 值 |
| --- | ---: |
| `max_text_length` | `224` |
| `max_prompt_length` | `320` |
| `add_eos` | `true` |

编码逻辑是先保留 prompt，再用剩余位置装 output：

```text
prompt_ids = tokenizer(prompt)[:max_prompt_length]
reserve = 1 + len(prompt_ids) + 1(EOS)
output_ids = output_ids[:max(max_text_length - reserve, 0)]
labels = [-100 for BOS+prompt] + output_ids + EOS
```

v2.2 qcond 的 prompt 加入了更长的 `Grounding checklist` 和 evidence-field 要求，导致 prompt 本身已经超过或接近 `224` 的总文本预算。结果是：**89 条 qcond 训练样本的可训练 output token 数全部为 0**。模型实际主要学到的是“prompt 后立刻输出 EOS”，所以测试时 35 条 qcond 全部生成空 caption。

这解释了之前看起来矛盾的现象：

- target gate 全过：因为标准 target caption 本身是干净、可验证的。
- train/eval loss 接近 0：因为训练目标被截成了很容易学的 EOS，而不是完整 evidence caption。
- qcond 生成全空：模型按训练目标输出 EOS。
- no-question 不是全空但全错：no-question prompt 较短，仍保留了少量 output token，但大多只保留 evidence 开头片段，学成了残缺模板。

## 关键证据

### 1. v2.2 target 本身没有直接坏掉

v2.2 target gate：

| gate | result |
| --- | ---: |
| target semantic QA | `1.0000` |
| target caption quality gate | `true` |
| target evidence shape rate | `1.0000` |
| target answer-label-only rate | `0.0000` |
| target slot factuality | `1.0000` |
| target Grid2Op slot factuality | `1.0000` |

所以当前失败不能归因于“标准答案证据不可回答”。

### 2. 训练和评估流程确实跑完了

v2.2 qcond/no-question paired training 已在 3090 上完整执行：

| run | pipeline complete | smoke audit |
| --- | ---: | ---: |
| v2.2 qcond | `true` | `true` |
| v2.2 no-question | `true` | `true` |

所以当前失败也不是 GPU runtime 或脚本中途失败。

### 3. 生成结果显示 qcond 是协议性空输出

qcond 生成指标：

| metric | value |
| --- | ---: |
| test rows | `35` |
| empty caption rate | `1.0000` |
| mean caption chars | `0.0` |
| semantic QA | `0.0000` |

`predictions.jsonl` 中 `pred_caption` 和 `pred_caption_raw` 都是空字符串。也就是说，不是 cleaning 把内容删掉，而是 raw generation 本身为空。

### 4. Token-budget 诊断直接解释空输出

用远端 3090 环境的同一个 `Qwen/Qwen3-4B` tokenizer 统计训练样本，在当前 collator 配置下得到：

| dataset | n | mean prompt tokens kept | zero-output rows | mean output tokens kept |
| --- | ---: | ---: | ---: | ---: |
| v2.1 qcond | `89` | `157.64` | `2` | `52.61` |
| v2.2 qcond | `89` | `247.81` | `89` | `0.00` |
| v2.2 no-question | `89` | `198.47` | `13` | `27.60` |

这说明：

- v2.1 qcond 大部分样本还能训练到 target caption，所以至少能生成一些 evidence。
- v2.2 qcond 所有样本的 output 都被截成 0，所以模型没有见过完整 target caption。
- v2.2 no-question 只保留了残缺 target 前缀，因此生成残缺、重复、错任务 evidence。

## 当前问题链路

我现在会把失败链路总结成这样：

1. 为了修复 numeric grounding，v2.2 在 prompt 中加入了更长的 grounding checklist 和 required evidence fields。
2. 训练脚本没有同步提高 `max_text_length`，仍然用默认 `224`。
3. collator 的预算是 prompt 优先，output 后填。
4. qcond prompt 已经吃光总预算，target caption 被截到 0 token。
5. 训练 loss 变得很好看，但学到的是 EOS，不是证据生成。
6. 生成阶段 qcond 立即停止，得到空 caption。
7. no-question 因为 prompt 短一点，保留了少量 output token，于是生成 evidence-like 片段，但不完整、不对应问题。

## 这轮不应该得出的结论

不要从这轮训练结果推出：

- “v2.2 numeric-grounding target 不可用”；
- “Qwen3-4B 学不会 Natural QCC”；
- “问题必须重新写一遍”；
- “需要直接扩数据或换大模型”。

当前更合理的结论是：

> v2.2 数据修复让 target 更完整，但没有同步调整 SFT 文本预算，导致训练目标被截断；这轮训练验证主要暴露的是训练协议问题，而不是数据质量上限。

## 下一步最小验证

不要先扩数据，也不要先换模型。建议按下面顺序做：

1. 给 `run_natural_qcc_gpu_smoke.py` 或 preflight 增加 token-budget audit：
   - 报告 prompt tokens、output tokens、output kept tokens；
   - 如果 qcond `zero_output_kept_rate > 0` 或平均保留率太低，直接 fail。
2. 重跑 v2.2 前先设置：
   - `max_text_length >= 512`；
   - `max_prompt_length` 可保留 `320` 或升到 `384`；
   - 确认 qcond 训练集中 `output_tokens_kept` 基本不再为 0。
3. 先做 5-example overfit：
   - 如果 train-set generation 能复现完整 evidence caption，再跑完整 89/35；
   - 如果 overfit 仍空输出，再查 checkpoint save/load 和 `generate()` 起始位置。
4. 完整训练后同时看：
   - qcond train-set generation；
   - qcond test-set generation；
   - raw caption 和 cleaned caption；
   - semantic QA；
   - caption quality；
   - slot factuality。
5. 只有在上述协议修复后仍失败，才回到数据层面继续看 Grid2Op long-window/counterfactual grounding。

## 是否需要 GPT Pro

这次不一定需要 GPT Pro 才能判断主因，因为 token-budget 证据已经直接解释 qcond 空输出。

但可以让 GPT Pro 做独立审计，重点不是让它判断答案对错，而是让它 review：

- 这个 `max_text_length=224` 截断诊断是否充分；
- 是否还存在 save/load、LoRA、`inputs_embeds` generation、EOS/pad token 配置等次级风险；
- 下一轮最小修复实验该怎么排优先级。

对应 prompt 已整理在：

`GPT_PRO_PROMPT_NATURAL_QCC_V22_FAILURE_DIAGNOSIS_20260520.md`

