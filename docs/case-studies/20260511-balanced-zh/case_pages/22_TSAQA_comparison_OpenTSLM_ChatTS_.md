### Case 22：TSAQA comparison：OpenTSLM 错、ChatTS 对

- 数据集：`TSAQA`
- Case ID：`tsaqa::0665`
- 问题类型：`comparison`
- 领域 / 子数据集：`["healthcare", "healthcare"]` / `-`
- artifact 说明：TSAQA 此 case 已按 full-eval task 顺序和 local index 回连 phase_a 原始题干/序列；当前本地没有保存 OpenTSLM/ChatTS 原始 caption 对照文本，因此此处展示可用 SFT caption 样本和多条件答案。
- 数值摘要：n=410, min=-2.1711, max=2.4555, mean=-2.1951e-06, std=0.99999, slope=7.1544e-05, argmax=54, argmin=267

![tsaqa::0665](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/tsaqa_0665.png)

**QA 问题**

- 原文：Does time series 1 have greater variability, measured by coefficient of variation, than time series 2, while both series show some level of persistence in short-term autocorrelations and frequent cyclic peaks and troughs?
Respond ONLY with the letter of the correct choice (T or F).

Choices:
T: True.
F: False.
- 中文翻译：时间序列 1 的变异性（以变异系数衡量）是否大于时间序列 2，同时两个序列在短期自相关中都表现出一定程度的持续性，并且频繁出现周期性峰值和谷值？
仅用正确选项的字母（T 或 F）作答。

选项：
T：真。
F：假。
- 背景信息中文：["由光电容积脉搏波（PPG）和心电图（ECG）信号的滑动 32 秒窗口得到的心率测量数值序列（单位：次/分钟），其中每个数值反映其对应窗口内的估计心率。", "美国每日出生人数的时间序列。"]
- 选项：
-
- 正确答案：`F`

**生成的 caption 与中文翻译**

**可用 caption 样本 原文**

1. Noisy with std around 0.52.
2. The time series is showing sin periodic fluctuation: the amplitude of the periodic fluctuation is 2.5 between point 0 and point 410. Each fluctuation period is approximately 79.3 points, thus the overall fluctuation is low frequency.
3. Keep steady from 0.31 to 1.05.
4. No local characteristics found.

**可用 caption 样本 中文翻译**

1. 噪声较大，标准差约为 0.52。
2. 该时间序列表现出正弦周期性波动：在点 0 到点 410 之间，周期性波动的振幅为 2.5。每个波动周期约为 79.3 个点，因此整体波动为低频。
3. 从 0.31 到 1.05 保持稳定。
4. 未发现局部特征。

**不同输入条件下的答案 / 评分**

| 输入条件 | 预测答案 | 结果 |
| --- | --- | --- |
| `meta_only` | `F` | 正确 |
| `numbers` | `F` | 正确 |
| `opentslm_caption` | `T` | 错误 |
| `opentslm_caption_plus` | `F` | 正确 |
| `chatts_caption` | `F` | 正确 |
| `chatts_caption_plus` | `F` | 正确 |
| `tool_agent` | `F` | 正确 |

**Case 分析**

- 失败标签：TSAQA comparison：OpenTSLM 错、ChatTS 对
- 关键结论：该题比较两个医疗时间序列的变异系数和自相关/周期峰谷。OpenTSLM caption 条件答错，ChatTS 和 numbers 答对，说明多序列比较需要保留跨序列相对量，而不是只描述单条序列。
