### Case 02：峰值位置被错误 caption 污染

- 数据集：`TSShapeQA-OOD`
- Case ID：`tsshapeqa::0005::timemmd:Energy:Weekly_New_England_(:w512:s0`
- 问题类型：`EXTREMA_POS`
- 领域 / 子数据集：`Energy` / `timemmd`
- 数值摘要：n=512, min=0.993, max=1.791, mean=1.2973, std=0.18544, slope=0.00081632, argmax=425, argmin=308
- 标注特征：`{'ambiguous': False, 'argmax_idx': 425, 'bucket': 'last', 'rel_position': 0.8317025440313112}`

![tsshapeqa::0005::timemmd:Energy:Weekly_New_England_(:w512:s0](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/tsshapeqa_0005_timemmd_Energy_Weekly_New_England__w512_s0.png)

**QA 问题**

**题干原文**

In which third of this 512-week gasoline price series does the highest price occur?

**题干中文翻译**

这条 512 周汽油价格序列中的最高价格出现在哪三分之一时段？
- 选项：
- A. last third
  中文：A. 最后三分之一
- B. cannot determine from data
  中文：B. 无法从数据中确定
- C. middle third
  中文：C. 中间三分之一
- D. first third
  中文：D. 前三分之一
- 正确答案：`A`

**生成的 caption 与中文翻译**

**OpenTSLM caption 原文**

The time series shows a flat trend with low volatility and a strong seasonal pattern repeating every 104 weeks. The data experiences a notable upward phase early in the window, followed by a significant downward movement in the first half, and a smaller upward trend in the second half. A peak occurs in the first half, reaching about 1.5 standard deviations above the mean, while a valley appears late in the window, about 1.2 standard deviations below the mean. The series is strongly positively correlated with weekly prices from the New England region.

**OpenTSLM caption 中文翻译**

该时间序列呈现低波动的平稳趋势，并具有每 104 周重复一次的强季节性模式。数据在窗口早期经历了显著上升阶段，随后在前半段出现明显下行，并在后半段呈现较小幅度的上升趋势。一个峰值出现在前半段，达到高于均值约 1.5 个标准差的位置；一个谷值出现在窗口后期，约低于均值 1.2 个标准差。该序列与新英格兰地区的周价格呈强正相关。

**ChatTS caption 原文**

The overall trend is increasing. The global maximum, approximately 1.56, occurs around point 511, which is in the last third of the 512-point window. Short-term fluctuations are more pronounced in the first half (points 1–256) due to a higher-frequency sinusoidal pattern with a period of ~100 points, compared to a longer period of ~194 points in the second half (points 257–512).

**ChatTS caption 中文翻译**

整体趋势是上升的。全局最大值约为 1.56，出现在点 511 附近，位于 512 点窗口的后三分之一。由于前半部分（点 1–256）存在周期约为 100 点的较高频率正弦模式，而后半部分（点 257–512）的周期较长，约为 194 点，因此前半部分的短期波动更为明显。

**OpenTSLM Q3-format SFT caption 原文**

The time series shows a flat trend with high volatility and no clear seasonality. The data starts with a moderate upward movement in the early part of the window, followed by a stronger increase in the first half, and a significant rise in the second half. A peak occurs late in the window, reaching about 3.0 standard deviations above the mean, while a valley is observed early on, about 1.9 standard deviations below the mean. The series has a strong positive correlation with another gas price variable, PADD 1B.

**OpenTSLM Q3-format SFT caption 中文翻译**

该时间序列表现为趋势平稳、波动性高，且没有明显季节性。数据在窗口早期以温和上升开始，随后在前半段出现更强的增长，并在后半段显著上升。峰值出现在窗口后期，达到约高于均值 3.0 个标准差；而谷值出现在早期，约低于均值 1.9 个标准差。该序列与另一个汽油价格变量 PADD 1B 呈强正相关。

**不同输入条件下的答案 / 评分**

| 输入条件 | 预测答案 | 结果 |
| --- | --- | --- |
| `meta_only` | `A` | 正确 |
| `numbers` | `A` | 正确 |
| `numbers_cot` | `A` | 正确；原始输出见下方；源 artifact 似乎只保留了输出片段 |
| `opentslm_caption` | `D` | 错误 |
| `opentslm_caption_plus` | `C` | 错误 |
| `chatts_caption` | `A` | 正确 |
| `chatts_caption_plus` | `A` | 正确 |
| `tool_agent` | `A` | 正确 |

**模型原始输出（按源 artifact 原样展示）**

**`numbers_cot` 原始输出**

> 注：该字段在源 artifact 中已经像是从中间开始保存的片段，当前报告不再二次裁剪；无法从现有文件恢复更早的前文。

series’ maximum value is about 1.791, and it appears well after the midpoint of the 512 weeks, closer to the later portion of the data. So the highest price occurs in the last third.

Final answer: A

**`numbers_cot` 中文翻译**

序列的最大值约为 1.791，并且它出现在 512 周中点之后较远的位置，更接近数据的后半部分。因此，最高价格出现在后三分之一。

最终答案：A


**Case 分析**

- 失败标签：峰值位置被错误 caption 污染
- 关键结论：真实峰值在最后三分之一；OpenTSLM caption 写成前半段峰值，导致 caption-only 和 caption+numbers 都偏离。ChatTS 保留了最后三分之一这个关键证据。
