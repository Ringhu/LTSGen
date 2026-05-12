# FREDQA 原生多变量 caption 重跑报告

本报告用于回答一个具体问题：OpenTSLM/ChatTS 是否应该用原生多变量 caption 方式重跑，而不是把 FREDQA 拆成逐变量 caption 后再拼回 QA prompt。正文为中文；caption 原文保留英文，并提供中文翻译。

## 实验口径

- `OpenTSLM fixed per-variable`：修复旧脚本的 shape bug 后重跑逐变量 caption。旧脚本把单变量序列传成 `[1, T]`，这轮改为 `[T, 1]`。
- `OpenTSLM native multivariate`：使用 `mixed_from_forecasting/stage2_captioning/checkpoints/best_model.pt`，每个 QA 样本一次性输入 `[T, D]`。
- `ChatTS native multivariate`：在一个 prompt 中放多个 `<ts><ts/>` token，并传入多个时间序列；这是 ChatTS processor 支持的多时间序列输入形式。
- 下游 QA 模型固定为 `gpt-5.4`；八个条件只改变输入证据。
- 远程运行在 A100 的 GPU 2；GPU 1 存在 ECC 异常，本轮没有使用。

## Artifact 完整性

- QA 样本数：`604`。
- 逐变量 caption 输入：`1393` 条。
- OpenTSLM 修正逐变量 caption：`1393` 条。
- OpenTSLM 原生多变量 caption：`604` 条。
- ChatTS 原生多变量 caption：`604` 条。
- GPT QA 预测：`4832` 条，对应 `604 × 8` 个条件。

## 统计图

![去掉 meta-only 后原生多变量救回率](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_hard_subset_rescue.png)

![按变量数准确率](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_by_nvars_accuracy.png)

![按问题类型准确率](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_by_attribute_accuracy.png)

## 核心统计：去掉 meta-only 可答对题后，原生多变量能答对多少

过滤规则：先去掉 `meta_only` 能答对的题，只保留 `meta_only` 答错的 `119` 个 hard cases。下面统计的是在这些题上，原生多变量 caption 条件到底能救回多少。

| 统计口径 | 条件 | 答对/剩余题数 | 比例 | 含义 |
| --- | --- | ---: | ---: | --- |
| OpenTSLM 原生多变量 caption | `opentslm_native_caption` | 19/119 | 15.97% | 只给原生多变量 caption；衡量 OpenTSLM native caption 本身能否提供足够证据。 |
| OpenTSLM 原生多变量 caption + 数值 | `opentslm_native_caption_plus` | 27/119 | 22.69% | 原生 caption 和 raw numbers 混合；衡量 caption 是否能辅助数值输入。 |
| ChatTS 原生多变量 caption | `chatts_native_caption` | 24/119 | 20.17% | ChatTS 多 `&lt;ts&gt;` prompt 的 caption-only 效果。 |
| ChatTS 原生多变量 caption + 数值 | `chatts_native_caption_plus` | 34/119 | 28.57% | ChatTS 原生 caption 与 raw numbers 混合后的效果；这是 hard subset 中最强条件。 |
| 任一原生多变量 caption-only 能答对 | `opentslm_native_caption ∪ chatts_native_caption` | 31/119 | 26.05% | 表示只要换成两个原生多变量 captioner 之一，最多能救回多少 meta-only 错题。 |
| 任一原生多变量 caption+numbers 能答对 | `opentslm_native_caption_plus ∪ chatts_native_caption_plus` | 39/119 | 32.77% | 表示原生多变量 caption 与数值联合时的可救回上限。 |

**直接结论**：在 `119` 个 meta-only 答错题里，OpenTSLM 原生多变量 caption-only 能答对 `19` 题（15.97%），ChatTS 原生多变量 caption-only 能答对 `24` 题（20.17%）。如果允许 caption + raw numbers，ChatTS native 条件最高，能答对 `34/119`（28.57%）。

| 交集/差集口径 | 数量 | 占 hard subset 比例 | 含义 |
| --- | ---: | ---: | --- |
| 两个原生 caption-only 都答对 | 12 | 10.08% | 两种 captioner 在同一 hard case 上都提供了足够证据。 |
| 只有 OpenTSLM native caption-only 答对 | 7 | 5.88% | OpenTSLM 原生多变量相对 ChatTS 的独有正例。 |
| 只有 ChatTS native caption-only 答对 | 12 | 10.08% | ChatTS 原生多变量相对 OpenTSLM 的独有正例。 |
| 两个原生 caption-only 都答错 | 88 | 73.95% | caption-only 仍不能解决的主要失败池。 |
| 两个原生 caption+numbers 都答对 | 22 | 18.49% | 加上 raw numbers 后两种原生 caption 条件都能答对。 |
| 两个原生 caption+numbers 都答错 | 80 | 67.23% | 即使给原生 caption 和 raw numbers 也不能解决的 hard cases。 |

## 辅助对照：hard subset 上八种输入条件的准确率

这一表保留所有输入条件，便于和 `numbers`、逐变量 caption 对照；主结论仍以上一节原生多变量救回率为准。

| 输入条件 | 正确/总数 | Accuracy | 相对 meta_only | 相对 numbers | 统计含义 |
| --- | ---: | ---: | ---: | ---: | --- |
| 只给题目和选项 (`meta_only`) | 0/119 | 0.00% | +0.00 pp | -23.53 pp | 只看题干、选项和领域先验；不代表模型读懂时间序列。 |
| 题目 + 原始数值序列 (`numbers`) | 28/119 | 23.53% | +23.53 pp | +0.00 pp | 直接给原始数值后的参照；若仍低，说明长数值输入本身也难以稳定计算。 |
| 题目 + OpenTSLM 修正逐变量 caption (`opentslm_fixed_caption`) | 21/119 | 17.65% | +17.65 pp | -5.88 pp | 修正 shape 后的逐变量 OpenTSLM caption；检验旧 per-variable 方案本身是否有效。 |
| 题目 + OpenTSLM 修正逐变量 caption + 数值 (`opentslm_fixed_caption_plus`) | 29/119 | 24.37% | +24.37 pp | +0.84 pp | 逐变量 caption 与数值混合；检验 caption 是否能辅助 raw numbers。 |
| 题目 + OpenTSLM 原生多变量 caption (`opentslm_native_caption`) | 19/119 | 15.97% | +15.97 pp | -7.56 pp | OpenTSLM 原生多变量 checkpoint 一次性生成 caption；检验跨变量摘要是否更好。 |
| 题目 + OpenTSLM 原生多变量 caption + 数值 (`opentslm_native_caption_plus`) | 27/119 | 22.69% | +22.69 pp | -0.84 pp | OpenTSLM 原生多变量 caption 与数值混合；检验证据融合是否单调。 |
| 题目 + ChatTS 原生多变量 caption (`chatts_native_caption`) | 24/119 | 20.17% | +20.17 pp | -3.36 pp | ChatTS 在一个 prompt 中放多个 `&lt;ts&gt;` token；检验其多序列提示能力。 |
| 题目 + ChatTS 原生多变量 caption + 数值 (`chatts_native_caption_plus`) | 34/119 | 28.57% | +28.57 pp | +5.04 pp | ChatTS 原生多变量 caption 与数值混合；检验 ChatTS 线索是否会被 numbers 干扰。 |

## 辅助对照：全量 604 题准确率

全量准确率会被题干和选项先验抬高，因为 `meta_only` 单独就能答对大量问题；这里仅作为背景，不作为主要结论。

| 输入条件 | 正确/总数 | Accuracy | 相对 meta_only | 相对 numbers | 统计含义 |
| --- | ---: | ---: | ---: | ---: | --- |
| 只给题目和选项 (`meta_only`) | 485/604 | 80.30% | +0.00 pp | -1.66 pp | 只看题干、选项和领域先验；不代表模型读懂时间序列。 |
| 题目 + 原始数值序列 (`numbers`) | 495/604 | 81.95% | +1.66 pp | +0.00 pp | 直接给原始数值后的参照；若仍低，说明长数值输入本身也难以稳定计算。 |
| 题目 + OpenTSLM 修正逐变量 caption (`opentslm_fixed_caption`) | 486/604 | 80.46% | +0.17 pp | -1.49 pp | 修正 shape 后的逐变量 OpenTSLM caption；检验旧 per-variable 方案本身是否有效。 |
| 题目 + OpenTSLM 修正逐变量 caption + 数值 (`opentslm_fixed_caption_plus`) | 497/604 | 82.28% | +1.99 pp | +0.33 pp | 逐变量 caption 与数值混合；检验 caption 是否能辅助 raw numbers。 |
| 题目 + OpenTSLM 原生多变量 caption (`opentslm_native_caption`) | 490/604 | 81.13% | +0.83 pp | -0.83 pp | OpenTSLM 原生多变量 checkpoint 一次性生成 caption；检验跨变量摘要是否更好。 |
| 题目 + OpenTSLM 原生多变量 caption + 数值 (`opentslm_native_caption_plus`) | 496/604 | 82.12% | +1.82 pp | +0.17 pp | OpenTSLM 原生多变量 caption 与数值混合；检验证据融合是否单调。 |
| 题目 + ChatTS 原生多变量 caption (`chatts_native_caption`) | 488/604 | 80.79% | +0.50 pp | -1.16 pp | ChatTS 在一个 prompt 中放多个 `&lt;ts&gt;` token；检验其多序列提示能力。 |
| 题目 + ChatTS 原生多变量 caption + 数值 (`chatts_native_caption_plus`) | 504/604 | 83.44% | +3.15 pp | +1.49 pp | ChatTS 原生多变量 caption 与数值混合；检验 ChatTS 线索是否会被 numbers 干扰。 |

全量下 OpenTSLM 修正逐变量 caption 为 `80.46%`，OpenTSLM 原生多变量 caption 为 `81.13%`，差值 `+0.66 pp`。ChatTS 原生多变量 caption 为 `80.79%`。

## 关键错误/救回模式

| 模式 | 数量 | 占 QA 比例 | 背后含义 |
| --- | ---: | ---: | --- |
| OpenTSLM fixed 错、OpenTSLM native 对 | 17 | 2.81% | 原生多变量 caption 有可能保留逐变量摘要丢掉的关系信息。 |
| OpenTSLM fixed 对、OpenTSLM native 错 | 13 | 2.15% | 把多变量压成一个 caption 也可能牺牲变量级细节。 |
| OpenTSLM fixed 错、ChatTS native 对 | 21 | 3.48% | ChatTS 的多 token prompt 在部分样本上比 OpenTSLM 逐变量更可用。 |
| OpenTSLM native 错、ChatTS native 对 | 17 | 2.81% | OpenTSLM 原生多变量并不自动成为最强 captioner。 |
| 两个原生多变量 caption 都错，但 numbers 对 | 11 | 1.82% | 原生多变量 caption 仍然会丢失精确计算证据。 |
| 三种 caption 都错，但 numbers 对 | 7 | 1.16% | 这是真正的 caption bottleneck：所有摘要都不如 raw numbers。 |
| meta-only 错，但 numbers 对 | 28 | 4.64% | 排除语言先验后，原始数值确实能救回的一组。 |
| meta-only 错，但 OpenTSLM fixed 对 | 21 | 3.48% | 逐变量 OpenTSLM caption 有效的正例。 |
| meta-only 错，但 OpenTSLM native 对 | 19 | 3.15% | OpenTSLM 原生多变量 caption 有效的正例。 |
| meta-only 错，但 ChatTS native 对 | 24 | 3.97% | ChatTS 原生多变量 caption 有效的正例。 |
| meta、numbers、三种 caption 全错 | 78 | 12.91% | 失败可能来自公式执行、反事实设定、领域知识或长题干定位。 |
| caption 与 numbers 全错，但 meta-only 对 | 4 | 0.66% | 该题主要被语言先验答对，时序证据反而干扰。 |

注：上述模式不是互斥集合，不能把数量直接相加。

## 按变量数分类

| 变量数 | 样本数 | meta | numbers | fixed cap | fixed cap+num | native cap | native cap+num | ChatTS native | ChatTS native+num |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 146 | 81.51% | 84.25% | 80.14% | 82.19% | 83.56% | 82.88% | 82.88% | 82.19% |
| 2 | 233 | 82.40% | 83.69% | 82.83% | 84.12% | 83.26% | 81.97% | 79.83% | 85.84% |
| 3 | 137 | 76.64% | 75.18% | 77.37% | 79.56% | 75.18% | 81.02% | 79.56% | 80.29% |
| 4 | 70 | 78.57% | 85.71% | 81.43% | 82.86% | 81.43% | 84.29% | 82.86% | 85.71% |
| 5 | 18 | 77.78% | 77.78% | 72.22% | 77.78% | 77.78% | 77.78% | 77.78% | 77.78% |

## 按问题类型分类

| 问题类型 | 样本数 | meta | numbers | fixed cap | native cap | ChatTS native | 统计解读 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 溯因推理 (`Abductive Reasoning`) | 274 | 85.04% | 85.77% | 85.77% | 85.04% | 86.13% | 用于判断不同推理类型下，原生多变量 caption 是否比逐变量 caption 更接近任务证据。 |
| 归纳推理 (`Inductive Reasoning`) | 157 | 80.25% | 82.17% | 80.89% | 80.89% | 82.17% | 用于判断不同推理类型下，原生多变量 caption 是否比逐变量 caption 更接近任务证据。 |
| 类比推理 (`Analogical Reasoning`) | 152 | 78.95% | 77.63% | 78.29% | 77.63% | 79.61% | 用于判断不同推理类型下，原生多变量 caption 是否比逐变量 caption 更接近任务证据。 |
| 因果推理：干预型 (`Causal Reasoning - Interventional`) | 118 | 85.59% | 90.68% | 89.83% | 88.98% | 88.98% | 用于判断不同推理类型下，原生多变量 caption 是否比逐变量 caption 更接近任务证据。 |
| 因果推理：反事实型 (`Causal Reasoning - Counterfactual`) | 103 | 66.02% | 69.90% | 64.08% | 67.96% | 65.05% | 用于判断不同推理类型下，原生多变量 caption 是否比逐变量 caption 更接近任务证据。 |
| 因果推理：关联型 (`Causal Reasoning - Associational`) | 84 | 86.90% | 88.10% | 85.71% | 85.71% | 83.33% | 用于判断不同推理类型下，原生多变量 caption 是否比逐变量 caption 更接近任务证据。 |
| 演绎推理 (`Deductive Reasoning`) | 69 | 78.26% | 75.36% | 76.81% | 79.71% | 79.71% | 用于判断不同推理类型下，原生多变量 caption 是否比逐变量 caption 更接近任务证据。 |
| Comparative or Analogical Reasoning (`Comparative or Analogical Reasoning`) | 1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 用于判断不同推理类型下，原生多变量 caption 是否比逐变量 caption 更接近任务证据。 |
| Analytical Reasoning (`Analytical Reasoning`) | 1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 用于判断不同推理类型下，原生多变量 caption 是否比逐变量 caption 更接近任务证据。 |

## Case Study

下面的 case 是按新重跑结果动态抽取的，每个 case 包括时序图、QA 原文和中文翻译、三类 caption 原文和中文翻译、八种输入条件下的 `gpt-5.4` 答案。

<details>
<summary>📈 Case 01: FREDQA `832` | OpenTSLM 原生多变量救回 fixed 逐变量失败</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::832` |
| 变量数 / 序列长度 | `2` / `[822, 822]` |
| 问题类型 | `Causal Reasoning - Counterfactual` |
| 正确答案 | `A` |
| 失败/对比模式 | OpenTSLM 原生多变量救回 fixed 逐变量失败 |
| 本 case 关注点 | 检验原生多变量 checkpoint 是否比逐变量 caption 更能保留跨变量证据 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | 100*(FEDMINNFRWG/CPIAUCSL), 100*(Index May 2015=100/Index May 2015=100), Monthly | 822 | 60.8749 | 99.724 | 53.524@19 | 152.935@253 | -0.0122087 |
| 2 | Federal Minimum Hourly Wage for Nonfarm Workers for the United States, Dollars per Hour, Monthly, Not Seasonally Adjusted | 822 | 0.4 | 7.25 | 0.4@0 | 7.25@750 | 0.00852341 |

<details>
<summary>🖼 时序图</summary>

![FREDQA 832](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_832.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

> You are a time series analysis expert. In a U.S. labor market context, there are 2 metrics: Real Federal Minimum Wage (100*(FEDMINNFRWG/CPIAUCSL), indexed to May 2015=100, monthly)&lt;ts&gt;&lt;ts/&gt;; Nominal Federal Minimum Wage (Federal Minimum Hourly Wage for Nonfarm Workers, dollars per hour, monthly, not seasonally adjusted)&lt;ts&gt;&lt;ts/&gt;. Data is collected monthly from January 1947 to June 2015. Congress raised the nominal minimum wage from $6.55 to $7.25 in July 2009. If this increase had not occurred (i.e., the nominal wage remained at its June 2009 level through June 2015), what would the real minimum wage have been in June 2015? Use the actual real wage in June 2015 and actual nominal wage in June 2015 from the time series to compute the counterfactual value.

**题干中文翻译**

> 你是一名时间序列分析专家。在美国劳动力市场背景下，有 2 个指标：真实联邦最低工资（100*(FEDMINNFRWG/CPIAUCSL)，以 2015 年 5 月=100 为指数，按月）&lt;ts&gt;&lt;ts/&gt;；名义联邦最低工资（非农工人的联邦每小时最低工资，美元/小时，按月，未经季节性调整）&lt;ts&gt;&lt;ts/&gt;。数据按月收集，时间范围为 1947 年 1 月至 2015 年 6 月。国会于 2009 年 7 月将名义最低工资从 6.55 美元提高到 7.25 美元。如果这一增幅没有发生（即名义工资在 2009 年 6 月的水平一直保持到 2015 年 6 月），那么 2015 年 6 月的真实最低工资会是多少？请使用时间序列中 2015 年 6 月的实际真实工资和 2015 年 6 月的实际名义工资来计算反事实值。

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Approximately 90, which is lower than the actual real wage | 约为 90，低于实际真实工资 |
| `B` | Approximately 110, which is higher than the actual real wage | 约为 110，高于实际真实工资 |
| `C` | Approximately 99.7, which is the same as the actual real wage | 约为 99.7，与实际真实工资相同 |
| `D` | Approximately 66, which is much lower than the actual real wage | 约为 66，远低于实际真实工资 |

**正确答案**：`A`

**标准解释原文**

> The real minimum wage is calculated as (Nominal Wage / CPI) * 100 (indexed to May 2015=100). To find the counterfactual real wage, we use the ratio of the counterfactual nominal wage ($6.55, June 2009 level) to the actual nominal wage ($7.25, June 2015 level), multiplied by the actual real wage (99.724, June 2015). This gives (6.55 / 7.25) * 99.724 ≈ 90.1. The counterfactual value is lower because the nominal wage would have stayed lower, while inflation (reflected in the CPI) continued to erode its purchasing power—consistent with the pattern that unindexed nominal wage increases are offset by inflation over time.

**标准解释中文翻译**

> 真实最低工资的计算公式为（名义工资 / CPI）* 100（以 2015 年 5 月=100 为指数）。为了求反事实真实工资，我们使用反事实名义工资（6.55 美元，2009 年 6 月水平）与实际名义工资（7.25 美元，2015 年 6 月水平）的比值，再乘以 2015 年 6 月的实际真实工资（99.724）。得到（6.55 / 7.25）* 99.724 ≈ 90.1。反事实值更低，因为名义工资会保持在较低水平，而通货膨胀（体现在 CPI 中）继续侵蚀其购买力——这与未按通胀指数化的名义工资上涨会随着时间被通胀抵消的模式一致。

</details>

<details>
<summary>📝 三类 caption 与中文翻译</summary>

#### OpenTSLM 修正逐变量 caption：变量 1 | 100*(FEDMINNFRWG/CPIAUCSL), 100*(Index May 2015=100/Index May 2015=100), Monthly

**原文**

> The time series shows a flat trend with low volatility and weak seasonality, characterized by a weakly negative correlation with the CPIAUCSL index. Early in the window, there is a notable upward phase followed by a significant downward movement in the first half, and a smaller upward shift in the second half. A peak occurs in the first half, reaching about 1.5 standard deviations above the mean, while a deeper valley appears in the second half, reaching about 2.0 standard deviations below the mean. The overall net change is a modest increase of approximately 1.1%.

**中文翻译**

> 该时间序列呈现平坦趋势、低波动和弱季节性特征，与 CPIAUCSL 指数呈弱负相关。在窗口前期，先出现明显上升阶段，随后在前半段出现显著下降，在后半段又有较小幅度的上升。前半段出现一个峰值，达到均值以上约 1.5 个标准差，而后半段出现一个更深的谷值，达到均值以下约 2.0 个标准差。整体净变化为约 1.1% 的小幅增加。

#### OpenTSLM 修正逐变量 caption：变量 2 | Federal Minimum Hourly Wage for Nonfarm Workers for the United States, Dollars per Hour, Monthly, Not Seasonally Adjusted

**原文**

> The time series shows a flat trend with low volatility and weak seasonality, characterized by a weakly negative correlation with the Federal Minimum Hourly Wage for Nonfarm Workers. The data experiences a gradual upward movement early in the window, followed by a more pronounced increase in the first half, and a significant rise in the second half, culminating in a peak that is about 2.0 standard deviations above the mean toward the end of the period.

**中文翻译**

> 该时间序列呈现平坦趋势、低波动和弱季节性特征，与非农工人的联邦每小时最低工资呈弱负相关。数据在窗口前期经历了缓慢上升，随后在前半段出现更明显的增加，并在后半段显著上升，最终在期末附近达到约高于均值 2.0 个标准差的峰值。

#### OpenTSLM 原生多变量 caption

**原文**

> The time series shows a flat trend with low volatility and weak seasonality, characterized by a weakly negative correlation with the Federal Minimum Hourly Wage for Nonfarm Workers. The data experiences a gradual upward movement early in the window, followed by a more pronounced increase in the first half, and a significant rise in the second half, peaking at a level about 1.6 standard deviations above the mean. There is no clear valley identified in the series.

**中文翻译**

> 该时间序列呈现平坦趋势、低波动和弱季节性特征，与非农工人的联邦每小时最低工资呈弱负相关。数据在窗口前期经历了缓慢上升，随后在前半段出现更明显的增加，并在后半段显著上升，峰值约高于均值 1.6 个标准差。序列中未发现明显谷值。

#### ChatTS 原生多变量 caption

**原文**

> Variable 1: The length is 822. The overall trend contains multiple segments: increasing from point 0 to 268, decreasing from 268 to 541, and increasing again from 541 to 821. The value starts around 60.87 and ends around 99.72, with an overall amplitude of 38.85. The time series is showing triangle periodic fluctuation: the amplitude of the periodic fluctuation is 27.0 between point 0 and point 822. Each fluctuation period is approximately 171.0 points, thus the overall fluctuation is low frequency. The overall noise standard deviation is around 0.01, very small compared the overall change of the curve. The curve is overall smooth with almost no noise. In terms of local characteristics, a sudden increase with an amplitude of 56.65 occurred between point 35 and point 37, with the time series value rising from around 63

**中文翻译**

> 变量 1：长度为 822。整体趋势包含多个片段：从点 0 到 268 上升，从 268 到 541 下降，然后从 541 到 821 再次上升。数值起始约为 60.87，结束约为 99.72，总振幅为 38.85。该时间序列表现出三角形周期波动：在点 0 到点 822 之间，周期波动振幅为 27.0。每个波动周期约为 171.0 个点，因此整体波动为低频。整体噪声标准差约为 0.01，与曲线的整体变化相比非常小。曲线整体平滑，几乎没有噪声。就局部特征而言，在点 35 到点 37 之间发生了一次幅度为 56.65 的突然上升，时间序列数值从约 63

</details>

<details>
<summary>🧪 下游 QA 模型答案 / 评分</summary>

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；八行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `D` | `A` | ✗ 错误 | D |
| 题目 + 原始数值序列 (`numbers`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM 修正逐变量 caption (`opentslm_fixed_caption`) | `D` | `A` | ✗ 错误 | D |
| 题目 + OpenTSLM 修正逐变量 caption + 数值 (`opentslm_fixed_caption_plus`) | `D` | `A` | ✗ 错误 | D |
| 题目 + OpenTSLM 原生多变量 caption (`opentslm_native_caption`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM 原生多变量 caption + 数值 (`opentslm_native_caption_plus`) | `A` | `A` | ✓ 正确 | A |
| 题目 + ChatTS 原生多变量 caption (`chatts_native_caption`) | `D` | `A` | ✗ 错误 | D |
| 题目 + ChatTS 原生多变量 caption + 数值 (`chatts_native_caption_plus`) | `A` | `A` | ✓ 正确 | A |

</details>

<details>
<summary>🔎 Case 分析</summary>

- **答案格局**：`meta_only=D✗, numbers=A✓, opentslm_fixed_caption=D✗, opentslm_fixed_caption_plus=D✗, opentslm_native_caption=A✓, opentslm_native_caption_plus=A✓, chatts_native_caption=D✗, chatts_native_caption_plus=A✓`。
- **这个 case 说明的问题**：检验原生多变量 checkpoint 是否比逐变量 caption 更能保留跨变量证据
- **对训练失败的含义**：如果原生多变量 caption 仍然答错，说明失败不是简单由“逐变量生成导致缺少跨变量上下文”造成；caption 还需要按题目抽取指定日期、窗口统计、变量差值/比值、排序或领域机制。若原生多变量能救回 fixed 逐变量失败，则说明跨变量联合输入确实有价值，但仍需要看这种现象在全量统计中占多少。

</details>

</details>

<details>
<summary>📈 Case 02: FREDQA `392` | OpenTSLM 原生多变量不如 fixed 逐变量</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::392` |
| 变量数 / 序列长度 | `4` / `[6, 6, 6, 6]` |
| 问题类型 | `Inductive Reasoning`, `Abductive Reasoning` |
| 正确答案 | `D` |
| 失败/对比模式 | OpenTSLM 原生多变量不如 fixed 逐变量 |
| 本 case 关注点 | 检验把多条序列一次性压缩成一个 caption 是否会丢失变量级细节 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | Net Worth Held by the Top 1% (99th to 100th Wealth Percentiles), Index Q4 2019=100, Quarterly, Not Seasonally Adjusted  | 6 | 100 | 118.317 | 90.2166@1 | 118.317@5 | 4.67329 |
| 2 | Net Worth Held by the 90th to 99th Wealth Percentiles, Index Q4 2019=100, Quarterly, Not Seasonally Adjusted  | 6 | 100 | 112.641 | 93.9779@1 | 112.641@5 | 3.18539 |
| 3 | Net Worth Held by the 50th to 90th Wealth Percentiles, Index Q4 2019=100, Quarterly, Not Seasonally Adjusted  | 6 | 100 | 119.685 | 98.7686@1 | 119.685@5 | 4.29576 |
| 4 | Net Worth Held by the Bottom 50% (1st to 50th Wealth Percentiles), Index Q4 2019=100, Quarterly, Not Seasonally Adjusted  | 6 | 100 | 151.904 | 99.7641@1 | 151.904@5 | 11.0618 |

<details>
<summary>🖼 时序图</summary>

![FREDQA 392](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_392.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

> You are a time series analysis expert. In a Wealth Distribution system, there are 4 metrics: Net Worth Held by the Top 1% (99th to 100th Wealth Percentiles), Index Q4 2019=100&lt;ts&gt;&lt;ts/&gt;; Net Worth Held by the 90th to 99th Wealth Percentiles, Index Q4 2019=100&lt;ts&gt;&lt;ts/&gt;; Net Worth Held by the 50th to 90th Wealth Percentiles, Index Q4 2019=100&lt;ts&gt;&lt;ts/&gt;; Net Worth Held by the Bottom 50% (1st to 50th Wealth Percentiles), Index Q4 2019=100&lt;ts&gt;&lt;ts/&gt;. Using quarterly data from October 2019 to January 2021, calculate the percentage change in net worth from Q4 2019 (2019-10-01) to Q1 2021 (2021-01-01) for each wealth group. Which group showed the largest net worth increase during this period, and what economic factor primarily explains this growth based on asset composition differences?

**题干中文翻译**

> 你是一名时间序列分析专家。在一个财富分配系统中，有4个指标：最富有1%（财富百分位第99到100位）持有的净资产，Q4 2019=100&lt;ts&gt;&lt;ts/&gt;；90到99财富百分位持有的净资产，Q4 2019=100&lt;ts&gt;&lt;ts/&gt;；50到90财富百分位持有的净资产，Q4 2019=100&lt;ts&gt;&lt;ts/&gt;；底部50%（财富百分位第1到50位）持有的净资产，Q4 2019=100&lt;ts&gt;&lt;ts/&gt;。使用从2019年10月到2021年1月的季度数据，计算每个财富组从Q4 2019（2019-10-01）到Q1 2021（2021-01-01）的净资产百分比变化。哪个群体在此期间显示出最大的净资产增长，以及根据资产构成差异，这种增长主要由什么经济因素解释？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Top 1% due to recovery of equity markets | 由于股市复苏，最富有1% |
| `B` | 90th to 99th percentiles due to business valuation rebounds | 由于企业估值反弹，90到99财富百分位 |
| `C` | 50th to 90th percentiles due to retirement account gains | 由于退休账户收益，50到90财富百分位 |
| `D` | Bottom 50% due to housing price appreciation | 由于房价上涨，底部50% |

**正确答案**：`D`

**标准解释**

> 原始 FREDQA 样本没有提供标准解释字段；本报告保留题干、选项、正确答案和模型输出用于 case study。

</details>

<details>
<summary>📝 三类 caption 与中文翻译</summary>

#### OpenTSLM 修正逐变量 caption：变量 1 | Net Worth Held by the Top 1% (99th to 100th Wealth Percentiles), Index Q4 2019=100, Quarterly, Not Seasonally Adjusted 

**原文**

> The time series shows a gradual upward trend with low volatility and a medium-strength seasonal pattern repeating every 18 periods. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a slightly smaller increase in the second half. A notable peak occurs late in the window, reaching about 1.2 standard deviations above the mean, while a deep valley is observed early on, dropping about 2.0 standard deviations below the mean. The series is strongly positively correlated with the net worth of the top 1% population.

**中文翻译**

> 该时间序列显示出平缓上升趋势、低波动性，以及每18个周期重复一次的中等强度季节性模式。数据在窗口前段开始时呈适度增长，随后在前半段出现更明显的上升，后半段则增长略小。一个显著峰值出现在窗口后期，达到约比均值高1.2个标准差，而一个深谷出现在较早时期，下降约2.0个标准差到均值以下。该序列与最富有1%人群的净资产呈强正相关。

#### OpenTSLM 修正逐变量 caption：变量 2 | Net Worth Held by the 90th to 99th Wealth Percentiles, Index Q4 2019=100, Quarterly, Not Seasonally Adjusted 

**原文**

> The time series shows a gradual upward trend with low volatility and a medium-strength seasonal pattern repeating every 15 quarters. Early in the window, there is a slight decline, followed by a moderate increase in the first half and a more pronounced rise in the second half. A notable peak occurs late in the window, reaching about 1.3 standard deviations above the mean, while a deep valley is observed early on, reaching about 2.0 standard deviations below the mean. The series is strongly positively correlated with the 75th to 90th wealth percentiles' net worth and strongly negatively correlated with the 10th to 25th wealth percentiles' net worth.

**中文翻译**

> 该时间序列显示出平缓上升趋势、低波动性，以及每15个季度重复一次的中等强度季节性模式。窗口前段出现轻微下降，随后在前半段出现适度增长，并在后半段出现更明显的上升。一个显著峰值出现在窗口后期，达到约比均值高1.3个标准差，而一个深谷出现在较早时期，达到约比均值低2.0个标准差。该序列与75到90财富百分位的净资产呈强正相关，并与10到25财富百分位的净资产呈强负相关。

#### OpenTSLM 修正逐变量 caption：变量 3 | Net Worth Held by the 50th to 90th Wealth Percentiles, Index Q4 2019=100, Quarterly, Not Seasonally Adjusted 

**原文**

> The time series shows a gradual upward trend with low volatility and a medium-strength seasonal pattern repeating every 15 quarters. Early in the window, there is a moderate increase, followed by a decline in the first half, and a significant rise in the second half. A notable peak occurs late in the window, reaching about 1.3 standard deviations above the mean, while a deep valley is observed around the middle, reaching about 2.0 standard deviations below the mean. The overall net increase over the time span is approximately 20.5%.

**中文翻译**

> 该时间序列显示出平缓上升趋势、低波动性，以及每15个季度重复一次的中等强度季节性模式。窗口前段出现适度增长，随后在前半段出现下降，并在后半段出现显著上升。一个显著峰值出现在窗口后期，达到约比均值高1.3个标准差，而一个深谷出现在中间附近，达到约比均值低2.0个标准差。整个时间跨度内的总体净增长约为20.5%。

#### OpenTSLM 修正逐变量 caption：变量 4 | Net Worth Held by the Bottom 50% (1st to 50th Wealth Percentiles), Index Q4 2019=100, Quarterly, Not Seasonally Adjusted 

**原文**

> The time series shows a gradual upward trend with low volatility and a medium-strength seasonal pattern repeating every 15 quarters. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a slightly smaller but still positive growth in the second half. A notable peak occurs late in the window, reaching about 1.2 standard deviations above the mean, while a deep valley is observed early on, dropping about 2.0 standard deviations below the mean. The overall net increase over the time span is approximately 37.5%.

**中文翻译**

> 该时间序列显示出平缓上升趋势、低波动性，以及每15个季度重复一次的中等强度季节性模式。数据在窗口前段开始时呈适度增长，随后在前半段出现更明显的上升，后半段则增长略小但仍为正。一个显著峰值出现在窗口后期，达到约比均值高1.2个标准差，而一个深谷出现在较早时期，下降约2.0个标准差到均值以下。整个时间跨度内的总体净增长约为37.5%。

#### OpenTSLM 原生多变量 caption

**原文**

> The time series shows a gradual upward trend with low volatility and a medium-strength seasonal pattern repeating every four quarters. The data starts with a moderate increase in the early part of the window, followed by a stronger rise in the first half, and a slightly smaller increase in the second half. A notable peak occurs late in the window, reaching about 1.2 standard deviations above the mean, while a deep valley is observed early on, reaching about 2.0 standard deviations below the mean. The overall growth over the time span is substantial, with a net increase of over 50%.

**中文翻译**

> 该时间序列显示出平缓上升趋势、低波动性，以及每四个季度重复一次的中等强度季节性模式。数据在窗口前段开始时呈适度增长，随后在前半段出现更强劲的上升，后半段则增长略小。一个显著峰值出现在窗口后期，达到约比均值高1.2个标准差，而一个深谷出现在较早时期，达到约比均值低2.0个标准差。整个时间跨度内的总体增长相当显著，净增长超过50%。

#### ChatTS 原生多变量 caption

**原文**

> All four time series exhibit steady upward trends from their baseline of ~100, with minimal noise (standard deviation ~0.00). Variable 1 shows the highest growth (18.33 total increase), followed by Variables 2 (12.64), 3 (19.69), and 4 (51.90). Notable changes include a sharp spike in Variable 1 between points 2-4, but no periodic fluctuations or local features are observed. Cross-variable analysis reveals synchronized upward movements, suggesting a systemic driver such as economic growth. The significant divergence in Variable 4's growth compared to others indicates potential wealth redistribution or unique factors affecting the bottom 50%.

**中文翻译**

> 所有四个时间序列都从约100的基线稳步上升，噪声极小（标准差约为0.00）。变量1增长最高（总增幅18.33），其次是变量2（12.64）、变量3（19.69）和变量4（51.90）。显著变化包括变量1在第2-4个点之间出现尖锐峰值，但未观察到周期性波动或局部特征。跨变量分析显示同步上升运动，表明存在诸如经济增长之类的系统性驱动因素。变量4的增长与其他变量相比显著分化，表明可能存在财富再分配或影响底部50%的独特因素。

</details>

<details>
<summary>🧪 下游 QA 模型答案 / 评分</summary>

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；八行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `A` | `D` | ✗ 错误 | A |
| 题目 + 原始数值序列 (`numbers`) | `D` | `D` | ✓ 正确 | D |
| 题目 + OpenTSLM 修正逐变量 caption (`opentslm_fixed_caption`) | `D` | `D` | ✓ 正确 | D |
| 题目 + OpenTSLM 修正逐变量 caption + 数值 (`opentslm_fixed_caption_plus`) | `D` | `D` | ✓ 正确 | D |
| 题目 + OpenTSLM 原生多变量 caption (`opentslm_native_caption`) | `A` | `D` | ✗ 错误 | A |
| 题目 + OpenTSLM 原生多变量 caption + 数值 (`opentslm_native_caption_plus`) | `D` | `D` | ✓ 正确 | D |
| 题目 + ChatTS 原生多变量 caption (`chatts_native_caption`) | `D` | `D` | ✓ 正确 | D |
| 题目 + ChatTS 原生多变量 caption + 数值 (`chatts_native_caption_plus`) | `D` | `D` | ✓ 正确 | D |

</details>

<details>
<summary>🔎 Case 分析</summary>

- **答案格局**：`meta_only=A✗, numbers=D✓, opentslm_fixed_caption=D✓, opentslm_fixed_caption_plus=D✓, opentslm_native_caption=A✗, opentslm_native_caption_plus=D✓, chatts_native_caption=D✓, chatts_native_caption_plus=D✓`。
- **这个 case 说明的问题**：检验把多条序列一次性压缩成一个 caption 是否会丢失变量级细节
- **对训练失败的含义**：如果原生多变量 caption 仍然答错，说明失败不是简单由“逐变量生成导致缺少跨变量上下文”造成；caption 还需要按题目抽取指定日期、窗口统计、变量差值/比值、排序或领域机制。若原生多变量能救回 fixed 逐变量失败，则说明跨变量联合输入确实有价值，但仍需要看这种现象在全量统计中占多少。

</details>

</details>

<details>
<summary>📈 Case 03: FREDQA `111` | ChatTS 原生多变量对，OpenTSLM 原生多变量错</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::111` |
| 变量数 / 序列长度 | `2` / `[137, 137]` |
| 问题类型 | `Analogical Reasoning`, `Inductive Reasoning`, `Abductive Reasoning` |
| 正确答案 | `B` |
| 失败/对比模式 | ChatTS 原生多变量对，OpenTSLM 原生多变量错 |
| 本 case 关注点 | 比较 ChatTS 多 token prompt 与 OpenTSLM 原生多变量 caption 的失败差异 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | bank 1 100 | 137 | 5.94 | 2.99 | 1.41@121 | 6.71@72 | -0.0239858 |
| 2 | bank out of 100 | 137 | 4.65 | 7.01 | 2.88@99 | 8.16@131 | 0.0110376 |

<details>
<summary>🖼 时序图</summary>

![FREDQA 111](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_111.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

> You are a time series analysis expert. In a Credit Card Delinquency system, there are 2 metrics: Credit Card Delinquency Rate for the Top 100 Banks (percentage of total credit card loans)&lt;ts&gt;&lt;ts/&gt;; Credit Card Delinquency Rate for Smaller Banks (not in the Top 100, percentage of total credit card loans)&lt;ts&gt;&lt;ts/&gt;. Using quarterly data from January 1991 to January 2025, calculate the average quarterly delinquency rate for each bank group in 1995 and in 2015. Determine whether the smaller banks’ rate was higher or lower than the Top 100 Banks’ rate in each year. Based on this comparison, which economic factor best explains the observed change in the relationship between the two series?

**题干中文翻译**

> 你是一名时间序列分析专家。在一个信用卡违约系统中，有 2 个指标：Top 100 银行的信用卡违约率（占信用卡贷款总额的百分比）&lt;ts&gt;&lt;ts/&gt;；小型银行的信用卡违约率（不在 Top 100 中，占信用卡贷款总额的百分比）&lt;ts&gt;&lt;ts/&gt;。使用 1991 年 1 月至 2025 年 1 月的季度数据，计算 1995 年和 2015 年每个银行组的季度平均违约率。判断在每一年中，小型银行的比率是高于还是低于 Top 100 银行的比率。基于这一比较，哪种经济因素最好地解释了这两个序列之间关系的观察到的变化？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Top 100 banks tightened credit standards more aggressively than smaller banks following the 2008 financial crisis | 在 2008 年金融危机之后，Top 100 银行比小型银行更积极地收紧了信贷标准 |
| `B` | Smaller banks increasingly targeted higher-risk credit card customers to compete with larger banks for market share | 为了与大型银行争夺市场份额，小型银行越来越多地针对更高风险的信用卡客户 |
| `C` | Regulatory reforms in the 2010s required smaller banks to report delinquencies more accurately than Top 100 banks | 2010 年代的监管改革要求小型银行比 Top 100 银行更准确地报告违约情况 |
| `D` | Inflation in the 2010s reduced the real burden of credit card debt for Top 100 bank customers more than for smaller bank customers | 2010 年代的通货膨胀降低了 Top 100 银行客户信用卡债务的实际负担，而对小型银行客户的影响较小 |

**正确答案**：`B`

**标准解释**

> 原始 FREDQA 样本没有提供标准解释字段；本报告保留题干、选项、正确答案和模型输出用于 case study。

</details>

<details>
<summary>📝 三类 caption 与中文翻译</summary>

#### OpenTSLM 修正逐变量 caption：变量 1 | bank 1 100

**原文**

> The time series shows a flat trend with low volatility and a strong seasonal pattern repeating every 120 time units. There is a noticeable upward phase early in the window followed by a significant downward movement in the first half, then a smaller upward trend in the second half. A peak occurs in the first half with a magnitude of about 2.2 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 1.6 standard deviations from the mean. The series exhibits strong positive correlation with bank 2 100 and moderate positive correlation with bank 3 100.

**中文翻译**

> 该时间序列呈现平坦趋势、低波动性，并具有每 120 个时间单位重复一次的强季节性模式。窗口前期出现明显上升阶段，随后在前半段出现显著下降运动，然后在后半段出现较小的上升趋势。前半段出现一个峰值，其幅度约为均值的 2.2 个标准差，而窗口早期观察到一个谷值，其幅度约为均值的 1.6 个标准差。该序列与 bank 2 100 和 bank 3 100 呈现强正相关。

#### OpenTSLM 修正逐变量 caption：变量 2 | bank out of 100

**原文**

> The time series shows a flat trend with low volatility and medium strength seasonality every 85 time units. There is a noticeable upward phase early in the window followed by a significant downward phase in the first half, then another upward movement in the second half. A peak occurs in the first half with a magnitude of about 3.1 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 1.9 standard deviations from the mean. The series has strong positive correlations with two other variables, indicating a consistent relationship over time.

**中文翻译**

> 该时间序列呈现平坦趋势、低波动性，并且每 85 个时间单位具有中等强度的季节性。窗口前期出现明显上升阶段，随后在前半段出现显著下降阶段，然后在后半段再次上升。前半段出现一个峰值，其幅度约为均值的 3.1 个标准差，而窗口早期观察到一个谷值，其幅度约为均值的 1.9 个标准差。该序列与另外两个变量具有强正相关，表明其在整个时间上保持一致的关系。

#### OpenTSLM 原生多变量 caption

**原文**

> The time series shows a flat trend with low volatility and medium strength seasonality every 12 periods. There is a noticeable upward phase early in the window followed by a significant downward phase in the second half. A peak occurs in the second half with a magnitude of about 2.3 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 2.0 standard deviations from the mean. The series has a strong positive correlation with another variable, "bank out of 100."

**中文翻译**

> 该时间序列呈现平坦趋势、低波动性，并且每 12 个周期具有中等强度的季节性。窗口前期出现明显上升阶段，随后在后半段出现显著下降阶段。后半段出现一个峰值，其幅度约为均值的 2.3 个标准差，而窗口早期观察到一个谷值，其幅度约为均值的 2.0 个标准差。该序列与另一个变量“100 中的银行”具有强正相关。

#### ChatTS 原生多变量 caption

**原文**

> Variable 1 exhibits an overall steady trend, starting at approximately 5.94 and ending around 2.99, with an amplitude of -2.95. The series shows high-frequency sinusoidal fluctuations with a period of about 20.2 points and an amplitude of 2.3. There is a random noise with a standard deviation of 0.25, indicating a noisy curve. Notable local changes include a sudden decrease between points 9 and 14 with an amplitude of 2.32, and a sudden increase between points 119 and 125 with an amplitude of 1.37. Variable 2 also has a steady trend, starting at around 4.65 and ending at approximately 7.01, with an amplitude of 2.36. It displays low-frequency sinusoidal fluctuations with a period of about 77.1 points and an amplitude of 3.8. The series has no significant noise, with a very small standard deviation of around 0.00

**中文翻译**

> 变量 1 表现出整体稳定的趋势，起始值约为 5.94，结束值约为 2.99，幅度为 -2.95。该序列显示出高频正弦波动，周期约为 20.2 个点，幅度为 2.3。存在标准差为 0.25 的随机噪声，表明曲线较为嘈杂。值得注意的局部变化包括：在点 9 到 14 之间出现突然下降，幅度为 2.32；在点 119 到 125 之间出现突然上升，幅度为 1.37。变量 2 也具有稳定的趋势，起始值约为 4.65，结束值约为 7.01，幅度为 2.36。它表现出低频正弦波动，周期约为 77.1 个点，幅度为 3.8。该序列几乎没有显著噪声，标准差非常小，约为 0.00

</details>

<details>
<summary>🧪 下游 QA 模型答案 / 评分</summary>

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；八行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `A` | `B` | ✗ 错误 | A |
| 题目 + 原始数值序列 (`numbers`) | `B` | `B` | ✓ 正确 | B |
| 题目 + OpenTSLM 修正逐变量 caption (`opentslm_fixed_caption`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM 修正逐变量 caption + 数值 (`opentslm_fixed_caption_plus`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM 原生多变量 caption (`opentslm_native_caption`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM 原生多变量 caption + 数值 (`opentslm_native_caption_plus`) | `A` | `B` | ✗ 错误 | A |
| 题目 + ChatTS 原生多变量 caption (`chatts_native_caption`) | `B` | `B` | ✓ 正确 | B |
| 题目 + ChatTS 原生多变量 caption + 数值 (`chatts_native_caption_plus`) | `A` | `B` | ✗ 错误 | A |

</details>

<details>
<summary>🔎 Case 分析</summary>

- **答案格局**：`meta_only=A✗, numbers=B✓, opentslm_fixed_caption=A✗, opentslm_fixed_caption_plus=A✗, opentslm_native_caption=A✗, opentslm_native_caption_plus=A✗, chatts_native_caption=B✓, chatts_native_caption_plus=A✗`。
- **这个 case 说明的问题**：比较 ChatTS 多 token prompt 与 OpenTSLM 原生多变量 caption 的失败差异
- **对训练失败的含义**：如果原生多变量 caption 仍然答错，说明失败不是简单由“逐变量生成导致缺少跨变量上下文”造成；caption 还需要按题目抽取指定日期、窗口统计、变量差值/比值、排序或领域机制。若原生多变量能救回 fixed 逐变量失败，则说明跨变量联合输入确实有价值，但仍需要看这种现象在全量统计中占多少。

</details>

</details>

<details>
<summary>📈 Case 04: FREDQA `210` | OpenTSLM 原生多变量对，ChatTS 原生多变量错</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::210` |
| 变量数 / 序列长度 | `2` / `[61, 61]` |
| 问题类型 | `Deductive Reasoning`, `Inductive Reasoning`, `Analogical Reasoning` |
| 正确答案 | `B` |
| 失败/对比模式 | OpenTSLM 原生多变量对，ChatTS 原生多变量错 |
| 本 case 关注点 | 定位 OpenTSLM 原生多变量 caption 的相对优势样本 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | Quits: Total Private | 61 | 0.5638 | 0.5717 | 0.3913@33 | 0.5799@22 | -0.000175003 |
| 2 | Layoffs and Discharges | 61 | 0.3764 | 0.3597 | 0.351@22 | 0.5464@33 | 6.92068e-05 |

<details>
<summary>🖼 时序图</summary>

![FREDQA 210](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_210.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

> You are a time series analysis expert. In a U.S. labor market system, there are 2 metrics: Quits (Total Private, as a share of total separations)&lt;ts&gt;&lt;ts/&gt;; Layoffs and Discharges (as a share of total separations)&lt;ts&gt;&lt;ts/&gt;. Using quarterly data from 2001 Q1 to 2016 Q1, compute the ratio of quits to layoffs and discharges for 2007 Q1 (pre-Great Recession), 2009 Q1 (recession trough), and 2016 Q1 (post-recession recovery). Based on these ratios and the economic meaning of quits (a sign of worker confidence in finding better job opportunities) and layoffs (a sign of economic stress and potential wage cuts for reemployed workers), which conclusion about labor market dynamism over this period is supported?

**题干中文翻译**

> 你是一位时间序列分析专家。在美国劳动力市场系统中，有 2 个指标：自愿离职（Total Private，占总分离人数的比例）&lt;ts&gt;&lt;ts/&gt;；裁员和解雇（占总分离人数的比例）&lt;ts&gt;&lt;ts/&gt;。使用 2001 Q1 到 2016 Q1 的季度数据，计算 2007 Q1（大衰退前）、2009 Q1（衰退谷底）和 2016 Q1（衰退后复苏）时，自愿离职与裁员和解雇的比率。基于这些比率以及自愿离职（表明工人对找到更好工作机会的信心）和裁员（表明经济压力以及被重新雇用工人潜在工资下降）的经济含义，以下关于该时期劳动力市场活力的结论哪一项得到支持？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Labor market dynamism peaked during the recession, as the quit-to-layoff ratio was highest in 2009 Q1 | 劳动力市场活力在衰退期间达到峰值，因为 2009 Q1 的自愿离职与裁员比率最高 |
| `B` | Dynamism declined during the recession but fully recovered by 2016, as the quit-to-layoff ratio matched its pre-recession level | 活力在衰退期间下降，但到 2016 年完全恢复，因为自愿离职与裁员比率回到了衰退前水平 |
| `C` | Dynamism remained weak post-recession because layoffs were still higher in 2016 Q1 than in 2007 Q1 | 衰退后活力仍然疲弱，因为 2016 Q1 的裁员仍高于 2007 Q1 |
| `D` | Dynamism improved steadily from 2001 to 2016, as quits consistently rose while layoffs fell | 活力从 2001 年到 2016 年稳步改善，因为自愿离职持续上升而裁员下降 |

**正确答案**：`B`

**标准解释**

> 原始 FREDQA 样本没有提供标准解释字段；本报告保留题干、选项、正确答案和模型输出用于 case study。

</details>

<details>
<summary>📝 三类 caption 与中文翻译</summary>

#### OpenTSLM 修正逐变量 caption：变量 1 | Quits: Total Private

**原文**

> The time series shows a flat trend with low volatility and a medium-strength seasonal pattern repeating every 20 periods. There is a noticeable upward phase early in the window followed by a downward phase in the first half. A peak occurs in the first half with a magnitude of about 1.5 standard deviations from the mean, while a deeper valley is observed early in the window, reaching about 2.0 standard deviations from the mean. The series exhibits a strong positive correlation with Quits: Total Federal.

**中文翻译**

> 该时间序列呈现平稳趋势，波动较低，并且存在中等强度的季节性模式，每 20 个周期重复一次。在窗口早期有明显的上升阶段，随后在前半段出现下降阶段。在前半段出现一个峰值，其幅度约为距离均值 1.5 个标准差；而在窗口早期观察到一个更深的谷值，约达到距离均值 2.0 个标准差。该序列与 Quits: Total Federal 呈现强正相关。

#### OpenTSLM 修正逐变量 caption：变量 2 | Layoffs and Discharges

**原文**

> The time series shows a flat trend with high volatility and weak seasonality, characterized by a weakly periodic pattern every 100 periods. The data experiences a significant net decline of about 10% over the entire time span. Early in the window, there is a notable downward phase with a large negative change, followed by a moderate upward movement in the first half and a smaller upward shift in the second half. A peak occurs early, reaching about 2.1 standard deviations above the mean, while a valley appears late, about 1.8 standard deviations below the mean. The series exhibits strong positive correlation with the number of workers and strong negative correlation with the unemployment rate.

**中文翻译**

> 该时间序列呈现平稳趋势，波动较高，季节性较弱，其特征是每 100 个周期出现一次弱周期性模式。数据在整个时间跨度内经历了约 10% 的显著净下降。在窗口早期，出现一个明显的下降阶段，伴随较大的负变化，随后在前半段出现中等程度的上升，在后半段出现较小的上升。一个峰值出现在较早时期，约为均值上方 2.1 个标准差，而一个谷值出现在较晚时期，约为均值下方 1.8 个标准差。该序列与劳动者数量呈强正相关，与失业率呈强负相关。

#### OpenTSLM 原生多变量 caption

**原文**

> The time series shows a flat trend with low volatility and medium strength seasonality every 20 periods. There is a noticeable upward phase early in the window followed by a significant downward phase in the second half. A peak occurs in the second half with a magnitude of about 2.0 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 1.8 standard deviations from the mean. The series exhibits a strong negative correlation with the variable "Layoffs and Discharges."

**中文翻译**

> 该时间序列呈现平稳趋势，波动较低，并且每 20 个周期具有中等强度的季节性。在窗口早期有明显的上升阶段，随后在后半段出现显著下降阶段。在后半段出现一个峰值，其幅度约为距离均值 2.0 个标准差，而在窗口早期观察到一个谷值，其幅度约为距离均值 1.8 个标准差。该序列与变量 "Layoffs and Discharges" 呈现强负相关。

#### ChatTS 原生多变量 caption

**原文**

> Variable 1 exhibits a steady trend with minimal noise and periodic fluctuations. It starts at 0.56 and ends near 0.57, showing a slight overall increase. Notable features include a slow decline followed by a rapid rise around point 30. Variable 2 also shows a steady trend but with more pronounced periodic fluctuations and a spike between points 28-32. Cross-correlation analysis indicates a weak positive relationship between the two variables, suggesting they may respond to similar underlying factors but with different magnitudes and timing.

**中文翻译**

> 变量 1 表现出稳定趋势，噪声很小，并伴有周期性波动。它从 0.56 开始，末尾接近 0.57，显示出轻微的整体上升。显著特征包括在 30 点附近先缓慢下降后快速上升。变量 2 也表现出稳定趋势，但周期性波动更明显，并在 28-32 点之间出现一个尖峰。交叉相关分析表明，两者之间存在弱正相关，说明它们可能对相似的潜在因素作出反应，但幅度和时间上存在差异。

</details>

<details>
<summary>🧪 下游 QA 模型答案 / 评分</summary>

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；八行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `C` | `B` | ✗ 错误 | C |
| 题目 + 原始数值序列 (`numbers`) | `B` | `B` | ✓ 正确 | B |
| 题目 + OpenTSLM 修正逐变量 caption (`opentslm_fixed_caption`) | `B` | `B` | ✓ 正确 | B |
| 题目 + OpenTSLM 修正逐变量 caption + 数值 (`opentslm_fixed_caption_plus`) | `B` | `B` | ✓ 正确 | B |
| 题目 + OpenTSLM 原生多变量 caption (`opentslm_native_caption`) | `B` | `B` | ✓ 正确 | B |
| 题目 + OpenTSLM 原生多变量 caption + 数值 (`opentslm_native_caption_plus`) | `B` | `B` | ✓ 正确 | B |
| 题目 + ChatTS 原生多变量 caption (`chatts_native_caption`) | `C` | `B` | ✗ 错误 | C |
| 题目 + ChatTS 原生多变量 caption + 数值 (`chatts_native_caption_plus`) | `B` | `B` | ✓ 正确 | B |

</details>

<details>
<summary>🔎 Case 分析</summary>

- **答案格局**：`meta_only=C✗, numbers=B✓, opentslm_fixed_caption=B✓, opentslm_fixed_caption_plus=B✓, opentslm_native_caption=B✓, opentslm_native_caption_plus=B✓, chatts_native_caption=C✗, chatts_native_caption_plus=B✓`。
- **这个 case 说明的问题**：定位 OpenTSLM 原生多变量 caption 的相对优势样本
- **对训练失败的含义**：如果原生多变量 caption 仍然答错，说明失败不是简单由“逐变量生成导致缺少跨变量上下文”造成；caption 还需要按题目抽取指定日期、窗口统计、变量差值/比值、排序或领域机制。若原生多变量能救回 fixed 逐变量失败，则说明跨变量联合输入确实有价值，但仍需要看这种现象在全量统计中占多少。

</details>

</details>

<details>
<summary>📈 Case 05: FREDQA `481` | 两个原生多变量 caption 都错，但 numbers 对</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::481` |
| 变量数 / 序列长度 | `3` / `[61, 61, 61]` |
| 问题类型 | `Abductive Reasoning` |
| 正确答案 | `A` |
| 失败/对比模式 | 两个原生多变量 caption 都错，但 numbers 对 |
| 本 case 关注点 | caption 压缩丢失精确日期、窗口、差值、比值或排序证据 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | US Regular Conventional Gas Price, Percent Change, Monthly, Not Seasonally Adjusted  | 61 | 3.4162 | 4.2427 | -17.7653@36 | 12.7305@50 | -0.0146734 |
| 2 | Public Transit Ridership, Percent Change, Monthly, Not Seasonally Adjusted  | 61 | 0.4909 | -0.6018 | -14.6704@34 | 16.3636@38 | -0.0185047 |
| 3 | Vehicle Miles Traveled, Percent Change, Monthly, Not Seasonally Adjusted  | 61 | -7.0598 | -8.3761 | -9.6498@8 | 18.8941@50 | -0.0130504 |

<details>
<summary>🖼 时序图</summary>

![FREDQA 481](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_481.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

> You are a time series analysis expert. In a U.S. Transportation and Energy system, there are 3 metrics: US Regular Conventional Gas Price, Percent Change (Monthly, Not Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;; Public Transit Ridership, Percent Change (Monthly, Not Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;; Vehicle Miles Traveled, Percent Change (Monthly, Not Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;. Using monthly data from January 2012 to January 2017, examine the percent change values for March 2015. The textbook substitution effect predicts that a large increase in gas prices would reduce vehicle miles traveled and increase public transit ridership. Based on the data for this month, which factor from the provided context best explains why the expected relationship is not observed?

**题干中文翻译**

> 你是一名时间序列分析专家。在美国交通和能源系统中，有 3 个指标：US Regular Conventional Gas Price, Percent Change (Monthly, Not Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;；Public Transit Ridership, Percent Change (Monthly, Not Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;；Vehicle Miles Traveled, Percent Change (Monthly, Not Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;。使用 2012 年 1 月到 2017 年 1 月的月度数据，考察 2015 年 3 月的百分比变化值。教科书中的替代效应预测，汽油价格的大幅上涨会减少车辆行驶里程并增加公共交通乘客量。根据该月的数据，给定背景中哪一个因素最能解释为什么没有观察到预期关系？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Seasonal increases in travel demand for spring and summer activities | 春季和夏季活动出行需求的季节性增加 |
| `B` | Temporary reductions in public transit service frequency | 公共交通服务频率的临时减少 |
| `C` | Long-term improvements in passenger vehicle fuel efficiency | 乘用车燃油效率的长期改善 |
| `D` | Nationwide increases in household disposable income | 全国范围内家庭可支配收入的增加 |

**正确答案**：`A`

**标准解释**

> 原始 FREDQA 样本没有提供标准解释字段；本报告保留题干、选项、正确答案和模型输出用于 case study。

</details>

<details>
<summary>📝 三类 caption 与中文翻译</summary>

#### OpenTSLM 修正逐变量 caption：变量 1 | US Regular Conventional Gas Price, Percent Change, Monthly, Not Seasonally Adjusted 

**原文**

> The time series shows a flat trend with high volatility and no clear seasonality. Early in the window, there is a significant downward movement, followed by an upward phase in the first half and another downward shift in the second half. A notable peak occurs in the second half, reaching about 4.2 standard deviations above the mean, while a valley in the first half is about 1.2 standard deviations below the mean. The data is strongly positively correlated with the US Regular Conventional Gas Price, Percent Change, Monthly, Seasonally Adjusted series.

**中文翻译**

> 该时间序列呈现平坦趋势，波动较大且没有明显季节性。在窗口前期，出现显著下降，随后在前半段进入上升阶段，并在后半段再次下降。一个显著峰值出现在后半段，约比均值高 4.2 个标准差，而前半段的一个谷值约比均值低 1.2 个标准差。该数据与 US Regular Conventional Gas Price, Percent Change, Monthly, Seasonally Adjusted 序列呈强正相关。

#### OpenTSLM 修正逐变量 caption：变量 2 | Public Transit Ridership, Percent Change, Monthly, Not Seasonally Adjusted 

**原文**

> The time series shows a flat trend with high volatility and no clear seasonality. Early in the window, there is a significant upward movement, followed by a sharp decline in the first half, and a smaller upward trend in the second half. A notable peak occurs in the first half, reaching about 5.6 standard deviations above the mean, while a valley appears late in the window, about 1.4 standard deviations below the mean. The data is strongly positively correlated with another related series.

**中文翻译**

> 该时间序列呈现平坦趋势，波动较大且没有明显季节性。在窗口前期，出现显著上升，随后在前半段急剧下降，并在后半段出现较小的上升趋势。一个显著峰值出现在前半段，约比均值高 5.6 个标准差，而一个谷值出现在窗口后期，约比均值低 1.4 个标准差。该数据与另一条相关序列呈强正相关。

#### OpenTSLM 修正逐变量 caption：变量 3 | Vehicle Miles Traveled, Percent Change, Monthly, Not Seasonally Adjusted 

**原文**

> The time series shows a flat trend with high volatility and no clear seasonality. Early in the window, there is a significant downward movement, followed by an upward phase in the first half and another downward shift in the second half. A notable peak occurs in the first half, reaching about 4.2 standard deviations above the mean, while a valley in the second half is about 1.4 standard deviations below the mean. The data exhibits strong negative correlation with vehicle miles traveled and strong positive correlation with vehicle miles traveled, percent change, quarterly.

**中文翻译**

> 该时间序列呈现平坦趋势，波动较大且没有明显季节性。在窗口前期，出现显著下降，随后在前半段进入上升阶段，并在后半段再次下降。一个显著峰值出现在前半段，约比均值高 4.2 个标准差，而后半段的一个谷值约比均值低 1.4 个标准差。该数据与 vehicle miles traveled 呈强负相关，并与 vehicle miles traveled, percent change, quarterly 呈强正相关。

#### OpenTSLM 原生多变量 caption

**原文**

> The time series shows a flat trend with high volatility and no clear seasonality. Early in the window, there is a significant downward change, followed by a strong upward movement in the first half, and a smaller decline in the second half. A notable peak occurs in the second half, reaching about 3.4 standard deviations above the mean, while a deep valley is observed in the first half, about 3.0 standard deviations below the mean. The series exhibits weak positive correlations with vehicle miles traveled and public transit ridership changes.

**中文翻译**

> 该时间序列呈现平坦趋势，波动较大且没有明显季节性。在窗口前期，出现显著下降，随后在前半段强劲上升，并在后半段小幅下降。一个显著峰值出现在后半段，约比均值高 3.4 个标准差，而一个深谷出现在前半段，约比均值低 3.0 个标准差。该序列与 vehicle miles traveled 和 public transit ridership changes 呈弱正相关。

#### ChatTS 原生多变量 caption

**原文**

> The time series for US Regular Conventional Gas Price exhibits no discernible trend, with values fluctuating around an average of -0.38. The variability, as measured by the standard deviation, is approximately 6.76, indicating significant noise. No local characteristics or periodic fluctuations were observed. Cross-correlation analysis reveals no consistent patterns between the gas price and the other two time series (Public Transit Ridership and Vehicle Miles Traveled), suggesting independent behavior. All three time series show steady overall trends with minimal end-to-end amplitude changes.

**中文翻译**

> US Regular Conventional Gas Price 的时间序列没有明显趋势，数值围绕平均值 -0.38 波动。以标准差衡量的变异性约为 6.76，表明噪声较大。未观察到局部特征或周期性波动。交叉相关分析表明，汽油价格与另外两个时间序列（Public Transit Ridership 和 Vehicle Miles Traveled）之间没有一致的模式，表明它们相互独立。三个时间序列整体上都呈稳定趋势，首尾幅度变化很小。

</details>

<details>
<summary>🧪 下游 QA 模型答案 / 评分</summary>

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；八行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `C` | `A` | ✗ 错误 | C |
| 题目 + 原始数值序列 (`numbers`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM 修正逐变量 caption (`opentslm_fixed_caption`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM 修正逐变量 caption + 数值 (`opentslm_fixed_caption_plus`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM 原生多变量 caption (`opentslm_native_caption`) | `C` | `A` | ✗ 错误 | C |
| 题目 + OpenTSLM 原生多变量 caption + 数值 (`opentslm_native_caption_plus`) | `A` | `A` | ✓ 正确 | A |
| 题目 + ChatTS 原生多变量 caption (`chatts_native_caption`) | `C` | `A` | ✗ 错误 | C |
| 题目 + ChatTS 原生多变量 caption + 数值 (`chatts_native_caption_plus`) | `A` | `A` | ✓ 正确 | A |

</details>

<details>
<summary>🔎 Case 分析</summary>

- **答案格局**：`meta_only=C✗, numbers=A✓, opentslm_fixed_caption=A✓, opentslm_fixed_caption_plus=A✓, opentslm_native_caption=C✗, opentslm_native_caption_plus=A✓, chatts_native_caption=C✗, chatts_native_caption_plus=A✓`。
- **这个 case 说明的问题**：caption 压缩丢失精确日期、窗口、差值、比值或排序证据
- **对训练失败的含义**：如果原生多变量 caption 仍然答错，说明失败不是简单由“逐变量生成导致缺少跨变量上下文”造成；caption 还需要按题目抽取指定日期、窗口统计、变量差值/比值、排序或领域机制。若原生多变量能救回 fixed 逐变量失败，则说明跨变量联合输入确实有价值，但仍需要看这种现象在全量统计中占多少。

</details>

</details>

<details>
<summary>📈 Case 06: FREDQA `701` | 三种 caption 都错，但 numbers 对</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::701` |
| 变量数 / 序列长度 | `2` / `[65, 65]` |
| 问题类型 | `Deductive Reasoning`, `Analogical Reasoning` |
| 正确答案 | `B` |
| 失败/对比模式 | 三种 caption 都错，但 numbers 对 |
| 本 case 关注点 | 逐变量 caption、OpenTSLM 原生多变量、ChatTS 原生多变量都没有保留下游所需证据 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | Housing Inventory: Active Listing Count in the United States 1109 | 65 | 1.58256e+06 | 569431 | 491969@57 | 1.58256e+06@0 | -14546.9 |
| 2 | Housing Inventory: Active Listing Count in the United States 1202 | 65 | 1.54983e+06 | 553510 | 465964@57 | 1.54983e+06@0 | -14604.1 |

<details>
<summary>🖼 时序图</summary>

![FREDQA 701](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_701.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

> You are a time series analysis expert. In a Housing Inventory system, there are 2 metrics: Housing Inventory: Active Listing Count (Old Methodology) in the United States 1109&lt;ts&gt;&lt;ts/&gt;; Housing Inventory: Active Listing Count (New Methodology) in the United States 1202&lt;ts&gt;&lt;ts/&gt;. Using monthly data from July 2016 to November 2021, compute the percentage difference between the old methodology and new methodology counts for November 2021, defined as [(new - old) / old] × 100%. What does the computed value indicate about the methodological revision's impact?

**题干中文翻译**

> 你是一名时间序列分析专家。在住房库存系统中，有两个指标：美国住房库存：活跃挂牌数量（旧方法）1109&lt;ts&gt;&lt;ts/&gt;；美国住房库存：活跃挂牌数量（新方法）1202&lt;ts&gt;&lt;ts/&gt;。使用 2016 年 7 月至 2021 年 11 月的月度数据，计算 2021 年 11 月旧方法与新方法数量之间的百分比差异，定义为 [(new - old) / old] × 100%。计算得到的值说明了方法修订对结果有何影响？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | The new methodology increased counts by approximately 2.8% | 新方法使数量增加了约 2.8% |
| `B` | The new methodology decreased counts by approximately 2.8% | 新方法使数量减少了约 2.8% |
| `C` | The new methodology increased counts by approximately 5.7% | 新方法使数量增加了约 5.7% |
| `D` | The new methodology decreased counts by approximately 5.7% | 新方法使数量减少了约 5.7% |

**正确答案**：`B`

**标准解释**

> 原始 FREDQA 样本没有提供标准解释字段；本报告保留题干、选项、正确答案和模型输出用于 case study。

</details>

<details>
<summary>📝 三类 caption 与中文翻译</summary>

#### OpenTSLM 修正逐变量 caption：变量 1 | Housing Inventory: Active Listing Count in the United States 1109

**原文**

> The time series shows a steady decline with low volatility and a medium-strength seasonal pattern repeating every 18 periods. The overall trend is downward, with the most significant drop occurring early in the window, followed by a moderate decrease in the first half, and a slight recovery in the second half. A notable peak appears early, standing out as about 1.4 standard deviations above the mean, while a deep valley forms late in the window, reaching about 1.8 standard deviations below the mean. The series is strongly positively correlated with two other housing inventory variables.

**中文翻译**

> 该时间序列呈现出平稳下降、波动较低且具有中等强度季节性模式的特征，每 18 个周期重复一次。总体趋势向下，窗口早期出现最显著的下降，随后在前半段出现适度下降，并在后半段略有恢复。一个显著的峰值较早出现，约比均值高 1.4 个标准差，而一个深谷出现在窗口后期，约比均值低 1.8 个标准差。该序列与另外两个住房库存变量呈强正相关。

#### OpenTSLM 修正逐变量 caption：变量 2 | Housing Inventory: Active Listing Count in the United States 1202

**原文**

> The time series shows a steady decline with low volatility and a medium-strength seasonal pattern repeating every 18 periods. The overall trend is downward, with the most significant drop occurring early in the window, followed by a moderate decrease in the first half, and a slight recovery in the second half. A notable peak appears early, standing out as about 1.5 standard deviations above the mean, while a deep valley forms late in the window, reaching about 1.8 standard deviations below the mean. The series is strongly positively correlated with two other housing inventory variables.

**中文翻译**

> 该时间序列呈现出平稳下降、波动较低且具有中等强度季节性模式的特征，每 18 个周期重复一次。总体趋势向下，窗口早期出现最显著的下降，随后在前半段出现适度下降，并在后半段略有恢复。一个显著的峰值较早出现，约比均值高 1.5 个标准差，而一个深谷出现在窗口后期，约比均值低 1.8 个标准差。该序列与另外两个住房库存变量呈强正相关。

#### OpenTSLM 原生多变量 caption

**原文**

> The time series shows a steady decline with low volatility and a medium-strength seasonal pattern repeating every 17 periods. The overall trend is downward, with the most significant drop occurring early in the window, followed by a moderate decrease in the first half, and a slight recovery in the second half. A notable low appears late in the window, about 1.5 standard deviations below the mean.

**中文翻译**

> 该时间序列呈现出平稳下降、波动较低且具有中等强度季节性模式的特征，每 17 个周期重复一次。总体趋势向下，窗口早期出现最显著的下降，随后在前半段出现适度下降，并在后半段略有恢复。一个显著的低点出现在窗口后期，约比均值低 1.5 个标准差。

#### ChatTS 原生多变量 caption

**原文**

> Both variables exhibit identical trends and patterns, indicating perfect synchronization. The series starts at ~1.55 million, drops to ~832,732 by point 35, and stabilizes near ~553,510. Variability is minimal (noise SD ~3) except for a sudden drop between points 39-48. Cross-correlation between the two variables is 1.0, confirming they mirror each other exactly.

**中文翻译**

> 这两个变量表现出完全相同的趋势和模式，表明它们完全同步。该序列起始于约 155 万，在第 35 个点下降到约 832,732，并稳定在约 553,510 附近。波动性极小（噪声标准差约为 3），但在第 39-48 个点之间出现一次突然下降。两个变量之间的互相关为 1.0，证实它们完全相互镜像。

</details>

<details>
<summary>🧪 下游 QA 模型答案 / 评分</summary>

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；八行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `A` | `B` | ✗ 错误 | A |
| 题目 + 原始数值序列 (`numbers`) | `B` | `B` | ✓ 正确 | B |
| 题目 + OpenTSLM 修正逐变量 caption (`opentslm_fixed_caption`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM 修正逐变量 caption + 数值 (`opentslm_fixed_caption_plus`) | `B` | `B` | ✓ 正确 | B |
| 题目 + OpenTSLM 原生多变量 caption (`opentslm_native_caption`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM 原生多变量 caption + 数值 (`opentslm_native_caption_plus`) | `B` | `B` | ✓ 正确 | B |
| 题目 + ChatTS 原生多变量 caption (`chatts_native_caption`) | `A` | `B` | ✗ 错误 | A |
| 题目 + ChatTS 原生多变量 caption + 数值 (`chatts_native_caption_plus`) | `B` | `B` | ✓ 正确 | B |

</details>

<details>
<summary>🔎 Case 分析</summary>

- **答案格局**：`meta_only=A✗, numbers=B✓, opentslm_fixed_caption=A✗, opentslm_fixed_caption_plus=B✓, opentslm_native_caption=A✗, opentslm_native_caption_plus=B✓, chatts_native_caption=A✗, chatts_native_caption_plus=B✓`。
- **这个 case 说明的问题**：逐变量 caption、OpenTSLM 原生多变量、ChatTS 原生多变量都没有保留下游所需证据
- **对训练失败的含义**：如果原生多变量 caption 仍然答错，说明失败不是简单由“逐变量生成导致缺少跨变量上下文”造成；caption 还需要按题目抽取指定日期、窗口统计、变量差值/比值、排序或领域机制。若原生多变量能救回 fixed 逐变量失败，则说明跨变量联合输入确实有价值，但仍需要看这种现象在全量统计中占多少。

</details>

</details>

<details>
<summary>📈 Case 07: FREDQA `115` | meta-only 错，但 OpenTSLM 原生多变量 caption 对</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::115` |
| 变量数 / 序列长度 | `3` / `[378, 378, 378]` |
| 问题类型 | `Inductive Reasoning`, `Abductive Reasoning` |
| 正确答案 | `C` |
| 失败/对比模式 | meta-only 错，但 OpenTSLM 原生多变量 caption 对 |
| 本 case 关注点 | 排除题干先验后，OpenTSLM 原生多变量 caption 是否真正提供证据 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | Multiple Jobholders, Primary Job Full Time, Secondary Job Part Time. | 378 | 3.5242 | 3.1488 | 2.3392@316 | 3.9664@26 | -0.00208006 |
| 2 | Multiple Jobholders, Primary and secondary Job part Time. | 378 | 1.2659 | 1.3622 | 0.8983@315 | 1.5645@21 | -0.000105908 |
| 3 | Multiple Jobholders, Primary and secondary Job full Time | 378 | 0.221 | 0.2786 | 0.1242@252 | 0.3167@78 | 2.32932e-05 |

<details>
<summary>🖼 时序图</summary>

![FREDQA 115](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_115.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

> You are a time series analysis expert. In a U.S. Labor Market system, there are 3 metrics: Multiple Jobholders, Primary Job Full Time, Secondary Job Part Time&lt;ts&gt;&lt;ts/&gt;; Multiple Jobholders, Primary and Secondary Job Part Time&lt;ts&gt;&lt;ts/&gt;; Multiple Jobholders, Primary and Secondary Job Full Time&lt;ts&gt;&lt;ts/&gt;. Using monthly data from January 1994 to June 2025, calculate the percentage point change for each metric from January 1994 to January 2024. Based on the magnitude and direction of these changes, which labor market trend best explains the most significant shift observed?

**题干中文翻译**

> 你是一位时间序列分析专家。在一个美国劳动力市场系统中，有 3 个指标：多个工作者，主要工作全职，次要工作兼职&lt;ts&gt;&lt;ts/&gt;；多个工作者，主要和次要工作兼职&lt;ts&gt;&lt;ts/&gt;；多个工作者，主要和次要工作全职&lt;ts&gt;&lt;ts/&gt;。使用 1994 年 1 月至 2025 年 6 月的月度数据，计算每个指标从 1994 年 1 月到 2024 年 1 月的百分点变化。根据这些变化的幅度和方向，哪种劳动力市场趋势最能解释所观察到的最显著变化？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Growth of the gig economy leading to more part-time secondary jobs | 零工经济的增长导致更多兼职的第二份工作 |
| `B` | Decline in full-time job stability encouraging additional full-time work | 全职工作稳定性的下降鼓励额外的全职工作 |
| `C` | Increased work-life balance preferences reducing full-time plus part-time moonlighting | 对工作与生活平衡偏好的增加减少了全职加兼职的夜间兼职工作 |
| `D` | Rise in remote work enabling more dual full-time job arrangements | 远程工作的兴起使更多双全职工作安排成为可能 |

**正确答案**：`C`

**标准解释**

> 原始 FREDQA 样本没有提供标准解释字段；本报告保留题干、选项、正确答案和模型输出用于 case study。

</details>

<details>
<summary>📝 三类 caption 与中文翻译</summary>

#### OpenTSLM 修正逐变量 caption：变量 1 | Multiple Jobholders, Primary Job Full Time, Secondary Job Part Time.

**原文**

> The time series shows a flat trend with low volatility and a strong seasonal pattern repeating every 12 months. There is a noticeable upward phase early in the window followed by a moderate upward movement in the first half, then a decline in the second half. A peak occurs in the second half with a magnitude of about 2.0 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 2.2 standard deviations from the mean. The series is strongly positively correlated with two related variables.

**中文翻译**

> 该时间序列呈现平坦趋势，波动性较低，并且有每 12 个月重复一次的强季节性模式。窗口前期有明显上升阶段，随后在前半段出现适度上升，之后在后半段下降。峰值出现在后半段，幅度约为均值的 2.0 个标准差，而谷值出现在窗口早期，幅度约为均值的 2.2 个标准差。该序列与另外两个相关变量呈强正相关。

#### OpenTSLM 修正逐变量 caption：变量 2 | Multiple Jobholders, Primary and secondary Job part Time.

**原文**

> The time series shows a flat trend with low volatility and a strong seasonal pattern repeating every 12 months. There is a noticeable upward phase early in the window followed by a more pronounced upward movement in the first half, then a significant downward shift in the second half. A peak occurs in the second half with a magnitude of about 2.1 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 2.2 standard deviations from the mean. The series exhibits a strong positive correlation with the number of full-time jobholders.

**中文翻译**

> 该时间序列呈现平坦趋势，波动性较低，并且有每 12 个月重复一次的强季节性模式。窗口前期有明显上升阶段，随后在前半段出现更明显的上升，之后在后半段出现显著下降。峰值出现在后半段，幅度约为均值的 2.1 个标准差，而谷值出现在窗口早期，幅度约为均值的 2.2 个标准差。该序列与全职工作者数量呈强正相关。

#### OpenTSLM 修正逐变量 caption：变量 3 | Multiple Jobholders, Primary and secondary Job full Time

**原文**

> The time series shows a flat trend with low volatility and a strong seasonal pattern repeating every 18 periods. There is a noticeable upward phase early in the window followed by a significant downward phase in the first half, and a smaller upward movement in the second half. A peak occurs in the first half with a magnitude of about 2.0 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 1.8 standard deviations from the mean. The series exhibits strong positive correlations with two related variables.

**中文翻译**

> 该时间序列呈现平坦趋势，波动性较低，并且有每 18 个周期重复一次的强季节性模式。窗口前期有明显上升阶段，随后在前半段出现显著下降阶段，之后在后半段有较小的上升。峰值出现在前半段，幅度约为均值的 2.0 个标准差，而谷值出现在窗口早期，幅度约为均值的 1.8 个标准差。该序列与另外两个相关变量呈强正相关。

#### OpenTSLM 原生多变量 caption

**原文**

> The time series shows a flat trend with low volatility and medium strength seasonality every 84 periods. There is a noticeable upward phase early in the window followed by a significant downward phase in the second half. A peak occurs in the second half with a magnitude of about 2.6 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 2.2 standard deviations from the mean. The series exhibits strong positive correlation with multiple jobholders in both full and part time roles.

**中文翻译**

> 该时间序列呈现平坦趋势，波动性较低，并且每 84 个周期有中等强度的季节性。窗口前期有明显上升阶段，随后在后半段出现显著下降阶段。峰值出现在后半段，幅度约为均值的 2.6 个标准差，而谷值出现在窗口早期，幅度约为均值的 2.2 个标准差。该序列与同时从事全职和兼职角色的多个工作者呈强正相关。

#### ChatTS 原生多变量 caption

**原文**

> The time series for Variable 1 exhibits an overall decreasing trend, starting at approximately 3.54 and ending around 3.07, with an amplitude of -0.47. The data shows moderate noise, indicated by a standard deviation of 0.14, contributing to a relatively smooth curve. Notable local changes include a sudden decrease between points 192 and 198, where the value dropped from about 3.27 to 2.96, forming a short trough with an amplitude of 0.33. Additionally, there is a downward spike between points 214 and 216, where the value rapidly fell from around 3.07 to 2.78 before quickly recovering. Cross-variable relationships suggest that while Variable 1 decreases, Variable 2 and Variable 3 show more stable trends, indicating potential inverse or independent dynamics between these variables.

**中文翻译**

> 变量 1 的时间序列表现出整体下降趋势，起始约为 3.54，结束约为 3.07，幅度为 -0.47。数据呈现中等噪声，其标准差为 0.14，形成了相对平滑的曲线。值得注意的局部变化包括第 192 点到第 198 点之间的突然下降，数值从约 3.27 降至 2.96，形成了一个幅度为 0.33 的短暂谷底。此外，第 214 点到第 216 点之间出现了向下尖峰，数值从约 3.07 快速下降到 2.78，随后迅速恢复。变量间关系表明，当变量 1 下降时，变量 2 和变量 3 显示出更稳定的趋势，表明这些变量之间可能存在反向或独立动态。

</details>

<details>
<summary>🧪 下游 QA 模型答案 / 评分</summary>

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；八行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `A` | `C` | ✗ 错误 | A |
| 题目 + 原始数值序列 (`numbers`) | `C` | `C` | ✓ 正确 | C |
| 题目 + OpenTSLM 修正逐变量 caption (`opentslm_fixed_caption`) | `C` | `C` | ✓ 正确 | C |
| 题目 + OpenTSLM 修正逐变量 caption + 数值 (`opentslm_fixed_caption_plus`) | `C` | `C` | ✓ 正确 | C |
| 题目 + OpenTSLM 原生多变量 caption (`opentslm_native_caption`) | `C` | `C` | ✓ 正确 | C |
| 题目 + OpenTSLM 原生多变量 caption + 数值 (`opentslm_native_caption_plus`) | `C` | `C` | ✓ 正确 | C |
| 题目 + ChatTS 原生多变量 caption (`chatts_native_caption`) | `C` | `C` | ✓ 正确 | C |
| 题目 + ChatTS 原生多变量 caption + 数值 (`chatts_native_caption_plus`) | `C` | `C` | ✓ 正确 | C |

</details>

<details>
<summary>🔎 Case 分析</summary>

- **答案格局**：`meta_only=A✗, numbers=C✓, opentslm_fixed_caption=C✓, opentslm_fixed_caption_plus=C✓, opentslm_native_caption=C✓, opentslm_native_caption_plus=C✓, chatts_native_caption=C✓, chatts_native_caption_plus=C✓`。
- **这个 case 说明的问题**：排除题干先验后，OpenTSLM 原生多变量 caption 是否真正提供证据
- **对训练失败的含义**：如果原生多变量 caption 仍然答错，说明失败不是简单由“逐变量生成导致缺少跨变量上下文”造成；caption 还需要按题目抽取指定日期、窗口统计、变量差值/比值、排序或领域机制。若原生多变量能救回 fixed 逐变量失败，则说明跨变量联合输入确实有价值，但仍需要看这种现象在全量统计中占多少。

</details>

</details>

<details>
<summary>📈 Case 08: FREDQA `396` | meta-only 错，但 ChatTS 原生多变量 caption 对</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::396` |
| 变量数 / 序列长度 | `4` / `[6, 6, 6, 6]` |
| 问题类型 | `Inductive Reasoning`, `Abductive Reasoning` |
| 正确答案 | `B` |
| 失败/对比模式 | meta-only 错，但 ChatTS 原生多变量 caption 对 |
| 本 case 关注点 | 排除题干先验后，ChatTS 原生多变量 caption 是否真正提供证据 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | Net Worth Held by the Top 1% (99th to 100th Wealth Percentiles), Index Q4 2019=100, Quarterly, Not Seasonally Adjusted  | 6 | 100 | 118.317 | 90.2166@1 | 118.317@5 | 4.67329 |
| 2 | Net Worth Held by the 90th to 99th Wealth Percentiles, Index Q4 2019=100, Quarterly, Not Seasonally Adjusted  | 6 | 100 | 112.641 | 93.9779@1 | 112.641@5 | 3.18539 |
| 3 | Net Worth Held by the 50th to 90th Wealth Percentiles, Index Q4 2019=100, Quarterly, Not Seasonally Adjusted  | 6 | 100 | 119.685 | 98.7686@1 | 119.685@5 | 4.29576 |
| 4 | Net Worth Held by the Bottom 50% (1st to 50th Wealth Percentiles), Index Q4 2019=100, Quarterly, Not Seasonally Adjusted  | 6 | 100 | 151.904 | 99.7641@1 | 151.904@5 | 11.0618 |

<details>
<summary>🖼 时序图</summary>

![FREDQA 396](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_396.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

> You are a time series analysis expert. In a U.S. Household Wealth system, there are 4 metrics: Net Worth Held by the Top 1% (99th to 100th Wealth Percentiles), indexed to Q4 2019=100, quarterly, not seasonally adjusted&lt;ts&gt;&lt;ts/&gt;; Net Worth Held by the 90th to 99th Wealth Percentiles, indexed to Q4 2019=100, quarterly, not seasonally adjusted&lt;ts&gt;&lt;ts/&gt;; Net Worth Held by the 50th to 90th Wealth Percentiles, indexed to Q4 2019=100, quarterly, not seasonally adjusted&lt;ts&gt;&lt;ts/&gt;; Net Worth Held by the Bottom 50% (1st to 50th Wealth Percentiles), indexed to Q4 2019=100, quarterly, not seasonally adjusted&lt;ts&gt;&lt;ts/&gt;. Using quarterly data from Q4 2019 (2019-10-01) to Q1 2021 (2021-01-01), calculate the percentage change in net worth index for each group over this period. Based on which group had the largest percentage change, which asset-composition factor from the context best explains this result?

**题干中文翻译**

> 你是一名时间序列分析专家。在一个美国住户财富系统中，有 4 个指标：最富有 1%（第 99 到第 100 财富百分位）持有的净资产，按 Q4 2019=100 进行指数化，季度数据，未进行季节调整&lt;ts&gt;&lt;ts/&gt;；第 90 到第 99 财富百分位持有的净资产，按 Q4 2019=100 进行指数化，季度数据，未进行季节调整&lt;ts&gt;&lt;ts/&gt;；第 50 到第 90 财富百分位持有的净资产，按 Q4 2019=100 进行指数化，季度数据，未进行季节调整&lt;ts&gt;&lt;ts/&gt;；底部 50%（第 1 到第 50 财富百分位）持有的净资产，按 Q4 2019=100 进行指数化，季度数据，未进行季节调整&lt;ts&gt;&lt;ts/&gt;。使用从 Q4 2019（2019-10-01）到 Q1 2021（2021-01-01）的季度数据，计算该期间内每个组的净资产指数百分比变化。根据哪个组的百分比变化最大，结合上下文，哪个资产构成因素最能解释这一结果？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Larger holdings of financial instruments and business stakes | 金融工具和商业股权持有量更大 |
| `B` | Higher proportion of wealth in real estate assets | 房地产资产在财富中的占比更高 |
| `C` | Greater reliance on labor income rather than asset appreciation | 更依赖劳动收入而非资产升值 |
| `D` | More diversified portfolios across stocks, bonds, and cash | 在股票、债券和现金之间的投资组合更加多元化 |

**正确答案**：`B`

**标准解释**

> 原始 FREDQA 样本没有提供标准解释字段；本报告保留题干、选项、正确答案和模型输出用于 case study。

</details>

<details>
<summary>📝 三类 caption 与中文翻译</summary>

#### OpenTSLM 修正逐变量 caption：变量 1 | Net Worth Held by the Top 1% (99th to 100th Wealth Percentiles), Index Q4 2019=100, Quarterly, Not Seasonally Adjusted 

**原文**

> The time series shows a gradual upward trend with low volatility and a medium-strength seasonal pattern repeating every 18 periods. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a slightly smaller increase in the second half. A notable peak occurs late in the window, reaching about 1.2 standard deviations above the mean, while a deep valley is observed early on, dropping about 2.0 standard deviations below the mean. The series is strongly positively correlated with the net worth of the top 1% population.

**中文翻译**

> 该时间序列表现出缓慢上升的趋势，波动较低，并且存在一种中等强度的季节性模式，每 18 个周期重复一次。数据在窗口前段开始时出现适度上升，随后在前半段出现更明显的上升，而在后半段则出现略小的上升。一个显著峰值出现在窗口后期，达到均值上方约 1.2 个标准差，而一个深谷出现在较早时期，下降到均值下方约 2.0 个标准差。该序列与最富有 1% 人口的净资产呈强正相关。

#### OpenTSLM 修正逐变量 caption：变量 2 | Net Worth Held by the 90th to 99th Wealth Percentiles, Index Q4 2019=100, Quarterly, Not Seasonally Adjusted 

**原文**

> The time series shows a gradual upward trend with low volatility and a medium-strength seasonal pattern repeating every 15 quarters. Early in the window, there is a slight decline, followed by a moderate increase in the first half and a more pronounced rise in the second half. A notable peak occurs late in the window, reaching about 1.3 standard deviations above the mean, while a deep valley is observed early on, reaching about 2.0 standard deviations below the mean. The series is strongly positively correlated with the 75th to 90th wealth percentiles' net worth and strongly negatively correlated with the 10th to 25th wealth percentiles' net worth.

**中文翻译**

> 该时间序列表现出缓慢上升的趋势，波动较低，并且存在一种中等强度的季节性模式，每 15 个季度重复一次。窗口前期略有下降，随后在前半段出现适度上升，并在后半段出现更明显的上升。一个显著峰值出现在窗口后期，达到均值上方约 1.3 个标准差，而一个深谷出现在较早时期，达到均值下方约 2.0 个标准差。该序列与第 75 到第 90 财富百分位的净资产呈强正相关，并与第 10 到第 25 财富百分位的净资产呈强负相关。

#### OpenTSLM 修正逐变量 caption：变量 3 | Net Worth Held by the 50th to 90th Wealth Percentiles, Index Q4 2019=100, Quarterly, Not Seasonally Adjusted 

**原文**

> The time series shows a gradual upward trend with low volatility and a medium-strength seasonal pattern repeating every 15 quarters. Early in the window, there is a moderate increase, followed by a decline in the first half, and a significant rise in the second half. A notable peak occurs late in the window, reaching about 1.3 standard deviations above the mean, while a deep valley is observed around the middle, reaching about 2.0 standard deviations below the mean. The overall net increase over the time span is approximately 20.5%.

**中文翻译**

> 该时间序列表现出缓慢上升的趋势，波动较低，并且存在一种中等强度的季节性模式，每 15 个季度重复一次。窗口前期出现适度上升，随后在前半段出现下降，并在后半段出现显著上升。一个显著峰值出现在窗口后期，达到均值上方约 1.3 个标准差，而一个深谷出现在中间附近，达到均值下方约 2.0 个标准差。整个时间跨度内的总体净增长约为 20.5%。

#### OpenTSLM 修正逐变量 caption：变量 4 | Net Worth Held by the Bottom 50% (1st to 50th Wealth Percentiles), Index Q4 2019=100, Quarterly, Not Seasonally Adjusted 

**原文**

> The time series shows a gradual upward trend with low volatility and a medium-strength seasonal pattern repeating every 15 quarters. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a slightly smaller but still positive growth in the second half. A notable peak occurs late in the window, reaching about 1.2 standard deviations above the mean, while a deep valley is observed early on, dropping about 2.0 standard deviations below the mean. The overall net increase over the time span is approximately 37.5%.

**中文翻译**

> 该时间序列表现出缓慢上升的趋势，波动较低，并且存在一种中等强度的季节性模式，每 15 个季度重复一次。数据在窗口前段开始时出现适度上升，随后在前半段出现更明显的上升，而在后半段则出现略小但仍为正的增长。一个显著峰值出现在窗口后期，达到均值上方约 1.2 个标准差，而一个深谷出现在较早时期，下降到均值下方约 2.0 个标准差。整个时间跨度内的总体净增长约为 37.5%。

#### OpenTSLM 原生多变量 caption

**原文**

> The time series shows a gradual upward trend with low volatility and a medium-strength seasonal pattern repeating every four quarters. The data starts with a moderate increase in the early part of the window, followed by a stronger rise in the first half, and a slightly smaller increase in the second half. A notable peak occurs late in the window, reaching about 1.2 standard deviations above the mean, while a deep valley is observed early on, reaching about 2.0 standard deviations below the mean. The overall growth over the time span is substantial, with a net increase of over 50%.

**中文翻译**

> 该时间序列表现出缓慢上升的趋势，波动较低，并且存在一种中等强度的季节性模式，每四个季度重复一次。数据在窗口前段开始时出现适度上升，随后在前半段出现更强的上升，而在后半段则出现略小的上升。一个显著峰值出现在窗口后期，达到均值上方约 1.2 个标准差，而一个深谷出现在较早时期，达到均值下方约 2.0 个标准差。整个时间跨度内的总体增长相当显著，净增长超过 50%。

#### ChatTS 原生多变量 caption

**原文**

> All four time series exhibit steady upward trends from their baseline of ~100, with minimal noise (standard deviation ~0.00). Variable 1 shows the highest growth (18.33 total increase), followed by Variables 2 (12.64), 3 (19.69), and 4 (51.90). Notable changes include a sharp spike in Variable 1 between points 2-4, but no periodic fluctuations or local features are observed. Cross-variable analysis reveals synchronized upward movements, suggesting a systemic driver such as economic growth. The significant divergence in Variable 4's growth compared to others indicates potential wealth redistribution or unique factors affecting the bottom 50%.

**中文翻译**

> 所有四个时间序列都从其约 100 的基线稳定上升，噪声极小（标准差约为 0.00）。变量 1 的增长最高（总增量 18.33），其次是变量 2（12.64）、变量 3（19.69）和变量 4（51.90）。值得注意的变化包括变量 1 在第 2-4 个点之间出现急剧尖峰，但没有观察到周期性波动或局部特征。跨变量分析显示同步上升，暗示存在诸如经济增长之类的系统性驱动因素。变量 4 的增长与其他变量相比显著分化，表明可能存在财富再分配或影响底部 50% 的独特因素。

</details>

<details>
<summary>🧪 下游 QA 模型答案 / 评分</summary>

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；八行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `A` | `B` | ✗ 错误 | A |
| 题目 + 原始数值序列 (`numbers`) | `B` | `B` | ✓ 正确 | B |
| 题目 + OpenTSLM 修正逐变量 caption (`opentslm_fixed_caption`) | `C` | `B` | ✗ 错误 | C |
| 题目 + OpenTSLM 修正逐变量 caption + 数值 (`opentslm_fixed_caption_plus`) | `B` | `B` | ✓ 正确 | B |
| 题目 + OpenTSLM 原生多变量 caption (`opentslm_native_caption`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM 原生多变量 caption + 数值 (`opentslm_native_caption_plus`) | `B` | `B` | ✓ 正确 | B |
| 题目 + ChatTS 原生多变量 caption (`chatts_native_caption`) | `B` | `B` | ✓ 正确 | B |
| 题目 + ChatTS 原生多变量 caption + 数值 (`chatts_native_caption_plus`) | `B` | `B` | ✓ 正确 | B |

</details>

<details>
<summary>🔎 Case 分析</summary>

- **答案格局**：`meta_only=A✗, numbers=B✓, opentslm_fixed_caption=C✗, opentslm_fixed_caption_plus=B✓, opentslm_native_caption=A✗, opentslm_native_caption_plus=B✓, chatts_native_caption=B✓, chatts_native_caption_plus=B✓`。
- **这个 case 说明的问题**：排除题干先验后，ChatTS 原生多变量 caption 是否真正提供证据
- **对训练失败的含义**：如果原生多变量 caption 仍然答错，说明失败不是简单由“逐变量生成导致缺少跨变量上下文”造成；caption 还需要按题目抽取指定日期、窗口统计、变量差值/比值、排序或领域机制。若原生多变量能救回 fixed 逐变量失败，则说明跨变量联合输入确实有价值，但仍需要看这种现象在全量统计中占多少。

</details>

</details>

<details>
<summary>📈 Case 09: FREDQA `587` | caption-only 对，但 caption+numbers 反而错</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::587` |
| 变量数 / 序列长度 | `2` / `[214, 214]` |
| 问题类型 | `Analogical Reasoning`, `Abductive Reasoning` |
| 正确答案 | `A` |
| 失败/对比模式 | caption-only 对，但 caption+numbers 反而错 |
| 本 case 关注点 | 检验多证据融合是否非单调，caption 加 numbers 后是否被干扰 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | candy | 214 | 100 | 146.961 | 99.8@5 | 146.961@213 | 0.237534 |
| 2 | all items | 214 | 100 | 146.785 | 100@0 | 147.116@211 | 0.24135 |

<details>
<summary>🖼 时序图</summary>

![FREDQA 587](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_587.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

> You are a time series analysis expert. In a Consumer Price Index (CPI) system, there are 2 metrics: Candy Price Index (set to 100 in December 1997)&lt;ts&gt;&lt;ts/&gt;; All Items CPI (general consumer price index, set to 100 in December 1997)&lt;ts&gt;&lt;ts/&gt;. Using monthly data from December 1997 to September 2015, calculate the ratio of the Candy Price Index to the All Items CPI for December 2007 (end of the pre-Great Recession economic boom) and December 2010 (three years into the Great Recession recovery). Based on these ratios, which economic factor best explains the change in the relative price of candy between these two periods?

**题干中文翻译**

> 你是一名时间序列分析专家。在一个消费者价格指数（CPI）系统中，有 2 个指标：糖果价格指数（1997 年 12 月设为 100）&lt;ts&gt;&lt;ts/&gt;；全部商品 CPI（一般消费者价格指数，1997 年 12 月设为 100）&lt;ts&gt;&lt;ts/&gt;。使用 1997 年 12 月到 2015 年 9 月的月度数据，计算 2007 年 12 月（大衰退前经济繁荣结束时）和 2010 年 12 月（大衰退复苏三年后）糖果价格指数与全部商品 CPI 的比率。基于这些比率，哪种经济因素最能解释这两个时期之间糖果相对价格的变化？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | High price elasticity of candy supply, allowing producers to meet demand changes without significant price increases | 糖果供给具有较高的价格弹性，使生产者能够在需求变化时满足需求而无需显著提高价格 |
| `B` | A sustained increase in consumer demand for candy as an 'affordable luxury' during economic downturns | 在经济低迷时期，消费者对糖果作为“可负担的奢侈品”的需求持续增加 |
| `C` | A temporary spike in the cost of cocoa, a key input for chocolate candy production | 可可成本的短暂飙升，可可是巧克力糖果生产的关键投入 |
| `D` | Reduced price competition in the candy market due to industry consolidation | 由于行业整合，糖果市场中的价格竞争减少 |

**正确答案**：`A`

**标准解释**

> 原始 FREDQA 样本没有提供标准解释字段；本报告保留题干、选项、正确答案和模型输出用于 case study。

</details>

<details>
<summary>📝 三类 caption 与中文翻译</summary>

#### OpenTSLM 修正逐变量 caption：变量 1 | candy

**原文**

> The time series shows a flat trend with low volatility and medium strength seasonality every 85 time units. There is a noticeable upward phase early in the window followed by a downward phase in the first half. A peak occurs in the first half with a magnitude of about 1.5 standard deviations from the mean, while a deeper valley is observed early in the window, reaching about 1.8 standard deviations below the mean. The series is strongly positively correlated with both the "milk" and "cookies" variables.

**中文翻译**

> 该时间序列表现为平坦趋势、低波动性，并且每 85 个时间单位具有中等强度的季节性。窗口早期有明显的上升阶段，随后在前半段出现下降阶段。前半段出现一个峰值，幅度约为均值的 1.5 个标准差，而在窗口早期观察到一个更深的谷值，约为均值下方 1.8 个标准差。该序列与“milk”和“cookies”变量均呈强正相关。

#### OpenTSLM 修正逐变量 caption：变量 2 | all items

**原文**

> The time series shows a flat trend with low volatility and a strong seasonal pattern repeating every 100 periods. There is a noticeable upward phase early in the window followed by a significant downward movement in the first half, then another upward trend in the second half. A peak occurs in the first half with a magnitude of about 1.5 standard deviations from the mean, while a deeper valley appears in the second half, reaching about 2.0 standard deviations from the mean. The data exhibits strong positive correlation with variable 2 and moderate positive correlation with variable 3.

**中文翻译**

> 该时间序列表现为平坦趋势、低波动性，并且每 100 个周期重复出现强季节性模式。窗口早期有明显的上升阶段，随后在前半段出现显著下降，再在后半段出现另一上升趋势。前半段出现一个峰值，幅度约为均值的 1.5 个标准差，而后半段出现一个更深的谷值，约为均值下方 2.0 个标准差。该数据与变量 2 呈强正相关，与变量 3 呈中等正相关。

#### OpenTSLM 原生多变量 caption

**原文**

> The time series shows a flat trend with low volatility and no strong seasonality. There is a noticeable downward phase early in the window followed by an upward movement in the same region. A peak occurs in the first half of the data, reaching about 1.5 standard deviations above the mean, while a deeper valley appears in the second half, reaching about 2.0 standard deviations below the mean. The series is strongly positively correlated with another variable, "all items."

**中文翻译**

> 该时间序列表现为平坦趋势、低波动性，且没有强季节性。窗口早期有明显的下降阶段，随后在同一区域出现上升运动。数据前半段出现一个峰值，约为均值上方 1.5 个标准差，而数据后半段出现一个更深的谷值，约为均值下方 2.0 个标准差。该序列与另一个变量“all items”呈强正相关。

#### ChatTS 原生多变量 caption

**原文**

> Both variables exhibit identical trends: an overall increasing pattern from 100.00 to 146.78 over 214 points. There is no periodicity or local characteristics observed in either series. The variability is minimal, with a noise standard deviation of 0.32 for candy and 0.61 for all items, indicating smooth curves. No significant changes or spikes are noted. The correlation between the two variables is perfect, suggesting they move in lockstep. No inverse or additional patterns exist between them.

**中文翻译**

> 两个变量表现出相同的趋势：从 100.00 到 146.78 的整体上升模式，共 214 个点。两个序列都没有观察到周期性或局部特征。波动性极小，糖果的噪声标准差为 0.32，全部商品的噪声标准差为 0.61，表明曲线平滑。没有发现显著变化或尖峰。两个变量之间的相关性是完全一致的，表明它们同步变化。两者之间不存在反向或额外模式。

</details>

<details>
<summary>🧪 下游 QA 模型答案 / 评分</summary>

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；八行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `B` | `A` | ✗ 错误 | B |
| 题目 + 原始数值序列 (`numbers`) | `B` | `A` | ✗ 错误 | B |
| 题目 + OpenTSLM 修正逐变量 caption (`opentslm_fixed_caption`) | `B` | `A` | ✗ 错误 | B |
| 题目 + OpenTSLM 修正逐变量 caption + 数值 (`opentslm_fixed_caption_plus`) | `C` | `A` | ✗ 错误 | C |
| 题目 + OpenTSLM 原生多变量 caption (`opentslm_native_caption`) | `C` | `A` | ✗ 错误 | C |
| 题目 + OpenTSLM 原生多变量 caption + 数值 (`opentslm_native_caption_plus`) | `B` | `A` | ✗ 错误 | B |
| 题目 + ChatTS 原生多变量 caption (`chatts_native_caption`) | `A` | `A` | ✓ 正确 | A |
| 题目 + ChatTS 原生多变量 caption + 数值 (`chatts_native_caption_plus`) | `B` | `A` | ✗ 错误 | B |

</details>

<details>
<summary>🔎 Case 分析</summary>

- **答案格局**：`meta_only=B✗, numbers=B✗, opentslm_fixed_caption=B✗, opentslm_fixed_caption_plus=C✗, opentslm_native_caption=C✗, opentslm_native_caption_plus=B✗, chatts_native_caption=A✓, chatts_native_caption_plus=B✗`。
- **这个 case 说明的问题**：检验多证据融合是否非单调，caption 加 numbers 后是否被干扰
- **对训练失败的含义**：如果原生多变量 caption 仍然答错，说明失败不是简单由“逐变量生成导致缺少跨变量上下文”造成；caption 还需要按题目抽取指定日期、窗口统计、变量差值/比值、排序或领域机制。若原生多变量能救回 fixed 逐变量失败，则说明跨变量联合输入确实有价值，但仍需要看这种现象在全量统计中占多少。

</details>

</details>

<details>
<summary>📈 Case 10: FREDQA `6` | meta、numbers、三种 caption 全错</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::6` |
| 变量数 / 序列长度 | `3` / `[282, 282, 282]` |
| 问题类型 | `Analogical Reasoning`, `Abductive Reasoning` |
| 正确答案 | `B` |
| 失败/对比模式 | meta、numbers、三种 caption 全错 |
| 本 case 关注点 | 失败不只是 caption 生成问题，还可能是公式执行、领域机制或长题干定位失败 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | OECD unemployment rate US 25-54 | 282 | 3.8333 | 3.2767 | 2.1667@55 | 11.3333@261 | 0.00300931 |
| 2 | unemployment rate | 282 | 4.7 | 4.2 | 3.4@55 | 13@261 | 0.000299659 |
| 3 | unemployment rate 25-54 | 282 | 3.8 | 3.5 | 2.2@55 | 11.3@261 | 0.00303461 |

<details>
<summary>🖼 时序图</summary>

![FREDQA 6](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-native-rerun-zh/figures/fredqa_native_6.png)

</details>

<details>
<summary>❓ QA 问题与中文翻译</summary>

**题干原文**

> You are a time series analysis expert. In a Labor Market system, there are 3 metrics: OECD Harmonized Unemployment Rate for ages 25-54 &lt;ts&gt;&lt;ts/&gt;; BLS Unemployment Rate for ages 16 and over &lt;ts&gt;&lt;ts/&gt;; BLS Unemployment Rate for ages 25-54 &lt;ts&gt;&lt;ts/&gt;. Using quarterly data from Q1 1955 to Q2 2025, determine which group had the largest unemployment decline from Q2 1975 to Q2 1976 by comparing BLS rates. What economic force primarily drove this divergence?

**题干中文翻译**

> 你是一位时间序列分析专家。在一个劳动力市场系统中，有3个指标：25-54岁人群的 OECD 统一失业率 &lt;ts&gt;&lt;ts/&gt;；16岁及以上人群的 BLS 失业率 &lt;ts&gt;&lt;ts/&gt;；25-54岁人群的 BLS 失业率 &lt;ts&gt;&lt;ts/&gt;。使用从 1955 年第一季度到 2025 年第二季度的季度数据，通过比较 BLS 比率，确定从 1975 年第二季度到 1976 年第二季度哪个群体的失业率下降幅度最大。是什么经济力量主要驱动了这种分化？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Strong recovery in cyclical industries employing prime-age workers | 周期性行业中雇佣核心年龄劳动者的强劲复苏 |
| `B` | Demographic shifts increasing youth labor force entry | 增加青年劳动力进入的人口结构变化 |
| `C` | Expanded social safety nets reducing older workers' job searches | 扩大社会保障网以减少年长工人的求职活动 |
| `D` | Supply-chain disruptions affecting manufacturing hubs | 影响制造业枢纽的供应链中断 |

**正确答案**：`B`

**标准解释**

> 原始 FREDQA 样本没有提供标准解释字段；本报告保留题干、选项、正确答案和模型输出用于 case study。

</details>

<details>
<summary>📝 三类 caption 与中文翻译</summary>

#### OpenTSLM 修正逐变量 caption：变量 1 | OECD unemployment rate US 25-54

**原文**

> The time series shows a flat trend with low volatility and medium strength seasonality every 102 periods. There is a noticeable upward phase early in the window followed by a significant downward phase in the first half, and a smaller upward movement in the second half. A peak occurs in the first half with a magnitude of about 2.2 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 1.8 standard deviations from the mean. The unemployment rate is moderately positively correlated with the Canadian unemployment rate and strongly positively correlated with the Australian unemployment rate.

**中文翻译**

> 该时间序列显示出平稳趋势、低波动性，并且每 102 个周期存在中等强度的季节性。窗口早期有明显上升阶段，随后在前半段出现显著下降阶段，第二阶段则有较小的上升运动。前半段出现一个峰值，其幅度约为距均值 2.2 个标准差，而在窗口早期观察到一个谷值，其幅度约为距均值 1.8 个标准差。该失业率与加拿大失业率呈中度正相关，与澳大利亚失业率呈强正相关。

#### OpenTSLM 修正逐变量 caption：变量 2 | unemployment rate

**原文**

> The unemployment rate shows a flat trend with low volatility and a strong seasonal pattern repeating every 20 periods. There is a noticeable upward phase early in the window followed by a significant downward movement in the first half, then a smaller upward trend in the second half. A peak occurs in the first half with a magnitude of about 2.2 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 1.7 standard deviations from the mean. The unemployment rate is strongly positively correlated with the average wage and moderately negatively correlated with the average price level.

**中文翻译**

> 该失业率显示出平稳趋势、低波动性，并且每 20 个周期重复一次强季节性模式。窗口早期有明显上升阶段，随后在前半段出现显著下降运动，之后在第二阶段呈现较小的上升趋势。前半段出现一个峰值，其幅度约为距均值 2.2 个标准差，而在窗口早期观察到一个谷值，其幅度约为距均值 1.7 个标准差。该失业率与平均工资呈强正相关，与平均价格水平呈中度负相关。

#### OpenTSLM 修正逐变量 caption：变量 3 | unemployment rate 25-54

**原文**

> The unemployment rate for individuals aged 25-54 shows a flat trend with low volatility and weak seasonal patterns. There is a notable upward phase early in the window followed by a significant downward movement in the first half, then a smaller upward trend in the second half. A peak occurs in the first half with a magnitude of about 2.8 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 1.7 standard deviations from the mean. The series exhibits strong positive correlations with unemployment rates for individuals aged 16-24 and 55-64.

**中文翻译**

> 25-54 岁人群的失业率显示出平稳趋势、低波动性和较弱的季节性模式。窗口早期有显著上升阶段，随后在前半段出现显著下降运动，之后在第二阶段呈现较小的上升趋势。前半段出现一个峰值，其幅度约为距均值 2.8 个标准差，而在窗口早期观察到一个谷值，其幅度约为距均值 1.7 个标准差。该序列与 16-24 岁和 55-64 岁人群的失业率呈强正相关。

#### OpenTSLM 原生多变量 caption

**原文**

> The time series shows a flat trend with low volatility and weak seasonality, spanning from 1955 to 2025. There is a notable upward phase early in the window followed by a significant downward movement in the first half, then a smaller upward trend in the second half. A peak occurs in the first half with a magnitude of about 2.2 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 2.0 standard deviations from the mean. The data exhibits strong positive correlation with the unemployment rate and strong negative correlation with the unemployment rate 25-54.

**中文翻译**

> 该时间序列显示出平稳趋势、低波动性和较弱的季节性，时间跨度从 1955 年到 2025 年。窗口早期有明显上升阶段，随后在前半段出现显著下降运动，之后在第二阶段呈现较小的上升趋势。前半段出现一个峰值，其幅度约为距均值 2.2 个标准差，而在窗口早期观察到一个谷值，其幅度约为距均值 2.0 个标准差。该数据与失业率呈强正相关，与 25-54 岁失业率呈强负相关。

#### ChatTS 原生多变量 caption

**原文**

> All three variables exhibit identical patterns: they start at ~3.80, end at ~3.50, and show overall steady trends with local variations. The time series display minimal noise (standard deviation ~0.00) and smooth transitions. Key local features include sudden increases (e.g., at points 10-18 and 76-86) and a sharp upward spike (points 260-262). The variables share identical periodic fluctuations (amplitude ~3.0, period ~77.7 points) and similar overall amplitudes (~0.30). Cross-correlation analysis indicates strong synchronization in both trend and local changes.

**中文翻译**

> 这三个变量都表现出相同的模式：它们都从约 3.80 开始，到约 3.50 结束，并且整体呈现稳定趋势，同时伴有局部变化。时间序列显示出极小的噪声（标准差约为 0.00）和平滑的过渡。关键局部特征包括突然上升（例如在第 10-18 点和第 76-86 点）以及一个明显的向上尖峰（第 260-262 点）。这些变量共享相同的周期性波动（振幅约为 3.0，周期约为 77.7 个点）以及相似的整体振幅（约为 0.30）。交叉相关分析表明，在趋势和局部变化方面都具有强同步性.

</details>

<details>
<summary>🧪 下游 QA 模型答案 / 评分</summary>

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；八行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `A` | `B` | ✗ 错误 | A |
| 题目 + 原始数值序列 (`numbers`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM 修正逐变量 caption (`opentslm_fixed_caption`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM 修正逐变量 caption + 数值 (`opentslm_fixed_caption_plus`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM 原生多变量 caption (`opentslm_native_caption`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM 原生多变量 caption + 数值 (`opentslm_native_caption_plus`) | `A` | `B` | ✗ 错误 | A |
| 题目 + ChatTS 原生多变量 caption (`chatts_native_caption`) | `A` | `B` | ✗ 错误 | A |
| 题目 + ChatTS 原生多变量 caption + 数值 (`chatts_native_caption_plus`) | `A` | `B` | ✗ 错误 | A |

</details>

<details>
<summary>🔎 Case 分析</summary>

- **答案格局**：`meta_only=A✗, numbers=A✗, opentslm_fixed_caption=A✗, opentslm_fixed_caption_plus=A✗, opentslm_native_caption=A✗, opentslm_native_caption_plus=A✗, chatts_native_caption=A✗, chatts_native_caption_plus=A✗`。
- **这个 case 说明的问题**：失败不只是 caption 生成问题，还可能是公式执行、领域机制或长题干定位失败
- **对训练失败的含义**：如果原生多变量 caption 仍然答错，说明失败不是简单由“逐变量生成导致缺少跨变量上下文”造成；caption 还需要按题目抽取指定日期、窗口统计、变量差值/比值、排序或领域机制。若原生多变量能救回 fixed 逐变量失败，则说明跨变量联合输入确实有价值，但仍需要看这种现象在全量统计中占多少。

</details>

</details>

## 全局分析

1. **这轮重跑首先修正了一个重要实验口径问题。** 旧的 OpenTSLM 逐变量脚本存在 `[1, T]` 输入 shape 问题，导致模型看到的不是长度为 `T` 的单变量序列，而更接近长度为 1、维度为 `T` 的异常输入。这轮 fixed per-variable 结果才是逐变量 OpenTSLM 的合理对照。

2. **原生多变量不是自动答案。** 如果 OpenTSLM native 相比 fixed per-variable 的提升很小或下降，说明失败不只是“逐变量生成没有跨变量上下文”；真正的问题是 caption 是否保留了下游 QA 需要的可计算证据。

3. **ChatTS 的多变量输入应理解为多 token prompt 支持。** 它可以一次输入多个时间序列 token，但这不等价于已经专门训练成 FREDQA 式多变量证据抽取器。因此结果若优于 OpenTSLM，也更可能来自保守、简洁的形态描述，而不是完整领域推理。

4. **对导师讨论最重要的是 hard subset 的救回率，而不是全量准确率。** 过滤掉 meta-only 已答对样本后，只剩 `119` 个真正需要时序证据的题；OpenTSLM native caption-only 只能救回 `19` 题，ChatTS native caption-only 只能救回 `24` 题，任一原生 caption-only 最多救回 `31` 题。这说明原生多变量输入有价值，但覆盖面很有限。

5. **下一步不应只继续换 captioner。** 更直接的改进是 task-aware evidence schema：从题目抽取日期/窗口/变量关系，用工具或训练目标显式生成指定值、差值、比值、均值、排序、反事实中间量，再让 LLM 做解释和选项匹配。

