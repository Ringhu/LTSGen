<details>
<summary>🧪 Case 23：TSAQA | TSAQA comparison：两个 caption 都错，numbers/tool 对</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `TSAQA` |
| Case ID | `tsaqa::0677` |
| 问题类型 | `comparison` |
| 领域 / 子数据集 | `["web", "web"]` / `-` |
| 正确答案 | `B` |

- artifact 说明：TSAQA 此 case 已按 full-eval task 顺序和 local index 回连 phase_a 原始题干/序列；当前本地没有保存 OpenTSLM/ChatTS 原始 caption 对照文本，因此此处展示可用 SFT caption 样本和多条件答案。

数值摘要：n=406, min=-1.8571, max=7.6106, mean=2.4631e-06, std=1, slope=0.00012909, argmax=318, argmin=168

<details>
<summary>🖼 时序图</summary>

![tsaqa::0677](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/tsaqa_0677.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

Which time series exhibits a stronger positive local trend based on visible upward spikes in the data?
Respond ONLY with the letter of the correct choice (A, B, C, or D).

Choices:
A: Time Series 1
B: Time Series 2
C: Both exhibit equal strength
D: Neither exhibits a positive local trend

**题干中文翻译**

哪条时间序列基于数据中可见的向上尖峰表现出更强的正向局部趋势？
请仅用正确选项的字母作答（A、B、C 或 D）。

选项：
A：时间序列 1
B：时间序列 2
C：两者表现出相同强度
D：两者都没有表现出正向局部趋势

**背景信息原文**

["A time series of daily page\u2010view counts for a single English Wikipedia article.", "A time series of daily page\u2010view counts for a single English Wikipedia article."]

**背景信息中文翻译**

["单篇英文维基百科文章每日页面浏览次数的时间序列。", "单篇英文维基百科文章每日页面浏览次数的时间序列。"]

**选项**
无固定选项；题目要求按指定格式直接生成答案。

**正确答案**：`B`

</details>

<details>
<summary>📝 生成的 caption 与中文翻译</summary>

**可用 caption 样本 原文**

1. Noisy with std around 0.62.
2. No periodic fluctuations observed, showing no periodic fluctuation.
3. Keep steady from -0.50 to -0.50.
4. At point 152 and point 155 and point 159, there were 3 consecutive upward spikes with amplitudes ranging from 2.39 to 3.04, with the time series value repeatedly rising sharply from around -0.50 to around 1.89 and 2.47 and 1.9, and then quickly falling back to around -0.50, forming a continuous upward spike;at point 298 and point 302 and point 309 and point 314 and point 320, there were 5 consecutive upward spikes with amplitudes ranging from 3.89 to 7.47, with the time series value repeatedly rising sharply from around -0.50 to around 5.77 and 3.39 and 7.24 and 6.94 and 4.37, and then quickly falling back to around -0.50, forming a continuous upward spike.

**可用 caption 样本 中文翻译**

1. 含噪声，标准差约为 0.62。
2. 未观察到周期性波动，表现为无周期性波动。
3. 从 -0.50 到 -0.50 保持稳定。
4. 在点 152、点 155 和点 159，出现了 3 个连续的向上尖峰，幅度范围为 2.39 到 3.04，时间序列值反复从约 -0.50 急剧上升到约 1.89、2.47 和 1.9，然后迅速回落到约 -0.50，形成连续的向上尖峰；在点 298、点 302、点 309、点 314 和点 320，出现了 5 个连续的向上尖峰，幅度范围为 3.89 到 7.47，时间序列值反复从约 -0.50 急剧上升到约 5.77、3.39、7.24、6.94 和 4.37，然后迅速回落到约 -0.50，形成连续的向上尖峰。

</details>

<details>
<summary>🧪 下游 QA 模型答案 / 评分</summary>

| 输入条件 | 预测答案 | 结果 |
| --- | --- | --- |
| `meta_only` | `C` | 错误 |
| `numbers` | `B` | 正确 |
| `opentslm_caption` | `C` | 错误 |
| `opentslm_caption_plus` | `A` | 错误 |
| `chatts_caption` | `C` | 错误 |
| `chatts_caption_plus` | `A` | 错误 |
| `tool_agent` | `B` | 正确 |

</details>

<details>
<summary>🔎 Case 分析</summary>

- 失败标签：TSAQA comparison：两个 caption 都错，numbers/tool 对
- 关键结论：问题要求判断哪个序列有更强的正向局部趋势。两个 caption 模型都未能把 upward spikes 的相对强弱编码清楚，raw numbers 和 tool-agent 可以恢复答案。

</details>

</details>
