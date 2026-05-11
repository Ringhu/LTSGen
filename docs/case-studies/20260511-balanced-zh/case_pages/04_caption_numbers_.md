### Case 04：caption+numbers 整合不稳定

- 数据集：`TSShapeQA-OOD`
- Case ID：`tsshapeqa::0011::exchange_rate:1:w384:s2496`
- 问题类型：`VOLATILITY_REGION`
- 领域 / 子数据集：`finance` / `exchange_rate`
- 数值摘要：n=384, min=1.3723, max=1.5974, mean=1.4682, std=0.05175, slope=-0.00038125, argmax=20, argmin=330
- 标注特征：`{'ambiguous': False, 'higher_half': 'first', 'ratio_first_over_second': 1.2128497962927494, 'std_first': 0.02240062292164124, 'std_second': 0.018469412279161965}`

![tsshapeqa::0011::exchange_rate:1:w384:s2496](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/tsshapeqa_0011_exchange_rate_1_w384_s2496.png)

**QA 问题**

- 原文：Which half of this exchange-rate series shows larger short-term fluctuations overall?
- 中文翻译：该汇率序列的哪一半整体上表现出更大的短期波动？
- 选项：
- A: A. Second half
  中文：A. 后半段
- B: B. Roughly equal volatility
  中文：B. 波动性大致相等
- C: C. Cannot tell from the series
  中文：C. 无法从该序列判断
- D: D. First half
  中文：D. 前半部分
- 正确答案：`D`

**生成的 caption 与中文翻译**

**OpenTSLM caption 原文**

1. The time series shows a steady upward trend with low volatility and a strong seasonal pattern repeating every 18 periods. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a slightly smaller but still positive growth in the second half. A notable peak occurs in the second half, reaching about 1.3 standard deviations above the mean, while a deep valley is observed early in the window, about 2.0 standard deviations below the mean. The series is strongly correlated with variable '2', showing a strong positive relationship.

**OpenTSLM caption 中文翻译**

1. 该时间序列呈现稳定的上升趋势，波动性较低，并且具有每 18 个周期重复一次的强季节性模式。数据在窗口早期开始出现适度增长，随后在前半段出现更明显的上升，而在后半段增长幅度略小但仍为正。后半段出现一个显著峰值，达到高于均值约 1.3 个标准差，而窗口早期观察到一个深谷，低于均值约 2.0 个标准差。该序列与变量 '2' 强相关，表现出很强的正相关关系。

**ChatTS caption 原文**

The overall trend is decreasing. The global maximum occurs at the start of the time series (first third of the window). The first half of the window exhibits larger short-term fluctuations, including a rapid decline with an amplitude of 0.12, whereas the second half shows smaller fluctuations.

**ChatTS caption 中文翻译**

整体趋势是下降的。全局最大值出现在时间序列的开始处（窗口的前三分之一）。窗口的前半段表现出较大的短期波动，包括一次幅度为 0.12 的快速下降，而后半段的波动较小。

**OpenTSLM Q3-format SFT caption 原文**

The time series shows a flat trend with medium volatility and a medium-strength daily seasonality. The data starts with a significant downward phase early in the window, followed by an upward movement in the first half, and then a sharp decline in the second half. A notable peak occurs in the second half, reaching about 3.0 standard deviations above the mean, while a valley is observed around the middle of the series, approximately 1.8 standard deviations below the mean. Several variables exhibit moderate positive correlations with the target series.

**OpenTSLM Q3-format SFT caption 中文翻译**

该时间序列呈现平稳趋势，具有中等波动性和中等强度的日季节性。数据在窗口早期以显著下降阶段开始，随后在前半段出现上升走势，然后在后半段急剧下降。后半段出现一个显著峰值，达到均值以上约 3.0 个标准差；而在序列中部附近观察到一个谷值，约低于均值 1.8 个标准差。多个变量与目标序列表现出中等程度的正相关。

**不同输入条件下的答案 / 评分**

| 输入条件 | 预测答案 | 结果 |
| --- | --- | --- |
| `meta_only` | `A` | 错误 |
| `numbers` | `D` | 正确 |
| `numbers_cot` | `A` | 错误；rebounds, especially around the middle and later sections (larger swings between roughly 1.47 and 1.37, then back up). That indicates greater short-term volatilit ...[截断] |
| `opentslm_caption` | `D` | 正确 |
| `opentslm_caption_plus` | `A` | 错误 |
| `chatts_caption` | `D` | 正确 |
| `chatts_caption_plus` | `D` | 正确 |
| `tool_agent` | `D` | 正确 |

**Case 分析**

- 失败标签：caption+numbers 整合不稳定
- 关键结论：numbers 和 caption 单独都能给出正确答案，但 caption+numbers 反而答错，说明下游 QA 不是简单累加证据，而会被自然语言描述重新加权甚至带偏。
