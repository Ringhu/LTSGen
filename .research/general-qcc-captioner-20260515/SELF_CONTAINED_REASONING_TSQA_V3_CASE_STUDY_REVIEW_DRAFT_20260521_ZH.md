# Self-contained Reasoning TSQA v3 Case Study 审阅稿（2026-05-21）

## 这份稿子的目的

这份 case study 用来核对两件事：

1. 当前 `emnlp-benchmark-pipeline` 分支确实同步了 longline 分支的 Natural-QCC / reviewer-gate 质量要求。
2. 新生成的 `self_contained_reasoning_qa_v3` 是否符合你想要的自然 QA 风格：场景自包含、问题自然、gold answer 来自 deterministic support slots，caption 不泄漏 `Answer label`。

本稿只选 6 条代表样本，不是最终 benchmark。所有样本都来自：

- v3 positive seed：`.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/self_contained_reasoning_tsqa_v3_ready.jsonl`
- full60 data-only probe：`.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/data_only_probe_full60/self_contained_reasoning_tsqa_gpt_data_only_probe.json`
- reviewer gate：`.research/general-qcc-captioner-20260515/seed_quality_review_v3_fullprobe_20260521/`

质量约束来自已同步文件：

- `.research/general-qcc-captioner-20260515/NATURAL_QCC_RESEARCH_ROUTE_AND_REVIEWER_GATE_20260521_ZH.md`

## 当前同步后的写法标准

合格样本应当包含：

- **Scene / 场景**：普通领域用户能理解，不暴露 simulator 名称或内部 ID。
- **Decision rule / 决策规则**：如果答案依赖阈值或优先级，题面必须写清楚。
- **Question / 问题**：一个自然的领域决策问题。
- **Options / 选项**：四个自然答案。
- **Gold / 正确答案**：由 support slots 和规则确定，不由 LLM 决定。
- **Evidence caption / 证据 caption**：描述关键时序证据，不写 `Answer label`，不写选项字母。
- **Audit / 审计信息**：source id、support slots、probe 结果。

下面 6 个 case 均满足：`answer_label == support_slots.answer_label`，且 `target_caption/output/oracle_evidence_caption` 不含 `Answer label`。

---

## Case 1: Grid2Op 风险下降判断

### 场景中文

电网调度员正在比较一次计划断线运行和匹配的正常运行。无需了解任何特定平台背景：`x0` 是每个时间步的“断线运行减正常运行”的压力差，`x0` 为正表示断线更紧张，`x0` 为负表示断线更安全。

### Scene EN

A power-grid operator is comparing a planned line-outage run with a matched normal run. No platform-specific prior knowledge is needed: `x0` is the outage-minus-normal stress difference at each step, so positive `x0` means the outage is more stressful and negative `x0` means it is less stressful.

### 决策规则

压缩表每行对应一个连续时间块。跨行计算 `x0` 均值、`x1` 均值、`x2` 均值和 `x3` 最大值。

- 若 `x0_mean >= +0.05` 且 `x1_mean >= 0.80`，选风险上升。
- 若 `x0_mean <= -0.05` 且 `x2_mean >= 0.80`，选风险下降。
- 若 `|x0_mean| <= 0.02` 且 `max_x3 <= 0.03`，选风险基本不变。
- 否则选需要人工复核。

### 问题

根据规则和 `x0` 序列，调度员应如何判断这次计划断线的影响？

### Options

- A. 风险上升 / risk increases
- B. 风险下降 / risk decreases
- C. 风险基本不变 / risk is broadly unchanged
- D. 需要人工复核 / manual review needed

### Gold

**B. 风险下降 / risk decreases**

### Evidence caption

中文：跨压缩块看，`x0` 均值为 `-0.1071`；高于 `+0.05` 和低于 `-0.05` 的比例分别为 `0.0%`、`100.0%`，`x0` 最大绝对值为 `0.1169`。正向压力门槛不满足，负向压力门槛满足，低变化门槛不满足。

EN: Across compact blocks, mean `x0` is `-0.1071`; the shares above `+0.05` and below `-0.05` are `0.0%` and `100.0%`, and max absolute `x0` is `0.1169`. The positive-stress gate is not met, the negative-stress gate is met, and the low-change gate is not met.

### Audit

- id: `self_contained_reasoning_v3::grid2op::scenario_first_pilot::grid2op::line_disconnection::012::grid_line_disconnection_counterfactual_risk::self_contained_grid_counterfactual_risk`
- support slots: `x0_mean=-0.1071100439`, `frac_gt_pos_0_05=0.0`, `frac_lt_neg_0_05=1.0`, `max_abs_x0=0.1168529161`, `answer_label=risk decreases`
- data-only probe: `B / risk decreases`
- probe reason 摘要：mean `x0` clearly negative，mean `x2=1.0`，因此 risk-decreases rule satisfied。

---

## Case 2: CityLearn 供能预留判断

### 场景中文

建筑能耗规划员需要为一个 256 步运行窗口安排供能预留。无需了解任何特定平台背景。`x0` 是建筑用电需求，`x2` 是本地太阳能支持；这里定义净电网负荷为 `x0 - 0.15*x2`。

### Scene EN

A building energy planner is deciding when to reserve supply for a 256-step operating window. No platform-specific prior knowledge is needed. `x0` is building demand, `x2` is local solar support, and net grid load is defined here as `x0 - 0.15*x2`.

### 决策规则

压缩表每行对应一个连续时间块；`x3` 已经是该块平均净电网负荷。把压缩行分成早段、中段、后段。

- 若最高一段的 `x3` 均值比第二高至少高 `0.30`，就为该段优先预留供能。
- 否则按均衡供能准备。
- 若差距低于 `0.30`，最终答案必须是均衡供能。

### 问题

根据净负荷规则，这个窗口应在哪个时段优先预留供能？

### Options

- A. 优先为早段预留供能 / reserve early
- B. 优先为中段预留供能 / reserve middle
- C. 优先为后段预留供能 / reserve late
- D. 按均衡供能准备 / balanced reserve

### Gold

**D. 按均衡供能准备 / balanced reserve**

### Evidence caption

中文：早段、中段、后段平均净负荷分别为 `5.332`、`4.746`、`5.257`。最高段是早段，第二高均值为 `5.257`，最高与第二高差距为 `0.0752`；相对于 `0.30` 的分离阈值，该门槛不满足。

EN: Early, middle, and late mean net loads are `5.332`, `4.746`, and `5.257`. The largest third is early, the second-largest mean is `5.257`, and the top-second gap is `0.0752` against the `0.30` separation threshold, so the separation gate is not met.

### Audit

- id: `self_contained_reasoning_v3::citylearn::scenario_first_pilot::citylearn::demand_response_reserve::001::citylearn_reserve_planning_from_controlled_peak::self_contained_building_net_load_reserve`
- support slots: `early_net_mean=5.3318978584`, `middle_net_mean=4.7460750942`, `late_net_mean=5.2566785898`, `gap_top_second=0.0752192686`, `answer_label=balanced reserve`
- data-only probe: `D / balanced reserve`
- probe reason 摘要：largest third 是 early，但 top-second gap 只有 `0.0752 < 0.30`，所以 rule requires balanced reserve。

---

## Case 3: Traffic 事件后拥堵判断

### 场景中文

交通分析员正在查看一段道路的时间序列。无需了解任何特定交通平台背景。`x0` 是平均车速，`x1` 是排队长度，`x2` 是车道占有率。队列和占有率越高越差，车速越高越好。

### Scene EN

A traffic analyst is reviewing one road segment over time. No traffic-platform prior knowledge is needed. `x0` is mean speed, `x1` is queue length, and `x2` is lane occupancy. Higher queue and occupancy are worse; higher speed is better.

### 决策规则

压缩表每行对应一个连续时间块；`x3` 已经是该块平均拥堵分数 `x1 + 8*x2 - 0.05*x0`。把压缩行分成事件前、事件中、事件后三段。

- 先检查事件中 `x3` 均值是否比事件前高出 `0.50` 以上。
- 若没有，直接选没有清晰拥堵冲击，不再判断恢复类别。
- 只有事件中升高超过 `0.50` 时，才继续判断恢复、持续或部分恢复。

### 问题

根据拥堵分数规则，事件阶段之后交通状态如何变化？

### Options

- A. 没有清晰拥堵冲击 / no clear congestion shock
- B. 拥堵恢复 / congestion recovers
- C. 部分恢复 / partial recovery
- D. 拥堵持续 / congestion persists

### Gold

**A. 没有清晰拥堵冲击 / no clear congestion shock**

### Evidence caption

中文：事件前、事件中、事件后拥堵分数均值分别为 `6.398`、`6.421`、`6.154`。事件中相对事件前上升 `0.0221`，对应 `0.50` 的冲击门槛；事件后相对事件前为 `-0.2448`，并比事件中低 `0.2668`。冲击、恢复、持续三个门槛分别不满足、不满足、不满足。

EN: Pre-event, event, and post-event congestion-score means are `6.398`, `6.421`, and `6.154`. The event rise over pre-event is `0.0221` versus the `0.50` shock gate; post-event is `-0.2448` from pre-event and `0.2668` below the event phase. The shock, recovery, and persistence gates are not met, not met, and not met.

### Audit

- id: `self_contained_reasoning_v3::traffic::scenario_first_pilot::traffic::signal_policy_comparison::032::traffic_signal_policy_counterfactual_queue::self_contained_traffic_recovery_reasoning`
- support slots: `pre_score_mean=6.3984813151`, `event_score_mean=6.4205420424`, `post_score_mean=6.1537210370`, `answer_label=no clear congestion shock`
- data-only probe: `A / no clear congestion shock`
- probe reason 摘要：event mean 只比 pre-event 高 `0.02206`，没有超过 `0.50`，所以不进入恢复类别判断。

---

## Case 4: Water 水压恢复判断

### 场景中文

供水服务运维人员正在查看一个服务窗口中的水压和流量。无需了解任何特定水网平台背景。`x0` 是水压，`x1` 是管道流量。类似漏水的事件通常会降低水压并提高流量。

### Scene EN

A water-service operator is reviewing pressure and flow over one service window. No water-platform prior knowledge is needed. `x0` is pressure and `x1` is pipe flow. A leak-like event usually lowers pressure while increasing flow.

### 决策规则

压缩表每行对应一个连续时间块。`x0` 是分块平均水压，`x1` 是分块平均流量，`x2` 是分块最低水压。把压缩行分成事件前、事件中、事件后三段。

- 若最低 `x2 < 55`，事件中 `x1` 均值比事件前高出 `> 1.0`，且事件后 `x0` 均值仍比事件前低 `2.0` 以上，选持续漏水压力风险。
- 若事件中 `x0` 均值比事件前低 `2.0` 以上，且事件后 `x0` 均值反弹到至少“事件前 `x0` 均值 - `1.0`”，选扰动后水压恢复。
- 若前面规则都不满足，且事件后 `x0` 均值距离事件前不超过 `2.0`，选服务稳定。
- 否则选需要人工复核。

### 问题

根据水压-流量恢复规则，应报告哪种供水服务状态？

### Options

- A. 持续漏水压力风险 / persistent leak pressure risk
- B. 扰动后水压恢复 / pressure recovers after disturbance
- C. 服务稳定 / stable service
- D. 需要人工复核 / manual review needed

### Gold

**B. 扰动后水压恢复 / pressure recovers after disturbance**

### Evidence caption

中文：事件前、事件中、事件后水压均值分别为 `71.92`、`64.72`、`76.72`；最低水压为 `56.70`，事件中流量上升 `-0.0397`。按顺序检查时，漏损风险、恢复、稳定水压三个门槛分别不满足、满足、不满足。

EN: Pre-event, event, and post-event pressure means are `71.92`, `64.72`, and `76.72`; minimum pressure is `56.70`, and event flow rises by `-0.0397`. Under the ordered checks, the leak-risk, recovery, and stable-pressure gates are not met, met, and not met.

### Audit

- id: `self_contained_reasoning_v3::water::scenario_first_pilot::water::leak_event_service_state::003::water_leak_event_service_state::self_contained_water_service_recovery`
- support slots: `pre_pressure_mean=71.9199052150`, `event_pressure_mean=64.7213317974`, `post_pressure_mean=76.7218676975`, `min_pressure=56.6994966250`, `event_flow_increase=-0.0397246403`, `answer_label=pressure recovers after disturbance`
- data-only probe: `B / pressure recovers after disturbance`
- probe reason 摘要：event pressure 比 pre-event 低超过 `2.0`，post-event rebound 到 `pre-event - 1.0` 以上，因此 recovery rule applies。

### 审阅提示

这条 Water case 可答，但 `event flow rises by -0.0397` 这句不够自然，因为负数其实表示没有上升。后续 v3.1 建议改成 “event flow changes by -0.0397” 或 “does not rise”。这正是 full60 probe 后我标记 Water 需要继续打磨的原因。

---

## Case 5: AIOps 主导症状排查

### 场景中文

SRE 正在排查一个服务遥测窗口。无需了解任何特定平台背景。`x0` 是 CPU 负载，`x1` 是内存工作集，`x2` 是网络接收速率，`x3` 是网络发送速率。

### Scene EN

An SRE is triaging one service telemetry window. No platform-specific prior knowledge is needed. `x0` is CPU load, `x1` is memory working set, `x2` is network receive rate, and `x3` is network transmit rate.

### 决策规则

压缩表每行对应一个连续时间块。跨行计算前半段/后半段 `x1` 均值、`x2` 最大值、`x3` 最大值和 `x0` 最大值。

- 只有 `x1` 增长至少 `15%` 时才选内存泄漏模式。
- 只有 `x2` 或 `x3` 最大值至少 `2.5` 时才选网络突发模式。
- 只有 `x0` 最大值至少 `0.85` 时才选 CPU 饱和模式。
- 否则选没有主导症状。
- 内存规则优先。

### 问题

根据排障规则，SRE 应优先关注哪种症状？

### Options

- A. 内存泄漏模式 / memory leak pattern
- B. 网络突发模式 / network burst pattern
- C. CPU 饱和模式 / cpu saturation pattern
- D. 没有主导症状 / no dominant symptom

### Gold

**D. 没有主导症状 / no dominant symptom**

### Evidence caption

中文：内存均值从前半段 `9663229.9` 变为后半段 `9557010.6`，变化幅度为 `-1.1%`。接收和发送峰值比为 `1.513`、`1.475`，CPU 最大值为 `0.4261`。按优先级看，内存、网络、CPU 三个门槛分别不满足、不满足、不满足。

EN: Mean memory changes from `9663229.9` in the first half to `9557010.6` in the second half (`-1.1%`). Receive and transmit peak ratios are `1.513` and `1.475`, and max CPU is `0.4261`. In priority order, the memory, network, and CPU gates are not met, not met, and not met.

### Audit

- id: `self_contained_reasoning_v3::aiopslab::scenario_first_pilot::aiopslab::incident_fault_injection::004::aiops_incident_dominant_symptom::self_contained_aiops_symptom_triage`
- support slots: `memory_first_half_mean=9663229.9483`, `memory_second_half_mean=9557010.6086`, `memory_growth_ratio=-0.0109921155`, `rx_peak_median_ratio=1.5128212896`, `tx_peak_median_ratio=1.4750458250`, `cpu_max=0.4260868714`, `answer_label=no dominant symptom`
- data-only probe: `D / no dominant symptom`
- probe reason 摘要：memory growth far below `15%`，network ratios below `2.5`，CPU below `0.85`。

---

## Case 6: FinRL 回撤优先风险判断

### 场景中文

市场分析师正在查看一个资产价格窗口。无需了解任何特定平台背景。`x0` 是资产价格，`x1` 是市场背景指标，`x2` 是交易量。

### Scene EN

A market analyst is reviewing one asset price window. No platform-specific prior knowledge is needed. `x0` is asset price, `x1` is a market context indicator, and `x2` is trading volume.

### 决策规则

压缩表每行对应一个连续时间块。计算总收益率 `last x0 / first x0 - 1`，并根据 `x0` 的历史峰值计算最大回撤。

- 若最大回撤 `<= -20%`，必须优先选严重回撤风险。
- 只有该条件不满足时，才根据总收益率选择：
  - 总收益率 `>= +8%` 选上行状态。
  - 总收益率 `<= -8%` 选下行状态。
  - 其余选横盘状态。

### 问题

根据总收益率和最大回撤，这段价格窗口应如何分类？

### Options

- A. 上行状态 / bullish regime
- B. 下行状态 / bearish regime
- C. 横盘状态 / sideways regime
- D. 严重回撤风险 / severe drawdown risk

### Gold

**D. 严重回撤风险 / severe drawdown risk**

### Evidence caption

中文：总收益率为 `-34.1%`，相对历史峰值的最大回撤为 `-34.1%`。`-20%` 的回撤优先门槛满足；若该门槛未触发，`+8%` 与 `-8%` 的收益率门槛分别不满足、满足。

EN: Total return is `-34.1%`, and maximum drawdown from the running peak is `-34.1%`. The drawdown priority gate at `-20%` is met; if that gate is not active, the `+8%` and `-8%` return gates are not met and met.

### Audit

- id: `self_contained_reasoning_v3::finrl::scenario_first_pilot::finrl::market_regime_review::011::finrl_controlled_market_regime_review::self_contained_finrl_return_drawdown_regime`
- support slots: `total_return=-0.3409954688`, `max_drawdown=-0.3409954688`, `answer_label=severe drawdown risk`
- data-only probe: `D / severe drawdown risk`
- probe reason 摘要：first `x0=100`，last `x0=65.9005`，total return 和 maximum drawdown 都约为 `-34.10%`，触发 drawdown priority。

## 审阅结论草案

从这 6 条看，当前同步后的 v3 case 已经体现了新的质量要求：

- 不再是旧 1980 slot lookup 风格。
- 题面包含场景、变量、规则和自然问题。
- gold answer 可由 support slots 复算。
- caption 是 evidence-only，没有 `Answer label`。
- 每条都有 data-only probe 审计。

但仍有需要你重点审的地方：

1. **Water caption wording**：`flow rises by -0.0397` 这类表述应在 v3.1 修成更自然的 “flow changes by”。
2. **规则篇幅**：CityLearn / Traffic / Water 的规则偏长，适合 benchmark 自包含性，但可能影响自然感。
3. **英文 option label**：当前仍保留 machine-friendly label，例如 `balanced reserve`、`no dominant symptom`，如果要投稿展示，可以再做一层更自然的 display label。
4. **case-study 展示版和训练版要分开**：训练版可以 compact，论文展示版应更像真实业务问答，减少变量名密度。

