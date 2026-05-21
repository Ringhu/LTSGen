# MultiSim Question Repair 说明（2026-05-19）

## 背景

这次修复针对一个很具体的问题：原来的 case-study 问题经常只问“哪个变量更相关”“哪个窗口更高”“这个故障是什么”，但没有告诉读者这个模拟器是什么、`x0/x1/x2` 分别代表什么、判定规则是什么。结果是，哪怕人来答，也会像看到一串陌生代号一样，不知道问题到底要求什么。

这和 QCC 的目标不冲突。QCC 仍然要求模型输出自然语言 evidence caption；但 question 本身必须给出足够的背景和任务定义，不能把必要的领域知识默认给读者。

## 修复格式

每个问题统一修成三段：

```text
Background: 这个模拟器/领域是什么，x0/x1/x2 等变量是什么意思。
Task rule: 这个问题应该按什么规则判断。
Specific question: 原始的具体问题。
```

关键边界：

- question 可以写变量含义、领域背景、固定判定流程。
- question 不能写当前样本的 support-slot 数值、答案标签、当前窗口证据。
- evidence caption 仍然负责给出当前样本的证据。
- AIOps 的 application / service / fault-family / provenance 这类题，如果只给数值时间序列，是不可答的；必须注入官方 metadata，或者从纯 TS grounding 评估里排除。

## 已实现产物

- 修复脚本：`scripts/generate/repair_multisim_questions.py`
- case-study 样本修复输出：`.research/general-qcc-captioner-20260515/question_repair_20260519/repaired_multisim_v5_balanced8_predictions.jsonl`
- case-study 审计：`.research/general-qcc-captioner-20260515/question_repair_20260519/repaired_multisim_v5_balanced8_audit.json`
- SFT smoke 修复输出：`.research/general-qcc-captioner-20260515/question_repair_20260519/repaired_multisim_v3_eval_source_dev_sft_smoke64.jsonl`
- SFT smoke 审计：`.research/general-qcc-captioner-20260515/question_repair_20260519/repaired_multisim_v3_eval_source_dev_sft_smoke64_audit.json`

## 审计结果

case-study 48 条：

- 覆盖 6 个来源：`aiopslab_official_v3 / citylearn / finrl_scaled / grid2op / traffic / water`，每个 8 条。
- `repaired`: 41
- `needs_metadata_context`: 5
- `weak_rule`: 2
- `missing_context_count`: 0
- `support_slot_numeric_leak_count`: 0
- `clarity_gate_pass`: true

SFT smoke 64 条：

- 覆盖 `citylearn / water / grid2op / traffic / aiops`。
- `repaired`: 62
- `needs_metadata_context`: 2
- `missing_context_count`: 0
- `support_slot_numeric_leak_count`: 0
- `clarity_gate_pass`: true

这里的 pass 只说明“问题结构和非泄漏审计通过”，不说明所有题都适合作为论文 case study。`needs_metadata_context` 和 `weak_rule` 必须单独处理。

## 例子 1：Grid2Op 电网相关性题

原问题：

```text
Which compact variable is more strongly associated with maximum line-loading stress x0:
total demand x1 or generation margin x2?
```

问题在哪里：

没有电网背景的人不知道 `maximum line-loading stress` 是什么，也不知道 `x1/x2` 是什么。更重要的是，“more strongly associated” 到底看相关系数、互信息、峰值同步还是别的指标，原问题没说。

修复后：

```text
Background: This is a Grid2Op power-grid window. x0 is maximum line-loading
stress over grid lines, x1 is total demand, and x2 is generation margin.
A line-loading stress value above 1.0 means overload.
Task rule: Cross-variable rule: compare absolute correlations between the
target signal and each companion signal. Use both weak when both correlations
are small, and both similar when the correlations are close.
Specific question: Which compact variable is more strongly associated with
maximum line-loading stress x0: total demand x1 or generation margin x2?
```

现在人可以知道：这是电网窗口，`x0` 是线路压力，`x1` 是负荷，`x2` 是发电裕度；这道题用绝对相关系数判定。

## 例子 2：Grid2Op 反事实干预题

原问题：

```text
The provided trace is intervention-minus-factual after disconnecting line 1
at global step 512, shown in segment post769_1025. What is the strongest
post-event stress deviation in x0?
```

问题在哪里：

这个问题已经有一些背景，但没有明说正负号怎么解释。非 Grid2Op 读者可能不知道 `intervention-minus-factual` 为正到底代表干预更安全还是更危险。

修复后：

```text
Background: This is a Grid2Op power-grid window. x0 is maximum line-loading
stress over grid lines, x1 is total demand, and x2 is generation margin.
A line-loading stress value above 1.0 means overload.
Task rule: Counterfactual rule: the trace describes intervention-minus-factual
post-event stress. Positive deviations mean the intervention raises stress;
negative deviations mean it lowers stress. Classify the strongest deviation
as upward peak, downward dip, or no material change.
Specific question: The provided trace is intervention-minus-factual after
disconnecting line 1 at global step 512, shown in segment post769_1025. What
is the strongest post-event stress deviation in x0?
```

这里没有泄漏当前样本的最大差值，只补了符号和判定规则。

## 例子 3：AIOps 元数据题

原问题：

```text
Which benchmark application generated this AIOpsLab telemetry case?
```

问题在哪里：

这不是纯时间序列问题。只看 CPU、memory、network telemetry，不能可靠推出“这个 case 来自 social-network 还是 hotel-reservation”。原来的形式会逼模型从数字里猜 metadata，case study 里看起来就像幻觉。

修复后：

```text
Background: This is an AIOpsLab microservice telemetry case. Numeric channels
usually include service CPU load, memory working set, network receive rate,
and network transmit rate. Application, service, fault-family, and provenance
questions require official case metadata rather than inference from numeric
telemetry alone.
Task rule: This is a metadata-context task. It is not answerable from the
numeric time series alone; the official case metadata field named by the
question must be provided or this row should be excluded from pure time-series
grounding evaluation.
Specific question: Which benchmark application generated this AIOpsLab
telemetry case?
```

这类题目前不应该作为“模型读时间序列理解了故障”的正面例子。它只能用于 metadata-conditioned QCC，或者从纯 TS case study 中移除。

## 例子 4：CityLearn domain-context 弱规则题

原问题：

```text
What demand-pressure regime best describes this CityLearn window?
```

问题在哪里：

“demand-pressure regime” 听起来像领域判断，但原问题没有说明 regime 的类别、阈值、变量依据。修复脚本只能把它标成 `weak_rule`，因为现在还没有足够清晰的公开判定规则。

当前修复：

```text
Background: This is a CityLearn building-energy window. x0 is total building
load, x1 is an outdoor/weather support signal, and x2 is solar-generation
support. Higher x0 means higher building demand.
Task rule: Domain-context rule: use the domain-specific operational state
variables named in the question and evidence caption. This row should expose
the decision thresholds before paper-facing use.
Specific question: What demand-pressure regime best describes this CityLearn
window?
```

结论：这条还不能直接放进 case study。要么把 regime 定义成明确阈值，例如 low/intermediate/high demand pressure 的规则；要么换成 trend、window comparison、volatility 这类已经清楚的 primitive。

## 例子 5：Traffic lead-lag 题

原问题：

```text
Does traffic speed x0 tend to lead or lag queue length x1?
```

问题在哪里：

如果不给交通背景，人不知道 speed 和 queue 的方向含义；如果不给 lead-lag 规则，人也不知道“lead”是按哪个滞后相关定义。

修复规则：

```text
Background: This is a traffic simulation window. x0 is mean traffic speed,
x1 is queue length, and x2 is lane occupancy. Lower speed and higher queue
or occupancy indicate congestion.
Task rule: Lead-lag rule: compare lagged correlation with zero-lag correlation.
Positive lag means x0 leads x1; negative lag means x1 leads x0. If the best
lagged correlation is not meaningfully stronger than zero lag, answer no
clear lead.
```

这类题修复后比较适合讨论，因为它有领域背景，也有明确的可验证判定规则。

## 对 case-study 的直接建议

短期不要再把原始 question 直接贴进 case study。应当先经过 question repair gate：

1. 必须包含 `Background / Task rule / Specific question`。
2. 必须通过 support-slot 数值泄漏检查。
3. `needs_metadata_context` 不能作为纯时间序列理解案例。
4. `weak_rule` 不能作为正面案例；除非先补齐具体阈值或类别定义。
5. Grid2Op case study 优先选 `cross_variable_relation`、`counterfactual_peak_stress`、`trend`、`window_comparison`、`lead_lag` 这类规则明确的题。

当前最需要人工讨论的不是“模型为什么错”，而是“这些问题是否已经是人类可答的问题”。这个修复把问题分成三类：可用、需要 metadata、规则仍弱。
