# LTSGen Case Study 折叠显示预览

这个文件只用于预览 GitHub Markdown 的 details/summary 折叠效果。主报告暂时没有改动。

设计目标：

- 每个 case 是一个外层折叠块。
- 图像、QA、caption、下游 QA 模型答案、case 分析分别作为内层折叠块。
- 文本保持普通 Markdown 展示，不使用 fenced code block 包裹普通文本。
- 后续如果效果合适，可以把 `balanced_case_study_zh_notion.md` 中的 27 个 case 都改成这种结构。

---

<details>
<summary>📈 Case 01：TSShapeQA-OOD | mixed trend 被压缩成 flat/upward</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `TSShapeQA-OOD` |
| Case ID | `tsshapeqa::0008::exchange_rate:5:w384:s3456` |
| 问题类型 | `TREND` |
| 领域 / 子数据集 | `finance` / `exchange_rate` |
| 正确答案 | `B` |

数值摘要：n=384, min=0.008729, max=0.010699, mean=0.0093172, std=0.00025239, slope=7.1632e-07, argmax=204, argmin=44

<details>
<summary>🖼 时序图</summary>

![tsshapeqa::0008::exchange_rate:5:w384:s3456](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/tsshapeqa_0008_exchange_rate_5_w384_s3456.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

Across the full period, what is the overall direction of this exchange-rate series?

**题干中文翻译**

在整个时期内，该汇率序列的整体走势方向是什么？

**选项**

- A. Steadily decreasing overall
  中文：A. 整体稳步下降
- B. Mixed, with no consistent direction
  中文：B. 混合变化，没有一致方向
- C. Steadily increasing overall
  中文：C. 整体稳步上升
- D. Roughly flat with minor noise
  中文：D. 大致平稳，仅有轻微噪声

</details>

<details>
<summary>📝 生成的 caption 与中文翻译</summary>

<details>
<summary>OpenTSLM caption</summary>

**原文**

7. The time series shows a strong seasonal pattern with a period of 40 time units, and a gradual upward trend over the entire window. The early part of the series experiences a significant increase, followed by a moderate rise in the first half, and a slight flattening in the second half. A notable peak occurs in the second half, reaching about 1.5 standard deviations above the mean, while a deep valley is observed early in the window, about 1.8 standard deviations below the mean. The series is strongly correlated with variables 6 and 3, showing strong positive relationships.

**中文翻译**

7. 该时间序列呈现出明显的季节性模式，周期为 40 个时间单位，并且在整个窗口内呈现逐渐上升的趋势。序列早期出现显著增长，随后在前半段中等幅度上升，在后半段略有趋平。后半段出现一个显著峰值，达到均值以上约 1.5 个标准差；而窗口早期观察到一个深谷，约低于均值 1.8 个标准差。该序列与变量 6 和变量 3 强相关，表现出很强的正相关关系。

</details>

<details>
<summary>ChatTS caption</summary>

**原文**

The overall trend is flat, with no significant changes in value throughout the time series. The global maximum, which is consistently around 0.01, is present throughout the entire window, indicating no specific peak position. There are no short-term fluctuations observed in either half of the window. In summary, the time series exhibits a steady trend with no notable peaks or fluctuations.

**中文翻译**

整体趋势平稳，在整个时间序列中数值没有显著变化。全局最大值始终约为 0.01，贯穿整个窗口，表明没有特定的峰值位置。在窗口的任一半段都未观察到短期波动。总之，该时间序列表现出稳定趋势，没有明显峰值或波动。

</details>

</details>

<details>
<summary>🧪 不同输入条件下的下游 QA 模型答案</summary>

| 输入条件 | 预测答案 | 结果 |
| --- | --- | --- |
| `meta_only` | `B` | 正确 |
| `numbers` | `B` | 正确 |
| `numbers_cot` | `D` | 错误；源 artifact 似乎只保留了输出片段 |
| `opentslm_caption` | `C` | 错误 |
| `opentslm_caption_plus` | `C` | 错误 |
| `chatts_caption` | `D` | 错误 |
| `chatts_caption_plus` | `D` | 错误 |
| `tool_agent` | `B` | 正确 |

**说明**

- `opentslm_caption`：下游 QA 模型只看到 OpenTSLM 生成的 caption。
- `chatts_caption`：下游 QA 模型只看到 ChatTS 生成的 caption。
- `numbers`：下游 QA 模型直接看到原始时序数值。
- `caption_plus`：下游 QA 模型同时看到 caption 和原始数值。

</details>

<details>
<summary>🔎 Case 分析</summary>

- 失败标签：mixed trend 被压缩成 flat/upward
- 关键结论：真实答案需要识别完整窗口内的 mixed movement；OpenTSLM 把它写成上升和季节性，ChatTS 把它写成平坦，两个 caption 都没有保留可回答 QA 的趋势证据。
- 对导师讨论的含义：这个 case 说明失败不是 caption 文笔不流畅，而是自然语言中间表示没有稳定保留 answer-supporting evidence。

</details>

</details>

---

<details>
<summary>🗄 Case 07：Dataset-A | Oracle 局部 spike 被幻觉成 seasonality</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `dataset_a` |
| Case ID | `dataset_a::0000` |
| 问题类型 | `noise,local,season,local-inductive` |
| 能力标签 | `noise`, `local`, `season`, `local-inductive` |

数值摘要：n=256, min=0, max=4.2794, mean=0.016716, std=0.26694, slope=0.00030456, argmax=227, argmin=0

<details>
<summary>🖼 时序图</summary>

![dataset_a::0000](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/dataset_a_0000.png)

</details>

<details>
<summary>🏷 标注属性与正确答案</summary>

**Dataset-A 标注属性中文**

- 几乎没有噪声。
- 局部特征：point 226 附近有 upward spike，幅度约 4.28。
- 周期性：无周期性波动。
- 领域解释：数据库正在经历与 enqueue resources 相关的严重争用问题。

**正确答案中文**

1. 几乎没有噪声，整体噪声标准差约为 0.00。
2. 向上尖峰，位置约在 point 226，幅度为 4.28。
3. 无周期性波动。
4. 向上尖峰，位置约在 point 226，幅度为 4.28。数据库正经历与入队资源相关的严重争用问题。

</details>

<details>
<summary>❓ QA 问题摘要</summary>

题目要求模型分析 Oracle Database System 中 `"##enq: SQ - contention"` 这条长度为 256 的时间序列，并按固定格式回答四类问题：

- 噪声特征：noisy / almost no noise。
- 局部特征波动：需要给出类型、位置和幅度。
- 周期性：periodic fluctuation / no periodic fluctuation。
- 局部特征及其物理含义：需要把形态和数据库争用语义联系起来。

</details>

<details>
<summary>📝 生成的 caption 与中文翻译</summary>

<details>
<summary>OpenTSLM caption</summary>

**原文**

The time series shows a flat trend with low volatility and a strong seasonal pattern repeating every 180 time units. There is a noticeable upward phase early in the window followed by a significant downward movement in the first half, then a smaller upward trend in the second half. A peak occurs in the first half with a magnitude of about 1.6 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 1.7 standard deviations from the mean. The series exhibits strong negative correlation with the "SQ - contention" variable.

**中文翻译**

该时间序列呈现平稳趋势，波动性较低，并具有每 180 个时间单位重复一次的强季节性模式。窗口早期有一个明显的上升阶段，随后在前半段出现显著下降，之后在后半段出现较小的上升趋势。前半段出现一个峰值，幅度约为偏离均值 1.6 个标准差；窗口早期观察到一个谷值，幅度约为偏离均值 1.7 个标准差。该序列与“SQ - contention”变量表现出强负相关。

</details>

<details>
<summary>ChatTS caption</summary>

**原文**

1) almost no noise 2) no periodic fluctuation 3) keep steady 4) upward spike, position around point 226, amplitude 4.28

**中文翻译**

1) 几乎没有噪声 2) 无周期性波动 3) 保持稳定 4) 向上尖峰，位置约在 point 226，幅度 4.28

</details>

</details>

<details>
<summary>🧪 不同输入条件下的下游 QA 模型评分</summary>

| 条件 | 平均分 | 分项分数 |
| --- | ---: | --- |
| `opentslm_meta_only` | 0.50 | local=0.00，local-inductive=0.00，noise=1.00，season=1.00 |
| `opentslm_numbers` | 0.50 | local=0.00，local-inductive=0.00，noise=1.00，season=1.00 |
| `opentslm_caption` | 0.25 | local=0.00，local-inductive=0.00，noise=1.00，season=0.00 |
| `opentslm_caption_plus` | 0.95 | local=0.97，local-inductive=0.81，noise=1.00，season=1.00 |
| `chatts_caption` | 0.96 | local=1.00，local-inductive=0.83，noise=1.00，season=1.00 |
| `chatts_caption_plus` | 0.96 | local=1.00，local-inductive=0.83，noise=1.00，season=1.00 |

</details>

<details>
<summary>🔎 Case 分析</summary>

- 失败标签：Oracle 局部 spike 被幻觉成 seasonality。
- 关键结论：真实属性是 point 226 的 upward spike，领域含义是 enqueue 资源争用；OpenTSLM 编造了 180-step seasonality 和多处事件，ChatTS 保留了关键局部事实。
- 对导师讨论的含义：OpenTSLM 的 caption 不是“信息少”，而是看起来完整但事实不稳；这会直接污染下游 QA。

</details>

</details>

---

## 如果这个效果可接受，主报告可以这样改

<details>
<summary>🧭 后续批量改造方案</summary>

1. 保留主报告开头的采样覆盖、阅读方式和全局分析。
2. 把每个 `### Case xx` 改成一个外层 details 折叠块。
3. 每个 case 内部统一拆成 5 个内层折叠块：
   - 🖼 时序图
   - ❓ QA 问题与中文翻译
   - 📝 caption 与中文翻译
   - 🧪 下游 QA 模型答案 / 评分
   - 🔎 Case 分析
4. Dataset-A/FREDQA 这种长题干 case，默认只在摘要里展示问题类型，把完整题干放进折叠块。
5. 保持普通 Markdown 文本，不使用代码块包裹普通文本。

</details>
