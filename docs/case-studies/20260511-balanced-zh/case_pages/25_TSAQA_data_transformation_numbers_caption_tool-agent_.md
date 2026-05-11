### Case 25：TSAQA data transformation：numbers/caption 都错，tool-agent 对

- 数据集：`TSAQA`
- Case ID：`tsaqa::0858`
- 问题类型：`data_transformation`
- 领域 / 子数据集：`["finance", "nature"]` / `-`
- artifact 说明：TSAQA 此 case 已按 full-eval task 顺序和 local index 回连 phase_a 原始题干/序列；当前本地没有保存 OpenTSLM/ChatTS 原始 caption 对照文本，因此此处展示可用 SFT caption 样本和多条件答案。
- 数值摘要：n=60, min=-1.8082, max=1.7084, mean=3.3333e-06, std=1, slope=0.056825, argmax=59, argmin=0

![tsaqa::0858](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/tsaqa_0858.png)

**QA 问题**

- 原文：Is the following sequence the Fourier Transform of the given time series?
[0, 13.7297, 33.7742, 18.4157, 4.0489, 3.7777, 1.4631, 2.522, 1.5447, 1.2527, 3.8876, 3.288, 2.882, 1.1669, 3.6571, 2.2853, 3.1854, 1.8801, 1.3621, 0.9566, 0.6499, 0.3914, 0.3976, 1.8261, 1.0968, 1.3006, 0.624, 1.7817, 2.3862, 0.7909, 1.4543, 0.7909, 2.3862, 1.7817, 0.624, 1.3006, 1.0968, 1.8261, 0.3976, 0.3914, 0.6499, 0.9566, 1.3621, 1.8801, 3.1854, 2.2853, 3.6571, 1.1669, 2.882, 3.288, 3.8876, 1.2527, 1.5447, 2.522, 1.4631, 3.7777, 4.0489, 18.4157, 33.7742, 13.7297]
Respond ONLY with the letter of the correct choice (T or F).

Choices:
T: True.
F: False.
- 中文翻译：这个序列是给定时间序列的傅里叶变换吗？
[0, 13.7297, 33.7742, 18.4157, 4.0489, 3.7777, 1.4631, 2.522, 1.5447, 1.2527, 3.8876, 3.288, 2.882, 1.1669, 3.6571, 2.2853, 3.1854, 1.8801, 1.3621, 0.9566, 0.6499, 0.3914, 0.3976, 1.8261, 1.0968, 1.3006, 0.624, 1.7817, 2.3862, 0.7909, 1.4543, 0.7909, 2.3862, 1.7817, 0.624, 1.3006, 1.0968, 1.8261, 0.3976, 0.3914, 0.6499, 0.9566, 1.3621, 1.8801, 3.1854, 2.2853, 3.6571, 1.1669, 2.882, 3.288, 3.8876, 1.2527, 1.5447, 2.522, 1.4631, 3.7777, 4.0489, 18.4157, 33.7742, 13.7297]
只回复正确选项的字母（T 或 F）。

选项：
T: 正确。
F: 错误。
- 背景信息中文：["某一条美国经济时间序列的月度宏观经济指标测量时间序列。", "某一 1.5°×1.5° 经纬网格单元的每日降水测量时间序列（毫米）。"]
- 选项：
-
- 正确答案：`F`

**生成的 caption 与中文翻译**

**可用 caption 样本 原文**

1) almost no noise 2) no periodic fluctuation 3) increase from -1.81 to 1.71 4) No local features found.

**可用 caption 样本 中文翻译**

1) 几乎没有噪声 2) 没有周期性波动 3) 从 -1.81 增加到 1.71 4) 未发现局部特征。

**不同输入条件下的答案 / 评分**

| 输入条件 | 预测答案 | 结果 |
| --- | --- | --- |
| `meta_only` | `T` | 错误 |
| `numbers` | `T` | 错误 |
| `opentslm_caption` | `T` | 错误 |
| `opentslm_caption_plus` | `T` | 错误 |
| `chatts_caption` | `T` | 错误 |
| `chatts_caption_plus` | `T` | 错误 |
| `tool_agent` | `F` | 正确 |

**Case 分析**

- 失败标签：TSAQA data transformation：numbers/caption 都错，tool-agent 对
- 关键结论：该题判断 Fourier transform 序列真伪。numbers 和两个 caption 条件都答错，但 tool-agent 答对，说明这类题需要显式计算工具，而不是语言模型凭描述判断。
