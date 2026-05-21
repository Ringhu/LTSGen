# Natural QCC Failure-Domain v2.1 清洗统一风格训练报告（2026-05-20）

## 结论

本轮按计划做了 v2.1 数据清洗和统一风格：把 evidence target 统一成 `Evidence / Decision rule / Therefore` 结构，并加强生成后清洗，截断中文续写、prompt echo、`You are a`、`Scene:` 等残片。

结果是：**caption 形态问题被修好了，但 QA 准确率没有提升。** q-conditioned 的 generated caption quality gate 从 v2 的 `false` 变成 v2.1 的 `true`，evidence_shape_rate 从 `0.6857` 到 `1.0000`，answer_label_only_rate 从 `0.2000` 到 `0.0000`。但是 qcond semantic QA 仍是 `0.3143`，和 v2 完全相同。

所以这轮最重要的结论不是“模型变强了”，而是：**上一轮的短标签/无数字问题确实是格式与清洗问题；但最终答题瓶颈主要转向 numeric grounding，也就是模型会写出像证据的句子，却常常填错数值、窗口位置或反事实方向。**

## 数据清洗做了什么

v2.1 没有改 gold answer，也没有让 LLM 决定答案。清洗只使用已有 deterministic support slots 生成统一 evidence target。

主要改动：

- 新增 `--style_repair` 构建路径，输出到 `sft_evidence_only_v21/`。
- 每条 target 统一为三段：`Evidence: ... Decision rule: ... Therefore, ...`。
- 对 `region_stds`、`extrema_index/value`、`event_abs_z`、half-window mean、correlation、lead-lag、counterfactual diff 等 support slot 生成显式数字证据。
- 生成清洗新增 prompt echo 和中文续写截断，避免旧版把 `The early, middle, and late options...` 截成 `The early, middle, and late`。

## Target Gate

| gate | result |
| --- | ---: |
| rows | 124 |
| train/test | 89 / 35 |
| target semantic QA | 1.0000 |
| target quality gate | true |
| target evidence shape | 1.0000 |
| target answer-label-only | 0.0000 |

这说明 v2.1 target 本身是可答的，而且不是答案标签捷径。

## 同配置训练结果

配置保持和 v2 可比：`Qwen/Qwen3-4B`、`prefix` bridge、5 epochs、`max_new_tokens=128`、`clean_max_sentences=3`、semantic evaluator。

| run | semantic QA | empty answer rate | caption quality gate | evidence shape | answer-label-only |
| --- | ---: | ---: | ---: | ---: | ---: |
| v2 qcond | 0.3143 | 0.4000 | false | 0.6857 | 0.2000 |
| v2 no-question | 0.1429 | 0.7714 | false | 0.3429 | 0.3143 |
| v2.1 qcond | 0.3143 | 0.2857 | true | 1.0000 | 0.0000 |
| v2.1 no-question | 0.1143 | 0.6571 | true | 1.0000 | 0.0000 |

q-conditioning gap：

| version | qcond | no-question | gap |
| --- | ---: | ---: | ---: |
| v2 | 0.3143 | 0.1429 | +0.1714 |
| v2.1 | 0.3143 | 0.1143 | +0.2000 |

解释：gap 变大主要不是 qcond 变强，而是 no-question 更弱；qcond 准确率持平。

## 按域变化

| domain | v2 qcond | v2.1 qcond | change |
| --- | ---: | ---: | ---: |
| AIOpsLab | 0.0000 | 0.2000 | +0.2000 |
| CityLearn | 0.5000 | 0.5000 | 0.0000 |
| Grid2Op | 0.3000 | 0.0000 | -0.3000 |
| Traffic | 0.3333 | 0.4167 | +0.0834 |
| Water | 0.5000 | 0.6667 | +0.1667 |

这个表说明 v2.1 不是全面提升。它帮了 Traffic/Water/AIOps，但明显伤害了 Grid2Op。

## 为什么会这样

### 1. 清洗解决了“证据形态”，没有解决“数值 grounding”

v2 的失败经常是：

- `The early, middle, and late`
- `Factual overload`
- 无数字的模板句
- prompt echo 或中文续写

v2.1 后这些基本消失，quality gate 直接过了。但模型开始稳定生成一种更完整的模板句，同时把错误数值填进模板里。例如：

- gold 是 first-half `797,644.80`、second-half `801,177.60`，模型写成 `1023.69` 和 `-1024.87`。
- gold Grid2Op extrema 是 step `809`，模型写成 step `239`。
- gold counterfactual stress 是正向升高，模型写成负向降低。

所以当前不是语言格式问题，而是时间序列到数值证据的拷贝/定位能力不足。

### 2. 统一模板降低了输出随机性，但也放大了“套模板填错数”的问题

v2.1 输出看起来都像 evidence caption，甚至 no-question 的 evidence_shape 也到 `1.0000`。这说明统一风格让模型更容易学会“应该写什么形状”。但它不保证“数字来自当前 trace”。模型可能从训练集中记住常见数字模式，然后迁移到错误样本。

### 3. Grid2Op 对统一模板最敏感

Grid2Op 失败集中在长窗口、局部窗口位置、反事实 segment 和 stress diff 上。这些任务不仅要写自然语言，还要绑定：

- local step vs global step；
- 256/512/2048 窗口长度；
- factual vs intervention；
- max/min/mean diff 的方向；
- early/middle/late 的边界。

v2.1 的通用模板没有显式训练模型“怎么从 trace 中复制这些 slot 数值”，所以 Grid2Op 从 `0.3000` 掉到 `0.0000`。

### 4. q-conditioning 信号仍然存在，但还不是方法成功

v2.1 qcond `0.3143`，no-question `0.1143`，gap `+0.2000`。这说明问题条件仍有用，因为没有 question 的模型更难知道该写哪个证据。但 qcond 自身没有变强，所以这只能算 smoke-level 正信号，不是 full method claim。

## 下一步建议

不要继续只做风格清洗，也不要直接大规模扩数据。下一步应做 **numeric grounding repair**：

1. 对 Grid2Op 单独做 value-copy/slot-grounding 诊断：检查生成数值是否接近 support_slots，而不只看 semantic QA。
2. 对长窗口和反事实任务使用更强的 domain-specific target 模板，明确 local step、window length、factual/intervention 方向。
3. 加一个 `slot factuality` metric：数值误差、方向一致性、segment 一致性。
4. 小规模尝试把 support-slot verbalization 作为辅助训练目标，避免模型只学模板不学数值。
5. 继续保留三道 gate：semantic QA、caption quality、qcond-vs-no-question gap；但新增 numeric grounding gate 后再扩容。
