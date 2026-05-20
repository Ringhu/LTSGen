# FREDQA 重跑统计与 Case Study 中文报告

本报告基于当前这一轮 FREDQA 重跑结果生成，正文为中文；原始 QA、OpenTSLM caption、ChatTS caption 和辅助 QA 模型输出保留英文原文，并提供中文翻译用于组会/导师讨论。

## 实验范围与读取方式

- QA 样本数：`604`。
- 变量级 caption 样本数：`1393`；OpenTSLM caption `1393` 条，ChatTS caption `1393` 条。
- GPT QA 预测数：`3624`，对应 `604 × 6` 个条件。
- 下游 QA 辅助模型是 `gpt-5.4`；`meta_only`、`numbers`、`opentslm_caption`、`chatts_caption` 等只是输入证据不同，不是不同 QA 模型。
- 本轮完整重跑覆盖的是 `FREDQA`；之前的多数据集 case study 仍在 `docs/case-studies/20260511-balanced-zh/`，本报告不把其他数据集旧 artifact 混入本轮统计。
- 关键统计模式不是互斥集合，因此模式计数用于定位现象，不能直接相加成总失败数。

## 统计图

![总体准确率](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_overall_accuracy.png)

![过滤 meta-only 答对样本后的准确率](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_meta_wrong_accuracy.png)

![按问题类型准确率](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_by_attribute_accuracy.png)

![按变量数准确率](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_by_nvars_accuracy.png)

![过滤 meta-only 答对样本后按问题类型准确率](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_meta_wrong_by_attribute_accuracy.png)

![过滤 meta-only 答对样本后按变量数准确率](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_meta_wrong_by_nvars_accuracy.png)

## 总体准确率

| 输入条件 | 正确/总数 | Accuracy | 相对 meta_only | 相对 numbers | 统计含义 |
| --- | ---: | ---: | ---: | ---: | --- |
| 只给题目和选项 | 489/604 | 80.96% | +0.00 pp | -1.16 pp | 只考察题干、选项和领域先验，不应被解释为模型读懂时序。 |
| 题目 + 原始数值序列 | 496/604 | 82.12% | +1.16 pp | +0.00 pp | 直接给数值后的上限参照；边际增益小，说明长数值输入并没有被稳定利用。 |
| 题目 + OpenTSLM caption | 487/604 | 80.63% | -0.33 pp | -1.49 pp | OpenTSLM caption 单独作为证据时低于 meta-only，说明摘要会丢失或扭曲关键信息。 |
| 题目 + OpenTSLM caption + 数值 | 497/604 | 82.28% | +1.32 pp | +0.17 pp | 本轮最高，但只比 meta-only 高 1.32 pp，更像轻微辅助而不是可靠证据链。 |
| 题目 + ChatTS caption | 495/604 | 81.95% | +0.99 pp | -0.17 pp | 高于 OpenTSLM caption，说明 ChatTS 的简洁形态摘要在部分题上更可用。 |
| 题目 + ChatTS caption + 数值 | 491/604 | 81.29% | +0.33 pp | -0.83 pp | 低于 ChatTS caption-only，说明加入数值并不保证单调提升。 |

**直接结论**：最高条件是 `opentslm_caption_plus`，准确率 82.28%，但只比 `meta_only` 高 1.32 个百分点。`opentslm_caption` 单独低于 `meta_only`，说明当前 OpenTSLM caption 作为下游 QA 证据并不可靠；`ChatTS caption` 更高，但加入数值后也会下降，说明 evidence fusion 本身不稳定。

## 过滤 meta-only 可答对样本后的准确率

过滤规则：只保留 `meta_only` 答错的样本，即排除 `489` 个题干/选项/领域先验已经能答对的 case，剩余 `115` 个 harder subset。这个统计更接近“模型是否真的从时序证据中获益”。

| 输入条件 | 正确/总数 | Accuracy | 相对 meta_only | 相对 numbers | 统计含义 |
| --- | ---: | ---: | ---: | ---: | --- |
| 只给题目和选项 | 0/115 | 0.00% | +0.00 pp | -23.48 pp | 过滤条件本身，因此为 0；该子集排除了题干和选项先验已能解出的样本。 |
| 题目 + 原始数值序列 | 27/115 | 23.48% | +23.48 pp | +0.00 pp | 直接读原始数值后只救回 27/115，说明长数值输入远不是可靠 oracle。 |
| 题目 + OpenTSLM caption | 16/115 | 13.91% | +13.91 pp | -9.57 pp | 只救回 16/115，低于 ChatTS，也低于 numbers；OpenTSLM caption 单独证据更弱。 |
| 题目 + OpenTSLM caption + 数值 | 25/115 | 21.74% | +21.74 pp | -1.74 pp | 25/115，接近 numbers 但仍低；caption+numbers 只能救回少数样本。 |
| 题目 + ChatTS caption | 24/115 | 20.87% | +20.87 pp | -2.61 pp | 24/115，是 caption-only 条件中最高，但仍只有约 21%。 |
| 题目 + ChatTS caption + 数值 | 22/115 | 19.13% | +19.13 pp | -4.35 pp | 22/115，低于 ChatTS caption-only，继续显示混合输入不单调。 |

**直接结论**：去掉 meta-only 已能答对的 `489` 个样本后，所有非 meta 输入的准确率都大幅下降；`numbers` 只救回 `27/115`，`OpenTSLM caption` 只救回 `16/115`，`ChatTS caption` 只救回 `24/115`。这说明原始 80%+ 总体准确率主要来自语言先验，而不是稳定的时序证据读取。

在 harder subset 中，所有非 meta 条件都答错的样本仍有 `74/115`；至少一种时序/文本证据形式能救回的样本只有 `41/115`。这组数比总体 accuracy 更能说明当前训练为什么失败。

## 过滤 meta-only 后按变量数分类

| 变量数 | meta-only 错样本数 | numbers | OpenTSLM cap | OpenTSLM cap+num | ChatTS cap | ChatTS cap+num | 统计解读 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 23 | 4.35% | 4.35% | 0.00% | 8.70% | 4.35% | 单变量 hard case 几乎全灭，说明难点通常是局部日期/公式/领域机制，而不是变量数量。 |
| 2 | 42 | 30.95% | 23.81% | 28.57% | 30.95% | 26.19% | 二变量是最能被 numbers/ChatTS 救回的一组，但也只有约 31%。 |
| 3 | 32 | 21.88% | 12.50% | 28.12% | 21.88% | 21.88% | OpenTSLM caption-only 明显偏弱，caption+numbers 才接近 numbers。 |
| 4 | 14 | 42.86% | 7.14% | 28.57% | 14.29% | 21.43% | numbers 达到 42.86%，但 caption-only 很低，说明多变量精确计算不应压缩成泛化摘要。 |
| 5 | 4 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 样本数只有 4，所有非 meta 条件均为 0，暂不做强结论。 |

## 过滤 meta-only 后按问题类型分类

| 问题类型 | meta-only 错样本数 | numbers | OpenTSLM cap | OpenTSLM cap+num | ChatTS cap | ChatTS cap+num | 统计解读 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 溯因推理 (`Abductive Reasoning`) | 42 | 16.67% | 4.76% | 14.29% | 9.52% | 14.29% | hard 子集里 caption 救回率很低，说明背景解释题没有被通用形态摘要充分支持。 |
| 因果推理：反事实型 (`Causal Reasoning - Counterfactual`) | 33 | 21.21% | 18.18% | 18.18% | 27.27% | 21.21% | ChatTS caption-only 最高但仍只有 27.27%，反事实计算仍是主要难点。 |
| 类比推理 (`Analogical Reasoning`) | 31 | 12.90% | 3.23% | 9.68% | 6.45% | 9.68% | 几乎全灭，类比题在去掉语言先验后最能暴露证据组织失败。 |
| 归纳推理 (`Inductive Reasoning`) | 31 | 25.81% | 9.68% | 22.58% | 16.13% | 22.58% | numbers 和 caption+numbers 有一定救回，但 caption-only 不足。 |
| 演绎推理 (`Deductive Reasoning`) | 16 | 25.00% | 18.75% | 25.00% | 18.75% | 25.00% | 各条件都只有 18.75%–25%，规则执行和符号推理仍不稳定。 |
| 因果推理：干预型 (`Causal Reasoning - Interventional`) | 15 | 53.33% | 26.67% | 46.67% | 40.00% | 26.67% | numbers 最高 53.33%，说明指定事件前后的数值证据确实关键。 |
| 因果推理：关联型 (`Causal Reasoning - Associational`) | 10 | 20.00% | 20.00% | 30.00% | 30.00% | 20.00% | 样本少，但 caption+numbers 和 ChatTS caption 略高，说明关联型仍有少量可救空间。 |

## 关键错误模式

| 模式 | 数量 | 占 QA 比例 | 背后含义 | 可能结论 |
| --- | ---: | ---: | --- | --- |
| OpenTSLM caption 错、ChatTS caption 对 | 24 | 3.97% | 两个 caption 模型不是同一种失败；ChatTS 在部分局部形态或相对关系上保留了更可用的证据。 | 需要单独分析 caption 生成质量，而不是只看最终 QA accuracy。 |
| OpenTSLM caption 对、ChatTS caption 错 | 16 | 2.65% | OpenTSLM 也有少量优势 case，因此问题不能简化成某一个 caption 模型总是更好。 | 失败不是单向的，训练/评估要保留模型差异。 |
| 两个 caption 都错，但 numbers 对 | 13 | 2.15% | 自然语言摘要丢失了指定日期、指定窗口或公式所需的精确信息；这是真正的 caption bottleneck。 | 当前 caption 训练目标没有对齐 QA 所需的数值抽取。 |
| caption 与 numbers 错，但 meta-only 对 | 1 | 0.17% | 题干/选项先验足够强，加入时序证据反而可能引入干扰；这会抬高不依赖时序理解的表观能力。 | FREDQA 中存在语言先验可绕过时序的样本。 |
| meta、numbers、两个 caption 全错 | 79 | 13.08% | 失败不只是输入形式问题，还包括公式执行、反事实设定、领域制度知识与长题干推理。 | 需要工具计算、公式化中间变量或领域知识增强。 |
| meta-only 错，但 numbers 对 | 27 | 4.47% | 原始数值确实能提供额外证据；这类样本可用于验证模型是否真的读数据。 | 有一小部分问题确实依赖时序证据，适合做正向 case。 |
| meta-only 错，但 ChatTS caption 对 | 24 | 3.97% | ChatTS 有时能把关键形态压缩成可用线索，是 caption 成功的正例。 | ChatTS 可作为较强 caption baseline，但仍不稳定。 |
| meta-only 错，但 OpenTSLM caption 对 | 16 | 2.65% | OpenTSLM 也能在部分样本中提供有用证据，但总体增益不稳定。 | OpenTSLM 的成功 case 数量较少，需要定位其可迁移模式。 |

注：上述模式不是互斥集合，不能把数量直接相加；例如同一个样本可以同时属于 `numbers_rescue_meta_wrong` 和 `opentslm_wrong_chatts_right`。

## 按变量数分类

| 变量数 | 样本数 | meta-only | numbers | OpenTSLM cap | OpenTSLM cap+num | ChatTS cap | ChatTS cap+num | 说明 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 146 | 84.25% | 82.19% | 82.19% | 82.19% | 80.82% | 82.19% | 单变量题 meta-only 最高，说明很多题可由题干和选项先验解决。 |
| 2 | 233 | 81.97% | 84.12% | 82.83% | 84.12% | 85.41% | 82.40% | ChatTS caption 最高，说明二变量相对关系上简洁 caption 有优势。 |
| 3 | 137 | 76.64% | 77.37% | 76.64% | 79.56% | 78.10% | 78.83% | 所有条件下降，三变量关系开始显著增加证据整合难度。 |
| 4 | 70 | 80.00% | 85.71% | 78.57% | 82.86% | 81.43% | 81.43% | numbers 明显高于 caption，说明多变量精确计算不适合压缩成通用 caption。 |
| 5 | 18 | 77.78% | 77.78% | 77.78% | 77.78% | 77.78% | 77.78% | 样本少，所有条件一致，暂不做强结论。 |

## 按问题类型分类

| 问题类型 | 样本数 | meta-only | numbers | OpenTSLM cap | OpenTSLM cap+num | ChatTS cap | ChatTS cap+num | 统计解读 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 溯因推理 (`Abductive Reasoning`) | 274 | 84.67% | 85.40% | 84.31% | 85.04% | 85.77% | 85.40% | 整体较高，很多问题可由背景语义和选项排除完成。 |
| 归纳推理 (`Inductive Reasoning`) | 157 | 80.25% | 81.53% | 79.62% | 82.17% | 80.89% | 82.17% | caption+numbers 略优，归纳型题对形态摘要有一定收益。 |
| 类比推理 (`Analogical Reasoning`) | 152 | 79.61% | 78.29% | 78.95% | 78.29% | 78.29% | 78.95% | numbers/caption 都低于 meta-only，说明类比题容易被额外证据干扰。 |
| 因果推理：干预型 (`Causal Reasoning - Interventional`) | 118 | 87.29% | 92.37% | 88.98% | 91.53% | 87.29% | 88.98% | numbers 提升最大，说明干预型题常依赖指定事件前后的精确数值。 |
| 因果推理：反事实型 (`Causal Reasoning - Counterfactual`) | 103 | 67.96% | 68.93% | 66.02% | 67.96% | 72.82% | 66.02% | 全表最难；ChatTS caption-only 最高但 cap+num 下降，反事实计算与证据融合不稳定。 |
| 因果推理：关联型 (`Causal Reasoning - Associational`) | 84 | 88.10% | 88.10% | 86.90% | 90.48% | 86.90% | 88.10% | OpenTSLM cap+num 最高，关联型问题更容易从趋势/共变信息获益。 |
| 演绎推理 (`Deductive Reasoning`) | 69 | 76.81% | 75.36% | 75.36% | 76.81% | 79.71% | 78.26% | ChatTS caption 略高，但整体仍受规则执行限制。 |

## Case Study

下面每个 case 都包含时序图、原始 QA 与中文翻译、OpenTSLM/ChatTS 生成 caption 与中文翻译、六种输入条件下的 `gpt-5.4` 回答，以及对应分析。本节已去掉 `meta_only` 已经答对的 case，所有展示样本都属于 `meta_only` 答错的 harder subset。

## 📈 Case 01：FREDQA `1079` | OpenTSLM 错、ChatTS 对

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::1079` |
| FREDQA 原始 idx | `1079` |
| 变量数 / 序列长度 | `2` / `[40, 40]` |
| 问题类型 | `Causal Reasoning - Interventional` |
| 正确答案 | `B` |
| 失败/对比模式 | OpenTSLM 错、ChatTS 对 |
| 本 case 关注点 | 家庭资产/负债变化率在通胀冲击前后的比值变化 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | (CXUCHGASSETLB0101M/CPIAUCSL)*100, (U.S. $/Index 1982-1984=100)*100, Annual | 40 | 2300.51 | 5828.28 | 2035.66@11 | 14747.9@37 | 162.972 |
| 2 | (CXUCHGLIABLB0101M/CPIAUCSL)*100, (U.S. $/Index 1982-1984=100)*100, Annual | 40 | 1155.55 | 2299.94 | 1077.14@1 | 11319@19 | 88.4598 |

### 🖼 时序图

![FREDQA 1079](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_1079.png)


### ❓ QA 问题与中文翻译

**题干原文**

> You are a time series analysis expert. In a U.S. household balance sheet system, there are 2 metrics: Inflation-adjusted net change in total household assets (annual, U.S. $/Index 1982–1984=100)*100&lt;ts&gt;&lt;ts/&gt;; Inflation-adjusted net change in total household liabilities (annual, U.S. $/Index 1982–1984=100)*100&lt;ts&gt;&lt;ts/&gt;. The data spans 1984–2023 annually. Unexpected inflation occurred in 2021–2022, and research links such inflation to changes in household balance sheet components. Calculate the ratio of annual asset change to annual liability change for 2020 (a pre-inflation baseline) and 2022, then identify the most plausible causal inference about how unexpected inflation affected the relationship between these two metrics.

**题干中文翻译**

> 你是一名时间序列分析专家。在一个美国居民家庭资产负债表系统中，有 2 个指标：经通胀调整后的家庭总资产年度净变化（年度，美国美元/指数 1982–1984=100）*100&lt;ts&gt;&lt;ts/&gt;；经通胀调整后的家庭总负债年度净变化（年度，美国美元/指数 1982–1984=100）*100&lt;ts&gt;&lt;ts/&gt;。数据按年度覆盖 1984–2023 年。2021–2022 年发生了意外通胀，研究将这种通胀与家庭资产负债表组成部分的变化联系起来。计算 2020 年（通胀前基线）和 2022 年的年度资产变化与年度负债变化之比，然后判断关于意外通胀如何影响这两个指标之间关系的最可能因果推断。

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | The ratio increased from ~1.17 to ~1.20, suggesting unexpected inflation boosted asset growth more than liability growth. | 该比率从约 1.17 增加到约 1.20，表明意外通胀推动资产增长的幅度大于负债增长。 |
| `B` | The ratio decreased from ~1.17 to ~0.90, suggesting unexpected inflation reduced asset growth relative to liability growth. | 该比率从约 1.17 降至约 0.90，表明意外通胀相对于负债增长削弱了资产增长。 |
| `C` | The ratio stayed constant at ~1.0, suggesting unexpected inflation had no differential effect on assets vs. liabilities. | 该比率保持在约 1.0 不变，表明意外通胀对资产与负债之间没有差异化影响。 |
| `D` | The ratio flipped from ~0.85 to ~1.10, suggesting unexpected inflation reversed the relationship between assets and liabilities. | 该比率从约 0.85 翻转至约 1.10，表明意外通胀逆转了资产与负债之间的关系。 |

**正确答案**：`B`

**标准解释原文**

> First, calculate the 2020 ratio: 2020 asset change (9516.88) divided by 2020 liability change (8132.71) equals ~1.17. Next, calculate the 2022 ratio: 2022 asset change (4469.19) divided by 2022 liability change (4963.68) equals ~0.90. The ratio dropped from ~1.17 to ~0.90, meaning asset changes went from being 17% higher than liability changes to 10% lower. This shift supports the causal inference that unexpected inflation reduced asset growth relative to liability growth—consistent with the research that unexpected inflation impacts different balance sheet components (assets vs. liabilities) differently. Option B correctly reflects both the ratio change and the causal logic linking the inflation event to the altered asset-liability relationship.

**标准解释中文翻译**

> 首先，计算 2020 年比率：2020 年资产变化（9516.88）除以 2020 年负债变化（8132.71）等于约 1.17。接着，计算 2022 年比率：2022 年资产变化（4469.19）除以 2022 年负债变化（4963.68）等于约 0.90。该比率从约 1.17 降至约 0.90，意味着资产变化从比负债变化高 17% 变为低 10%。这一变化支持这样的因果推断：意外通胀相对于负债增长削弱了资产增长——这与研究中关于意外通胀会不同地影响家庭资产负债表不同组成部分（资产 vs. 负债）的结论一致。选项 B 正确反映了比率变化以及将通胀事件与资产-负债关系改变联系起来的因果逻辑。


### 📝 生成的 caption 与中文翻译

#### 变量 1：(CXUCHGASSETLB0101M/CPIAUCSL)*100, (U.S. $/Index 1982-1984=100)*100, Annual

**OpenTSLM caption 原文**

> The time series shows a steady upward trend with low volatility and a strong seasonal pattern repeating every 18 years. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a slightly smaller but still positive growth in the second half. A notable peak occurs late in the window, reaching about 1.5 standard deviations above the mean, while a valley is observed early on, about 1.2 standard deviations below the mean. The series is strongly positively correlated with another economic indicator and moderately correlated with a second variable.

**OpenTSLM caption 中文翻译**

> 该时间序列呈现稳定上升趋势，波动较低，并具有每 18 年重复一次的强季节性模式。数据在窗口前半部分开始于适度增长，随后在前半段出现更明显的上升，而在后半段则呈现稍小但仍为正的增长。一个显著峰值出现在窗口后期，约高于均值 1.5 个标准差；同时，一个谷值出现在较早时期，约低于均值 1.2 个标准差。该序列与另一个经济指标呈强正相关，并与第二个变量呈中度相关。

**ChatTS caption 原文**

> The overall trend is mixed, with an initial increase followed by a decrease. The global maximum occurs at point 36 (last third of the 40-point window). Short-term fluctuations are more pronounced in the first half (points 1–20) due to the upward convex pattern observed there.

**ChatTS caption 中文翻译**

> 总体趋势是混合的，先上升后下降。全局最大值出现在第 36 个点（40 点窗口的后三分之一）。短期波动在前半段（第 1–20 点）更为明显，这是由于那里观察到向上的凸形模式。

#### 变量 2：(CXUCHGLIABLB0101M/CPIAUCSL)*100, (U.S. $/Index 1982-1984=100)*100, Annual

**OpenTSLM caption 原文**

> The time series shows a steady upward trend with low volatility, characterized by a strong seasonal pattern repeating every 21 periods. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a slightly smaller but still positive growth in the second half. A notable peak occurs late in the window, reaching about 1.5 standard deviations above the mean. There is no valley identified, and the overall growth over the time span is substantial, with a net increase of over 100%.

**OpenTSLM caption 中文翻译**

> 该时间序列呈现稳定上升趋势，波动较低，特点是每 21 个周期重复一次的强季节性模式。数据在窗口前半部分开始于适度增长，随后在前半段出现更明显的上升，而在后半段则呈现稍小但仍为正的增长。一个显著峰值出现在窗口后期，约高于均值 1.5 个标准差。未识别到谷值，且整个时间跨度内总体增长显著，净增幅超过 100%。

**ChatTS caption 原文**

> The overall trend is increasing. The global maximum occurs at point 23 (middle third of the window). Short-term fluctuations are more pronounced in the first half of the window, where the spike between points 15-17 and the rapid decline at 23-27 are located.

**ChatTS caption 中文翻译**

> 总体趋势是上升的。全局最大值出现在第 23 个点（窗口的中间三分之一）。短期波动在窗口前半段更为明显，其中第 15-17 点之间的尖峰以及第 23-27 点之间的快速下降位于该区域。


### 🧪 下游 QA 模型答案 / 评分

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `A` | `B` | ✗ 错误 | A |
| 题目 + 原始数值序列 (`numbers`) | `B` | `B` | ✓ 正确 | B |
| 题目 + OpenTSLM caption (`opentslm_caption`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM caption + 数值 (`opentslm_caption_plus`) | `B` | `B` | ✓ 正确 | B |
| 题目 + ChatTS caption (`chatts_caption`) | `B` | `B` | ✓ 正确 | B |
| 题目 + ChatTS caption + 数值 (`chatts_caption_plus`) | `A` | `B` | ✗ 错误 | A |


### 🔎 Case 分析

- **答案格局**：`meta_only=A✗, numbers=B✓, opentslm_caption=A✗, opentslm_caption_plus=B✓, chatts_caption=B✓, chatts_caption_plus=A✗`。
- **关键问题**：OpenTSLM 把两条序列都写成稳定上升，弱化了 2022 年资产变化相对负债变化下降这一局部比值证据；ChatTS 至少保留了资产先升后降、负债峰值位置等局部形态，因此 caption-only 能答对。
- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。



## 📈 Case 02：FREDQA `1145` | OpenTSLM 错、ChatTS 对，但 caption+numbers 不稳

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::1145` |
| FREDQA 原始 idx | `1145` |
| 变量数 / 序列长度 | `3` / `[90, 90, 90]` |
| 问题类型 | `Causal Reasoning - Interventional` |
| 正确答案 | `B` |
| 失败/对比模式 | OpenTSLM 错、ChatTS 对，但 caption+numbers 不稳 |
| 本 case 关注点 | 疫情后不同年龄组劳动参与率缺口比较 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | LNS11300036-73.0, %-73.0, Monthly, Seasonally Adjusted  | 90 | -1.1 | -2 | -8.7@27 | 0.3@16 | 0.00524592 |
| 2 | LNS11300060-83.1, %-83.1, Monthly, Seasonally Adjusted  | 90 | -1.4 | 0.4 | -3.3@27 | 0.8@78 | 0.0218241 |
| 3 | LNS11324230-40.2, %-40.2, Monthly, Seasonally Adjusted  | 90 | -0.7 | -2.2 | -2.2@89 | 0.3@18 | -0.023649 |

### 🖼 时序图

![FREDQA 1145](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_1145.png)


### ❓ QA 问题与中文翻译

**题干原文**

> You are a time series analysis expert. In the U.S. labor market, there are 3 metrics:
> Labor force participation rate (LFPR) percentage-point change from January 2020 for 20–24-year-olds (baseline LFPR: 73.0% in Jan 2020)&lt;ts&gt;&lt;ts/&gt;;
> LFPR percentage-point change from January 2020 for 25–54-year-olds (baseline LFPR: 83.1% in Jan 2020)&lt;ts&gt;&lt;ts/&gt;;
> LFPR percentage-point change from January 2020 for 55+-year-olds (baseline LFPR: 40.2% in Jan 2020)&lt;ts&gt;&lt;ts/&gt;.
> Monthly data is available from January 2018 to June 2025. News outlets cited childcare disruptions (affecting younger workers) and early retirements (affecting older workers) as drivers of pandemic-era LFPR declines. As of December 2022, none of the age groups had fully recovered to their January 2020 LFPR levels. Which conclusion about the pandemic’s causal effects on LFPR is most supported by comparing the December 2022 percentage-point gaps relative to January 2020 across the three groups?

**题干中文翻译**

> 你是一名时间序列分析专家。在美国劳动力市场中，有 3 个指标：
> 20–24 岁人群劳动参与率（LFPR）相对于 2020 年 1 月的百分点变化（基线 LFPR：2020 年 1 月为 73.0%）&lt;ts&gt;&lt;ts/&gt;；
> 25–54 岁人群 LFPR 相对于 2020 年 1 月的百分点变化（基线 LFPR：2020 年 1 月为 83.1%）&lt;ts&gt;&lt;ts/&gt;；
> 55 岁及以上人群 LFPR 相对于 2020 年 1 月的百分点变化（基线 LFPR：2020 年 1 月为 40.2%）&lt;ts&gt;&lt;ts/&gt;。
> 月度数据可从 2018 年 1 月获取到 2025 年 6 月。新闻媒体将育儿中断（影响较年轻的工人）和提前退休（影响较年长的工人）归因于疫情时期 LFPR 下降的驱动因素。截至 2022 年 12 月，没有任何年龄组完全恢复到其 2020 年 1 月的 LFPR 水平。通过比较三组相对于 2020 年 1 月在 2022 年 12 月的百分点差距，关于疫情对 LFPR 因果影响的哪一结论最有支持？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Early retirements had a stronger causal impact than childcare disruptions, as the 55+ group’s December 2022 LFPR gap was 0.3 percentage points larger than the 20–24 group’s gap. | 提前退休的因果影响比育儿中断更强，因为 55 岁以上组在 2022 年 12 月的 LFPR 差距比 20–24 岁组大 0.3 个百分点。 |
| `B` | Childcare disruptions had a stronger causal impact than early retirements, as the 20–24 group’s December 2022 LFPR gap was 0.3 percentage points larger than the 55+ group’s gap. | 育儿中断的因果影响比提前退休更强，因为 20–24 岁组在 2022 年 12 月的 LFPR 差距比 55 岁以上组大 0.3 个百分点。 |
| `C` | Neither factor contributed significantly to LFPR declines, as all three groups’ gaps were less than 2 percentage points. | 这两个因素都没有显著导致 LFPR 下降，因为三组的差距都小于 2 个百分点。 |
| `D` | Early retirements primarily affected the 25–54 group, as their December 2022 LFPR gap was the smallest among the three groups. | 提前退休主要影响了 25–54 岁组，因为他们在 2022 年 12 月的 LFPR 差距是三组中最小的。 |

**正确答案**：`B`

**标准解释原文**

> First, we use the data to identify the December 2022 LFPR gaps: the 20–24 group was -1.7 percentage points below January 2020, the 55+ group was -1.4 percentage points below, and the 25–54 group was -0.7 percentage points below. The causal factors link childcare disruptions to younger workers (20–24) and early retirements to older workers (55+). Since the 20–24 group’s gap is 0.3 percentage points larger than the 55+ group’s, this supports the conclusion that childcare disruptions had a stronger causal impact. Option A is incorrect because the 55+ gap is smaller, not larger. Option C is incorrect because gaps of 1.4–1.7 percentage points are meaningful for labor force dynamics. Option D is incorrect because the 25–54 group’s small gap suggests minimal impact from retirement (a factor targeting older workers).

**标准解释中文翻译**

> 首先，我们利用数据识别 2022 年 12 月的 LFPR 差距：20–24 岁组比 2020 年 1 月低 1.7 个百分点，55 岁以上组比 2020 年 1 月低 1.4 个百分点，25–54 岁组比 2020 年 1 月低 0.7 个百分点。因果因素将育儿中断与较年轻工人（20–24 岁）联系起来，将提前退休与较年长工人（55 岁以上）联系起来。由于 20–24 岁组的差距比 55 岁以上组大 0.3 个百分点，这支持了育儿中断具有更强因果影响的结论。选项 A 不正确，因为 55 岁以上组的差距更小，而不是更大。选项 C 不正确，因为 1.4–1.7 个百分点的差距对劳动力动态而言是有意义的。选项 D 不正确，因为 25–54 岁组较小的差距表明退休（针对较年长工人的因素）影响很小。


### 📝 生成的 caption 与中文翻译

#### 变量 1：LNS11300036-73.0, %-73.0, Monthly, Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a flat trend with low volatility and no clear seasonality. It begins with a moderate upward movement in the early part of the window, followed by a significant decline in the first half, and a smaller decline in the second half. A peak occurs in the first half, reaching about 1.5 standard deviations above the mean, while a valley appears late in the window, also about 1.5 standard deviations below the mean. The series has a strong positive correlation with another variable, LNS11300036-73.0, and a moderate positive correlation with another, LNS14600036.

**OpenTSLM caption 中文翻译**

> 该时间序列呈现平稳趋势、低波动性且没有明显季节性。它在窗口的前半部分开始时有一个适度上升，随后在前半部分出现显著下降，在后半部分出现较小的下降。峰值出现在前半部分，约为均值上方 1.5 个标准差，而谷值出现在窗口后期，也约为均值下方 1.5 个标准差。该序列与另一个变量 LNS11300036-73.0 呈强正相关，并且与另一个变量 LNS14600036 呈中等正相关。

**ChatTS caption 原文**

> The overall trend is mixed: it starts with an increasing phase from point 0 to 30, followed by a decreasing phase from point 30 to 90. The global maximum occurs at point 18, which is in the first third of the 90-point window. The first half of the window (points 0–45) exhibits larger short-term fluctuations, including a rapid rise and a subsequent spike, compared to the smoother decline in the second half (points 45–90).

**ChatTS caption 中文翻译**

> （源 artifact 未提供该字段。）

#### 变量 2：LNS11300060-83.1, %-83.1, Monthly, Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a steady upward trend with low volatility and a strong seasonal pattern repeating every 12 months. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a slightly smaller but still positive growth in the second half. A notable peak occurs late in the window, reaching about 1.5 standard deviations above the mean, while a valley is observed early on, about 1.2 standard deviations below the mean. The series is strongly correlated with another economic indicator, suggesting a consistent relationship over time.

**OpenTSLM caption 中文翻译**

> 该时间序列呈现稳定上升趋势、低波动性以及每 12 个月重复一次的强季节性模式。数据在窗口前半部分开始时有适度增长，随后在前半部分出现更明显的上升，在后半部分继续保持略小但仍为正的增长。一个显著峰值出现在窗口后期，约为均值上方 1.5 个标准差，而谷值出现在早期，约为均值下方 1.2 个标准差。该序列与另一个经济指标强相关，表明随时间存在一致关系。

**ChatTS caption 原文**

> The overall trend is mixed: it decreases initially, then increases sharply. The global maximum occurs at point 87 (last third of the window). Short-term fluctuations are larger in the first half (points 1–45) compared to the second half (points 46–90).

**ChatTS caption 中文翻译**

> （源 artifact 未提供该字段。）

#### 变量 3：LNS11324230-40.2, %-40.2, Monthly, Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a flat trend with low volatility and weak seasonality, characterized by a weakly negative correlation with the variable LNS11324230. The data begins with a moderate upward movement in the early part of the window, followed by a significant decline in the first half, and a smaller decline in the second half. A peak occurs in the first half, reaching about 1.8 standard deviations above the mean, while a valley appears late in the window, about 1.2 standard deviations below the mean. The overall net change is a substantial decrease of over 100%.

**OpenTSLM caption 中文翻译**

> 该时间序列呈现平稳趋势、低波动性和弱季节性，并且与变量 LNS11324230 呈弱负相关。数据在窗口前半部分开始时有适度上升，随后在前半部分出现显著下降，在后半部分出现较小的下降。峰值出现在前半部分，约为均值上方 1.8 个标准差，而谷值出现在窗口后期，约为均值下方 1.2 个标准差。总体净变化是超过 100% 的显著下降。

**ChatTS caption 原文**

> The overall trend is decreasing. The global maximum occurs at point 10 (first third of the window). Short-term fluctuations are more pronounced in the first half (amplitude ~0.9) compared to the second half (amplitude ~0.5).

**ChatTS caption 中文翻译**

> （源 artifact 未提供该字段。）


### 🧪 下游 QA 模型答案 / 评分

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `A` | `B` | ✗ 错误 | A |
| 题目 + 原始数值序列 (`numbers`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM caption (`opentslm_caption`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM caption + 数值 (`opentslm_caption_plus`) | `B` | `B` | ✓ 正确 | B |
| 题目 + ChatTS caption (`chatts_caption`) | `B` | `B` | ✓ 正确 | B |
| 题目 + ChatTS caption + 数值 (`chatts_caption_plus`) | `A` | `B` | ✗ 错误 | A |


### 🔎 Case 分析

- **答案格局**：`meta_only=A✗, numbers=A✗, opentslm_caption=A✗, opentslm_caption_plus=B✓, chatts_caption=B✓, chatts_caption_plus=A✗`。
- **关键问题**：题目要求比较 2022 年 12 月相对 2020 年 1 月的缺口。ChatTS 的单独 caption 捕捉了年轻组和年长组不同恢复形态，OpenTSLM 的通用趋势描述不足；但加入数值后 ChatTS+numbers 又答错，说明下游模型融合 caption 与数值时并不单调。
- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。



## 📈 Case 03：FREDQA `997` | meta-only 错，只有 OpenTSLM caption 对

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::997` |
| FREDQA 原始 idx | `997` |
| 变量数 / 序列长度 | `2` / `[137, 137]` |
| 问题类型 | `Causal Reasoning - Associational` |
| 正确答案 | `A` |
| 失败/对比模式 | meta-only 错，只有 OpenTSLM caption 对 |
| 本 case 关注点 | 大银行与小银行信用卡逾期率在 2007 到 2020 年的反转 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | bank 1 100 | 137 | 5.94 | 2.99 | 1.41@121 | 6.71@72 | -0.0239858 |
| 2 | bank out of 100 | 137 | 4.65 | 7.01 | 2.88@99 | 8.16@131 | 0.0110376 |

### 🖼 时序图

![FREDQA 997](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_997.png)


### ❓ QA 问题与中文翻译

**题干原文**

> You are a time series analysis expert. In a credit card market, there are 2 metrics: Credit card delinquency rate for the largest 100 banks (percentage of total balances, where a higher value indicates more customers failing to repay on time)&lt;ts&gt;&lt;ts/&gt;; Credit card delinquency rate for smaller banks (same definition)&lt;ts&gt;&lt;ts/&gt;. The data is quarterly from January 1991 to January 2025. In 2007Q1 (pre-2008 financial crisis), the largest 100 banks had a 4.0% delinquency rate and smaller banks had a 3.46% rate. By 2020Q1 (post-2008 crisis and 2020 recession), the largest 100 banks had a 1.9% rate and smaller banks had a 7.04% rate. Which causal claim is most consistent with the associational pattern between bank size category and delinquency rate changes over this period?

**题干中文翻译**

> 你是一位时间序列分析专家。在信用卡市场中，有 2 个指标：最大 100 家银行的信用卡拖欠率（总余额的百分比，数值越高表示更多客户未能按时还款）&lt;ts&gt;&lt;ts/&gt;；规模较小银行的信用卡拖欠率（定义相同）&lt;ts&gt;&lt;ts/&gt;。数据为季度数据，时间范围从 1991 年 1 月到 2025 年 1 月。2007Q1（2008 年金融危机前），最大 100 家银行的拖欠率为 4.0%，规模较小银行的拖欠率为 3.46%。到 2020Q1（2008 年危机后和 2020 年衰退之后），最大 100 家银行的拖欠率为 1.9%，规模较小银行的拖欠率为 7.04%。在这段时期内，银行规模类别与拖欠率变化之间的关联模式，最符合哪一项因果主张？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Between 2007 and 2020, larger banks increased the minimum credit score required for new cardholders by 20%, while smaller banks decreased theirs by 15%. | 在 2007 年到 2020 年之间，大型银行将新持卡人的最低信用评分要求提高了 20%，而小型银行将其降低了 15%。 |
| `B` | Smaller banks reduced their customer service staffing by 30% between 2007 and 2020, making it harder for borrowers to resolve payment issues. | 规模较小的银行在 2007 年到 2020 年之间将客户服务人员减少了 30%，使借款人更难解决还款问题。 |
| `C` | The Federal Reserve’s 2010 regulation capped credit card late fees at $25 for all banks, reducing delinquency incentives equally across size categories. | 美联储 2010 年的法规将所有银行的信用卡滞纳金上限设为 25 美元，从而对不同规模类别的拖欠激励产生了同等程度的降低。 |
| `D` | Larger banks launched mobile apps for bill payments in 2015, while smaller banks did not adopt digital tools until 2022. | 大型银行在 2015 年推出了用于账单支付的移动应用，而小型银行直到 2022 年才采用数字工具。 |

**正确答案**：`A`

**标准解释原文**

> First, compare the given rates to identify the pattern: in 2007Q1, the largest 100 banks (4.0%) had a higher delinquency rate than smaller banks (3.46%). By 2020Q1, this reversed—largest banks (1.9%) had a much lower rate than smaller banks (7.04%). Option A directly links this reversal to customer selection: larger banks tightening credit approval (higher minimum credit scores) would reduce high-risk borrowers (lowering their delinquency rate), while smaller banks relaxing approval (lower minimum scores) would increase high-risk borrowers (raising their rate). This aligns with the message’s question about whether smaller banks became worse at customer selection. Option B fails to explain why larger banks’ rates dropped. Option C is inconsistent because it claims equal effects across banks, but trends diverged. Option D’s timeline (mobile apps starting in 2015) does not fully explain the 2007–2020 trend or the magnitude of smaller banks’ rate increase.

**标准解释中文翻译**

> 首先，将给定的比率进行比较以识别模式：在 2007Q1，最大 100 家银行（4.0%）的拖欠率高于规模较小银行（3.46%）。到 2020Q1，这一关系反转了——大型银行（1.9%）的比率明显低于小型银行（7.04%）。选项 A 直接将这一反转与客户筛选联系起来：大型银行收紧信贷审批（提高最低信用评分）会减少高风险借款人（从而降低拖欠率），而小型银行放宽审批（降低最低评分）会增加高风险借款人（从而提高拖欠率）。这与题目关于规模较小银行是否在客户筛选方面变差的问题相吻合。选项 B 不能解释为什么大型银行的比率下降。选项 C 不一致，因为它声称对所有银行的影响相同，但趋势却分化了。选项 D 的时间线（2015 年开始使用移动应用）并不能充分解释 2007—2020 年的趋势，也不能解释小型银行比率上升的幅度。


### 📝 生成的 caption 与中文翻译

#### 变量 1：bank 1 100

**OpenTSLM caption 原文**

> The time series shows a steady upward trend with low volatility and a strong seasonal pattern repeating every 12 months. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a slightly smaller but still positive growth in the second half. A notable peak occurs late in the window, reaching about 1.2 standard deviations above the mean, while a deep valley is observed early on, reaching about 1.8 standard deviations below the mean. The series is strongly correlated with two other variables, indicating a consistent relationship over time.

**OpenTSLM caption 中文翻译**

> 该时间序列显示出稳定上升趋势，波动较低，并具有每 12 个月重复一次的强季节性模式。数据在窗口前期开始时略有上升，随后在前半段出现更明显的上升，而在后半段增长略小但仍为正。窗口后期出现一个显著峰值，约为均值以上 1.2 个标准差，而在前期观察到一个深谷，约为均值以下 1.8 个标准差。该序列与另外两个变量具有很强的相关性，表明其随时间保持一致的关系。

**ChatTS caption 原文**

> The overall trend is decreasing. The global maximum occurs around point 73 (middle third of the window). Short-term fluctuations are larger in the first half (amplitude ~2.5) compared to the second half (amplitude ~1.7).

**ChatTS caption 中文翻译**

> 总体趋势是下降的。全局最大值大约出现在第 73 个点附近（窗口的中间三分之一）。前半段的短期波动更大（振幅约为 2.5），而后半段更小（振幅约为 1.7）。

#### 变量 2：bank out of 100

**OpenTSLM caption 原文**

> The time series shows a steady upward trend with low volatility and a strong seasonal pattern repeating every 18 periods. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a significant surge in the second half. A notable peak occurs late in the window, reaching about 1.5 standard deviations above the mean. The series is strongly correlated with two other variables, indicating a positive relationship.

**OpenTSLM caption 中文翻译**

> 该时间序列显示出稳定上升趋势，波动较低，并具有每 18 个周期重复一次的强季节性模式。数据在窗口前期开始时略有上升，随后在前半段出现更明显的上升，而在后半段出现显著跃升。窗口后期出现一个显著峰值，约为均值以上 1.5 个标准差。该序列与另外两个变量具有很强的相关性，表明其存在正向关系。

**ChatTS caption 原文**

> The overall trend is mixed, with an initial decrease followed by an increase. The global maximum occurs at point 136, which is in the last third of the 137-point window. Short-term fluctuations are more pronounced in the first half (amplitude ~1.8) compared to the second half (amplitude ~2.8).

**ChatTS caption 中文翻译**

> 总体趋势是混合的，先下降后上升。全局最大值出现在第 136 个点，位于 137 点窗口的最后三分之一。前半段的短期波动更明显（振幅约为 1.8），而后半段更大（振幅约为 2.8）。


### 🧪 下游 QA 模型答案 / 评分

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `D` | `A` | ✗ 错误 | D |
| 题目 + 原始数值序列 (`numbers`) | `D` | `A` | ✗ 错误 | D |
| 题目 + OpenTSLM caption (`opentslm_caption`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM caption + 数值 (`opentslm_caption_plus`) | `D` | `A` | ✗ 错误 | D |
| 题目 + ChatTS caption (`chatts_caption`) | `D` | `A` | ✗ 错误 | D |
| 题目 + ChatTS caption + 数值 (`chatts_caption_plus`) | `D` | `A` | ✗ 错误 | D |


### 🔎 Case 分析

- **答案格局**：`meta_only=D✗, numbers=D✗, opentslm_caption=A✓, opentslm_caption_plus=D✗, chatts_caption=D✗, chatts_caption_plus=D✗`。
- **关键问题**：这个 case 去掉了 meta-only 已能答对的语言先验样本。题目要求比较两类银行逾期率从 2007Q1 到 2020Q1 的方向反转，并把它映射到客户筛选机制。只有 OpenTSLM caption-only 答对，说明少数情况下 OpenTSLM 的跨变量趋势摘要能提供有效线索；但 numbers 和 caption+numbers 都错，也说明该线索没有稳定转化为可计算证据。
- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。



## 📈 Case 04：FREDQA `1141` | OpenTSLM/数值对、ChatTS 错

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::1141` |
| FREDQA 原始 idx | `1141` |
| 变量数 / 序列长度 | `3` / `[121, 121, 121]` |
| 问题类型 | `Causal Reasoning - Interventional` |
| 正确答案 | `A` |
| 失败/对比模式 | OpenTSLM/数值对、ChatTS 错 |
| 本 case 关注点 | 疫情冲击前后 sticky CPI 与 core CPI 的差距变化 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | Sticky Price Consumer Price Index, Percent Change from Year Ago, Monthly, Seasonally Adjusted  | 121 | 2.0738 | 6.6047 | 1.6055@97 | 6.6608@119 | 0.0201255 |
| 2 | Consumer Price Index for All Urban Consumers: All Items in U.S. City Average, Percent Change from Year Ago, Monthly, Seasonally Adjusted  | 121 | 1.6841 | 6.3403 | -0.2299@24 | 8.9993@113 | 0.0447715 |
| 3 | Consumer Price Index for All Urban Consumers: All Items Less Food and Energy in U.S. City Average, Percent Change from Year Ago, Monthly, Seasonally Adjusted  | 121 | 1.9098 | 5.5391 | 1.1837@89 | 6.6329@116 | 0.0268265 |

### 🖼 时序图

![FREDQA 1141](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_1141.png)


### ❓ QA 问题与中文翻译

**题干原文**

> You are a time series analysis expert. In a U.S. consumer price tracking system, there are 3 metrics: Sticky Price Consumer Price Index (Percent Change from Year Ago, Monthly, Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;; Consumer Price Index for All Urban Consumers: All Items (Percent Change from Year Ago, Monthly, Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;; Consumer Price Index for All Urban Consumers: All Items Less Food and Energy (Percent Change from Year Ago, Monthly, Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;. The data covers January 2013 to January 2023. The COVID-19-induced recession in 2020 is hypothesized to have altered the alignment between the sticky price CPI (a measure of slow-to-change prices) and the all items less food and energy CPI (a measure excluding volatile food/energy). To evaluate this, you calculate the absolute percentage point difference between these two metrics in January 2019 (pre-recession) and January 2021 (post-recession). Based on the data, which conclusion about the recession’s causal impact is most supported?

**题干中文翻译**

> 你是一名时间序列分析专家。在一个美国消费者价格跟踪系统中，有 3 个指标：Sticky Price Consumer Price Index (Percent Change from Year Ago, Monthly, Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;；Consumer Price Index for All Urban Consumers: All Items (Percent Change from Year Ago, Monthly, Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;；Consumer Price Index for All Urban Consumers: All Items Less Food and Energy (Percent Change from Year Ago, Monthly, Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;。数据覆盖 2013 年 1 月到 2023 年 1 月。假设 2020 年 COVID-19 引发的衰退改变了 sticky price CPI（衡量价格变化缓慢的指标）与 all items less food and energy CPI（剔除波动较大的食品/能源）之间的一致性。为评估这一点，你计算 2019 年 1 月（衰退前）和 2021 年 1 月（衰退后）这两个指标之间的绝对百分点差异。根据数据，关于这次衰退的因果影响，哪一项结论最得到支持？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | The recession reduced alignment between the two metrics, as the absolute difference increased by approximately 0.17 percentage points. | 这次衰退降低了两个指标之间的一致性，因为绝对差异增加了约 0.17 个百分点。 |
| `B` | The recession increased alignment between the two metrics, as the absolute difference decreased by approximately 0.17 percentage points. | 这次衰退提高了两个指标之间的一致性，因为绝对差异减少了约 0.17 个百分点。 |
| `C` | The recession had no meaningful impact, as the absolute difference changed by less than 0.10 percentage points. | 这次衰退没有明显影响，因为绝对差异变化小于 0.10 个百分点。 |
| `D` | The recession reversed their order, but alignment remained unchanged because the difference stayed within 0.20 percentage points. | 这次衰退使它们的顺序发生了逆转，但一致性保持不变，因为差异仍在 0.20 个百分点以内。 |

**正确答案**：`A`

**标准解释原文**

> First, calculate the absolute differences between the sticky price CPI (timeseries1) and all items less food and energy CPI (timeseries3) for the specified periods: 
> - January 2019 (pre-recession): |2.7782 (sticky) - 2.33 (all items less food/energy)| = 0.4482 percentage points. 
> - January 2021 (post-recession): |2.3458 (sticky) - 2.9652 (all items less food/energy)| = 0.6194 percentage points. 
> The difference increased by ~0.17 percentage points, indicating reduced alignment. Since the COVID-19 recession was the only major intervening supply/demand shock between these periods, the data supports the causal inference that the recession reduced alignment between the two core inflation metrics. Option A correctly reflects this.

**标准解释中文翻译**

> 首先，计算指定时期 sticky price CPI (timeseries1) 与 all items less food and energy CPI (timeseries3) 之间的绝对差异：
> - 2019 年 1 月（衰退前）：|2.7782 (sticky) - 2.33 (all items less food/energy)| = 0.4482 个百分点。
> - 2021 年 1 月（衰退后）：|2.3458 (sticky) - 2.9652 (all items less food/energy)| = 0.6194 个百分点。
> 差异增加了约 0.17 个百分点，表明一致性降低。由于 COVID-19 衰退是这两个时期之间唯一主要的供需冲击，因此数据支持这样的因果推断：这次衰退降低了这两个核心通胀指标之间的一致性。选项 A 正确反映了这一点。


### 📝 生成的 caption 与中文翻译

#### 变量 1：Sticky Price Consumer Price Index, Percent Change from Year Ago, Monthly, Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a flat trend with low volatility and no strong seasonality. It begins with a significant decline in the early part of the window, followed by a moderate increase in the first half, and a smaller decline in the second half. A notable peak occurs in the second half, reaching about 1.5 standard deviations above the mean, while a deep valley is observed early in the window, about 1.8 standard deviations below the mean. The series exhibits a moderate positive correlation with another economic indicator.

**OpenTSLM caption 中文翻译**

> 该时间序列呈现平稳趋势，波动较低且没有明显季节性。它在窗口前半部分开始时出现显著下降，随后在前半段适度上升，并在后半段略有下降。一个显著峰值出现在后半段，约高于均值 1.5 个标准差，而一个深谷出现在窗口早期，约低于均值 1.8 个标准差。该序列与另一项经济指标呈中等正相关。

**ChatTS caption 原文**

> The overall trend is increasing. The global maximum (6.66) occurs at the end of the last third of the window. Short-term fluctuations are larger in the first half (amplitude ~0.9) compared to the second half (amplitude ~0.2).

**ChatTS caption 中文翻译**

> 总体趋势是上升的。全局最大值（6.66）出现在窗口最后三分之一的末端。第一半段的短期波动更大（幅度约 0.9），而第二半段更小（幅度约 0.2）。

#### 变量 2：Consumer Price Index for All Urban Consumers: All Items in U.S. City Average, Percent Change from Year Ago, Monthly, Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a steady upward trend with low volatility, characterized by a strong seasonal pattern repeating every 18 months. The early part of the window experiences a moderate increase, followed by a more pronounced rise in the first half, and a slightly smaller but still positive growth in the second half. The overall growth is substantial, indicating a consistent upward movement throughout the period.

**OpenTSLM caption 中文翻译**

> 该时间序列呈现稳定的上升趋势，波动较低，且具有每 18 个月重复一次的强季节性模式。窗口早期经历了适度上升，随后在前半段出现更明显的上升，并在后半段继续以略小但仍为正的幅度增长。整体增长幅度较大，表明在整个时期内持续向上运动。

**ChatTS caption 原文**

> The overall trend is mixed, with initial increases followed by decreases and later rises. The global maximum occurs at point 101 (last third of the 121-point window). Short-term fluctuations are larger in the first half (amplitude ~1.7) compared to the second half (amplitude ~0.7).

**ChatTS caption 中文翻译**

> 总体趋势是混合的，先上升后下降，随后再次上升。全局最大值出现在第 101 个点（121 点窗口的最后三分之一）。第一半段的短期波动更大（幅度约 1.7），而第二半段较小（幅度约 0.7）。

#### 变量 3：Consumer Price Index for All Urban Consumers: All Items Less Food and Energy in U.S. City Average, Percent Change from Year Ago, Monthly, Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a flat trend with low volatility and no strong seasonality. It begins with a significant decline in the early part of the window, followed by a moderate increase in the first half, and a smaller decline in the second half. A notable peak occurs in the second half, reaching about 1.5 standard deviations above the mean, while a deep valley is observed early in the window, about 2.0 standard deviations below the mean. The series exhibits a moderate negative correlation with the consumer price index for food and energy.

**OpenTSLM caption 中文翻译**

> 该时间序列呈现平稳趋势，波动较低且没有明显季节性。它在窗口前半部分开始时出现显著下降，随后在前半段适度上升，并在后半段略有下降。一个显著峰值出现在后半段，约高于均值 1.5 个标准差，而一个深谷出现在窗口早期，约低于均值 2.0 个标准差。该序列与食品和能源消费者价格指数呈中等负相关。

**ChatTS caption 原文**

> The overall trend is increasing. The global maximum (6.63) occurs at point 101, which is in the last third of the 121-point window. Short-term fluctuations are larger in the first half (amplitude ~0.6) compared to the second half (amplitude ~0.2).

**ChatTS caption 中文翻译**

> 总体趋势是上升的。全局最大值（6.63）出现在第 101 个点，位于 121 点窗口的最后三分之一。第一半段的短期波动更大（幅度约 0.6），而第二半段更小（幅度约 0.2）。


### 🧪 下游 QA 模型答案 / 评分

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `C` | `A` | ✗ 错误 | C |
| 题目 + 原始数值序列 (`numbers`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM caption (`opentslm_caption`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM caption + 数值 (`opentslm_caption_plus`) | `A` | `A` | ✓ 正确 | A |
| 题目 + ChatTS caption (`chatts_caption`) | `B` | `A` | ✗ 错误 | B |
| 题目 + ChatTS caption + 数值 (`chatts_caption_plus`) | `B` | `A` | ✗ 错误 | B |


### 🔎 Case 分析

- **答案格局**：`meta_only=C✗, numbers=A✓, opentslm_caption=A✓, opentslm_caption_plus=A✓, chatts_caption=B✗, chatts_caption_plus=B✗`。
- **关键问题**：正确答案依赖两个指定月份的绝对差。OpenTSLM+numbers 都能支持这个差值计算，ChatTS 把三个价格指标主要概括成 increasing/mixed，不能稳定表达指定月份之间的对齐程度。
- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。



## 📈 Case 05：FREDQA `1028` | 两个 caption 都错，numbers 对

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::1028` |
| FREDQA 原始 idx | `1028` |
| 变量数 / 序列长度 | `4` / `[641, 641, 641, 641]` |
| 问题类型 | `Causal Reasoning - Interventional` |
| 正确答案 | `A` |
| 失败/对比模式 | 两个 caption 都错，numbers 对 |
| 本 case 关注点 | 报纸与烟草工业贡献的两条因果 claim 同时验证 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | cheese | 641 | 0.1065 | 0.4136 | 0.1065@0 | 0.5912@580 | 0.00044206 |
| 2 | tobacco | 641 | 0.6576 | 0.996 | 0.5522@78 | 2.1119@353 | 0.000726568 |
| 3 | fruit | 641 | 1.0856 | 1.0238 | 0.7936@439 | 1.3167@362 | 3.36753e-06 |
| 4 | newspaper | 641 | 1.5056 | 0.3173 | 0.3173@640 | 1.7483@173 | -0.00175494 |

### 🖼 时序图

![FREDQA 1028](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_1028.png)


### ❓ QA 问题与中文翻译

**题干原文**

> You are a time series analysis expert. In a U.S. industrial production system, there are 4 metrics: Cheese (relative contribution to overall industrial growth, index value)&lt;ts&gt;&lt;ts/&gt;; Tobacco (relative contribution to overall industrial growth, index value)&lt;ts&gt;&lt;ts/&gt;; Fruit (relative contribution to overall industrial growth, index value)&lt;ts&gt;&lt;ts/&gt;; Newspaper (relative contribution to overall industrial growth, index value)&lt;ts&gt;&lt;ts/&gt;. The data are monthly from January 1972 to May 2025. Analysts argue two causal links: (1) the 1995 commercialization of the internet led Newspaper’s contribution to drop by at least 20% over the next 10 years, and (2) 1990s regulatory shifts increased Tobacco’s contribution by more than 15% from 1990 to 2000. Using the January values for each year, calculate the percentage changes for both metrics and determine which causal claim(s) the data supports.

**题干中文翻译**

> 你是一名时间序列分析专家。在一个美国工业生产系统中，有4个指标：Cheese（对整体工业增长的相对贡献，指数值）&lt;ts&gt;&lt;ts/&gt;；Tobacco（对整体工业增长的相对贡献，指数值）&lt;ts&gt;&lt;ts/&gt;；Fruit（对整体工业增长的相对贡献，指数值）&lt;ts&gt;&lt;ts/&gt;；Newspaper（对整体工业增长的相对贡献，指数值）&lt;ts&gt;&lt;ts/&gt;。数据为月度数据，时间范围从1972年1月到2025年5月。分析师认为存在两个因果关系：(1) 1995年互联网商业化导致Newspaper在接下来的10年里贡献至少下降20%，以及(2) 1990年代的监管变化使Tobacco从1990年到2000年的贡献增加了超过15%。使用每年1月的数值，计算这两个指标的百分比变化，并判断数据支持哪一个或哪些因果主张。

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Both claims are supported: Newspaper declined by ≥20% and Tobacco grew by &gt;15%. | 两个主张都得到支持：Newspaper下降了≥20%，且Tobacco增长了&gt;15%。 |
| `B` | Only the first claim is supported: Newspaper declined by ≥20%, but Tobacco grew by ≤15%. | 只有第一个主张得到支持：Newspaper下降了≥20%，但Tobacco增长了≤15%。 |
| `C` | Only the second claim is supported: Tobacco grew by &gt;15%, but Newspaper declined by &lt;20%. | 只有第二个主张得到支持：Tobacco增长了&gt;15%，但Newspaper下降了&lt;20%。 |
| `D` | Neither claim is supported: Newspaper declined by &lt;20% and Tobacco grew by ≤15%. | 两个主张都未得到支持：Newspaper下降了&lt;20%，且Tobacco增长了≤15%。 |

**正确答案**：`A`

**标准解释原文**

> To evaluate the claims, calculate percentage changes using the formula: (Final Value - Initial Value) / Initial Value * 100. For Newspaper, the January 1995 value is ~1.6, and the January 2005 value is ~1.2—this equals a 25% decline (≥20%), supporting the first claim about the internet’s impact. For Tobacco, the January 1990 value is ~1.0, and the January 2000 value is ~1.2—this equals a 20% growth (&gt;15%), supporting the second claim about regulatory changes. The data aligns with both causal arguments: the internet reduced demand for printed newspapers (lowering their industrial contribution), while regulatory shifts likely expanded tobacco production or market access (increasing its contribution).

**标准解释中文翻译**

> 为了评估这些主张，使用公式计算百分比变化：(最终值 - 初始值) / 初始值 * 100。对于Newspaper，1995年1月的数值约为1.6，而2005年1月的数值约为1.2——这相当于下降了25%（≥20%），支持关于互联网影响的第一个主张。对于Tobacco，1990年1月的数值约为1.0，而2000年1月的数值约为1.2——这相当于增长了20%（&gt;15%），支持关于监管变化的第二个主张。数据与两个因果论点都一致：互联网减少了对印刷报纸的需求（降低了其工业贡献），而监管变化可能扩大了烟草生产或市场准入（增加了其贡献）。


### 📝 生成的 caption 与中文翻译

#### 变量 1：cheese

**OpenTSLM caption 原文**

> The time series shows a steady upward trend with low volatility and a strong seasonal pattern repeating every 18 periods. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a slightly smaller but still positive growth in the second half. A notable peak occurs late in the window, reaching about 1.2 standard deviations above the mean. The series is strongly correlated with two other variables, both showing strong positive relationships.

**OpenTSLM caption 中文翻译**

> 时间序列表现出稳定的上升趋势，波动性较低，并且有一个强烈的季节性模式，每18个周期重复一次。数据在窗口前期开始时出现适度增长，随后在前半段更明显上升，后半段则增长略小但仍为正。一个显著峰值出现在窗口后期，达到均值以上约1.2个标准差。该序列与另外两个变量强相关，两者都表现出强正相关关系。

**ChatTS caption 原文**

> The overall trend is increasing. The global maximum, 0.59, occurs at point 633, which is in the last third of the 641-point window. Short-term fluctuations are larger in the first half (amplitude ~0.05) compared to the second half (amplitude ~0.02).

**ChatTS caption 中文翻译**

> 总体趋势为上升。全局最大值0.59出现在点633，位于641点窗口的最后三分之一。短期波动在前半段更大（幅度约0.05），而后半段更小（幅度约0.02）。

#### 变量 2：tobacco

**OpenTSLM caption 原文**

> The time series shows a strong seasonal pattern with a period of 4 quarters, and a high level of volatility. The data starts with a significant upward trend in the early part of the window, followed by a moderate increase in the first half, and then a sharp decline in the second half. There is a notable peak in the second half, which is about 2.1 standard deviations above the mean, and a valley early in the window, about 1.5 standard deviations below the mean. The overall net change is a decrease of approximately 12.7%.

**OpenTSLM caption 中文翻译**

> 时间序列表现出强烈的季节性模式，周期为4个季度，且波动性较高。数据在窗口前期开始时出现明显上升趋势，随后在前半段适度增加，然后在后半段急剧下降。第二半段存在一个显著峰值，约为均值以上2.1个标准差，窗口前期存在一个谷值，约为均值以下1.5个标准差。整体净变化约为下降12.7%。

**ChatTS caption 原文**

> The overall trend is increasing. The global maximum, 2.11, occurs at point 319, which is in the middle third of the 641-point window. Short-term fluctuations are larger in the first half (amplitude ~0.3) compared to the second half (amplitude ~0.2).

**ChatTS caption 中文翻译**

> 总体趋势为上升。全局最大值2.11出现在点319，位于641点窗口的中间三分之一。短期波动在前半段更大（幅度约0.3），而后半段更小（幅度约0.2）。

#### 变量 3：fruit

**OpenTSLM caption 原文**

> The time series shows a flat trend with low volatility and medium strength seasonality every 12 time units. There is a noticeable upward phase early in the window followed by a more pronounced upward movement in the first half, which is followed by a significant downward shift in the second half. A peak occurs in the second half with a magnitude of about 1.5 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 1.8 standard deviations from the mean. The series has a weak negative correlation with the variable "milk."

**OpenTSLM caption 中文翻译**

> 时间序列表现出平稳趋势，波动性较低，并且每12个时间单位有中等强度的季节性。窗口前期存在明显的上升阶段，随后在前半段出现更明显的上升运动，之后在后半段出现显著下降。第二半段出现一个峰值，其幅度约为距均值1.5个标准差，而窗口前期观察到一个谷值，其幅度约为1.8个标准差。该序列与变量"milk."存在弱负相关。

**ChatTS caption 原文**

> The overall trend is steady. The global maximum occurs at point 330, which is in the middle third of the window (points 214-423). Short-term fluctuations are larger in the first half of the window, particularly around points 60-130 and 250-330.

**ChatTS caption 中文翻译**

> 总体趋势稳定。全局最大值出现在点330，位于窗口中间三分之一（点214-423）。短期波动在窗口前半段更大，特别是在点60-130和250-330附近。

#### 变量 4：newspaper

**OpenTSLM caption 原文**

> The time series shows a consistent downward trend with low volatility and a medium-strength seasonal pattern repeating every 10 periods. The values decrease significantly in the early part of the window, with a notable drop early on that is about 2.1 standard deviations below the mean. The decline continues throughout the series, with a less severe drop in the second half, but the overall trend remains negative.

**OpenTSLM caption 中文翻译**

> 时间序列表现出持续下降趋势，波动性较低，并且有一个中等强度的季节性模式，每10个周期重复一次。数值在窗口前期显著下降，早期出现一个显著下跌，约为均值以下2.1个标准差。下降贯穿整个序列，后半段下跌程度较轻，但整体趋势仍为负。

**ChatTS caption 原文**

> The overall trend is mixed, with multiple segments: stable (0–211), increasing (211–427), and decreasing (427–640). The global maximum occurs at point 211, which is in the middle third of the window (positions 213–427). Short-term fluctuations are larger in the first half (amplitude ~0.2) compared to the second half (amplitude ~0.0).

**ChatTS caption 中文翻译**

> 总体趋势混合，包含多个区段：稳定（0–211）、上升（211–427）和下降（427–640）。全局最大值出现在点211，位于窗口中间三分之一（位置213–427）。短期波动在前半段更大（幅度约0.2），而后半段更小（幅度约0.0）。


### 🧪 下游 QA 模型答案 / 评分

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `D` | `A` | ✗ 错误 | D |
| 题目 + 原始数值序列 (`numbers`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM caption (`opentslm_caption`) | `B` | `A` | ✗ 错误 | B |
| 题目 + OpenTSLM caption + 数值 (`opentslm_caption_plus`) | `B` | `A` | ✗ 错误 | B |
| 题目 + ChatTS caption (`chatts_caption`) | `D` | `A` | ✗ 错误 | D |
| 题目 + ChatTS caption + 数值 (`chatts_caption_plus`) | `B` | `A` | ✗ 错误 | B |


### 🔎 Case 分析

- **答案格局**：`meta_only=D✗, numbers=A✓, opentslm_caption=B✗, opentslm_caption_plus=B✗, chatts_caption=D✗, chatts_caption_plus=B✗`。
- **关键问题**：题目要求按指定年份计算百分比变化。两个 caption 都给出大量趋势、季节性、峰谷摘要，但没有可靠保留 1995/2005 与 1990/2000 的精确变化，因此 caption-only 错；直接数值能答对。
- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。



## 📈 Case 06：FREDQA `1087` | 两个 caption 都错，numbers 对

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::1087` |
| FREDQA 原始 idx | `1087` |
| 变量数 / 序列长度 | `3` / `[22, 22, 22]` |
| 问题类型 | `Causal Reasoning - Associational` |
| 正确答案 | `A` |
| 失败/对比模式 | 两个 caption 都错，numbers 对 |
| 本 case 关注点 | GDP price index、gross domestic purchases、PCE price index 的平均通胀排序 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | Gross domestic purchases (chain-type price index), Percent Change from Year Ago, Quarterly, Seasonally Adjusted | 22 | 1.3192 | 2.4044 | 0.7462@3 | 7.3799@11 | 0.0765262 |
| 2 | Personal Consumption Expenditures: Chain-type Price Index, Percent Change from Year Ago, Quarterly, Seasonally Adjusted | 22 | 1.3894 | 2.4682 | 0.5431@3 | 6.9182@11 | 0.0953232 |
| 3 | Gross Domestic Product: Chain-type Price Index, Percent Change from Year Ago, Quarterly, Seasonally Adjusted | 22 | 1.5694 | 2.4528 | 0.7664@3 | 7.7619@11 | 0.0742591 |

### 🖼 时序图

![FREDQA 1087](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_1087.png)


### ❓ QA 问题与中文翻译

**题干原文**

> You are a time series analysis expert. In a U.S. economic reporting system, there are 3 metrics: Gross domestic purchases &lt;ts&gt;&lt;ts/&gt; (chain-type price index), Percent Change from Year Ago, Quarterly, Seasonally Adjusted (measures prices for domestically produced and imported goods/services bought by consumers, businesses, and governments); Personal Consumption Expenditures &lt;ts&gt;&lt;ts/&gt;: Chain-type Price Index, Percent Change from Year Ago, Quarterly, Seasonally Adjusted (measures prices for domestic and imported goods/services bought by consumers); Gross Domestic Product &lt;ts&gt;&lt;ts/&gt;: Chain-type Price Index, Percent Change from Year Ago, Quarterly, Seasonally Adjusted (measures prices for domestically produced goods/services bought by consumers, businesses, governments, and the rest of the world). Data is collected quarterly from July 2019 to October 2024. Suppose you calculate the average year-over-year inflation rate for each metric from April 2021 (Q2 2021) to April 2022 (Q2 2022). Based on the metrics’ scopes, which of the following rank-orderings (from highest to lowest average inflation) and causal explanations is most consistent with the data?

**题干中文翻译**

> 你是一位时间序列分析专家。在一个美国经济报告系统中，有 3 个指标：Gross domestic purchases &lt;ts&gt;&lt;ts/&gt;（链式价格指数），同比百分比变化，季度，季节调整后（衡量消费者、企业和政府购买的国内生产和进口商品/服务的价格）；Personal Consumption Expenditures &lt;ts&gt;&lt;ts/&gt;：Chain-type Price Index，同比百分比变化，季度，季节调整后（衡量消费者购买的国内和进口商品/服务的价格）；Gross Domestic Product &lt;ts&gt;&lt;ts/&gt;：Chain-type Price Index，同比百分比变化，季度，季节调整后（衡量消费者、企业、政府和世界其他地区购买的国内生产商品/服务的价格）。数据按季度收集，时间范围从 2019 年 7 月到 2024 年 10 月。假设你计算了从 2021 年 4 月（2021 年第 2 季度）到 2022 年 4 月（2022 年第 2 季度）每个指标的平均同比通胀率。根据这些指标的覆盖范围，以下哪种排序（从高到低的平均通胀）及因果解释最符合数据？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Gross Domestic Product Price Index &gt; Gross domestic purchases index &gt; Personal Consumption Expenditures Price Index; domestic production for global markets had higher inflation than imported goods for consumers. | Gross Domestic Product Price Index &gt; Gross domestic purchases index &gt; Personal Consumption Expenditures Price Index; 面向全球市场的国内生产比面向消费者的进口商品具有更高的通胀。 |
| `B` | Personal Consumption Expenditures Price Index &gt; Gross domestic purchases index &gt; Gross Domestic Product Price Index; imported consumer goods had higher inflation than domestic production for businesses. | Personal Consumption Expenditures Price Index &gt; Gross domestic purchases index &gt; Gross Domestic Product Price Index; 消费者进口商品的通胀高于企业的国内生产。 |
| `C` | Gross domestic purchases index &gt; Gross Domestic Product Price Index &gt; Personal Consumption Expenditures Price Index; business/government imports had higher inflation than domestic production for exports. | Gross domestic purchases index &gt; Gross Domestic Product Price Index &gt; Personal Consumption Expenditures Price Index; 企业/政府进口的通胀高于用于出口的国内生产。 |
| `D` | Gross Domestic Product Price Index &gt; Personal Consumption Expenditures Price Index &gt; Gross domestic purchases index; domestic production for governments had higher inflation than imported goods for businesses. | Gross Domestic Product Price Index &gt; Personal Consumption Expenditures Price Index &gt; Gross domestic purchases index; 面向政府的国内生产比面向企业的进口商品具有更高的通胀。 |

**正确答案**：`A`

**标准解释原文**

> First, calculate the average year-over-year inflation for each metric from Q2 2021 (April 2021, index 7) to Q2 2022 (April 2022, index 11):
> - Gross Domestic Product Price Index (timeseries3): (4.4214 + 5.0742 + 6.1556 + 6.9813 + 7.7619) / 5 ≈ 6.08%
> - Gross domestic purchases index (timeseries1): (4.0472 + 4.6596 + 5.8135 + 6.7134 + 7.3799) / 5 ≈ 5.72%
> - Personal Consumption Expenditures Price Index (timeseries2): (4.0389 + 4.6249 + 5.8385 + 6.6236 + 6.9182) / 5 ≈ 5.61%
> The rank-ordering is Gross Domestic Product Price Index &gt; Gross domestic purchases index &gt; Personal Consumption Expenditures Price Index. This aligns with the metrics’ scopes: the Gross Domestic Product Price Index includes domestically produced goods sold to global markets (not in the other indexes), which likely had higher inflation than imported consumer goods (included in PCEPI but not GDPPI). The Gross domestic purchases index, which adds business/government imports to PCEPI’s consumer focus, falls in the middle—consistent with moderate inflation in business/government imports relative to domestic production for global markets.

**标准解释中文翻译**

> 首先，计算从 2021 年第 2 季度（2021 年 4 月，index 7）到 2022 年第 2 季度（2022 年 4 月，index 11）每个指标的平均同比通胀：
> - Gross Domestic Product Price Index (timeseries3): (4.4214 + 5.0742 + 6.1556 + 6.9813 + 7.7619) / 5 ≈ 6.08%
> - Gross domestic purchases index (timeseries1): (4.0472 + 4.6596 + 5.8135 + 6.7134 + 7.3799) / 5 ≈ 5.72%
> - Personal Consumption Expenditures Price Index (timeseries2): (4.0389 + 4.6249 + 5.8385 + 6.6236 + 6.9182) / 5 ≈ 5.61%
> 排序为 Gross Domestic Product Price Index &gt; Gross domestic purchases index &gt; Personal Consumption Expenditures Price Index。这与这些指标的覆盖范围一致：Gross Domestic Product Price Index 包括面向全球市场的国内生产商品（不在其他指数中），其通胀可能高于消费者进口商品（包含在 PCEPI 中但不在 GDPPI 中）。Gross domestic purchases index 将企业/政府进口加入 PCEPI 的消费者范围，因此位居中间——这与企业/政府进口相对于面向全球市场的国内生产的中等通胀相一致。


### 📝 生成的 caption 与中文翻译

#### 变量 1：Gross domestic purchases (chain-type price index), Percent Change from Year Ago, Quarterly, Seasonally Adjusted

**OpenTSLM caption 原文**

> The time series shows a gradual upward trend with low volatility and a medium-strength seasonal pattern repeating every 18 periods. Early in the window, there is a notable decline, followed by a strong upward movement in the first half, and a moderate increase in the second half. A peak occurs late in the window, reaching about 1.5 standard deviations above the mean, while a valley is observed early, about 1.2 standard deviations below the mean. The overall net change is a significant increase of over 100%.

**OpenTSLM caption 中文翻译**

> 该时间序列显示出平缓上升趋势，波动较低，并带有中等强度的季节性模式，每 18 个周期重复一次。在窗口前期，有明显下降，随后在前半段出现强劲上升，后半段则为适度增长。窗口后期出现一个峰值，约比均值高 1.5 个标准差；而在早期观察到一个谷值，约比均值低 1.2 个标准差。整体净变化为显著增加，超过 100%。

**ChatTS caption 原文**

> The overall trend is flat, with no significant direction. The global maximum occurs at point 9, which falls in the first third of the 22-point window (positions 1-7.33 to 14.66). Short-term fluctuations are more pronounced in the first half (points 1-11) due to the rapid rise and decline observed there. The second half shows a slower decline and stabilization.

**ChatTS caption 中文翻译**

> 整体趋势平稳，没有明显方向。全局最大值出现在第 9 个点，位于 22 点窗口的前三分之一（位置 1-7.33 到 14.66）。短期波动在前半段（点 1-11）更为明显，因为那里观察到快速上升和下降。后半段则表现为较慢的下降和稳定。

#### 变量 2：Personal Consumption Expenditures: Chain-type Price Index, Percent Change from Year Ago, Quarterly, Seasonally Adjusted

**OpenTSLM caption 原文**

> The time series shows a gradual upward trend with low volatility, featuring a moderate seasonal pattern repeating every four quarters. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a slightly smaller increase in the second half. A notable peak occurs in the second half, reaching about 1.5 standard deviations above the mean, while a deep valley is observed early in the window, about 1.8 standard deviations below the mean. The series is strongly positively correlated with another economic indicator, suggesting a consistent relationship over time.

**OpenTSLM caption 中文翻译**

> 该时间序列显示出平缓上升趋势，波动较低，并具有每四个季度重复一次的中等季节性模式。数据在窗口前期开始时有中等幅度增长，随后在前半段出现更明显的上升，后半段则为略小的增长。第二半段出现一个显著峰值，约比均值高 1.5 个标准差；而窗口前期观察到一个较深谷值，约比均值低 1.8 个标准差。该序列与另一经济指标呈强正相关，表明随时间具有一致的关系。

**ChatTS caption 原文**

> The overall trend is steady. The global maximum occurs at point 9, which is in the first third of the 22-point window. The first half of the window (points 0-11) exhibits larger short-term fluctuations, including a rapid rise from around 1.40 to around 6.92, followed by a decline. The second half shows smaller fluctuations, stabilizing around 2.47. **Conclusion**: Steady trend; maximum in first third; larger fluctuations in first half.

**ChatTS caption 中文翻译**

> 整体趋势稳定。全局最大值出现在第 9 个点，位于 22 点窗口的前三分之一。窗口前半段（点 0-11）表现出更大的短期波动，包括从约 1.40 快速上升到约 6.92，随后下降。后半段波动较小，稳定在约 2.47 附近。**结论**：趋势稳定；最大值位于前三分之一；前半段波动更大。

#### 变量 3：Gross Domestic Product: Chain-type Price Index, Percent Change from Year Ago, Quarterly, Seasonally Adjusted

**OpenTSLM caption 原文**

> The time series shows a long-term downward trend with low volatility and weak seasonal patterns. Early in the window, there is a moderate upward movement, followed by a significant decline in the first half, and a smaller upward shift in the second half. A notable peak occurs in the first half, reaching about 1.6 standard deviations above the mean, while a deep valley appears late in the window, reaching about 2.0 standard deviations below the mean. The overall net change is a decline of approximately 12.4%.

**OpenTSLM caption 中文翻译**

> 该时间序列显示出长期下降趋势，波动较低，并带有较弱的季节性模式。在窗口前期，有适度上升，随后在前半段出现显著下降，后半段则略有回升。前半段出现一个显著峰值，约比均值高 1.6 个标准差；而在窗口后期出现一个深谷，约比均值低 2.0 个标准差。整体净变化约为下降 12.4%。

**ChatTS caption 原文**

> The overall trend is flat, with no significant direction. The global maximum of 7.76 occurs at point 9, which is in the first third of the 22-point window. The first half of the window (points 1–11) exhibits larger short-term fluctuations compared to the second half (points 12–22). In summary, the trend is flat, the peak is in the first third, and the first half has larger fluctuations.

**ChatTS caption 中文翻译**

> 整体趋势平稳，没有明显方向。全局最大值为 7.76，出现在第 9 个点，位于 22 点窗口的前三分之一。窗口前半段（点 1–11）相比后半段（点 12–22）表现出更大的短期波动。总之，趋势平稳，峰值在前三分之一，前半段波动更大。


### 🧪 下游 QA 模型答案 / 评分

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `C` | `A` | ✗ 错误 | C |
| 题目 + 原始数值序列 (`numbers`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM caption (`opentslm_caption`) | `C` | `A` | ✗ 错误 | C |
| 题目 + OpenTSLM caption + 数值 (`opentslm_caption_plus`) | `C` | `A` | ✗ 错误 | C |
| 题目 + ChatTS caption (`chatts_caption`) | `C` | `A` | ✗ 错误 | C |
| 题目 + ChatTS caption + 数值 (`chatts_caption_plus`) | `C` | `A` | ✗ 错误 | C |


### 🔎 Case 分析

- **答案格局**：`meta_only=C✗, numbers=A✓, opentslm_caption=C✗, opentslm_caption_plus=C✗, chatts_caption=C✗, chatts_caption_plus=C✗`。
- **关键问题**：这类问题需要对指定窗口求平均并排序。caption 的全局趋势描述会遮蔽 Q2 2021 到 Q2 2022 的局部均值关系，说明 FREDQA 中很多“领域解释题”首先还是数值抽取题。
- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。



## 📈 Case 07：FREDQA `884` | 六种条件全错

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::884` |
| FREDQA 原始 idx | `884` |
| 变量数 / 序列长度 | `1` / `[80]` |
| 问题类型 | `Causal Reasoning - Counterfactual` |
| 正确答案 | `A` |
| 失败/对比模式 | 六种条件全错 |
| 本 case 关注点 | IRA 余额的疫情反事实外推 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | (IRA/CUUS0000SA0)*100, (Bil. of $/Index 1982-1984=100)*100, Semiannual, Not Seasonally Adjusted  | 80 | 536.249 | 1942.92 | 536.249@0 | 2232.06@73 | 12.477 |

### 🖼 时序图

![FREDQA 884](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_884.png)


### ❓ QA 问题与中文翻译

**题干原文**

> You are a time series analysis expert. This is a metric called Inflation-Adjusted IRA Account Balances (calculated as (IRA dollar value / Consumer Price Index, 1982-1984=100) * 100) collected from the Board of Governors of the Federal Reserve System &lt;ts&gt;&lt;ts/&gt;. The data are semiannual, spanning from January 1984 to July 2023. In 2020, the COVID-19 pandemic reduced consumer spending and led to temporary IRA tax benefits, both of which increased IRA balances. Suppose the pandemic had not occurred, and IRA balances had continued growing at the average semiannual rate observed from July 2018 to July 2019. What would the approximate IRA balance have been in January 2021, and how does this counterfactual value compare to the actual January 2021 balance?

**题干中文翻译**

> 你是一名时间序列分析专家。这是一个名为经通胀调整的 IRA 账户余额（计算方式为（IRA 美元价值 / 消费者价格指数，1982-1984=100）*100）的指标，数据来自美国联邦储备系统理事会 &lt;ts&gt;&lt;ts/&gt;。数据为半年一次，时间跨度从 1984 年 1 月到 2023 年 7 月。2020 年，COVID-19 疫情减少了消费者支出，并带来了临时 IRA 税收优惠，这两者都增加了 IRA 余额。假设疫情没有发生，并且 IRA 余额继续以 2018 年 7 月到 2019 年 7 月之间观察到的平均半年增长率增长。那么，2021 年 1 月的 IRA 余额大约会是多少，这个反事实数值与 2021 年 1 月的实际余额相比如何？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Approximately $1,825 billion, which is about $407 billion lower than the actual value | 大约 1,8250 亿美元，这比实际值低约 4,070 亿美元 |
| `B` | Approximately $2,078 billion, which is about $154 billion lower than the actual value | 大约 2,0780 亿美元，这比实际值低约 1,540 亿美元 |
| `C` | Approximately $2,232 billion, which is equal to the actual value | 大约 2,2320 亿美元，这与实际值相等 |
| `D` | Approximately $2,639 billion, which is about $407 billion higher than the actual value | 大约 2,6390 亿美元，这比实际值高约 4,070 亿美元 |

**正确答案**：`A`

**标准解释原文**

> First, calculate the pre-pandemic semiannual growth rate: the IRA balance was $1,692.68 billion in July 2018 and $1,745.67 billion in July 2019, a $52.99 billion increase over 2 periods. The average semiannual growth is $52.99 / 2 = $26.50 billion. Next, extrapolate this trend from July 2019 ($1,745.67 billion) to January 2021 (3 periods later): $1,745.67 + ($26.50 * 3) = $1,825.17 billion. The actual January 2021 balance is $2,232.06 billion. The counterfactual value is ~$407 billion lower because the pandemic’s reduced spending (boosting savings) and temporary tax benefits—factors absent in the hypothetical scenario—drove faster growth than the pre-2019 trend. This confirms the counterfactual balance would be far lower than actual.

**标准解释中文翻译**

> 首先，计算疫情前的半年增长率：IRA 余额在 2018 年 7 月为 1,692.68 十亿美元，在 2019 年 7 月为 1,745.67 十亿美元，2 个期间增加了 52.99 十亿美元。平均半年增长为 52.99 / 2 = 26.50 十亿美元。接下来，将这一趋势从 2019 年 7 月（1,745.67 十亿美元）外推到 2021 年 1 月（之后 3 个期间）：1,745.67 +（26.50 * 3）= 1,825.17 十亿美元。实际的 2021 年 1 月余额为 2,232.06 十亿美元。反事实数值大约低 407 十亿美元，因为疫情导致的支出减少（提高了储蓄）和临时税收优惠——这些因素在假设情景中不存在——推动了比 2019 年前趋势更快的增长。这证实了反事实余额会远低于实际值。


### 📝 生成的 caption 与中文翻译

#### 变量 1：(IRA/CUUS0000SA0)*100, (Bil. of $/Index 1982-1984=100)*100, Semiannual, Not Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a steady upward trend with low volatility and a strong seasonal pattern repeating every 21 periods. The data starts with a moderate increase in the early part of the window, followed by a more pronounced rise in the first half, and a slightly smaller but still positive growth in the second half. There is a notable dip early in the window, about 1.2 standard deviations below the mean, but no clear peak or labeled anomaly is present. The overall growth over the time span is substantial, with a net increase of over 100%.

**OpenTSLM caption 中文翻译**

> 时间序列显示出平稳上升趋势，波动性较低，并且存在每 21 个周期重复一次的强季节性模式。数据在窗口前半部分开始时有适度增长，随后在前半段出现更明显的上升，在后半段则增长略小但仍为正。窗口早期有一个显著下跌，约比均值低 1.2 个标准差，但没有明显峰值或标记的异常。整个时间跨度内的总体增长相当可观，净增长超过 100%。

**ChatTS caption 原文**

> The overall trend is increasing. The global maximum (2232.12) occurs in the last third of the window (positions 54–79). Short-term fluctuations are more pronounced in the first half (positions 1–37), where two sudden increases with amplitudes of 491.93 and 265.44 occur, compared to the second half, which shows a smoother rise with a single spike of 355.44. Answer: Up; last third; first half.

**ChatTS caption 中文翻译**

> 整体趋势是上升的。全局最大值（2232.12）出现在窗口的后三分之一（位置 54–79）。短期波动在前半段（位置 1–37）更为明显，其中出现了两个幅度分别为 491.93 和 265.44 的突然增加，而后半段则显示出更平滑的上升，仅有一个幅度为 355.44 的峰值。答案：上升；后三分之一；前半段。


### 🧪 下游 QA 模型答案 / 评分

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `B` | `A` | ✗ 错误 | B |
| 题目 + 原始数值序列 (`numbers`) | `B` | `A` | ✗ 错误 | B |
| 题目 + OpenTSLM caption (`opentslm_caption`) | `B` | `A` | ✗ 错误 | B |
| 题目 + OpenTSLM caption + 数值 (`opentslm_caption_plus`) | `B` | `A` | ✗ 错误 | B |
| 题目 + ChatTS caption (`chatts_caption`) | `B` | `A` | ✗ 错误 | B |
| 题目 + ChatTS caption + 数值 (`chatts_caption_plus`) | `B` | `A` | ✗ 错误 | B |


### 🔎 Case 分析

- **答案格局**：`meta_only=B✗, numbers=B✗, opentslm_caption=B✗, opentslm_caption_plus=B✗, chatts_caption=B✗, chatts_caption_plus=B✗`。
- **关键问题**：题目需要用 2018-07 到 2019-07 的半年度平均增长率外推到 2021-01。caption 的全局 upward trend 和 last-third maximum 信息不足以执行反事实公式，数值条件也没有让 QA 模型稳定完成多步计算。
- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。



## 📈 Case 08：FREDQA `560` | 六种条件全错

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::560` |
| FREDQA 原始 idx | `560` |
| 变量数 / 序列长度 | `1` / `[80]` |
| 问题类型 | `Abductive Reasoning`, `Analogical Reasoning` |
| 正确答案 | `B` |
| 失败/对比模式 | 六种条件全错 |
| 本 case 关注点 | FDIC 机构倒闭峰值与监管解释 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | Failures of all Institutions for the United States and Other Areas, Number of Institutions, Annual, Not Seasonally Adjusted  | 80 | 9 | 24 | 0@71 | 530@55 | 0.918671 |

### 🖼 时序图

![FREDQA 560](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_560.png)


### ❓ QA 问题与中文翻译

**题干原文**

> You are a time series analysis expert. This is a metric called Failures of all Institutions for the United States and Other Areas, Number of Institutions, Annual, Not Seasonally Adjusted collected from the Federal Deposit Insurance Corporation (FDIC) &lt;ts&gt;&lt;ts/&gt;. Using annual data from 1934 to 2013, identify the number of institution failures in 1989 (a peak year of the savings and loan crisis) and 2009 (a peak year of the 2008–2009 recession). Based on these values, which regulatory or institutional factor best explains why the 2008–2009 recession—despite being deeper—had far fewer failures than the 1980s crisis, consistent with the FDIC’s mandate to stabilize the financial system?

**题干中文翻译**

> 您是一位时间序列分析专家。这是一项名为“美国及其他地区所有机构的失败数量（机构数量，年度，未季节性调整）”的指标，数据来自联邦存款保险公司（FDIC）&lt;ts&gt;&lt;ts/&gt;。使用1934年至2013年的年度数据，找出1989年（储蓄和贷款危机的一个峰值年份）和2009年（2008–2009年衰退的一个峰值年份）的机构倒闭数量。基于这些数值，哪一个监管或制度因素最能解释为什么2008–2009年衰退——尽管更为严重——的机构倒闭数却远少于20世纪80年代的危机，这与FDIC稳定金融体系的职责一致？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Reduced FDIC insurance limits for individual depositors in the 2000s, which minimized panic-driven bank runs | 20世纪2000年代将个人存款人的FDIC保险限额降低，从而最小化了由恐慌驱动的银行挤兑 |
| `B` | Stricter capital adequacy rules for banks adopted after the savings and loan crisis to prevent insolvency | 在储蓄和贷款危机之后为防止资不抵债而采用了更严格的银行资本充足率规则 |
| `C` | A sharp drop in the number of savings and loan associations operating in the U.S. by the 2000s | 到2000年代，在美国运营的储蓄和贷款协会数量急剧下降 |
| `D` | The FDIC’s temporary suspension of its 'too big to fail' policy during the 2008–2009 recession | FDIC在2008–2009年衰退期间暂时暂停了其“too big to fail”政策 |

**正确答案**：`B`

**标准解释原文**

> （源 artifact 未提供该字段。）

**标准解释中文翻译**

> （源 artifact 未提供该字段。）


### 📝 生成的 caption 与中文翻译

#### 变量 1：Failures of all Institutions for the United States and Other Areas, Number of Institutions, Annual, Not Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a consistent downward trend with low volatility and a strong seasonal pattern repeating every 18 years. The data starts with a significant decline in the early part of the window, followed by a moderate decrease in the first half, and a slight increase in the second half. A notable peak occurs early in the window, standing out as about 2.1 standard deviations above the mean. The series is strongly correlated with another related variable, indicating a close relationship between the two.

**OpenTSLM caption 中文翻译**

> 该时间序列表现出持续下降的趋势，波动性较低，并且存在一个强烈的季节性模式，每18年重复一次。数据在窗口前期开始时显著下降，随后在前半段适度下降，并在后半段略有上升。一个显著的峰值出现在窗口早期，明显高于均值约2.1个标准差。该序列与另一个相关变量高度相关，表明两者之间存在紧密关系。

**ChatTS caption 原文**

> The overall trend is flat, with the time series starting at ~9.02 and ending at ~24.04. The global maximum of 530.0 (at point 54) occurs in the middle third of the window (points 41-59). Short-term fluctuations are more pronounced in the first half (e.g., the spike between points 2-4) compared to the second half (which shows a gradual decline after point 54). Answer: Flat trend; middle third; first half.

**ChatTS caption 中文翻译**

> 总体趋势平稳，时间序列从约9.02开始，到24.04结束。全局最大值530.0（位于第54个点）出现在窗口的中间三分之一（第41-59个点）。短期波动在前半段更为明显（例如第2-4个点之间的尖峰），相比之下后半段（在第54个点之后呈现逐渐下降）。答案：平稳趋势；中间三分之一；前半段。


### 🧪 下游 QA 模型答案 / 评分

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `C` | `B` | ✗ 错误 | C |
| 题目 + 原始数值序列 (`numbers`) | `C` | `B` | ✗ 错误 | C |
| 题目 + OpenTSLM caption (`opentslm_caption`) | `C` | `B` | ✗ 错误 | C |
| 题目 + OpenTSLM caption + 数值 (`opentslm_caption_plus`) | `C` | `B` | ✗ 错误 | C |
| 题目 + ChatTS caption (`chatts_caption`) | `C` | `B` | ✗ 错误 | C |
| 题目 + ChatTS caption + 数值 (`chatts_caption_plus`) | `C` | `B` | ✗ 错误 | C |


### 🔎 Case 分析

- **答案格局**：`meta_only=C✗, numbers=C✗, opentslm_caption=C✗, opentslm_caption_plus=C✗, chatts_caption=C✗, chatts_caption_plus=C✗`。
- **关键问题**：模型全部选择了表面上合理但并非标准答案的选项，说明该题不是单纯读峰值，还要求把 1980s S&amp;L crisis 与之后更严格资本充足率规则联系起来；caption 没有编码制度性解释。
- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。



## 📈 Case 09：FREDQA `964` | meta-only 错，只有 ChatTS caption 对

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::964` |
| FREDQA 原始 idx | `964` |
| 变量数 / 序列长度 | `1` / `[426]` |
| 问题类型 | `Causal Reasoning - Interventional` |
| 正确答案 | `B` |
| 失败/对比模式 | meta-only 错，只有 ChatTS caption 对 |
| 本 case 关注点 | 雷曼兄弟倒闭前后 PPI 的即时百分比变化 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | PPI | 426 | 100 | 224.866 | 100@0 | 237.3@357 | 0.278716 |

### 🖼 时序图

![FREDQA 964](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_964.png)


### ❓ QA 问题与中文翻译

**题干原文**

> You are a time series analysis expert. This is a metric called Producer Price Index (PPI)—which measures average changes in selling prices received by domestic producers for their output—collected from the Federal Reserve Economic Data (FRED) database &lt;ts&gt;&lt;ts/&gt;. The data is monthly from December 1989 to May 2025. The Lehman Brothers collapse on September 15, 2008, triggered a global financial crisis that disrupted commodity markets and supply chains. To evaluate the immediate causal impact of this event on producer prices, compare the PPI values for August 2008 (pre-collapse) and September 2008 (post-collapse). Which conclusion is most supported by the data and economic logic?

**题干中文翻译**

> 你是一名时间序列分析专家。这是一项称为生产者价格指数（PPI）的指标——它衡量国内生产者为其产出获得的销售价格平均变化——数据来自联邦储备经济数据（FRED）数据库 &lt;ts&gt;&lt;ts/&gt;。数据为月度数据，时间范围从1989年12月到2025年5月。雷曼兄弟于2008年9月15日倒闭，引发了一场全球金融危机，扰乱了大宗商品市场和供应链。为评估这一事件对生产者价格的直接因果影响，比较2008年8月（倒闭前）和2008年9月（倒闭后）的PPI值。哪一项结论最符合数据和经济逻辑？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | The collapse caused a 4.7% decrease in PPI, as reduced consumer demand lowered producer pricing power. | 倒闭导致PPI下降了4.7%，因为消费者需求减少降低了生产者的定价能力。 |
| `B` | The collapse caused a 4.7% increase in PPI, as short-term disruptions raised the cost of raw materials for producers. | 倒闭导致PPI上升了4.7%，因为短期扰动提高了生产者原材料的成本。 |
| `C` | The collapse had no immediate effect, as PPI remained unchanged between August and September 2008. | 倒闭没有立即影响，因为2008年8月和9月之间PPI保持不变。 |
| `D` | The collapse caused a 9.2% increase in PPI, as producers passed on full costs of financial market turmoil to buyers. | 倒闭导致PPI上升了9.2%，因为生产者将金融市场动荡的全部成本转嫁给了买家。 |

**正确答案**：`B`

**标准解释原文**

> First, calculate the percentage change in PPI: August 2008 = 182.7, September 2008 = 191.3. The change is (191.3 – 182.7)/182.7 ≈ 4.7%, ruling out A (decrease), C (no change), and D (9.2% increase). Causally, the Lehman collapse disrupted global supply chains and commodity markets, leading to short-term spikes in raw material costs (e.g., energy, metals) that producers passed on as higher prices. This aligns with the PPI increase and supports option B.

**标准解释中文翻译**

> 首先，计算PPI的百分比变化：2008年8月 = 182.7，2008年9月 = 191.3。变化为 (191.3 – 182.7)/182.7 ≈ 4.7%，排除了A（下降）、C（无变化）和D（9.2%上升）。从因果上看，雷曼倒闭扰乱了全球供应链和大宗商品市场，导致原材料成本（例如能源、金属）短期飙升，生产者将其以更高价格转嫁出去。这与PPI上升一致，并支持选项B。


### 📝 生成的 caption 与中文翻译

#### 变量 1：PPI

**OpenTSLM caption 原文**

> The time series shows a flat trend with low volatility and medium strength seasonality every 10 periods. There is a noticeable upward phase early in the window followed by a more pronounced upward movement in the first half, which is then followed by a significant downward shift in the second half. A peak occurs in the second half with a magnitude of about 1.5 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 1.7 standard deviations from the mean. The series exhibits strong positive correlation with variable A and moderate positive correlation with variable B.

**OpenTSLM caption 中文翻译**

> 时间序列显示出平坦的趋势、较低的波动性，以及每10个周期一次的中等强度季节性。窗口前期有一个明显的上升阶段，随后在前半段出现更显著的上升运动，接着在后半段出现显著下降。后半段出现一个峰值，其幅度约为相对于均值1.5个标准差，而在窗口前期观察到一个谷值，其幅度约为相对于均值1.7个标准差。该序列与变量A呈强正相关，与变量B呈中等正相关。

**ChatTS caption 原文**

> The overall trend is increasing. The global maximum is in the last third of the window. Short-term fluctuations are larger in the second half of the window.

**ChatTS caption 中文翻译**

> 整体趋势呈上升。全局最大值位于窗口的后三分之一处。短期波动在窗口后半段更大。


### 🧪 下游 QA 模型答案 / 评分

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `C` | `B` | ✗ 错误 | C |
| 题目 + 原始数值序列 (`numbers`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM caption (`opentslm_caption`) | `A` | `B` | ✗ 错误 | A |
| 题目 + OpenTSLM caption + 数值 (`opentslm_caption_plus`) | `A` | `B` | ✗ 错误 | A |
| 题目 + ChatTS caption (`chatts_caption`) | `B` | `B` | ✓ 正确 | B |
| 题目 + ChatTS caption + 数值 (`chatts_caption_plus`) | `A` | `B` | ✗ 错误 | A |


### 🔎 Case 分析

- **答案格局**：`meta_only=C✗, numbers=A✗, opentslm_caption=A✗, opentslm_caption_plus=A✗, chatts_caption=B✓, chatts_caption_plus=A✗`。
- **关键问题**：这个 case 需要比较 2008 年 8 月和 9 月 PPI 的短期变化。ChatTS 的简洁趋势摘要让 caption-only 条件答对，但 OpenTSLM、numbers 和两个 caption+numbers 条件都答错，说明即使直接给数值，长题干中的局部月份定位和百分比变化也没有被稳定执行。
- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。



## 📈 Case 10：FREDQA `481` | meta-only 错，数值/caption 全部救回

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::481` |
| FREDQA 原始 idx | `481` |
| 变量数 / 序列长度 | `3` / `[61, 61, 61]` |
| 问题类型 | `Abductive Reasoning` |
| 正确答案 | `A` |
| 失败/对比模式 | meta-only 错，数值/caption 全部救回 |
| 本 case 关注点 | 油价、公交客流、车辆里程在 2015 年 3 月的替代效应解释 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | US Regular Conventional Gas Price, Percent Change, Monthly, Not Seasonally Adjusted  | 61 | 3.4162 | 4.2427 | -17.7653@36 | 12.7305@50 | -0.0146734 |
| 2 | Public Transit Ridership, Percent Change, Monthly, Not Seasonally Adjusted  | 61 | 0.4909 | -0.6018 | -14.6704@34 | 16.3636@38 | -0.0185047 |
| 3 | Vehicle Miles Traveled, Percent Change, Monthly, Not Seasonally Adjusted  | 61 | -7.0598 | -8.3761 | -9.6498@8 | 18.8941@50 | -0.0130504 |

### 🖼 时序图

![FREDQA 481](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_481.png)


### ❓ QA 问题与中文翻译

**题干原文**

> You are a time series analysis expert. In a U.S. Transportation and Energy system, there are 3 metrics: US Regular Conventional Gas Price, Percent Change (Monthly, Not Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;; Public Transit Ridership, Percent Change (Monthly, Not Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;; Vehicle Miles Traveled, Percent Change (Monthly, Not Seasonally Adjusted)&lt;ts&gt;&lt;ts/&gt;. Using monthly data from January 2012 to January 2017, examine the percent change values for March 2015. The textbook substitution effect predicts that a large increase in gas prices would reduce vehicle miles traveled and increase public transit ridership. Based on the data for this month, which factor from the provided context best explains why the expected relationship is not observed?

**题干中文翻译**

> 你是一名时间序列分析专家。在美国交通和能源系统中，有 3 个指标：美国常规汽油价格，月度百分比变化，未经季节调整&lt;ts&gt;&lt;ts/&gt;；公共交通乘客量，月度百分比变化，未经季节调整&lt;ts&gt;&lt;ts/&gt;；车辆行驶英里数，月度百分比变化，未经季节调整&lt;ts&gt;&lt;ts/&gt;。使用 2012 年 1 月到 2017 年 1 月的月度数据，考察 2015 年 3 月的百分比变化值。教材中的替代效应预测，汽油价格的大幅上涨会减少车辆行驶英里数并增加公共交通乘客量。根据该月份的数据，提供的上下文中哪一因素最能解释为什么没有观察到预期关系？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Seasonal increases in travel demand for spring and summer activities | 春季和夏季活动的出行需求季节性增加 |
| `B` | Temporary reductions in public transit service frequency | 公共交通服务频率的暂时性减少 |
| `C` | Long-term improvements in passenger vehicle fuel efficiency | 乘用车燃油效率的长期改善 |
| `D` | Nationwide increases in household disposable income | 家庭可支配收入的全国性增加 |

**正确答案**：`A`

**标准解释原文**

> （源 artifact 未提供该字段。）

**标准解释中文翻译**

> （源 artifact 未提供该字段。）


### 📝 生成的 caption 与中文翻译

#### 变量 1：US Regular Conventional Gas Price, Percent Change, Monthly, Not Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a flat trend with low volatility and a medium-strength seasonal pattern repeating approximately every 102 months. The data experiences a significant decline early in the window, followed by a moderate increase in the first half, and a smaller decline in the second half. A notable peak occurs early, reaching about 2.0 standard deviations above the mean, while a deep valley appears late, reaching about 2.1 standard deviations below the mean. The series is strongly positively correlated with the US Regular Conventional Gas Price, Percent Change, Monthly, Seasonally Adjusted data.

**OpenTSLM caption 中文翻译**

> 该时间序列显示出平稳趋势、低波动性以及大约每 102 个月重复一次的中等强度季节模式。数据在窗口早期经历了显著下降，随后在前半段出现适度上升，并在后半段出现较小下降。一个显著峰值出现在早期，约高于均值 2.0 个标准差，而一个深谷出现在后期，约低于均值 2.1 个标准差。该序列与美国常规汽油价格、月度百分比变化、季节调整后数据呈强正相关。

**ChatTS caption 原文**

> The overall trend is flat, with values starting and ending around -0.31. The global maximum, which is also -0.31 due to the steady trend, occurs at point 12, located in the first third of the 61-point window. Short-term fluctuations are more pronounced in the first half of the series, characterized by high-frequency shakes with an amplitude of about 16.5, compared to the relatively stable values in the second half.

**ChatTS caption 中文翻译**

> 整体趋势平稳，数值起始和结束都在 -0.31 左右。全局最大值也为 -0.31，由于趋势平稳而保持不变，出现在第 12 个点，位于 61 点窗口的前 1/3。短期波动在序列前半段更为明显，其特征是高频震荡，幅度约为 16.5，而后半段数值相对稳定。

#### 变量 2：Public Transit Ridership, Percent Change, Monthly, Not Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a flat trend with low volatility and no clear seasonality. Early in the window, there is a moderate upward movement, followed by a significant downward phase in the first half, and a strong upward shift in the second half. A peak occurs in the second half, reaching about 1.5 standard deviations above the mean, while a valley is observed around the middle, about 1.3 standard deviations below the mean. The series is strongly positively correlated with two other variables related to public transit passenger changes.

**OpenTSLM caption 中文翻译**

> 该时间序列显示出平稳趋势、低波动性且没有明显季节性。窗口早期有中等程度的上升，随后在前半段出现显著下降阶段，并在后半段出现强劲上升。峰值出现在后半段，约高于均值 1.5 个标准差，而谷值出现在中间附近，约低于均值 1.3 个标准差。该序列与另外两个与公共交通乘客变化相关的变量呈强正相关。

**ChatTS caption 原文**

> The overall trend is flat. The global maximum, which is 0.49, is located in the first third of the window (positions 1-20). Short-term fluctuations are more pronounced in the first half of the window (positions 1-30) compared to the second half (positions 31-61). Total words: 67.

**ChatTS caption 中文翻译**

> 整体趋势平稳。全局最大值为 0.49，位于窗口前 1/3（位置 1-20）。与后半段（位置 31-61）相比，窗口前半段（位置 1-30）的短期波动更为明显。总词数：67。

#### 变量 3：Vehicle Miles Traveled, Percent Change, Monthly, Not Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a flat trend with high volatility and no clear seasonality. It begins with a significant downward phase early in the window, followed by an upward movement in the first half, and then a smaller decline in the second half. A notable peak occurs early, with a magnitude of about 2.0 standard deviations from the mean, while a deep valley appears in the second half, reaching about 2.1 standard deviations below the mean. The overall net change is a decrease of nearly 18%.

**OpenTSLM caption 中文翻译**

> 该时间序列显示出平稳趋势、高波动性且没有明显季节性。它在窗口早期开始时经历了显著下降阶段，随后在前半段出现上升运动，然后在后半段出现较小下降。一个显著峰值出现在早期，幅度约为距均值 2.0 个标准差，而一个深谷出现在后半段，约低于均值 2.1 个标准差。总体净变化为接近 18% 的下降。

**ChatTS caption 原文**

> The trend is flat. The global maximum is in the first third of the window. Short-term fluctuations are more pronounced in the first half of the window.

**ChatTS caption 中文翻译**

> 趋势平稳。全局最大值位于窗口前 1/3。短期波动在窗口前半段更为明显。


### 🧪 下游 QA 模型答案 / 评分

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `C` | `A` | ✗ 错误 | C |
| 题目 + 原始数值序列 (`numbers`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM caption (`opentslm_caption`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM caption + 数值 (`opentslm_caption_plus`) | `A` | `A` | ✓ 正确 | A |
| 题目 + ChatTS caption (`chatts_caption`) | `A` | `A` | ✓ 正确 | A |
| 题目 + ChatTS caption + 数值 (`chatts_caption_plus`) | `A` | `A` | ✓ 正确 | A |


### 🔎 Case 分析

- **答案格局**：`meta_only=C✗, numbers=A✓, opentslm_caption=A✓, opentslm_caption_plus=A✓, chatts_caption=A✓, chatts_caption_plus=A✓`。
- **关键问题**：没有时序证据时模型选错背景因素；加入数值或 caption 后都能定位春夏出行需求这一解释。这是少数 caption 真正提供有效证据的正例。
- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。



## 📈 Case 11：FREDQA `1209` | meta-only 错，数值/caption 全部救回

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::1209` |
| FREDQA 原始 idx | `1209` |
| 变量数 / 序列长度 | `4` / `[22, 22, 22, 22]` |
| 问题类型 | `Causal Reasoning - Interventional` |
| 正确答案 | `B` |
| 失败/对比模式 | meta-only 错，数值/caption 全部救回 |
| 本 case 关注点 | 圣路易斯 premature death crude rate 与 age-adjusted rate 的衰退前后变化 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | Premature Death Rate for St. Louis County, MO, Rate per 100,000, Annual, Not Seasonally Adjusted  | 22 | 395.6 | 555.2 | 353.7@8 | 555.2@21 | 5.27047 |
| 2 | Premature Death Rate for St. Louis city, MO, Rate per 100,000, Annual, Not Seasonally Adjusted  | 22 | 692.2 | 831.7 | 535.5@13 | 831.7@21 | 2.11101 |
| 3 | Age-Adjusted Premature Death Rate for St. Louis city, MO, Rate per 100,000, Annual, Not Seasonally Adjusted  | 22 | 730 | 701.8 | 516.2@14 | 730@0 | -5.22592 |
| 4 | Age-Adjusted Premature Death Rate for St. Louis County, MO, Rate per 100,000, Annual, Not Seasonally Adjusted  | 22 | 372.2 | 424.5 | 320.3@8 | 424.5@21 | 0.319819 |

### 🖼 时序图

![FREDQA 1209](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_1209.png)


### ❓ QA 问题与中文翻译

**题干原文**

> You are a time series analysis expert. In St. Louis, MO (encompassing St. Louis City and St. Louis County), there are four annual metrics (collected 1999–2020):
> 1. Premature Death Rate for St. Louis County (crude, per 100,000 residents)&lt;ts&gt;&lt;ts/&gt;;
> 2. Premature Death Rate for St. Louis City (crude, per 100,000 residents)&lt;ts&gt;&lt;ts/&gt;;
> 3. Age-Adjusted Premature Death Rate for St. Louis City (per 100,000 residents)&lt;ts&gt;&lt;ts/&gt;;
> 4. Age-Adjusted Premature Death Rate for St. Louis County (per 100,000 residents)&lt;ts&gt;&lt;ts/&gt;.
> The Great Recession (2007–2009) is hypothesized to have altered trends in premature deaths. For St. Louis City, calculate the average annual change in its crude rate (metric 2) from 2000–2006 (pre-recession) and the average annual change in its age-adjusted rate (metric 3) from 2010–2016 (post-recession). Which conclusion about the recession’s causal effect on these rates is supported by the data?

**题干中文翻译**

> 你是一名时间序列分析专家。在密苏里州圣路易斯（包括圣路易斯市和圣路易斯县），有四个年度指标（收集于1999–2020年）：
> 1. 圣路易斯县过早死亡率（粗率，每10万人居民）&lt;ts&gt;&lt;ts/&gt;；
> 2. 圣路易斯市过早死亡率（粗率，每10万人居民）&lt;ts&gt;&lt;ts/&gt;；
> 3. 圣路易斯市年龄调整过早死亡率（每10万人居民）&lt;ts&gt;&lt;ts/&gt;；
> 4. 圣路易斯县年龄调整过早死亡率（每10万人居民）&lt;ts&gt;&lt;ts/&gt;。
> 大衰退（2007–2009年）被假设已经改变了过早死亡的趋势。对于圣路易斯市，计算其粗率（指标2）在2000–2006年（衰退前）的平均年度变化，以及其年龄调整率（指标3）在2010–2016年（衰退后）的平均年度变化。关于衰退对这些比率的因果影响，哪一项结论得到了数据支持？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | The recession caused a steeper decline in both rates, consistent with economic growth reducing premature deaths. | 衰退导致两种比率下降得更陡，这与经济增长减少过早死亡是一致的。 |
| `B` | The recession reversed the crude rate’s decline but left the age-adjusted rate stable, implying age composition changes drove the crude trend. | 衰退逆转了粗率的下降，但使年龄调整率保持稳定，意味着年龄构成变化驱动了粗率趋势。 |
| `C` | The recession had no effect on the crude rate but accelerated the age-adjusted rate’s decline, contradicting the economic hypothesis. | 衰退对粗率没有影响，但加速了年龄调整率的下降，这与经济假设相矛盾。 |
| `D` | The recession caused both rates to rise sharply, confirming a direct link between economic downturns and premature deaths. | 衰退导致两种比率大幅上升，证实了经济下滑与过早死亡之间的直接联系。 |

**正确答案**：`B`

**标准解释原文**

> First, compute average annual changes using the time series data:
> - **Crude rate (metric 2, pre-recession 2000–2006):** From 627.7 to 612.1, a total decline of -15.6 over 6 years → **-2.6 per year** (declining).
> - **Crude rate (metric 2, post-recession 2010–2016):** From 558.0 to 618.8, a total increase of +60.8 over 6 years → **+10.1 per year** (rising).
> - **Age-adjusted rate (metric 3, pre-recession 2000–2006):** From 660.6 to 632.4, a total decline of -28.2 over 6 years → **-4.7 per year** (declining).
> - **Age-adjusted rate (metric 3, post-recession 2010–2016):** From 560.0 to 560.3, a negligible increase of +0.3 over 6 years → **~0 per year** (stable).
>
> The crude rate reversed from declining to rising post-recession, but the age-adjusted rate (which controls for population age composition) stabilized. Since age-adjustment removes confounding from changes in the city’s age structure, the recession’s apparent effect on the crude rate was not a true increase in premature deaths per age group—instead, it reflected shifts in who lived in St. Louis City. This supports option B.

**标准解释中文翻译**

> 首先，使用时间序列数据计算平均年度变化：
> - **粗率（指标2，衰退前2000–2006年）：** 从627.7到612.1，总共下降-15.6，历时6年 → **每年-2.6**（下降）。
> - **粗率（指标2，衰退后2010–2016年）：** 从558.0到618.8，总共上升+60.8，历时6年 → **每年+10.1**（上升）。
> - **年龄调整率（指标3，衰退前2000–2006年）：** 从660.6到632.4，总共下降-28.2，历时6年 → **每年-4.7**（下降）。
> - **年龄调整率（指标3，衰退后2010–2016年）：** 从560.0到560.3，6年内微弱上升+0.3 → **约每年0**（稳定）。
>
> 粗率在衰退后从下降转为上升，但年龄调整率（控制了人口年龄构成）稳定下来。由于年龄调整消除了城市年龄结构变化带来的混杂因素，衰退对粗率的表面影响并不是真正的每个年龄组过早死亡增加——相反，它反映了圣路易斯市居民构成的变化。这支持选项B。


### 📝 生成的 caption 与中文翻译

#### 变量 1：Premature Death Rate for St. Louis County, MO, Rate per 100,000, Annual, Not Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a downward trend with medium volatility and a medium-strength seasonal pattern repeating every 10 years. The premature death rate for St. Louis County, MO, has decreased by over 50% over the entire period. Early in the window, there was a notable decline, followed by a more pronounced drop in the first half, and a significant rise in the second half. A peak occurred around the middle of the time span, reaching about 1.5 standard deviations above the mean, while a valley in the second half was about 1.2 standard deviations below the mean. The rate is strongly positively correlated with the premature death rate for Madison County, MO.

**OpenTSLM caption 中文翻译**

> 该时间序列显示出下降趋势，具有中等波动性和每10年重复一次的中等强度季节模式。密苏里州圣路易斯县的过早死亡率在整个期间下降了超过50%。在窗口早期，出现了明显下降，随后在前半段出现了更显著的下降，并在后半段出现了明显上升。大约在时间跨度的中间出现了一个峰值，约比均值高1.5个标准差，而后半段的一个谷值约比均值低1.2个标准差。该比率与密苏里州麦迪逊县的过早死亡率呈强正相关。

**ChatTS caption 原文**

> The overall trend is increasing. The global maximum occurs at the final point (position 22 out of 22, last third of the window). Short-term fluctuations are more pronounced in the first half (points 1-11) due to the rapid decline followed by a slow rise, compared to the smoother trend in the second half (points 12-22).

**ChatTS caption 中文翻译**

> 总体趋势是上升的。全局最大值出现在最后一个点（第22个点，共22个点，位于窗口的后三分之一）。短期波动在前半段（点1-11）更为明显，这是由于快速下降后接着缓慢上升；相比之下，后半段（点12-22）的趋势更平稳。

#### 变量 2：Premature Death Rate for St. Louis city, MO, Rate per 100,000, Annual, Not Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a downward trend with medium volatility and a medium-strength seasonal pattern repeating every 10 years. The premature death rate for St. Louis city, MO, has decreased by over 50% over the entire period. The decline was most pronounced in the first half of the time window, followed by a relatively flat period in the second half. There was a notable dip early in the window, about 1.5 standard deviations below the mean. The rate is negatively correlated with both population and median income, suggesting potential inverse relationships.

**OpenTSLM caption 中文翻译**

> 该时间序列显示出下降趋势，具有中等波动性和每10年重复一次的中等强度季节模式。密苏里州圣路易斯市的过早死亡率在整个期间下降了超过50%。下降在时间窗口的前半段最为显著，随后在后半段相对平稳。窗口早期出现了一个明显低谷，约比均值低1.5个标准差。该比率与人口和家庭收入均呈负相关，表明可能存在反向关系。

**ChatTS caption 原文**

> The overall trend is increasing. The global maximum occurs at point 21, which is in the last third of the 22-point window. Short-term fluctuations are more pronounced in the first half (points 1-11) due to the rapid decline followed by a slow rise, compared to the steady increase in the second half (points 12-22). **Answer:** Trend: Increasing; Max Position: Last third; Fluctuations: First half

**ChatTS caption 中文翻译**

> 总体趋势是上升的。全局最大值出现在第21个点，位于22点窗口的后三分之一。短期波动在前半段（点1-11）更为明显，这是由于快速下降后接着缓慢上升；相比之下，后半段（点12-22）的趋势持续上升。**答案：** 趋势：上升；最大位置：后三分之一；波动：前半段

#### 变量 3：Age-Adjusted Premature Death Rate for St. Louis city, MO, Rate per 100,000, Annual, Not Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a downward trend with medium volatility and a medium-strength seasonal pattern repeating every three years. The data starts with a significant decline in the early part of the window, followed by a continued decrease in the first half, and a slight recovery in the second half. There is a notable peak early in the window, about 1.5 standard deviations above the mean, and a deep valley around the middle, about 2.0 standard deviations below the mean. The series is strongly negatively correlated with the age-adjusted premature death rate for Columbus, OH, and strongly positively correlated with the rate for Madison, WI.

**OpenTSLM caption 中文翻译**

> 该时间序列显示出下降趋势，具有中等波动性和每三年重复一次的中等强度季节模式。数据在窗口早期出现了显著下降，随后在前半段继续下降，并在后半段略有回升。窗口早期有一个明显峰值，约比均值高1.5个标准差，而中间附近有一个深谷，约比均值低2.0个标准差。该序列与俄亥俄州哥伦布市的年龄调整过早死亡率呈强负相关，并与威斯康星州麦迪逊市的比率呈强正相关。

**ChatTS caption 原文**

> The overall trend is flat. The global maximum occurs at point 0, in the first third of the window. Short-term fluctuations are more pronounced in the first half (shake with amplitude ~173.41) compared to the second half (steady decline). **Answer:** Flat; First third; First half

**ChatTS caption 中文翻译**

> 总体趋势是平坦的。全局最大值出现在第0个点，位于窗口的前三分之一。短期波动在前半段更为明显（振幅约173.41），相比之下，后半段则是稳定下降。**答案：** 平坦；前三分之一；前半段

#### 变量 4：Age-Adjusted Premature Death Rate for St. Louis County, MO, Rate per 100,000, Annual, Not Seasonally Adjusted 

**OpenTSLM caption 原文**

> The time series shows a downward trend with medium volatility and a medium-strength seasonal pattern repeating every three years. The data starts with a significant decline in the early part of the window, followed by a continued decrease in the first half, and a slight recovery in the second half. There is a notable peak early in the window, about 1.5 standard deviations above the mean, and a deep valley in the first half, about 2.0 standard deviations below the mean. The overall net change is a decline of nearly 40%.

**OpenTSLM caption 中文翻译**

> 该时间序列显示出下降趋势，具有中等波动性和每三年重复一次的中等强度季节模式。数据在窗口早期出现了显著下降，随后在前半段继续下降，并在后半段略有回升。窗口早期有一个明显峰值，约比均值高1.5个标准差，而前半段有一个深谷，约比均值低2.0个标准差。整体净变化是接近40%的下降。

**ChatTS caption 原文**

> The overall trend is flat, with values starting and ending around 372.20 to 424.50. The global maximum occurs at the final point (position 22) in the last third of the window. Short-term fluctuations are more pronounced in the first half (positions 1-11), where a rapid decline and recovery occur. Therefore, the answer is: Flat trend, global maximum in the last third, larger fluctuations in the first half.

**ChatTS caption 中文翻译**

> 总体趋势是平坦的，数值起始和结束大约在372.20到424.50之间。全局最大值出现在最后一个点（第22个位置），位于窗口的后三分之一。短期波动在前半段（位置1-11）更为明显，其中出现了快速下降和回升。因此，答案是：平坦趋势，全局最大值在后三分之一，前半段波动更大。


### 🧪 下游 QA 模型答案 / 评分

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `C` | `B` | ✗ 错误 | C |
| 题目 + 原始数值序列 (`numbers`) | `B` | `B` | ✓ 正确 | B |
| 题目 + OpenTSLM caption (`opentslm_caption`) | `B` | `B` | ✓ 正确 | B |
| 题目 + OpenTSLM caption + 数值 (`opentslm_caption_plus`) | `B` | `B` | ✓ 正确 | B |
| 题目 + ChatTS caption (`chatts_caption`) | `B` | `B` | ✓ 正确 | B |
| 题目 + ChatTS caption + 数值 (`chatts_caption_plus`) | `B` | `B` | ✓ 正确 | B |


### 🔎 Case 分析

- **答案格局**：`meta_only=C✗, numbers=B✓, opentslm_caption=B✓, opentslm_caption_plus=B✓, chatts_caption=B✓, chatts_caption_plus=B✓`。
- **关键问题**：题目需要比较两个阶段的平均年变化，并理解 age-adjustment 的含义。时序证据能把 meta-only 从错误方向拉回，说明部分干预型 FREDQA 确实受益于数据证据。
- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。



## 📈 Case 12：FREDQA `811` | caption-only 对，caption+numbers 反而错

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 数据集 | `FREDQA` |
| Case ID | `fredqa::811` |
| FREDQA 原始 idx | `811` |
| 变量数 / 序列长度 | `2` / `[12, 12]` |
| 问题类型 | `Causal Reasoning - Counterfactual` |
| 正确答案 | `A` |
| 失败/对比模式 | caption-only 对，caption+numbers 反而错 |
| 本 case 关注点 | 美墨净迁移镜像关系的反事实计算 |

变量摘要：

| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | Net migration for the United States | 12 | 1.83573e+06 | 4.77403e+06 | 1.55605e+06@1 | 8.85995e+06@7 | 370971 |
| 2 | Net migration for Mexico | 12 | -409085 | -300000 | -2.29647e+06@7 | -300000@11 | -8972.23 |

### 🖼 时序图

![FREDQA 811](https://raw.githubusercontent.com/Ringhu/LTSGen/fredqa-rerun-zh-20260512/docs/case-studies/20260512-fredqa-rerun-zh/figures/fredqa_811.png)


### ❓ QA 问题与中文翻译

**题干原文**

> You are a time series analysis expert. In a cross-border migration system, there are 2 metrics: Net migration for the United States (positive values mean more people entering than leaving)&lt;ts&gt;&lt;ts/&gt;; Net migration for Mexico (negative values mean more people leaving than entering)&lt;ts&gt;&lt;ts/&gt;. The metrics are 5-year estimates from 1962 to 2017. Key data points: 1992 U.S. net migration = 4,463,754, 1997 U.S. net migration = 8,859,954; 1992 Mexico net migration = -2,018,533, 1997 Mexico net migration = -2,296,470. From 1962–1992, U.S. net migration grew at an annual rate of 5.3%; between 1992–1997, this growth rate doubled to ~13% due to increased non-Mexican immigration (e.g., from Asia). Mexico’s net migration is historically a “mirror image” of the U.S.’s, meaning the ratio of Mexico’s net migration to the U.S.’s net migration remains relatively constant over time. If the 1992–1997 surge in U.S. net migration had not occurred (i.e., U.S. net migration continued growing at the 1962–1992 rate of 5.3% annually) and Mexico’s net migration had maintained its 1992 ratio to U.S. net migration, approximately how much higher or lower would Mexico’s 1997 net migration have been compared to its actual 1997 value?

**题干中文翻译**

> 你是一名时间序列分析专家。在一个跨境迁移系统中，有 2 个指标：美国的净迁移（正值表示进入人数多于离开人数）&lt;ts&gt;&lt;ts/&gt;；墨西哥的净迁移（负值表示离开人数多于进入人数）&lt;ts&gt;&lt;ts/&gt;。这些指标是 1962 年到 2017 年的 5 年估计值。关键数据点：1992 年美国净迁移 = 4,463,754，1997 年美国净迁移 = 8,859,954；1992 年墨西哥净迁移 = -2,018,533，1997 年墨西哥净迁移 = -2,296,470。从 1962 年到 1992 年，美国净迁移以每年 5.3% 的速度增长；在 1992 年到 1997 年之间，由于非墨西哥移民增加（例如来自亚洲），这一增长率翻了一番，约为 13%。墨西哥的净迁移在历史上是美国净迁移的“镜像”，这意味着墨西哥净迁移与美国净迁移的比率随时间保持相对恒定。如果 1992 年到 1997 年美国净迁移的激增没有发生（即美国净迁移继续以 1962 年到 1992 年每年 5.3% 的速度增长），并且墨西哥的净迁移维持其 1992 年相对于美国净迁移的比率，那么与其 1997 年的实际值相比，墨西哥 1997 年的净迁移大约会高多少或低多少？

**选项**

| 选项 | 原文 | 中文翻译 |
| --- | --- | --- |
| `A` | Actual Mexican net migration would be ~320,000 higher than counterfactual | 实际的墨西哥净迁移将比反事实情形高约 320,000 |
| `B` | Actual Mexican net migration would be ~320,000 lower than counterfactual | 实际的墨西哥净迁移将比反事实情形低约 320,000 |
| `C` | Actual Mexican net migration would be ~640,000 higher than counterfactual | 实际的墨西哥净迁移将比反事实情形高约 640,000 |
| `D` | Actual Mexican net migration would be ~640,000 lower than counterfactual | 实际的墨西哥净迁移将比反事实情形低约 640,000 |

**正确答案**：`A`

**标准解释原文**

> First, calculate the counterfactual 1997 U.S. net migration by extending the 1962–1992 5.3% annual growth rate: 4,463,754 * (1 + 0.053)^5 ≈ 5,777,629. Next, compute the 1992 ratio of Mexico’s to U.S.’s net migration: -2,018,533 / 4,463,754 ≈ -0.452. Apply this ratio to the counterfactual U.S. value to get Mexico’s counterfactual 1997 net migration: 5,777,629 * (-0.452) ≈ -2,612,644. Compare to actual 1997 Mexico net migration (-2,296,470): Actual minus counterfactual equals ~316,174, or ~320,000 higher. Counterfactually, if the U.S. surge (driven by non-Mexican immigration) had not occurred, Mexico’s net migration would have followed the mirror ratio and become more negative (lower). Since the surge was non-Mexican, Mexico’s actual net migration was less negative (higher) than the counterfactual.

**标准解释中文翻译**

> 首先，通过延续 1962 年到 1992 年每年 5.3% 的增长率，计算反事实的 1997 年美国净迁移：4,463,754 * (1 + 0.053)^5 ≈ 5,777,629。接下来，计算 1992 年墨西哥净迁移与美国净迁移的比率：-2,018,533 / 4,463,754 ≈ -0.452。将这一比率应用于反事实的美国数值，得到墨西哥反事实的 1997 年净迁移：5,777,629 * (-0.452) ≈ -2,612,644。与实际的 1997 年墨西哥净迁移（-2,296,470）相比：实际值减去反事实值等于约 316,174，即高约 320,000。反事实地说，如果美国的激增（由非墨西哥移民推动）没有发生，墨西哥的净迁移将会遵循镜像比率并变得更负（更低）。由于这一激增是非墨西哥来源，墨西哥的实际净迁移比反事实情形更不负（更高）。


### 📝 生成的 caption 与中文翻译

#### 变量 1：Net migration for the United States

**OpenTSLM caption 原文**

> The time series shows a strong seasonal pattern with a period of 4 quarters, and a high level of volatility. The overall trend is up then down then up, with a notable peak in the first half that is about 1.5 standard deviations above the mean, followed by a valley in the second half that is about 1.6 standard deviations below the mean. The net migration for the U.S. is strongly positively correlated with net migration for China and strongly negatively correlated with net migration for Mexico.

**OpenTSLM caption 中文翻译**

> 该时间序列表现出强烈的季节性模式，周期为 4 个季度，且波动性很高。整体趋势先上升后下降再上升，前半段有一个显著峰值，约比均值高 1.5 个标准差，随后在后半段出现一个谷值，约比均值低 1.6 个标准差。美国的净迁移与中国的净迁移强正相关，并且与墨西哥的净迁移强负相关。

**ChatTS caption 原文**

> The overall trend is increasing. The global maximum occurs at point 11, which is in the last third of the window. Short-term fluctuations are more pronounced in the first half (points 1–6) due to the spike there.

**ChatTS caption 中文翻译**

> 整体趋势是上升的。全局最大值出现在第 11 个点，位于窗口的后三分之一。短期波动在前半段（第 1–6 个点）由于那里出现的尖峰而更为明显。

#### 变量 2：Net migration for Mexico

**OpenTSLM caption 原文**

> The time series shows a strong seasonal pattern with a period of 4 quarters, and a high level of volatility. The overall trend is downward, with a significant net decrease of over 124% across the entire time span. The decline is most pronounced in the first half of the window, followed by a continued but slower decrease in the second half. There is a notable peak early in the window, about 1.6 standard deviations above the mean, and a deep valley late in the window, about 1.8 standard deviations below the mean. The data is strongly correlated with another variable, indicating a potential shared underlying economic factor.

**OpenTSLM caption 中文翻译**

> 该时间序列表现出强烈的季节性模式，周期为 4 个季度，且波动性很高。整体趋势向下，在整个时间跨度内累计净下降超过 124%。下降在窗口的前半段最为明显，随后在后半段继续下降但速度更慢。窗口前期有一个显著峰值，约比均值高 1.6 个标准差；窗口后期有一个深谷，约比均值低 1.8 个标准差。该数据与另一个变量强相关，表明可能存在共同的潜在经济因素。

**ChatTS caption 原文**

> The overall trend is steady. The global maximum occurs at point 9, which is in the first third of the 12-point window. The first half of the window (points 1-6) exhibits a significant downward spike with an amplitude of 1,570,538.74, whereas the second half (points 7-12) shows minimal variation. Therefore, the first half has larger short-term fluctuations.

**ChatTS caption 中文翻译**

> 整体趋势是平稳的。全局最大值出现在第 9 个点，位于 12 点窗口的前四分之一。窗口前半段（第 1-6 个点）出现了显著的向下尖峰，振幅为 1,570,538.74，而后半段（第 7-12 个点）变化很小。因此，前半段具有更大的短期波动。


### 🧪 下游 QA 模型答案 / 评分

表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。

| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |
| --- | --- | --- | --- | --- |
| 只给题目和选项 (`meta_only`) | `B` | `A` | ✗ 错误 | B |
| 题目 + 原始数值序列 (`numbers`) | `B` | `A` | ✗ 错误 | B |
| 题目 + OpenTSLM caption (`opentslm_caption`) | `A` | `A` | ✓ 正确 | A |
| 题目 + OpenTSLM caption + 数值 (`opentslm_caption_plus`) | `D` | `A` | ✗ 错误 | D |
| 题目 + ChatTS caption (`chatts_caption`) | `A` | `A` | ✓ 正确 | A |
| 题目 + ChatTS caption + 数值 (`chatts_caption_plus`) | `B` | `A` | ✗ 错误 | B |


### 🔎 Case 分析

- **答案格局**：`meta_only=B✗, numbers=B✗, opentslm_caption=A✓, opentslm_caption_plus=D✗, chatts_caption=A✓, chatts_caption_plus=B✗`。
- **关键问题**：OpenTSLM 和 ChatTS caption-only 都能答对，但加上数值后又失败，说明下游模型面对长题干、反事实增长率和原始数值时会出现证据整合不稳定；caption 有时像筛选后的线索，numbers 则增加了干扰。
- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。



## 全局 Case Study 分析

1. **FREDQA 的高 `meta_only` 准确率说明它并不纯粹是时序读取任务。** `meta_only` 已经达到 80.96%，604 条中有 489 条可以由题干、选项和领域常识先验答对。这意味着只看总体 QA accuracy 会严重高估模型从时间序列中提取证据的能力。

2. **过滤掉 meta-only 可答对样本后，失败更明显。** 在剩余 115 个 harder subset 中，`numbers` 只有 23.48%，`OpenTSLM caption` 只有 13.91%，`ChatTS caption` 只有 20.87%。这说明原始总体表里看似还不错的 80%+，大部分不是 caption 或 numbers 的贡献。

3. **当前 caption 训练失败的核心不是“语言不够流畅”，而是“证据不够任务化”。** OpenTSLM 和 ChatTS 大多能生成趋势、峰谷、波动、季节性等描述，但 FREDQA 经常需要指定月份/年份、窗口均值、比值、差值、反事实外推、干预前后比较，以及制度/宏观机制解释。通用 caption 没有保证这些证据被保留。

4. **OpenTSLM caption 的模板化问题更明显。** 多个 case 中 OpenTSLM 会重复生成 “steady upward trend / low volatility / strong seasonal pattern” 一类描述，即使问题真正需要局部日期计算。这会把 QA 模型从正确的局部证据带向全局形态概括。

5. **ChatTS 更简洁，但不是稳定上限。** ChatTS caption 在部分 counterfactual/interventional case 中能救回 meta-only，但 `chatts_caption_plus` 在 harder subset 中低于 `chatts_caption`，说明一旦同时给数值，QA 模型可能重新加权证据并被干扰。

6. **`numbers` 不是可靠 oracle。** 在 harder subset 中 `numbers` 也只有 23.48%，仍有 74 个样本所有非 meta 条件都答错。这说明长数值输入本身不会自动转化为正确计算；后续如果目标是可靠 QA，可能需要显式工具或结构化中间变量。

7. **对导师讨论最重要的结论**：目前训练路线没有失败在“caption 不能描述时序”，而是失败在“caption 没有按下游问题需要组织证据”。下一步应把 caption 目标从通用描述改成 task-aware evidence extraction，例如保留指定日期值、窗口统计、跨变量差/比值、反事实公式中间量，或让工具先计算这些中间量再交给 LLM 解释。

## 建议下一步

- 建一个 FREDQA evidence schema：每条 caption 不只写趋势，还必须写出题目中出现的日期/窗口/变量对应的数值、差值、比值和排序。
- 对 `both_caption_wrong_numbers_right` 的 13 个样本做 targeted caption 改写实验，验证只补充局部证据是否能救回 QA。
- 对 `meta_numbers_captions_all_wrong` 的 79 个样本拆分错误来源：公式执行失败、领域知识缺失、长题干定位失败、选项干扰。
- 增加一个 tool-assisted baseline：先从题目抽取需要计算的日期/窗口，再用 Python 计算中间量，最后让 LLM 只做解释和选项匹配。

