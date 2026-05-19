# Natural QA Balanced8 Case Study 分析报告（2026-05-19）

**对象:** `natural_multisim_v5_balanced8.jsonl`
**输入来源:** `multisim_qcc_v5_aiops_v3/case_study_simulator_data_20260518/raw_samples/balanced_eval_per_source8.jsonl`
**生成脚本:** `scripts/generate/build_natural_tsqa_balanced8.py`
**Reviewer 脚本:** `scripts/generate/review_natural_tsqa_balanced8.py`
**Reviewer 模型:** `gpt-5.5`，只评估自然性、可答性和风险，不决定 gold answer

## 1. 摘要结论

这批 case study 的核心目标，是把原先偏 `slot/verifier` 的时序 QA 改写成更像普通领域用户会问的问题，同时保持答案仍然可以由 deterministic support slots 复核。

最终结果：

| 指标 | 结果 |
| --- | ---: |
| 总样本数 | `48` |
| 来源域 | `6` |
| 每域抽样 | `8` |
| 进入自然 TS-QA candidate | `43` |
| metadata-only 排除 | `5` |
| GPT-5.5 reviewer 正例通过 | `43/43` |
| candidate 风险评级 | `43 low` |
| excluded 风险评级 | `5 high` |

主要判断：

- 自然化后的 43 条 candidate 已经能作为 case-study 正例池使用。问题不再只是证据槽位的拼接，而是被放进电网调度、建筑能耗控制、金融风险复盘、交通工程、供水运维和 SRE 排障等场景。
- 正确答案仍然不是由 LLM 判断。LLM 只负责改写和 review；gold answer 继续来自原始 support slots。
- AIOpsLab 中 5 条 metadata/provenance/fault-context 题被明确排除。这是必要的，因为它们依赖 official metadata，而不是单靠遥测时间序列可回答。
- lead-lag 类问题可以保留，但必须把滞后符号、零滞后比较和相关强度阈值写清楚。traffic lead-lag 是本轮最典型的 reviewer 驱动修复样本。

## 2. 为什么要重写这批问题

上一版 case study 暴露出几个问题：

1. 有些问题像从 support slots 里拼出来的校验句，而不是自然 QA。
2. 有些题面把内部 ID、窗口标签或局部/全局时间轴直接暴露给读者，例如 `post769_1025` 一类标签。
3. 一些问题只问时序统计本身，缺少领域背景和进一步推理语境。
4. lead-lag、counterfactual 和 regime 类任务如果缺少规则解释，很容易让读者无法判断选项边界。
5. AIOpsLab 的 metadata 题如果没有 metadata 表，不能伪装成纯时间序列问题。

本轮修复采用的策略是：

- 用 `scene` 承载领域背景、变量含义、时间轴和必要规则。
- 用 `question` 只问一个自然决策。
- 用 `options` 表达领域用户会选择的短答案。
- 用 `evidence` 保留足够少但可复核的数值证据。
- 用 GPT-5.5 reviewer 审查自然性和可答性，但不允许它改 gold answer。

## 3. Reviewer Gate

正例准入规则：

```text
review_scope == gpt55_candidate
decision == keep
naturalness_score >= 4
answerability_score >= 4
accuracy_risk == low
```

按来源统计：

| source | candidate | positive | 说明 |
| --- | ---: | ---: | --- |
| `aiopslab_official_v3` | 3 | 3 | 另外 5 条 metadata-only 被排除 |
| `citylearn` | 8 | 8 | 能耗负载、尖峰、波动、需求压力 |
| `finrl_scaled` | 8 | 8 | 价格、成交量、收益、回撤、市场状态 |
| `grid2op` | 8 | 8 | 负载压力、反事实断线、lead-lag、波动 |
| `traffic` | 8 | 8 | 车速、排队、信号策略、周期性 |
| `water` | 8 | 8 | 水压、流量、漏水反事实、恢复和韧性 |

Reviewer 仍保留了一些轻微问题标签，例如 `minor_variable_notation`、`lead_lag_requires_rule`、`slightly_rule_based_wording`。这些不是阻断项，但它们提示后续大规模生成时要继续减少 `x0/x1/x2` 的露出比例，并把规则更自然地写进场景。

## 4. 各域 Case Study 分析

### 4.1 AIOpsLab official v3: SRE 排障问题必须区分遥测和 metadata

AIOpsLab 是这批样本里边界最清楚的来源。它既有可由遥测窗口回答的问题，也有只能由 official metadata 回答的问题。

#### Case A: 内存压力是否前后相近

**Task:** `aiops_official_window_memory`
**问题:** 按 5% 相对差异规则，这个事故窗口中的服务内存占用是前后相近，还是某一半更重？
**选项:** 前后两半相近 / 前半段更高 / 后半段更高 / 无法判断
**答案:** 前后两半相近
**证据:** 前半段内存均值为 `797,644.80`，后半段均值为 `801,177.60`。按 5% 相对差异规则，两者应视为相近。

分析：

- 原始统计比较被改写成 SRE 对事故窗口的内存压力判断。
- 5% 规则写在问题和证据中，避免“相近”变成未定义的主观词。
- 这是可保留的纯遥测题，因为答案来自内存时间序列的窗口统计。

#### Case B: 网络接收速率哪段波动最大

**Task:** `aiops_official_network_volatility`
**问题:** 运维人员应该把窗口的哪一段视为网络接收速率波动最大的部分？
**选项:** 中期 / 后期 / 三段相近 / 早期
**答案:** 早期
**证据:** 窗口按时间三等分后比较标准差，结果选择早期。

分析：

- 这个问题仍然是统计型，但它被放进运维排查语境中，读起来像“应该重点检查哪一段网络波动”。
- Reviewer 给出 naturalness `5`、answerability `5`，说明这类窗口波动问题是 AIOps 遥测里的可用正例。

#### 排除边界

以下 AIOpsLab 任务被排除：

- `aiops_official_app_context`
- `aiops_official_case_provenance_context`
- `aiops_official_service_role_context`
- `aiops_official_fault_family_detail_context`
- `aiops_official_fault_context`

排除理由：这些题问的是 official app、case provenance、service role 或 fault metadata。若不给 metadata 表，模型不能只靠 CPU/内存/网络时间序列可靠回答。把它们保留为纯 TS-QA 正例会制造隐藏上下文错误。

### 4.2 CityLearn: 从负载统计转成能耗控制决策

CityLearn 的改写重点，是让问题不只问“x0 在哪段更高”，而是变成建筑控制器可理解的需求压力、尖峰和调度判断。

#### Case A: 建筑需求压力状态

**Task:** `city_domain_demand_context`
**问题:** 按照需求压力分档规则，建筑控制器应把这个窗口视为什么需求压力状态？
**选项:** 高建筑需求压力 / 低建筑需求压力 / 中等建筑需求压力 / 需求压力不清楚
**答案:** 中等建筑需求压力
**证据:** 平均负载 `5.07`，峰值负载 `12.04`。规则为平均负载至少 8 或峰值至少 16 时为高压；平均低于 3 且峰值低于 8 时为低压；否则为中等需求压力。

分析：

- 这是比纯时序统计更好的 QCC case。模型必须结合领域场景、阈值规则和窗口统计做判断。
- 证据短，但足以复核答案。
- Reviewer 认为 x2 的 solar/context 均值与本题无关，但不影响答案。这提示后续可以为每题隐藏无关变量解释，或让 scene 更聚焦。

#### Case B: 建筑用电孤立尖峰位置

**Task:** `city_anomaly_total_load`
**问题:** 把这个窗口按时间分成早期、中期和后期后，最明显的建筑用电需求孤立尖峰出现在什么位置？
**选项:** 早期 / 中期 / 后期 / 没有明显尖峰
**答案:** 后期
**证据:** 尖峰检测器使用绝对 z 分数 `3` 作为明显尖峰阈值；最强候选尖峰绝对 z 分数为 `3.51`，位置在窗口后段。

分析：

- 该题不只是问最高值位置，而是问异常检测结果。
- 阈值明确，避免“明显尖峰”成为主观判断。
- 适合作为 QCC 中“时序证据加领域判断规则”的正例。

### 4.3 FinRL: 避免“ticker 由问题指定”的不自然表达

FinRL 的修复重点，是把 `x0` 明确成某个 ticker 的历史价格序列，并把市场状态、回撤、成交量尖峰等问题写成金融分析语境。

#### Case A: GOOG 市场状态

**Task:** `fin_domain_market_regime`
**问题:** 先看总收益、再用波动率辅助判断，GOOG 在这段时间最符合哪种市场状态？
**选项:** 熊市/下行状态 / 牛市/上行状态 / 高波动横盘状态 / 低波动横盘状态
**答案:** 牛市/上行状态
**证据:** 总收益率 `18.51%`，收益波动率 `0.018`。规则为总收益率 `>= 5%` 归为牛市/上行，`<= -5%` 归为熊市/下行；介于其间再用波动率区分横盘状态。

分析：

- 这是用户前面要求的“必须结合背景知识和时序数据进一步推理”的典型样本。
- 问题不再说“股票代码由问题指定”，而是直接把 GOOG 放进场景。
- 选项都是金融分析中的自然类别，而不是 slot label。

#### Case B: MRK 回撤风险

**Task:** `fin_drawdown_price`
**问题:** 按照回撤分档规则，MRK 在这个窗口中的价格回撤应归为哪一类？
**选项:** 中等回撤 / 轻微回撤 / 严重回撤 / 回撤很小
**答案:** 严重回撤
**证据:** 回撤分档规则为小于 `5%` 为回撤很小，`5%-15%` 为轻微回撤，`15%-30%` 为中等回撤，超过 `30%` 为严重回撤。该窗口最大回撤为 `36.65%`。

分析：

- 该题要求模型理解回撤分档，而不是只复述一个最大值。
- 证据中给出阈值和数值，答案完全可复核。
- 适合作为金融域 case study，因为它比“最高点在哪段”更像真实风险复盘问题。

### 4.4 Grid2Op: 时间轴和反事实语义必须写进场景

Grid2Op 的自然化难点主要有两个：局部窗口和全局事件时间不一致，以及反事实轨迹的含义容易被误读。

#### Case A: 断线反事实压力影响

**Task:** `grid_counterfactual_peak_stress`
**问题:** 在这个事件后窗口里，断开线路对最大线路负载压力的主要影响是什么？
**选项:** 断线后压力更低 / 断线前后压力基本相同 / 断线后压力更高 / 无法判断
**答案:** 断线后压力更高
**证据:** 干预后与事实运行的压力差值范围为 `0.37` 到 `0.56`，因此断线后压力更高。

分析：

- 原始问题直接暴露 `global step 512` 和 `post769_1025`。自然化后，局部窗口和事件后关系放进 scene，问题只问调度员真正关心的影响。
- 反事实语义明确为“干预后减事实运行”。这解决了“断线前后”与“干预/事实对照”混淆的问题。
- Reviewer 仍指出选项 B 的中文“断线前后压力基本相同”可能被误读。后续大规模生成中建议统一写成“与事实运行相比基本没有变化”。

#### Case B: 总需求和线路压力是否有领先关系

**Task:** `grid_temporal_lead_lag`
**问题:** 总需求和最大线路负载压力之间是否表现出清晰的先后关系？
**选项:** 最大线路负载压力领先总需求 / 总需求领先最大线路负载压力 / 同步变化，没有稳定领先方 / 相关性太弱，无法判断先后
**答案:** 同步变化，没有稳定领先方
**证据:** 最强候选滞后为 `0`，相关系数为 `0.87`。

分析：

- 这条样本回应了前面“图上领先滞后接近，模型能不能答对”的问题。自然化后不强行让模型从图像感知里猜 lead-lag，而是在场景中说明 lag 0 表示同步变化。
- 该题适合作为“lead-lag 边界 case”。它不是因为某个变量明显领先，而是因为最强关系就在零滞后。
- 大规模扩展时，lead-lag 题应优先保留分离明显或规则清楚的样本，弱分离样本需要 reviewer gate。

### 4.5 Traffic: lead-lag 需要绝对相关强度和稳定性余量

Traffic 是本轮 reviewer 最有价值的修复来源。初版 traffic lead-lag 被 reviewer 标为 revise/medium risk，原因是负相关时“相关低于 0.35”的表述容易被误解。修复后改成“绝对相关强度”，并明确最强滞后相对同步关系的提升幅度。

#### Case A: 车速和排队是否有稳定先后关系

**Task:** `traffic_speed_queue_lead_lag`
**问题:** 车速变化和排队长度变化之间是否表现出清晰的先后关系？
**选项:** 车速变化领先排队变化 / 排队变化领先车速变化 / 相关性低于可用阈值 / 没有稳定的方向性领先
**答案:** 没有稳定的方向性领先
**证据:** 最强滞后为 `-3`，相关系数为 `-0.46`；同步相关系数为 `-0.44`。绝对相关强度只提升了 `0.02`，低于 `0.05` 的稳定性余量。

分析：

- 该题不是简单问“谁先谁后”，而是要求判断滞后关系是否稳定。
- 负相关不代表“弱相关”，所以证据必须用绝对相关强度。
- Reviewer 修复前后的差异说明，引入 reviewer 是必要的：它能抓到人类读者容易误解的数学措辞。

#### Case B: 自适应信号是否改善排队

**Task:** `traffic_signal_counterfactual_queue`
**问题:** 与固定信号基线相比，自适应信号策略是否改善了排队？
**选项:** 自适应信号下队列更低 / 没有实质队列变化 / 混合影响 / 自适应信号下队列更高
**答案:** 自适应信号下队列更高
**证据:** 自适应信号平均队列为 `2.91`，固定基线为 `2.56`。

分析：

- 这是交通域更自然的反事实 policy case。问题不是“factual_mean 和 counterfactual_mean 谁大”，而是“策略是否改善排队”。
- 答案需要知道队列长度越低越好，属于轻量领域背景加时序统计的推理。
- Reviewer 提醒“没有实质队列变化”最好有阈值。虽然本例差异方向明确，但后续模板应为 material/no-material 选项统一写阈值。

### 4.6 Water: 供水状态题适合作为领域推理正例

Water 域的优势是问题天然接近运维判断，例如低压风险、漏水影响、恢复状态和综合压力。

#### Case A: 综合压力状态

**Task:** `water_combined_stress_context`
**问题:** 按照综合压力评分规则，这个供水服务窗口最可能处于哪种运行状态？
**选项:** 严重综合压力 / 稳定综合状态 / 中等综合压力 / 综合状态不清楚
**答案:** 中等综合压力
**证据:** 综合压力分数为 `-66.31`，事件位于中期，严重低压标记为 `false`。规则为评分低于 `-50` 且窗口中段出现事件时，如果严重低压标记为 false，则归为中等综合压力。

分析：

- 该题结合了多个证据槽：压力评分、事件时段、严重低压标记。
- 它比单变量 extrema 更接近真实供水运维判断。
- 规则仍偏显式，但对于可验证 benchmark 是可接受的。

#### Case B: 事件后水压恢复状态

**Task:** `water_event_recovery_context`
**问题:** 按照事件前、中、后三阶段均值规则，事件后的水压状态最符合哪一种判断？
**选项:** 水压恢复 / 水压过冲 / 持续水压压力 / 没有事件恢复
**答案:** 水压过冲
**证据:** 事件前均值 `74.77`，事件中均值 `74.75`，事件后均值 `74.83`。规则为事件后均值只要高于事件前均值，就视为水压过冲。

分析：

- 该题要求模型比较事件前、中、后三段，而不是只定位一个点。
- “水压过冲”是有领域含义的状态词，但证据中给出判定规则，保证答案可验证。
- Reviewer 认为措辞略像规则题。后续可以把问题改成“事件后是否恢复到正常水平、过冲，还是仍偏低”，自然性会更好。

## 5. 跨域质量变化

### 5.1 从统计句改成领域决策

修复前的问题常见形式是：

```text
Which third has the highest volatility in x0?
What drawdown regime best describes target price x0?
Does speed movement lead queue movement?
```

修复后的问题更接近：

```text
建筑控制器应把这个窗口视为什么需求压力状态？
GOOG 在这段时间最符合哪种市场状态？
与固定信号基线相比，自适应信号策略是否改善了排队？
```

这种变化对 QCC 很关键。Captioner 不只是要转述统计值，而是要生成能支持领域判断的 evidence caption。

### 5.2 可验证性没有被牺牲

自然化以后，每道题仍保留：

- 原始 `id`
- `support_slots`
- 原始问题和选项
- gold answer letter
- gold answer label
- 中英文场景、问题、选项、证据
- reviewer decision 和风险评级

这意味着自然化不是“让 LLM 自由改题”，而是把 deterministic evidence 换成更自然的用户界面。

### 5.3 Reviewer 最有用的地方

Reviewer 在本轮主要抓到三类问题：

1. **hidden metadata:** AIOps official metadata 题不能作为纯 TS-QA。
2. **threshold ambiguity:** material、similar、weak、pronounced 等词必须给阈值或明显数值证据。
3. **lead-lag ambiguity:** 如果滞后相关和同步相关接近，必须说明选择 no-stable-lead 的规则。

这些问题靠单纯 lint 很难完全发现。Reviewer 适合作为自然性和读者可理解性的质量门。

## 6. 当前正例池可以怎么用

建议用途：

- 作为论文或内部汇报中的自然 TS-QA case study 样例池。
- 作为下一轮大规模生成规则的 golden pilot。
- 作为 QCC captioner 的定性评估集，检查 caption 是否提供了足够 evidence。
- 作为 reviewer prompt 的回归集，后续模板改动后重新跑 reviewer gate。

不建议用途：

- 不要把 5 条 metadata-only 排除样本混进纯 TS-QA 训练正例。
- 不要把 lead-lag 样本无限扩展到视觉上不可分、证据也不清楚的窗口。
- 不要只用 FinRL 扩量来证明 simulator 泛化。FinRL 更像历史市场 trace，不是因果交互仿真器。

## 7. 后续建议

1. 把这 43 条作为 `natural_qa_balanced8` 的正例池，人工再挑 12-18 条进入论文 case study。
2. 对每个域优先保留至少一种“领域规则加时序证据”的题型：
   - CityLearn: demand pressure、spike detection
   - FinRL: market regime、drawdown
   - Grid2Op: counterfactual stress、lead-lag boundary
   - Traffic: signal policy counterfactual、lead-lag stability
   - Water: combined stress、event recovery
   - AIOpsLab: memory pressure、network volatility
3. 大规模生成时，把 reviewer 的轻微标签转成模板规则：
   - material/no-material 必须有阈值。
   - weak/similar 必须有阈值或明显数值间隔。
   - lead-lag 必须说明 lag 符号和零滞后比较。
   - counterfactual 必须说明差值方向。
   - metadata-only 必须进入独立 metadata QA，不进入纯 TS-QA。
4. 下一步可以生成一个更大的自然化批次，例如每域 50-100 条，然后按同一 reviewer gate 筛选正例池。

## 8. 产物索引

| 类型 | 路径 |
| --- | --- |
| 自然化 QA JSONL | `.research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/natural_multisim_v5_balanced8.jsonl` |
| Lint JSON | `.research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/natural_multisim_v5_balanced8_lint.json` |
| Lint 报告 | `.research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/NATURAL_QA_BALANCED8_LINT_20260519_ZH.md` |
| Reviewer JSON | `.research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/natural_multisim_v5_balanced8_review.json` |
| Reviewer 报告 | `.research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/NATURAL_QA_BALANCED8_REVIEW_20260519_ZH.md` |
| 本分析报告 | `.research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/NATURAL_QA_BALANCED8_CASE_STUDY_ANALYSIS_20260519_ZH.md` |

