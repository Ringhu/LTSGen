### Case 01：mixed trend 被压缩成 flat/upward

- 数据集：`TSShapeQA-OOD`
- Case ID：`tsshapeqa::0008::exchange_rate:5:w384:s3456`
- 问题类型：`TREND`
- 领域 / 子数据集：`finance` / `exchange_rate`
- 数值摘要：n=384, min=0.008729, max=0.010699, mean=0.0093172, std=0.00025239, slope=7.1632e-07, argmax=204, argmin=44
- 标注特征：`{'ambiguous': False, 'label': 'mixed', 'norm_effect': 1.0870287886386036, 'r2': 0.09898349893857857, 'slope': 7.163240480146482e-07}`

![tsshapeqa::0008::exchange_rate:5:w384:s3456](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/tsshapeqa_0008_exchange_rate_5_w384_s3456.png)

**QA 问题**

- 原文：Across the full period, what is the overall direction of this exchange-rate series?
- 中文翻译：在整个时期内，该汇率序列的整体方向是什么？
- 选项：
- A: A. Steadily decreasing overall
  中文：A. 整体稳步下降
- B: B. Mixed, with no consistent direction
  中文：B. 混合变化，没有一致方向
- C: C. Steadily increasing overall
  中文：C. 整体稳步上升
- D: D. Roughly flat with minor noise
  中文：D. 大致平稳，仅有轻微噪声
- 正确答案：`B`

**生成的 caption 与中文翻译**

**OpenTSLM caption 原文**

7. The time series shows a strong seasonal pattern with a period of 40 time units, and a gradual upward trend over the entire window. The early part of the series experiences a significant increase, followed by a moderate rise in the first half, and a slight flattening in the second half. A notable peak occurs in the second half, reaching about 1.5 standard deviations above the mean, while a deep valley is observed early in the window, about 1.8 standard deviations below the mean. The series is strongly correlated with variables 6 and 3, showing strong positive relationships.

**OpenTSLM caption 中文翻译**

7. 该时间序列呈现出强烈的季节性模式，周期为 40 个时间单位，并且在整个窗口内呈现逐渐上升的趋势。序列早期经历了显著增长，随后在前半部分温和上升，并在后半部分略有趋平。后半部分出现一个显著峰值，达到均值以上约 1.5 个标准差；而窗口早期观察到一个深谷，约低于均值 1.8 个标准差。该序列与变量 6 和变量 3 强相关，表现出强正相关关系。

**ChatTS caption 原文**

The overall trend is flat, with no significant changes in value throughout the time series. The global maximum, which is consistently around 0.01, is present throughout the entire window, indicating no specific peak position. There are no short-term fluctuations observed in either half of the window. In summary, the time series exhibits a steady trend with no notable peaks or fluctuations.

**ChatTS caption 中文翻译**

整体趋势平稳，在整个时间序列中数值没有显著变化。全局最大值始终约为 0.01，贯穿整个窗口，表明没有特定的峰值位置。窗口的前半段和后半段均未观察到短期波动。总之，该时间序列表现出稳定趋势，没有明显峰值或波动。

**OpenTSLM Q3-format SFT caption 原文**

The time series shows a flat trend with high volatility and no clear seasonality. The data starts with a significant downward movement early in the window, followed by an upward phase in the first half, and then another decline in the second half. A notable peak occurs in the second half, reaching about 13.1 standard deviations above the mean, while a smaller valley is observed in the first half, about 1.0 standard deviation below the mean. The series has moderate positive and negative correlations with variables 6 and 3, respectively.

**OpenTSLM Q3-format SFT caption 中文翻译**

该时间序列呈现平稳趋势，波动性较高，且没有明显季节性。数据在窗口早期出现显著下行，随后在前半段进入上行阶段，然后在后半段再次下行。一个显著峰值出现在后半段，达到约高于均值 13.1 个标准差，而一个较小的谷值出现在前半段，约低于均值 1.0 个标准差。该序列分别与变量 6 和变量 3 存在中等程度的正相关和负相关。

**不同输入条件下的答案 / 评分**

| 输入条件 | 预测答案 | 结果 |
| --- | --- | --- |
| `meta_only` | `B` | 正确 |
| `numbers` | `B` | 正确 |
| `numbers_cot` | `D` | 错误；dly without a clear sustained trend, though the ending is slightly higher than the start. Overall, it looks mostly flat with minor noise rather than steadily incr ...[截断] |
| `opentslm_caption` | `C` | 错误 |
| `opentslm_caption_plus` | `C` | 错误 |
| `chatts_caption` | `D` | 错误 |
| `chatts_caption_plus` | `D` | 错误 |
| `tool_agent` | `B` | 正确 |

**Case 分析**

- 失败标签：mixed trend 被压缩成 flat/upward
- 关键结论：真实答案需要识别完整窗口内的 mixed movement；OpenTSLM 把它写成上升和季节性，ChatTS 把它写成平坦，两个 caption 都没有保留可回答 QA 的趋势证据。
