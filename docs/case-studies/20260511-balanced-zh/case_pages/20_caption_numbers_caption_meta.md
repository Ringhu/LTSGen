### Case 20：caption+numbers 弱于 caption / meta

- 数据集：`TSAQA`
- Case ID：`tsaqa::0004`
- 问题类型：`classification`
- 领域 / 子数据集：`synthetic` / `-`
- artifact 说明：TSAQA 此 case 已按 full-eval task 顺序和 local index 回连 phase_a 原始题干/序列；当前本地没有保存 OpenTSLM/ChatTS 原始 caption 对照文本，因此此处展示可用 SFT caption 样本和多条件答案。
- 数值摘要：n=128, min=-1.4575, max=1.429, mean=-1.5625e-06, std=1, slope=9.9218e-05, argmax=43, argmin=28

![tsaqa::0004](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/tsaqa_0004.png)

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
- 正确答案：`B`

**生成的 caption 与中文翻译**

**可用 caption 样本 原文**

1. Noisy with std around 0.20.
  2. No periodic fluctuations observed, showing no periodic fluctuation.
  3. Decrease from 0.29 to 0.01.
  4. Starting from point 28, the time series value falls from around 0.78 to around -1.48, forms a downward convex with an amplitude of about 0.92, and then rises back to around 0.27, forming a downward convex;starting from point 64, the time series value slowly rises, reaching a peak at point 80, followed by a rapid decline between point 80 and point 82 back to around -0.78, forming a slow rise followed by rapid decline.

**可用 caption 样本 中文翻译**

1. 噪声较大，标准差约为 0.20。
2. 未观察到周期性波动，显示无周期性波动。
3. 从 0.29 下降到 0.01。
4. 从第 28 个点开始，时间序列值从约 0.78 下降到约 -1.48，形成一个向下凸起，幅度约为 0.92，然后回升到约 0.27，形成向下凸起；从第 64 个点开始，时间序列值缓慢上升，在第 80 个点达到峰值，随后在第 80 个点到第 82 个点之间快速下降，回到约 -0.78，形成先缓慢上升后快速下降。

**不同输入条件下的答案 / 评分**

| 输入条件 | 预测答案 | 结果 |
| --- | --- | --- |
| `meta_only` | `B` | 正确 |
| `numbers` | `C` | 错误 |
| `opentslm_caption` | `B` | 正确 |
| `opentslm_caption_plus` | `A` | 错误 |
| `chatts_caption` | `A` | 错误 |
| `chatts_caption_plus` | `A` | 错误 |
| `tool_agent` | `B` | 正确 |

**Case 分析**

- 失败标签：caption+numbers 弱于 caption / meta
- 关键结论：OpenTSLM caption 单独正确，但 caption+numbers 错，显示混合输入可能让模型重新解释证据，造成集成失败。
