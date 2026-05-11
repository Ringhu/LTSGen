### Case 14：PIH 语义关系不在局部形态里

- 数据集：`FREDQA`
- Case ID：`fredqa::1033`
- 问题类型：`macro_economic_qa`
- artifact 说明：FREDQA has small n and no complete model-eval table in current artifacts; use for qualitative domain-context cases only.
- 数值摘要：n=626, min=96.613, max=443.51, mean=244.59, std=101.46, slope=0.28037, argmax=311, argmin=11

![fredqa::1033](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/fredqa_1033.png)

**QA 问题**

**题干原文**

```text
You are a time series analysis expert. In the U.S. macroeconomy, there are two quarterly metrics from 1947:Q1 to 2016:Q2: 1) Real gross domestic product (GDP) per capita <ts><ts/>, 2) Real personal consumption (nondurables plus services) <ts><ts/>. Both series are indexed so the consumption series passes through the GDP series. The Permanent Income Hypothesis (PIH) posits that household consumption depends primarily on perceived permanent income (trend GDP), while transitory income changes have little effect on consumption. Based on the association between the two series in the early period (1947:Q1–1984:Q1) versus the late period (1984:Q2–2016:Q2), which causal conclusion about GDP fluctuations is supported?
```

**题干中文翻译**

```text
你是时间序列分析专家。在美国宏观经济中，有两个从 1947:Q1 到 2016:Q2 的季度指标：1) 实际人均国内生产总值（GDP）<ts><ts/>，2) 实际个人消费（非耐用品加服务）<ts><ts/>。两个序列都经过指数化处理，使得消费序列穿过 GDP 序列。永久收入假说（PIH）认为，家庭消费主要取决于感知到的永久收入（趋势 GDP），而暂时性收入变化对消费影响很小。基于早期阶段（1947:Q1–1984:Q1）与晚期阶段（1984:Q2–2016:Q2）中这两个序列之间的关联，关于 GDP 波动支持哪一种因果结论？
```
- 选项：
- A: Early-period GDP fluctuations were driven more by transitory factors, while late-period fluctuations were driven more by permanent factors.
  中文：早期阶段的 GDP 波动更多由暂时性因素驱动，而后期阶段的波动更多由永久性因素驱动。
- B: Early-period GDP fluctuations were driven more by permanent factors, while late-period fluctuations were driven more by transitory factors.
  中文：早期阶段的 GDP 波动更多由永久性因素驱动，而后期阶段的波动更多由暂时性因素驱动。
- C: Both periods’ GDP fluctuations were driven equally by transitory and permanent factors.
  中文：两个时期的 GDP 波动同样由暂时性因素和永久性因素驱动。
- D: Late-period GDP fluctuations were driven by transitory factors unrelated to household perceptions of permanent income.
  中文：后期的 GDP 波动是由与家庭对永久收入的感知无关的暂时性因素驱动的。
- 正确答案：`A`

**标准解释原文**

```text
To solve this, first observe the association between GDP and consumption across periods: the data show GDP deviates more from consumption in the early period (1947:Q1–1984:Q1) but aligns closely with consumption in the late period (1984:Q2–2016:Q2). Per the PIH, consumption reflects permanent income (trend GDP), so deviations of GDP from consumption signal transitory income changes. Early-period deviations mean transitory factors dominated fluctuations, while late-period alignment means permanent factors (trend shifts) drove most GDP movement. This directly supports option A.
```

**标准解释中文翻译**

```text
为了解决这个问题，首先观察各时期 GDP 与消费之间的关联：数据显示，在早期（1947:Q1–1984:Q1），GDP 相对于消费的偏离更大，而在后期（1984:Q2–2016:Q2），GDP 与消费高度一致。根据 PIH，消费反映永久收入（趋势 GDP），因此 GDP 相对于消费的偏离表明暂时性收入变化。早期的偏离意味着暂时性因素主导了波动，而后期的一致性意味着永久性因素（趋势变化）驱动了大部分 GDP 变动。这直接支持选项 A。
```

**生成的 caption 与中文翻译**

**生成 caption 样本 1 原文**

```text
【序列 1：real gross domestic product per capita】变量组包括 real gross domestic product per capita, real gross domestic product per capita+real personl consumption。下文重点描述 real gross domestic product per capita，并分析其与其它变量的联动。 从全局走势看，时间跨度为 1947-01-01–2025-01-01，real gross domestic product per capita 首尾分别为 98.00 和 442.4。 细分来看：1947-01-01–1950-10-01，real gross domestic product per capita 呈稳步上行态势，由 98.00 变至 107.7。 随后，1950-10-01–1965-10-01，涨势未减，继续抬升至 152.0。 之后，1965-10-01–1972-10-01，保持上涨态势，由 152.0 走到 180.3。 紧接着，1972-10-01–1988-04-01，保持上涨态势，由 180.3 走到 249.3。 紧接着，1988-04-01–2025-01-01，保持上涨态势，由 249.3 走到 442.4。 值得注意的极值点有：几个显著高位出现在：2019-10-01≈407.22；2021-10-01≈423.71；2024-10-01≈443.51。 几个显著低位出现在：1947-07-01≈96.66；1949-04-01≈97.29；1951-10-01≈111.67。 从变量联动角度看：real gross domestic product per capita+real personl consumption 和 real gross domestic product per capita 的变化多半同向。
【序列 2：real gross domestic product per capita+real personl consumption】变量组包括 real gross domestic product per capita、real gross domestic product per capita+real personl consumption。下文重点描述 real gross domestic product per capita+real personl consumption，并分析其与其它变量的联动。 总体而言，时间跨度为 1947-01-01–2025-01-01，real gross domestic product per capita+real personl consumption 首尾分别为 100.0 和 437.3。 分阶段来看：1947-01-01–1972-07-01，real gross domestic product per capita+real personl consumption 呈明显上涨态势，由 100.0 变至 179.4。 紧接着，1972-07-01–1983-04-01，延续了上行趋势，从 179.4 进一步升至 218.1。 接着，1983-04-01–2005-01-01，保持上涨态势，由 218.1 走到 344.9。 紧接着，2005-01-01–2025-01-01，保持上涨态势，由 344.9 走到 437.3。 值得注意的极值点有：几个显著高位出现在：2007-01-01≈357.00；2008-04-01≈359.50；2019-10-01≈397.20。 几个显著低位出现在：1947-10-01≈99.40；1949-07-01≈100.30；1950-10-01≈103.50。 关于变量间的相关性：real gross domestic product per capita 和 real gross domestic product per capita+real personl consumption 的变化多半同向。 此外，未观察到明显的周期性规律。 临近 2025-01-01，real gross domestic product per capita+real personl consumption 仍在震荡，最终落在 437.30 左右。
```

**生成 caption 样本 1 中文翻译**

```text
【序列 1：real gross domestic product per capita】变量组包括 real gross domestic product per capita, real gross domestic product per capita+real personl consumption。下文重点描述 real gross domestic product per capita，并分析其与其它变量的联动。 从全局走势看，时间跨度为 1947-01-01–2025-01-01，real gross domestic product per capita 首尾分别为 98.00 和 442.4。 细分来看：1947-01-01–1950-10-01，real gross domestic product per capita 呈稳步上行态势，由 98.00 变至 107.7。 随后，1950-10-01–1965-10-01，涨势未减，继续抬升至 152.0。 之后，1965-10-01–1972-10-01，保持上涨态势，由 152.0 走到 180.3。 紧接着，1972-10-01–1988-04-01，保持上涨态势，由 180.3 走到 249.3。 紧接着，1988-04-01–2025-01-01，保持上涨态势，由 249.3 走到 442.4。 值得注意的极值点有：几个显著高位出现在：2019-10-01≈407.22；2021-10-01≈423.71；2024-10-01≈443.51。 几个显著低位出现在：1947-07-01≈96.66；1949-04-01≈97.29；1951-10-01≈111.67。 从变量联动角度看：real gross domestic product per capita+real personl consumption 和 real gross domestic product per capita 的变化多半同向。
【序列 2：real gross domestic product per capita+real personl consumption】变量组包括 real gross domestic product per capita、real gross domestic product per capita+real personl consumption。下文重点描述 real gross domestic product per capita+real personl consumption，并分析其与其它变量的联动。 总体而言，时间跨度为 1947-01-01–2025-01-01，real gross domestic product per capita+real personl consumption 首尾分别为 100.0 和 437.3。 分阶段来看：1947-01-01–1972-07-01，real gross domestic product per capita+real personl consumption 呈明显上涨态势，由 100.0 变至 179.4。 紧接着，1972-07-01–1983-04-01，延续了上行趋势，从 179.4 进一步升至 218.1。 接着，1983-04-01–2005-01-01，保持上涨态势，由 218.1 走到 344.9。 紧接着，2005-01-01–2025-01-01，保持上涨态势，由 344.9 走到 437.3。 值得注意的极值点有：几个显著高位出现在：2007-01-01≈357.00；2008-04-01≈359.50；2019-10-01≈397.20。 几个显著低位出现在：1947-10-01≈99.40；1949-07-01≈100.30；1950-10-01≈103.50。 关于变量间的相关性：real gross domestic product per capita 和 real gross domestic product per capita+real personl consumption 的变化多半同向。 此外，未观察到明显的周期性规律。 临近 2025-01-01，real gross domestic product per capita+real personl consumption 仍在震荡，最终落在 437.30 左右。
```

**不同输入条件下的答案 / 评分**

| 输入条件 | 预测答案 | 结果 |
| --- | --- | --- |
| 当前 artifact | - | 没有完整模型答案表，仅用于定性领域推理分析 |

**Case 分析**

- 失败标签：PIH 语义关系不在局部形态里
- 关键结论：问题要求利用永久收入假说比较早期/晚期 GDP 与消费的联动。caption 可以描述走势，但是否能推出 transitory/permanent factor 需要宏观经济概念。
