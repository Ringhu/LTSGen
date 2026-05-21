# Self-contained Reasoning TSQA 生成数据 Case Study（2026-05-21）

本报告盘点当前 `self_contained_reasoning_qa_v2_20260521` 这批生成数据的代表样例，目标是说明目前数据已经从早期的 “slot/value lookup” 转向更接近 benchmark 可用的自然 QA：题面自足、变量含义明确、答案由 simulator/trace 派生量确定，reviewer 可以审核自然性和可答性，但不能改 gold。

## 1. 数据位置与范围

**数据目录:** `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/`

**核心文件:**

| 文件 | 作用 |
| --- | --- |
| `self_contained_reasoning_tsqa.jsonl` | 主数据，每行包含 scene、variables、decision rule、question、options、values、support slots 和 gold |
| `self_contained_reasoning_tsqa_sft.jsonl` | SFT/对话格式导出 |
| `self_contained_reasoning_tsqa_summary.json` | 本地 schema/gate 汇总 |
| `self_contained_reasoning_tsqa_gpt_data_only_probe.json` | data-only GPT probe 原始结果 |
| `SELF_CONTAINED_REASONING_TSQA_GPT_DATA_ONLY_PROBE_20260521_ZH.md` | probe 报告 |
| `SELF_CONTAINED_REASONING_TSQA_V2_GENERATION_SPEC_20260521_ZH.md` | 当前生成规范 |

**生成脚本:** `scripts/generate/build_self_contained_reasoning_tsqa.py`

**评测 probe:** `scripts/eval/probe_self_contained_reasoning_tsqa_llm.py`

## 2. 数据集概况

当前 v2 是一个 seed/case-study 级别的数据资产，不是最终 benchmark release。

| 维度 | 当前状态 |
| --- | --- |
| rows | `60` |
| domains | `grid2op`, `citylearn`, `traffic`, `water`, `aiopslab`, `finrl` |
| 每个 domain 数量 | `10` |
| task families | 每个 domain 1 个 self-contained reasoning task |
| solver values | `compact_block_physical_features` |
| local schema gate | pass |
| answer distribution | `A=31`, `B=5`, `C=8`, `D=16` |
| data-only GPT probe | strict/semantic accuracy = `0.75` |

这批数据的关键变化不是规模，而是输入形态：

- 题面显式给出 domain 场景、变量含义、窗口切分方式和决策规则。
- `values` 给模型的是物理量/派生量压缩表，不再要求模型理解 z-score 或 simulator 内部字段。
- `support_slots` 仍保留为审计依据，但不作为答题所需的隐藏信息。
- negative class 和 rule precedence 被写进题面，避免模型在阈值未满足时强行选择最像的正类。

## 3. Case Study 选择原则

下面 6 个 case 每个 domain 选 1 条，优先选择 data-only probe 中回答正确、证据链清楚的样本。每个 case 都保留以下字段：

- **Scene:** 自足背景，不要求知道具体 simulator。
- **Variables:** `x0/x1/...` 的业务含义。
- **Decision rule:** gold 的 deterministic 映射规则。
- **Question + options:** 自然决策型四选一问题。
- **Gold + evidence:** 由 trace 派生量计算得到。
- **Support slots:** 审计用数值，不由 LLM 决定。
- **Probe note:** 当前 data-only GPT probe 的表现。

## 4. Case 1: Grid2Op 计划断线风险判断

**Domain/source:** `grid2op`  
**Task family:** `self_contained_grid_counterfactual_risk`  
**Row ID:** `scenario_first_pilot::grid2op::line_disconnection::000::grid_line_disconnection_counterfactual_risk`

**Scene EN:** A power-grid operator is comparing a planned line-outage run with a matched normal run. No platform-specific prior knowledge is needed: x0 is the outage-minus-normal stress difference at each step, so positive x0 means the outage is more stressful and negative x0 means it is less stressful.

**场景中文:** 电网调度员正在比较一次计划断线运行和匹配的正常运行。无需了解任何特定平台背景：x0 是每个时间步的“断线运行减正常运行”的压力差，x0 为正表示断线更紧张，x0 为负表示断线更安全。

**Variables / 变量:**

- `x0`: 分块平均断线减正常压力差
- `x1`: 分块中差值大于 `+0.05` 的比例
- `x2`: 分块中差值小于 `-0.05` 的比例
- `x3`: 分块最大绝对压力差

**Decision rule / 决策规则:** 跨压缩行计算 `x0` 均值、`x1` 均值、`x2` 均值和 `x3` 最大值。若 `x0_mean >= +0.05` 且 `x1_mean >= 0.80`，选风险上升；若 `x0_mean <= -0.05` 且 `x2_mean >= 0.80`，选风险下降；若 `|x0_mean| <= 0.02` 且 `max_x3 <= 0.03`，选风险基本不变；否则选人工复核。

**Question EN:** Using the rule and the x0 series, what should the operator conclude about the planned outage?  
**问题中文:** 根据规则和 x0 序列，调度员应如何判断这次计划断线的影响？

**Options / 选项:**

- A. risk increases / 风险上升
- B. risk decreases / 风险下降
- C. risk is broadly unchanged / 风险基本不变
- D. manual review needed / 需要人工复核

**Gold:** `C` / 风险基本不变

**Evidence EN:** Mean x0 is `-0.01`, with `0.0%` of steps above `+0.05` and `0.0%` below `-0.05`; the rule maps this to risk is broadly unchanged.

**证据中文:** x0 均值为 `-0.01`，大于 `+0.05` 的时间步占 `0.0%`，小于 `-0.05` 的时间步占 `0.0%`；按规则判断为：风险基本不变。

**Support slots:** `x0_mean=-0.0059894895`, `frac_gt_pos_0_05=0.0`, `frac_lt_neg_0_05=0.0`, `max_abs_x0=0.0065343014`, `answer_label=risk is broadly unchanged`

**Compact values excerpt:** first rows are close to zero: `x0=-0.0053, -0.0055, -0.0057, -0.0060`; no row shows material positive or negative stress shift.

**Probe note:** data-only GPT probe returned `C` and correctly applied the “broadly unchanged” rule.

**Case value:** 这是最干净的 counterfactual case。它不要求懂 Grid2Op，只要理解 `outage-minus-normal` 的方向性和阈值规则即可。

## 5. Case 2: CityLearn 建筑供能预留窗口

**Domain/source:** `citylearn`  
**Task family:** `self_contained_building_net_load_reserve`  
**Row ID:** `scenario_first_pilot::citylearn::demand_response_reserve::001::citylearn_reserve_planning_from_controlled_peak`

**Scene EN:** A building energy planner is deciding when to reserve supply for a 256-step operating window. No platform-specific prior knowledge is needed. x0 is building demand, x2 is local solar support, and net grid load is defined here as x0 - 0.15*x2.

**场景中文:** 建筑能耗规划员需要为一个 256 步运行窗口安排供能预留。无需了解任何特定平台背景。x0 是建筑用电需求，x2 是本地太阳能支持；这里定义净电网负荷为 `x0 - 0.15*x2`。

**Variables / 变量:**

- `x0`: 分块平均建筑用电需求
- `x1`: 分块平均天气上下文
- `x2`: 分块平均本地太阳能支持
- `x3`: 分块平均净电网负荷

**Decision rule / 决策规则:** 把压缩行分成早段、中段、后段，比较三段 `x3` 均值。若最高一段比第二高至少高 `0.30`，就为该段预留供能；否则选择均衡供能。

**Question EN:** Using the net-load rule, when should supply be reserved for this window?  
**问题中文:** 根据净负荷规则，这个窗口应在哪个时段优先预留供能？

**Options / 选项:**

- A. reserve early / 优先为早段预留供能
- B. reserve middle / 优先为中段预留供能
- C. reserve late / 优先为后段预留供能
- D. balanced reserve / 按均衡供能准备

**Gold:** `D` / 按均衡供能准备

**Evidence EN:** Mean net loads for early, middle, and late thirds are `5.33`, `4.75`, and `5.26`; the top-vs-second gap is only `0.075`, below `0.30`.

**证据中文:** 早段、中段、后段平均净负荷分别为 `5.33`、`4.75`、`5.26`；最高段与第二高段差距只有 `0.075`，低于 `0.30`，因此按均衡供能准备。

**Support slots:** `early_net_mean=5.3318978584`, `middle_net_mean=4.7460750942`, `late_net_mean=5.2566785898`, `gap_top_second=0.0752192686`, `answer_label=balanced reserve`

**Compact values excerpt:** 前 4 个块的 `x3` 为 `5.53, 4.79, 5.20, 5.80`；后段也有高值，但总体第三均值没有形成足够差距。

**Probe note:** data-only GPT probe returned `D` and reproduced the three段均值计算。

**Case value:** 该 case 测的是“分段聚合 + margin threshold”。它比直接问最大值更自然，也能暴露模型是否会在差距不足时误选最高段。

## 6. Case 3: Traffic 事件后拥堵恢复判断

**Domain/source:** `traffic`  
**Task family:** `self_contained_traffic_recovery_reasoning`  
**Row ID:** `scenario_first_pilot::traffic::signal_policy_comparison::002::traffic_signal_policy_counterfactual_queue`

**Scene EN:** A traffic analyst is reviewing one road segment over time. No traffic-platform prior knowledge is needed. x0 is mean speed, x1 is queue length, and x2 is lane occupancy. Higher queue and occupancy are worse; higher speed is better.

**场景中文:** 交通分析员正在查看一段道路的时间序列。无需了解任何特定交通平台背景。x0 是平均车速，x1 是排队长度，x2 是车道占有率。队列和占有率越高越差，车速越高越好。

**Variables / 变量:**

- `x0`: 分块平均车速
- `x1`: 分块平均排队长度
- `x2`: 分块平均车道占有率
- `x3`: 分块平均拥堵分数，定义为 `x1 + 8*x2 - 0.05*x0`

**Decision rule / 决策规则:** 把压缩行分成事件前、事件中、事件后三段。先检查事件中 `x3` 均值是否比事件前高出 `0.50` 以上。若没有，直接选“没有清晰拥堵冲击”，不再判断恢复类别；只有事件中升高超过阈值时，才判断恢复、持续或部分恢复。

**Question EN:** Using the congestion-score rule, what happened after the event phase?  
**问题中文:** 根据拥堵分数规则，事件阶段之后交通状态如何变化？

**Options / 选项:**

- A. no clear congestion shock / 没有清晰拥堵冲击
- B. congestion recovers / 拥堵恢复
- C. partial recovery / 部分恢复
- D. congestion persists / 拥堵持续

**Gold:** `A` / 没有清晰拥堵冲击

**Evidence EN:** Mean congestion scores for pre-event, event, and post-event thirds are `6.50`, `6.63`, and `6.70`. Event is only `0.13` above pre-event, below the `0.50` shock threshold.

**证据中文:** 事件前、事件中、事件后平均拥堵分数分别为 `6.50`、`6.63`、`6.70`。事件中只比事件前高 `0.13`，低于 `0.50` 的冲击阈值，所以直接判为没有清晰拥堵冲击。

**Support slots:** `pre_score_mean=6.4997979772`, `event_score_mean=6.6256620133`, `post_score_mean=6.6999616010`, `answer_label=no clear congestion shock`

**Compact values excerpt:** 前 4 个块的 `x3` 为 `6.78, 5.64, 6.46, 7.12`；事件阶段均值没有超过冲击阈值。

**Probe note:** data-only GPT probe returned `A` and correctly停止后续恢复判断。

**Case value:** 该 case 的关键是 rule precedence。模型不能看到 post-event 仍高就直接选“持续”或“部分恢复”，必须先判断事件冲击是否成立。

## 7. Case 4: Water 供水服务状态判断

**Domain/source:** `water`  
**Task family:** `self_contained_water_service_recovery`  
**Row ID:** `scenario_first_pilot::water::leak_event_service_state::021::water_leak_event_service_state`

**Scene EN:** A water-service operator is reviewing pressure and flow over one service window. No water-platform prior knowledge is needed. x0 is pressure and x1 is pipe flow. A leak-like event usually lowers pressure while increasing flow.

**场景中文:** 供水服务运维人员正在查看一个服务窗口中的水压和流量。无需了解任何特定水网平台背景。x0 是水压，x1 是管道流量。类似漏水的事件通常会降低水压并提高流量。

**Variables / 变量:**

- `x0`: 分块平均服务水压
- `x1`: 分块平均管道流量
- `x2`: 分块最低水压

**Decision rule / 决策规则:** 把压缩行分成事件前、事件中、事件后三段。按顺序判断：持续漏水压力风险、扰动后水压恢复、服务稳定、人工复核。若前面规则满足，后面的规则不再应用。

**Question EN:** Using the pressure-flow recovery rule, what service state should be reported?  
**问题中文:** 根据水压-流量恢复规则，应报告哪种供水服务状态？

**Options / 选项:**

- A. persistent leak pressure risk / 持续漏水压力风险
- B. pressure recovers after disturbance / 扰动后水压恢复
- C. stable service / 服务稳定
- D. manual review needed / 需要人工复核

**Gold:** `C` / 服务稳定

**Evidence EN:** Pre/event/post pressure means are `71.28`, `71.16`, and `72.35`; minimum pressure is `66.21` and event flow increase is `-0.05`. No leak or recovery threshold is triggered, and post-event pressure is within the stable range.

**证据中文:** 事件前/中/后水压均值为 `71.28`、`71.16`、`72.35`；最低水压为 `66.21`，事件中流量增幅为 `-0.05`。漏水和恢复阈值都没有触发，事件后水压与事件前接近，因此服务稳定。

**Support slots:** `pre_pressure_mean=71.2774608324`, `event_pressure_mean=71.1595424588`, `post_pressure_mean=72.3457677312`, `min_pressure=66.2071567125`, `event_flow_increase=-0.0508939416`, `answer_label=stable service`

**Compact values excerpt:** 前 4 个块水压为 `69.48, 68.17, 72.74, 74.72`；最低分块压力仍为 `66.21`，未触发低压风险。

**Probe note:** data-only GPT probe returned `C` for this sample。但整体 water domain 只有 `4/10` 正确，是当前最需要 reviewer 修正规则表达的 domain。

**Case value:** 该 case 展示了供水任务可做成自然运维判断，但 water rule 的优先级和阈值较复杂，容易让模型把“稳定”和“恢复”混淆。

## 8. Case 5: AIOpsLab SRE 症状排障

**Domain/source:** `aiopslab`  
**Task family:** `self_contained_aiops_symptom_triage`  
**Row ID:** `scenario_first_pilot::aiopslab::incident_fault_injection::004::aiops_incident_dominant_symptom`

**Scene EN:** An SRE is triaging one service telemetry window. No platform-specific prior knowledge is needed. x0 is CPU load, x1 is memory working set, x2 is network receive rate, and x3 is network transmit rate.

**场景中文:** SRE 正在排查一个服务遥测窗口。无需了解任何特定平台背景。x0 是 CPU 负载，x1 是内存工作集，x2 是网络接收速率，x3 是网络发送速率。

**Variables / 变量:**

- `x0`: 分块 CPU 最大负载
- `x1`: 分块平均内存工作集
- `x2`: 分块接收速率峰值/中位数
- `x3`: 分块发送速率峰值/中位数

**Decision rule / 决策规则:** 若 `x1` 后半段均值比前半段增长至少 `15%`，选内存泄漏模式；否则若 `x2` 或 `x3` 最大值至少 `2.5`，选网络突发模式；否则若 `x0` 最大值至少 `0.85`，选 CPU 饱和模式；否则选没有主导症状。内存规则优先。

**Question EN:** Using the triage rule, which symptom should the SRE prioritize?  
**问题中文:** 根据排障规则，SRE 应优先关注哪种症状？

**Options / 选项:**

- A. memory leak pattern / 内存泄漏模式
- B. network burst pattern / 网络突发模式
- C. cpu saturation pattern / CPU 饱和模式
- D. no dominant symptom / 没有主导症状

**Gold:** `D` / 没有主导症状

**Evidence EN:** Memory changes from `9663229.95` to `9557010.61` (`-1.1%`), receive peak/median is `1.51`, transmit peak/median is `1.48`, and max CPU is `0.43`; no threshold is met.

**证据中文:** 内存均值从 `9663229.95` 变为 `9557010.61`（`-1.1%`），接收峰值/中位数为 `1.51`，发送峰值/中位数为 `1.48`，CPU 最大值为 `0.43`；所有正类阈值都未触发，因此没有主导症状。

**Support slots:** `memory_first_half_mean=9663229.94833505`, `memory_second_half_mean=9557010.608610492`, `memory_growth_ratio=-0.0109921155`, `rx_peak_median_ratio=1.5128212896`, `tx_peak_median_ratio=1.4750458250`, `cpu_max=0.4260868714`, `answer_label=no dominant symptom`

**Compact values excerpt:** CPU 最大值始终远低于 `0.85`；网络峰值/中位数低于 `2.5`；内存没有增长。

**Probe note:** data-only GPT probe returned `D` and explained that no threshold was triggered。

**Case value:** 该 case 很适合保留 negative class，因为它检查模型是否会在没有阈值触发时硬选“最像”的 A/B/C。

## 9. Case 6: FinRL 收益率与最大回撤分类

**Domain/source:** `finrl`  
**Task family:** `self_contained_finrl_return_drawdown_regime`  
**Row ID:** `scenario_first_pilot::finrl::market_regime_review::005::finrl_controlled_market_regime_review`

**Scene EN:** A market analyst is reviewing one asset price window. No platform-specific prior knowledge is needed. x0 is asset price, x1 is a market context indicator, and x2 is trading volume.

**场景中文:** 市场分析师正在查看一个资产价格窗口。无需了解任何特定平台背景。x0 是资产价格，x1 是市场背景指标，x2 是交易量。

**Variables / 变量:**

- `x0`: 分块收盘资产价格
- `x1`: 分块平均市场背景指标
- `x2`: 分块平均交易量
- `x3`: 分块最低资产价格

**Decision rule / 决策规则:** 计算总收益率 `last_x0 / first_x0 - 1`，并基于历史峰值计算最大回撤。若最大回撤 `<= -20%`，优先选严重回撤风险；否则按总收益率分类：`>= +8%` 为上行，`<= -8%` 为下行，其余为横盘。

**Question EN:** Using return and maximum drawdown, how should this price window be classified?  
**问题中文:** 根据总收益率和最大回撤，这段价格窗口应如何分类？

**Options / 选项:**

- A. bullish regime / 上行状态
- B. bearish regime / 下行状态
- C. sideways regime / 横盘状态
- D. severe drawdown risk / 严重回撤风险

**Gold:** `A` / 上行状态

**Evidence EN:** Total return is `83.7%` and maximum drawdown is `-5.0%`; severe drawdown does not trigger, and return is above `+8%`.

**证据中文:** 总收益率为 `83.7%`，最大回撤为 `-5.0%`；严重回撤阈值未触发，收益率超过 `+8%`，因此为上行状态。

**Support slots:** `total_return=0.8370901431`, `max_drawdown=-0.0496494173`, `answer_label=bullish regime`

**Compact values excerpt:** 第一个 `x0=100.0`，最后一个 `x0=183.709`；最大回撤约 `-5.0%`。

**Probe note:** data-only GPT probe returned `A` and correctly handled the condition “drawdown has priority, but the drawdown threshold is not triggered”。

**Case value:** 该 case 是金融任务里比较自然的一类：不是问单点数值，而是把收益率和风险阈值合成一个 regime 判断。

## 10. 跨 case 观察

### 10.1 当前数据已经具备 benchmark seed 的形态

这些 case 体现了 benchmark generation 的核心想法：simulator/trace 负责产生可复现时序与派生量，生成器把它们转成自然决策问题，gold 由 deterministic support slots 映射，而不是由 LLM 判断。

相比 5 月 19 日自然 QA pilot，这批 v2 数据进一步补上了三个关键点：

- **Self-contained:** 不要求读者知道 Grid2Op/CityLearn/AIOpsLab/FinRL 的内部背景。
- **Data-only answerable:** 给 `scene + variables + rule + values` 即可答题，不需要 evidence caption。
- **Reasoning-oriented:** 每题至少需要均值、分段均值、比例、峰值/中位数、最大回撤或 rule precedence。

### 10.2 Compact physical values 是当前最重要的生成改动

v1 中模型需要在较长序列上做太多低层计算，data-only probe 准确率只有约 `0.40`。v2 将 solver-visible `values` 改成连续时间块的物理量/派生量压缩表后，data-only probe 到 `0.75`。这说明当前数据方向更像“时序推理 benchmark”，而不是“长表格算术压力测试”。

需要强调：compact values 不是泄漏答案。它保留的是可解释的物理特征，例如分块均值、比例、峰值/中位数、最低压力等；gold 仍需要应用题面规则。

### 10.3 Hard cases 暴露了 reviewer 应该重点审核的点

data-only probe 的错误集中在 CityLearn 和 Water：

| source | acc | 主要问题 |
| --- | ---: | --- |
| `citylearn` | `5/10` | 模型经常算出早/中/晚均值和 gap，却在 final answer 里仍返回 `balanced reserve` |
| `water` | `4/10` | rule precedence、恢复阈值和稳定阈值容易混淆 |
| `traffic` | `8/10` | 部分样例 reason 已写出“no clear congestion shock”，但 final answer 仍选恢复类 |
| `aiopslab` | `9/10` | 个别样例 reason 判断正确但 final answer 字段错 |
| `finrl` | `9/10` | 个别样例把未达 `-20%` 的回撤误当成 severe drawdown |
| `grid2op` | `10/10` | 当前规则最清楚，但还需要扩展到更丰富的 counterfactual 类型 |

这说明 reviewer 不只要看自然语言是否顺，还要审核：

- 阈值条件是否存在方向歧义。
- “不满足阈值时选负类”的规则是否足够醒目。
- 多级规则的优先级是否能被普通模型稳定执行。
- answer letter 与 answer label 是否能被模型无歧义匹配。

### 10.4 当前还不能作为最终 benchmark 投稿版本

这批数据适合作为 case study、generation spec 和扩增 seed，但暂时不应包装成最终 benchmark：

- 规模只有 `60` 条。
- answer distribution 明显不平衡，`A` 占 `31/60`。
- 每个 domain 当前只有 1 个 task family，覆盖面还不够。
- 只有一个 data-only GPT probe，还没有通用 LLM 与 TS-LLM 的系统评测。
- Water/CityLearn 的错误率说明规则表达还需要修。
- 还缺少人工 reviewer 的正式审核记录和修改闭环。

## 11. 建议作为下一轮扩增的生成标准

基于这批 case，我建议下一轮扩增保留以下标准：

1. 每条数据必须自足：scene、variables、rule、question、options、values 足够推出答案。
2. `values` 使用 compact physical features；原始长序列留在 `raw_compact_values` 做审计。
3. 每个 task family 至少包含 4 类答案，并在生成阶段强制 answer balancing。
4. 每条题必须有 deterministic support slots，且 reviewer 不能改 gold。
5. 对每个样例执行 local verifier：support slots 与 visible values 的聚合结果一致。
6. 对每个 task family 执行 data-only LLM probe；若模型 reason 和 answer 字段不一致，进入 reviewer queue。
7. 对 Water/CityLearn 这类规则复杂任务，先修文案和阈值表达，再扩规模。

## 12. 结论

当前生成数据已经能支撑一段明确的 case study 叙事：

> We generate self-contained, simulator-grounded time-series QA cases. Each case exposes a natural decision scenario, physical time-series features, and explicit reasoning rules, while deterministic support slots provide gold labels and reviewer-auditable evidence.

这条路线有投稿潜力，但当前资产更适合作为 benchmark generation pipeline 的 seed evidence。下一步应把 v2 的生成规范固化，修复 Water/CityLearn 的规则表达，做 answer-balanced 扩增，并补上多模型评测与 reviewer audit。
