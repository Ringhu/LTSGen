### Case 19：TSAQA 分类：caption 与 numbers 都不够，tool-agent 对

- 数据集：`TSAQA`
- Case ID：`tsaqa::0003`
- 问题类型：`classification`
- 领域 / 子数据集：`synthetic` / `-`
- artifact 说明：TSAQA 此 case 已按 full-eval task 顺序和 local index 回连 phase_a 原始题干/序列；当前本地没有保存 OpenTSLM/ChatTS 原始 caption 对照文本，因此此处展示可用 SFT caption 样本和多条件答案。
- 数值摘要：n=128, min=-1.5334, max=1.5422, mean=-7.8125e-06, std=1, slope=0.0026186, argmax=45, argmin=34

![tsaqa::0003](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/tsaqa_0003.png)

**QA 问题**

- 原文：Classify the given time series into one of the categories below.
Respond ONLY with the letter of the correct choice (A, B, C, D).

Choices:
A: down-down (1306 cases)
B: up-down (1248 cases)
C: down-up (1245 cases)
D: up-up (1201 cases)
- 中文翻译：将给定的时间序列分类为以下类别之一。
仅回复正确选项的字母（A、B、C、D）。

选项：
A：下降-下降（1306 个案例）
B：上升-下降（1248 个案例）
C：下降-上升（1245 个案例）
D：上升-上升（1201 个案例）
- 背景信息中文：该时间序列来自一个数据集，该数据集旨在基于不同的上升和下降运动模式来模拟和分类序列，每个序列都根据四种方向类别之一进行标注，这些类别反映了上升和下降变化的不同组合。
- 选项：
-
- 正确答案：`D`

**生成的 caption 与中文翻译**

**可用 caption 样本 原文**

1. Noisy with std around 0.29.
2. No periodic fluctuations observed, showing no periodic fluctuation.
3. Decrease from 0.64 to -0.38.
4. Starting from point 34, the time series value rises from around 0.14 to around 1.38, forms an upward convex with an amplitude of about 1.74, and then falls back to around -0.58, forming a upward convex.

**可用 caption 样本 中文翻译**

1. 噪声较大，标准差约为 0.29。
2. 未观察到周期性波动，显示无周期性波动。
3. 从 0.64 下降到 -0.38。
4. 从第 34 个点开始，时间序列值从约 0.14 上升到约 1.38，形成一个向上凸起，幅度约为 1.74，然后回落到约 -0.58，形成一个向上凸起。

**不同输入条件下的答案 / 评分**

| 输入条件 | 预测答案 | 结果 |
| --- | --- | --- |
| `meta_only` | `C` | 错误 |
| `numbers` | `C` | 错误 |
| `opentslm_caption` | `B` | 错误 |
| `opentslm_caption_plus` | `B` | 错误 |
| `chatts_caption` | `B` | 错误 |
| `chatts_caption_plus` | `C` | 错误 |
| `tool_agent` | `D` | 正确 |

**Case 分析**

- 失败标签：TSAQA 分类：caption 与 numbers 都不够，tool-agent 对
- 关键结论：该 case 中两个 caption 条件和 numbers 都错，tool-agent 对，说明需要结构化工具提取方向组合，而不是只靠自然语言摘要。
