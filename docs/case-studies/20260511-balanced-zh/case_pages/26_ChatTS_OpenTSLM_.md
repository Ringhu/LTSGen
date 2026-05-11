### Case 26：ChatTS 错、OpenTSLM 对的反例

- 数据集：`TimeSeriesExam`
- Case ID：`timeseriesexam::tse_0010`
- 问题类型：`Anolmaly Detection`
- 数值摘要：n=128, min=-11.128, max=13.743, mean=3.8142, std=3.8011, slope=0.070196, argmax=103, argmin=0

![timeseriesexam::tse_0010](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/timeseriesexam_tse_0010.png)

**QA 问题**

**题干原文**

Is the given time series likely to have an anomaly?

**题干中文翻译**

给定的时间序列是否可能存在异常？
- 选项：
- A: No
  中文：否
- B: Yes, it's pattern is distorted by random spikes
  中文：是的，它的模式被随机尖峰扭曲了。
- C: Yes, it's pattern is flipped at certain point in time
  中文：是的，它的模式在某个时间点发生了翻转。
- 正确答案：`Yes, it's pattern is distorted by random spikes`

**生成的 caption 与中文翻译**

**OpenTSLM caption 原文**

The time series shows a downward trend early in the window followed by an upward movement in the first half and a stronger upward trend in the second half. There is a moderate seasonal pattern with a period of about 10 time units. The overall net change is a significant increase of over 40%. A notable peak occurs in the first half, reaching about 1.5 standard deviations above the mean, while a deep valley is observed early in the window, about 1.8 standard deviations below the mean. The data exhibits strong positive correlation with variable 2 and moderate positive correlation with variable 3.

**OpenTSLM caption 中文翻译**

该时间序列在窗口早期呈下降趋势，随后在前半段出现上行走势，并在后半段呈现更强的上升趋势。存在中等程度的季节性模式，周期约为 10 个时间单位。整体净变化为显著增加，增幅超过 40%。前半段出现一个显著峰值，达到均值以上约 1.5 个标准差；而窗口早期观察到一个深谷，约低于均值 1.8 个标准差。数据与变量 2 表现出强正相关，与变量 3 表现出中等正相关。

**ChatTS caption 原文**

The overall trend is increasing. The global maximum, 11.65, occurs at point 127, which is in the last third of the 128-point window. Short-term fluctuations, characterized by the standard deviation of noise (~3.0), are more pronounced in the first half of the window compared to the second half, where the trend stabilizes.

**ChatTS caption 中文翻译**

整体趋势是上升的。全局最大值 11.65 出现在点 127，位于 128 点窗口的后三分之一。由噪声标准差（约 3.0）表征的短期波动，在窗口前半部分比后半部分更明显，而后半部分的趋势趋于稳定。

**不同输入条件下的答案 / 评分**

| 输入条件 | 预测答案 | 结果 |
| --- | --- | --- |
| `meta_only` | `B` | 正确 |
| `numbers` | `B` | 正确 |
| `opentslm_caption` | `B` | 正确 |
| `chatts_caption` | `A` | 错误 |
| `wrong_caption` | `B` | 正确 |

**Case 分析**

- 失败标签：ChatTS 错、OpenTSLM 对的反例
- 关键结论：并非所有失败都来自 OpenTSLM；该 anomaly case 中 OpenTSLM 正确而 ChatTS 错，说明不同 caption 模型的偏差方向不同。
