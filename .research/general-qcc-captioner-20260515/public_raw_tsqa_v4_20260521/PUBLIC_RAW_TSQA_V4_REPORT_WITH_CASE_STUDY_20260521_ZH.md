# Public Raw TSQA v4 图文报告与 Case Study（2026-05-21）

## 一句话结论

本轮已把 benchmark 标准从 v3 的技术验证格式推进到 public raw time-series QA 格式：同一条 canonical raw-series 样本同时导出 LLM text view 和 TS-LLM array view，内部审计证据和 oracle evidence 不进入主评测 prompt。

## 产物结构

| 文件 | 用途 |
| --- | --- |
| `canonical_raw_tsqa_v4.jsonl` | 一份标准 raw time-series QA 数据 |
| `llm_text_view.jsonl` | 普通 LLM 使用：完整时序转 CSV 文本并放入 prompt |
| `tsllm_array_view.jsonl` | TS-LLM 使用：原始数组 + 同一问题文本 |
| `oracle_evidence.jsonl` | oracle evidence / upper-bound 条件 |
| `audit_support.jsonl` | 内部审计证据字段、verifier rule、source 和 reviewer trace |
| `mismatch_audit.jsonl` | 被排除样本及原因 |

## 规模与覆盖

- canonical rows: `39`
- raw/v3 gold mismatch or excluded: `2`
- public forbidden issues: `0`
- sanity check pass: `True`
- bilingual completeness: `39` / `39` canonical rows contain English and Chinese context, variables, decision guide, question, options, answer label, and evidence
- raw series length: `{'min': 96, 'max': 256}`
- answer distribution: `{"C": 3, "B": 4, "A": 19, "D": 13}`

![Domain distribution](figures/domain_distribution.svg)

![Answer distribution](figures/answer_distribution.svg)

![Raw series lengths](figures/time_series_lengths.svg)

## 为什么 LLM 和 TS-LLM 可以复用同一批数据

同一个 canonical record 保存原始时序、变量解释、问题、选项和 gold answer。LLM view 只是把 `time_series.values` 序列化成 CSV 文本；TS-LLM view 则直接保留同一个数组。两者不改变问题、不改变选项、不改变答案。

这保证了评测比较的是模型输入接口差异，而不是两套数据差异。

## Case Study

下面每个 case 都完整展示英文版本和中文版本。两种语言使用同一个 raw time-series、同一个选项字母、同一个 gold answer；差别只在题面语言。

### Case 1: `power_grid`

![Case 1 series](figures/case_1_power_grid.svg)

#### English Version

**Context**

A grid operator is assessing how a planned line outage changes line stress compared with normal operation.

**Time Axis**

ordered post-event operating window

**Variables**

- `stress_delta`: planned-outage line stress minus normal-operation line stress
- `demand_context`: system demand context signal
- `generation_margin_context`: generation margin context signal

**Decision Guide**

If the average stress difference is clearly positive and most readings are above +0.05, classify the outage as increasing stress. If the average is clearly negative and most readings are below -0.05, classify it as decreasing stress. If the series stays close to zero with only tiny deviations, classify it as broadly unchanged; otherwise request manual review.

**Question**

Based on the full stress-delta series, what should the operator conclude about the planned outage?

**Options**

- A. The planned outage increases stress.
- B. The planned outage decreases stress.
- C. The effect is broadly unchanged.
- D. The case needs manual review.

**Gold Answer**: `B` / `The planned outage decreases stress.`

**Audit Evidence**

The mean stress difference is -0.107113; 0.0% of readings are above +0.05 and 100.0% are below -0.05. The largest absolute deviation is 0.116853.

#### 中文版本

**场景**

电网调度员正在评估一次计划断线相对正常运行会如何改变线路压力。

**时间轴**

按时间排序的事件后运行窗口

**变量**

- `stress_delta`: 计划断线相对正常运行的线路压力差
- `demand_context`: 系统负荷背景信号
- `generation_margin_context`: 发电裕度背景信号

**判定规则**

如果平均压力差明显为正，且大多数读数高于 +0.05，则判为压力上升；如果平均压力差明显为负，且大多数读数低于 -0.05，则判为压力下降；如果整体接近 0 且波动很小，则判为基本不变；否则需要人工复核。

**问题**

根据完整压力差序列，调度员应如何判断这次计划断线的影响？

**选项**

- A. 计划断线会增加压力
- B. 计划断线会降低压力
- C. 整体影响基本不变
- D. 需要人工复核

**标准答案**: `B` / `计划断线会降低压力`

**审计证据**

压力差均值为 -0.107113；高于 +0.05 的读数占 0.0%，低于 -0.05 的读数占 100.0%，最大绝对偏差为 0.116853。

**内部审计证据字段摘要**

`{"stress_delta_mean": -0.10711293475739925, "share_above_pos_threshold": 0.0, "share_below_neg_threshold": 1.0, "max_abs_stress_delta": 0.11685291610575388, "verifier_answer_label": "risk decreases"}`

**LLM / TS-LLM view 对齐说明**

```text
LLM English prompt = English context + English variables + English decision guide + English question/options + raw series as CSV.
LLM Chinese prompt = Chinese context + Chinese variables + Chinese decision guide + Chinese question/options + same raw series as CSV.
TS-LLM view = same raw numeric array + English/Chinese text fields. The answer letter is shared.
```

**TS-LLM array shape**

```json
{
  "columns": [
    "stress_delta",
    "demand_context",
    "generation_margin_context"
  ],
  "timeseries_shape": [
    256,
    3
  ],
  "question_en": "Based on the full stress-delta series, what should the operator conclude about the planned outage?",
  "question_zh": "根据完整压力差序列，调度员应如何判断这次计划断线的影响？"
}
```

### Case 2: `building_energy`

![Case 2 series](figures/case_2_building_energy.svg)

#### English Version

**Context**

A building energy planner needs to decide whether supply should be reserved for the early, middle, late, or evenly across the operating window.

**Time Axis**

ordered operating window

**Variables**

- `demand`: building electricity demand
- `weather_context`: weather context signal
- `solar_support`: local solar support

**Decision Guide**

Compute net grid load as demand minus 0.15 times solar support. Compare the average net load in the early, middle, and late portions of the full sequence. If the highest portion exceeds the second-highest by at least 0.30, reserve more supply for that portion; otherwise use a balanced reserve strategy.

**Question**

From the full demand and solar-support series, which reserve strategy is most appropriate?

**Options**

- A. Reserve more supply for the early part of the window.
- B. Reserve more supply for the middle part of the window.
- C. Reserve more supply for the late part of the window.
- D. Use a balanced reserve strategy.

**Gold Answer**: `D` / `Use a balanced reserve strategy.`

**Audit Evidence**

The early, middle, and late net-load means are 5.32557, 4.74602, and 5.25447. The top-second gap is 0.0711006 against the 0.30 threshold.

#### 中文版本

**场景**

建筑能源调度员需要决定应为运行窗口的早段、中段、晚段或整体均衡预留供能。

**时间轴**

按时间排序的运行窗口

**变量**

- `demand`: 建筑用电需求
- `weather_context`: 天气背景信号
- `solar_support`: 本地太阳能支持

**判定规则**

将净电网负荷定义为需求减去 0.15 倍太阳能支持。比较完整序列早段、中段、晚段的平均净负荷；若最高段比第二高段至少高 0.30，则为该段优先预留供能，否则采用均衡策略。

**问题**

根据完整需求和太阳能支持序列，哪种供能预留策略最合适？

**选项**

- A. 优先为早段预留供能
- B. 优先为中段预留供能
- C. 优先为晚段预留供能
- D. 采用均衡供能策略

**标准答案**: `D` / `采用均衡供能策略`

**审计证据**

早段、中段、晚段净负荷均值分别为 5.32557、4.74602、5.25447；最高与第二高差距为 0.0711006，阈值为 0.30。

**内部审计证据字段摘要**

`{"early_net_load_mean": 5.325574036735931, "middle_net_load_mean": 4.746020988170356, "late_net_load_mean": 5.254473457602158, "top_second_gap": 0.07110057913377332, "verifier_answer_label": "balanced reserve"}`

**LLM / TS-LLM view 对齐说明**

```text
LLM English prompt = English context + English variables + English decision guide + English question/options + raw series as CSV.
LLM Chinese prompt = Chinese context + Chinese variables + Chinese decision guide + Chinese question/options + same raw series as CSV.
TS-LLM view = same raw numeric array + English/Chinese text fields. The answer letter is shared.
```

**TS-LLM array shape**

```json
{
  "columns": [
    "demand",
    "weather_context",
    "solar_support"
  ],
  "timeseries_shape": [
    256,
    3
  ],
  "question_en": "From the full demand and solar-support series, which reserve strategy is most appropriate?",
  "question_zh": "根据完整需求和太阳能支持序列，哪种供能预留策略最合适？"
}
```

### Case 3: `traffic`

![Case 3 series](figures/case_3_traffic.svg)

#### English Version

**Context**

A traffic analyst is reviewing road readings before, during, and after an event.

**Time Axis**

ordered before-during-after event window

**Variables**

- `speed`: mean speed
- `queue_length`: queue length
- `lane_occupancy`: lane occupancy

**Decision Guide**

Use queue length, lane occupancy, and speed to form a congestion score: queue length plus 8 times occupancy minus 0.05 times speed. First check whether the event portion rises by more than 0.50 over the pre-event portion. If not, there is no clear congestion shock. Only when that shock exists, decide whether congestion recovers, partially recovers, or persists using the post-event portion.

**Question**

What happened to congestion after the event phase?

**Options**

- A. No clear congestion shock occurs.
- B. Congestion recovers after the event.
- C. Congestion partially recovers.
- D. Congestion persists after the event.

**Gold Answer**: `A` / `No clear congestion shock occurs.`

**Audit Evidence**

The pre-event, event, and post-event congestion-score means are 6.39527, 6.42351, and 6.14901. The event rise over pre-event is 0.0282388.

#### 中文版本

**场景**

交通分析员正在查看事件前、事件中、事件后一段道路的时序读数。

**时间轴**

按时间排序的事件前-事件中-事件后窗口

**变量**

- `speed`: 平均车速
- `queue_length`: 排队长度
- `lane_occupancy`: 车道占有率

**判定规则**

用排队长度、车道占有率和车速形成拥堵分数：排队长度加 8 倍占有率再减去 0.05 倍车速。先看事件中分数是否比事件前高出 0.50 以上；若没有，则没有清晰拥堵冲击。只有冲击存在时，才继续判断恢复、部分恢复或持续。

**问题**

事件阶段之后，拥堵状态如何变化？

**选项**

- A. 没有清晰拥堵冲击
- B. 事件后拥堵恢复
- C. 事件后部分恢复
- D. 事件后拥堵持续

**标准答案**: `A` / `没有清晰拥堵冲击`

**审计证据**

事件前、事件中、事件后拥堵分数均值分别为 6.39527、6.42351、6.14901；事件中相对事件前上升 0.0282388。

**内部审计证据字段摘要**

`{"pre_event_score_mean": 6.39526655427803, "event_score_mean": 6.423505394523074, "post_event_score_mean": 6.149007909702109, "event_minus_pre": 0.028238840245044194, "post_minus_pre": -0.24625864457592073, "event_minus_post": 0.2744974848209649, "verifier_answer_label": "no clear congestion shock"}`

**LLM / TS-LLM view 对齐说明**

```text
LLM English prompt = English context + English variables + English decision guide + English question/options + raw series as CSV.
LLM Chinese prompt = Chinese context + Chinese variables + Chinese decision guide + Chinese question/options + same raw series as CSV.
TS-LLM view = same raw numeric array + English/Chinese text fields. The answer letter is shared.
```

**TS-LLM array shape**

```json
{
  "columns": [
    "speed",
    "queue_length",
    "lane_occupancy"
  ],
  "timeseries_shape": [
    256,
    3
  ],
  "question_en": "What happened to congestion after the event phase?",
  "question_zh": "事件阶段之后，拥堵状态如何变化？"
}
```

### Case 4: `water_service`

![Case 4 series](figures/case_4_water_service.svg)

#### English Version

**Context**

A water-service operator is reviewing pressure and flow readings around a disturbance event.

**Time Axis**

ordered before-during-after disturbance window

**Variables**

- `pressure`: service pressure
- `flow`: pipe flow
- `storage_context`: storage context signal

**Decision Guide**

If pressure falls very low, flow clearly increases during the event, and pressure remains depressed afterward, classify the window as persistent leak pressure risk. If pressure drops during the event but rebounds close to or above the pre-event level afterward, classify it as recovery after disturbance. If there is no earlier risk pattern and post-event pressure stays close to pre-event pressure, classify service as stable; otherwise request manual review.

**Question**

Which service state best describes this disturbance window?

**Options**

- A. Persistent leak pressure risk.
- B. Pressure recovers after the disturbance.
- C. Service remains stable.
- D. Manual review is needed.

**Gold Answer**: `B` / `Pressure recovers after the disturbance.`

**Audit Evidence**

Pressure moves from 71.8994 before the event to 64.7325 during the event and 76.6573 afterward. Minimum pressure is 56.6995, and event flow changes by -0.031266.

#### 中文版本

**场景**

供水运维人员正在查看一次扰动事件前后水压和流量读数。

**时间轴**

按时间排序的扰动前-扰动中-扰动后窗口

**变量**

- `pressure`: 服务水压
- `flow`: 管道流量
- `storage_context`: 蓄水背景信号

**判定规则**

若水压降得很低、事件中流量明显升高、且事件后水压仍明显低于事件前，则判为持续漏水压力风险。若事件中水压下降但事件后恢复到接近或高于事件前水平，则判为扰动后恢复。若前面风险模式不满足且事件后水压接近事件前，则判为服务稳定；否则需要人工复核。

**问题**

这段扰动窗口最符合哪种供水服务状态？

**选项**

- A. 持续漏水压力风险
- B. 扰动后水压恢复
- C. 服务保持稳定
- D. 需要人工复核

**标准答案**: `B` / `扰动后水压恢复`

**审计证据**

水压从事件前 71.8994 变为事件中 64.7325，事件后为 76.6573；最低水压为 56.6995，事件中流量变化为 -0.031266。

**内部审计证据字段摘要**

`{"pre_pressure_mean": 71.89942459366053, "event_pressure_mean": 64.73250268368636, "post_pressure_mean": 76.65727518549527, "min_pressure": 56.699496625046166, "event_flow_change": -0.03126601814196839, "verifier_answer_label": "pressure recovers after disturbance"}`

**LLM / TS-LLM view 对齐说明**

```text
LLM English prompt = English context + English variables + English decision guide + English question/options + raw series as CSV.
LLM Chinese prompt = Chinese context + Chinese variables + Chinese decision guide + Chinese question/options + same raw series as CSV.
TS-LLM view = same raw numeric array + English/Chinese text fields. The answer letter is shared.
```

**TS-LLM array shape**

```json
{
  "columns": [
    "pressure",
    "flow",
    "storage_context"
  ],
  "timeseries_shape": [
    256,
    3
  ],
  "question_en": "Which service state best describes this disturbance window?",
  "question_zh": "这段扰动窗口最符合哪种供水服务状态？"
}
```

### Case 5: `service_telemetry`

![Case 5 series](figures/case_5_service_telemetry.svg)

#### English Version

**Context**

An SRE is triaging one service telemetry window.

**Time Axis**

ordered service telemetry window

**Variables**

- `cpu_load`: CPU load
- `memory_working_set`: memory working set
- `network_receive_rate`: network receive rate
- `network_transmit_rate`: network transmit rate

**Decision Guide**

Prioritize memory leak only if memory grows by at least 15% from the first half to the second half. If not, prioritize a network burst only when receive or transmit has a peak-to-median ratio of at least 2.5. If neither applies, prioritize CPU saturation only when max CPU is at least 0.85. Otherwise report no dominant symptom.

**Question**

Which symptom should the SRE prioritize?

**Options**

- A. Prioritize a memory-leak pattern.
- B. Prioritize a network-burst pattern.
- C. Prioritize CPU saturation.
- D. No dominant symptom is present.

**Gold Answer**: `D` / `No dominant symptom is present.`

**Audit Evidence**

Memory changes from 9.66323e+06 to 9.55701e+06 (-1.1%). Receive and transmit peak-to-median ratios are 1.41425 and 1.41602, and max CPU is 0.426087.

#### 中文版本

**场景**

SRE 正在排查一个服务遥测窗口。

**时间轴**

按时间排序的服务遥测窗口

**变量**

- `cpu_load`: CPU 负载
- `memory_working_set`: 内存工作集
- `network_receive_rate`: 网络接收速率
- `network_transmit_rate`: 网络发送速率

**判定规则**

只有内存从前半段到后半段至少增长 15% 时才优先排查内存泄漏。否则，只有接收或发送速率的峰值/中位数比至少为 2.5 时才优先排查网络突发。若都不满足，只有 CPU 最大负载至少为 0.85 时才排查 CPU 饱和；否则报告没有主导症状。

**问题**

SRE 应优先关注哪种症状？

**选项**

- A. 优先排查内存泄漏模式
- B. 优先排查网络突发模式
- C. 优先排查 CPU 饱和
- D. 没有主导症状

**标准答案**: `D` / `没有主导症状`

**审计证据**

内存从 9.66323e+06 变为 9.55701e+06，变化 -1.1%；接收和发送峰值/中位数比分别为 1.41425、1.41602，CPU 最大值为 0.426087。

**内部审计证据字段摘要**

`{"memory_first_half_mean": 9663229.94833505, "memory_second_half_mean": 9557010.608610492, "memory_growth_ratio": -0.010992115503042417, "rx_peak_median_ratio": 1.4142464153882728, "tx_peak_median_ratio": 1.4160240046921517, "cpu_max": 0.4260868713772379, "verifier_answer_label": "no dominant symptom"}`

**LLM / TS-LLM view 对齐说明**

```text
LLM English prompt = English context + English variables + English decision guide + English question/options + raw series as CSV.
LLM Chinese prompt = Chinese context + Chinese variables + Chinese decision guide + Chinese question/options + same raw series as CSV.
TS-LLM view = same raw numeric array + English/Chinese text fields. The answer letter is shared.
```

**TS-LLM array shape**

```json
{
  "columns": [
    "cpu_load",
    "memory_working_set",
    "network_receive_rate",
    "network_transmit_rate"
  ],
  "timeseries_shape": [
    96,
    4
  ],
  "question_en": "Which symptom should the SRE prioritize?",
  "question_zh": "SRE 应优先关注哪种症状？"
}
```

### Case 6: `market`

![Case 6 series](figures/case_6_market.svg)

#### English Version

**Context**

A market analyst is reviewing an asset price window.

**Time Axis**

ordered market window

**Variables**

- `asset_price`: asset price
- `market_context`: market context signal
- `trading_volume`: trading volume

**Decision Guide**

Compute total return from the first to the last price and maximum drawdown from the running peak. Severe drawdown has priority if maximum drawdown is at least 20%. If that does not apply, classify the window as bullish when return is at least +8%, bearish when return is at most -8%, and sideways otherwise.

**Question**

How should this price window be classified?

**Options**

- A. Bullish regime.
- B. Bearish regime.
- C. Sideways regime.
- D. Severe drawdown risk.

**Gold Answer**: `D` / `Severe drawdown risk.`

**Audit Evidence**

Total return is -34.1%, and maximum drawdown from the running peak is -36.1%.

#### 中文版本

**场景**

市场分析师正在查看一段资产价格窗口。

**时间轴**

按时间排序的市场窗口

**变量**

- `asset_price`: 资产价格
- `market_context`: 市场背景信号
- `trading_volume`: 交易量

**判定规则**

计算首尾价格的总收益率，以及相对历史峰值的最大回撤。若最大回撤达到 20% 或以上，优先判为严重回撤风险。若没有触发回撤风险，则总收益率至少 +8% 判为上行，至多 -8% 判为下行，其余判为横盘。

**问题**

这段价格窗口应如何分类？

**选项**

- A. 上行状态
- B. 下行状态
- C. 横盘状态
- D. 严重回撤风险

**标准答案**: `D` / `严重回撤风险`

**审计证据**

总收益率为 -34.1%，相对历史峰值的最大回撤为 -36.1%。

**内部审计证据字段摘要**

`{"total_return": -0.34099546875088815, "max_drawdown": -0.3608915249726842, "verifier_answer_label": "severe drawdown risk"}`

**LLM / TS-LLM view 对齐说明**

```text
LLM English prompt = English context + English variables + English decision guide + English question/options + raw series as CSV.
LLM Chinese prompt = Chinese context + Chinese variables + Chinese decision guide + Chinese question/options + same raw series as CSV.
TS-LLM view = same raw numeric array + English/Chinese text fields. The answer letter is shared.
```

**TS-LLM array shape**

```json
{
  "columns": [
    "asset_price",
    "market_context",
    "trading_volume"
  ],
  "timeseries_shape": [
    256,
    3
  ],
  "question_en": "How should this price window be classified?",
  "question_zh": "这段价格窗口应如何分类？"
}
```

## 本轮剩余问题

- 当前 v4 只有 39 条，是 schema/pipeline 样板，不是最终 benchmark 规模。
- answer distribution 仍偏 A，需要扩增时做全局 answer balance。
- building_energy / traffic 的 ready seed 数量偏少，需要优先补齐。
- 下一步应在 v4 schema 上扩增，而不是继续扩 v3 compact-style 数据。
