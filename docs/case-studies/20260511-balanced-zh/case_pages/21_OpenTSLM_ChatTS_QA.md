<details>
<summary>🧪 Case 21：TSAQA | OpenTSLM 错、ChatTS 对的混合 QA</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `TSAQA` |
| Case ID | `tsaqa::0006` |
| 问题类型 | `classification` |
| 领域 / 子数据集 | `healthcare` / `-` |
| 正确答案 | `B` |

- artifact 说明：TSAQA 此 case 已按 full-eval task 顺序和 local index 回连 phase_a 原始题干/序列；当前本地没有保存 OpenTSLM/ChatTS 原始 caption 对照文本，因此此处展示可用 SFT caption 样本和多条件答案。

数值摘要：n=80, min=-1.0853, max=1.5287, mean=-6.25e-06, std=1, slope=-0.029443, argmax=13, argmin=50

<details>
<summary>🖼 时序图</summary>

![tsaqa::0006](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/tsaqa_0006.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

Classify the given time series into one of the categories below.
Respond ONLY with the letter of the correct choice (A, B).

Choices:
A: correct
B: incorrect

**题干中文翻译**

将给定时间序列分类到以下类别之一。
仅回复正确选项的字母（A、B）。

选项：
A：正确
B：不正确

**背景信息原文**

This time series comes from a dataset capturing hand and finger bone outlines extracted from medical images to support classification and prediction tasks related to bone outline detection accuracy, subject age group estimation, and Tanner-Whitehouse developmental scoring for pediatric bone age assessment.

**背景信息中文翻译**

该时间序列来自一个数据集，该数据集捕获从医学图像中提取的手部和手指骨骼轮廓，用于支持与骨骼轮廓检测准确性、受试者年龄组估计以及用于儿科骨龄评估的 Tanner-Whitehouse 发育评分相关的分类和预测任务。

**选项**
无固定选项；题目要求按指定格式直接生成答案。

**正确答案**：`B`

</details>

<details>
<summary>📝 生成的 caption 与中文翻译</summary>

**可用 caption 样本 原文**

The time series has almost no noise. It exhibits square periodic fluctuations with each period lasting approximately 25.1 points and having an amplitude of 1.6. The overall trend is decreasing, starting at -0.49 and ending at -1.09, with an overall amplitude of -0.60. No local characteristics were found beyond the described periodicity and trend.

**可用 caption 样本 中文翻译**

该时间序列几乎没有噪声。它呈现方形周期性波动，每个周期大约持续 25.1 个点，振幅为 1.6。整体趋势呈下降，从 -0.49 开始，到 -1.09 结束，整体幅度为 -0.60。除上述周期性和趋势外，未发现局部特征。

</details>

<details>
<summary>🧪 下游 QA 模型答案 / 评分</summary>

| 输入条件 | 预测答案 | 结果 |
| --- | --- | --- |
| `meta_only` | `A` | 错误 |
| `numbers` | `B` | 正确 |
| `opentslm_caption` | `A` | 错误 |
| `opentslm_caption_plus` | `B` | 正确 |
| `chatts_caption` | `B` | 正确 |
| `chatts_caption_plus` | `A` | 错误 |
| `tool_agent` | `B` | 正确 |

</details>

<details>
<summary>🔎 Case 分析</summary>

- 失败标签：OpenTSLM 错、ChatTS 对的混合 QA
- 关键结论：医疗骨轮廓分类问题中，ChatTS caption 与 numbers 能答对，OpenTSLM caption 答错；说明 caption 质量差异会直接转化为分类失败。

</details>

</details>
