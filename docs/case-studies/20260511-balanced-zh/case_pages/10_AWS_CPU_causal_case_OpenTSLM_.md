### Case 10：AWS CPU causal case：OpenTSLM 丢失因果条件

- 数据集：`dataset_a`
- Case ID：`dataset_a::0073`
- 问题类型：`causal`
- Dataset-A 能力标签：`causal`
- 数值摘要：n=256, min=30.482, max=51.6, mean=44.588, std=2.1897, slope=-0.0019699, argmax=129, argmin=128
- Dataset-A 标注属性：`['Routine operations with minor fluctuations. The time series indicates that despite a generally stable trend, there are small fluctuations near point 127, which could suggest standard variation due to routine operational activities rather than unusual events like hardware malfunctions or system updates.']`

![dataset_a::0073](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/dataset_a_0073.png)

**QA 问题**

- 原文：You are a time series analysis expert. This time series is "CPU Usage" from AWS API servers with length of 256: <ts><ts/>, please analyze the time series features and answer the following questions:
1. Given the time series for CPU Usage from AWS API servers, what is the most plausible explanation for the behavior observed near time point 127? Choose from: hardware malfunction, routine operations with minor fluctuations, or significant system update.
Now, based on the above questions, please strictly follow the output format requirements and provide the answers. Each line corresponds to an answer to a question, formatted as:1. Strictly formatted answer 1
- 中文翻译：你是时间序列分析专家。该时间序列是来自 AWS API 服务器的“CPU Usage”，长度为 256：<ts><ts/>，请分析该时间序列特征并回答以下问题：
1. 给定来自 AWS API 服务器的 CPU Usage 时间序列，在时间点 127 附近观察到的行为最可能的解释是什么？从以下选项中选择：硬件故障、伴随轻微波动的常规操作，或重大系统更新。
现在，请基于上述问题，严格遵循输出格式要求并提供答案。每一行对应一个问题的答案，格式为：1. 严格格式化的答案 1
- 选项：
-
- 正确答案：`1. Routine operations with minor fluctuations. The time series indicates that despite a generally stable trend, there are small fluctuations near point 127, which could suggest standard variation due to routine operational activities rather than unusual events like hardware malfunctions or system updates.
`

**生成的 caption 与中文翻译**

**OpenTSLM caption 原文**

The time series shows a flat trend with low volatility and medium strength seasonality every 100 time units. Early in the window, there is a significant upward phase followed by a sharp downward movement, with a peak that stands out as about 2.1 standard deviations above the mean. The data exhibits strong positive correlation with temperature and moderate positive correlation with humidity.

**OpenTSLM caption 中文翻译**

该时间序列呈现平稳趋势，波动性较低，并且每 100 个时间单位表现出中等强度的季节性。在窗口早期，存在一个显著的上升阶段，随后出现急剧下降，并有一个峰值明显高于均值约 2.1 个标准差。数据与温度表现出强正相关，与湿度表现出中等正相关。

**ChatTS caption 原文**

1. Noisy with std around 3.12.
2. No periodic fluctuations observed, showing no periodic fluctuation.
3. Keep steady from 44.92 to 44.92.
4. A downward spike with an amplitude of 14.21 occurred between point 128 and point 130, with the time series value rapidly falling from around 44.92 to around 30.71 and then quickly rising back to around 44.92, forming a downward spike.

**ChatTS caption 中文翻译**

1. 噪声标准差约为 3.12。
2. 未观察到周期性波动，显示无周期性波动。
3. 保持稳定，从 44.92 到 44.92。
4. 在点 128 和点 130 之间发生了一次幅度为 14.21 的向下尖峰，时间序列值从约 44.92 快速下降到约 30.71，然后迅速回升到约 44.92，形成向下尖峰。

**不同输入条件下的答案 / 评分**

| 条件 | 平均分 | 分项分数 |
| --- | ---: | --- |
| `opentslm_caption` | 0.00 | causal=0.00 |
| `opentslm_caption_plus` | 0.00 | causal=0.00 |
| `opentslm_numbers` | 1.00 | causal=1.00 |
| `chatts_caption` | 1.00 | causal=1.00 |
| `chatts_caption_plus` | 1.00 | causal=1.00 |
| `chatts_numbers` | 1.00 | causal=1.00 |

**代表性模型回答**

- `opentslm_caption` 原文：1. significant system update
  中文：1. 重大系统更新
- `opentslm_caption_plus` 原文：1. significant system update
  中文：1. 重要系统更新
- `opentslm_numbers` 原文：1. routine operations with minor fluctuations
  中文：1. 常规操作，伴有轻微波动
- `chatts_caption` 原文：1. routine operations with minor fluctuations
  中文：1. 常规运行，伴有轻微波动
- `chatts_caption_plus` 原文：1. routine operations with minor fluctuations
  中文：常规运行，伴有轻微波动
- `chatts_numbers` 原文：1. routine operations with minor fluctuations
  中文：1. 常规运行，伴有小幅波动

**Case 分析**

- 失败标签：AWS CPU causal case：OpenTSLM 丢失因果条件
- 关键结论：此类题目要求把形态变化和系统负载/服务事件联系起来；OpenTSLM caption 条件为 0 分而 ChatTS 为 1 分，说明领域因果语义不是自然从形态摘要中涌现。
