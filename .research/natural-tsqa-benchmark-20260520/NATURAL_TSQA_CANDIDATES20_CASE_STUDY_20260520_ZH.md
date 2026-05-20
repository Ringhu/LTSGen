# Natural TSQA Candidates20 Case Study（2026-05-20）

本文档记录一次小规模 `simulator-derived candidates + deterministic rewrite + GPT reviewer` 扩增试跑。目标不是训练模型，而是验证目前的数据流能否稳定产出接近 `natural_qa_pilot_20260519` 风格的自然时序 QA，并估计单样本生成成本。

## 结论摘要

- 本次按 `20/source` 构造了 `100` 条候选：`aiopslab_official_v3`、`citylearn`、`grid2op`、`traffic`、`water` 各 20 条。
- GPT reviewer 全量审查 `100/100` 条，通过主准入规则 `75/100`。
- 通过率按源分别为：AIOps `20/20`，CityLearn `16/20`，Grid2Op `16/20`，Traffic `13/20`，Water `10/20`。
- 主要问题不是自然语言风格，而是少数任务的可见规则、数值证据和 deterministic gold answer 不一致。Reviewer 对这些样本能有效拦截。
- 串行 reviewer 是当前瓶颈：`1398.07s / 100 = 13.98s/sample`。选样、确定性 rewrite 和 dataset build 几乎可以忽略。

## 资产路径

候选与自然化草案：

- 严格去重候选：`.research/natural-tsqa-benchmark-20260520/candidates20/natural_tsqa_candidates20.jsonl`
- 20/source 评估候选：`.research/natural-tsqa-benchmark-20260520/candidates20_including_seed_assets/natural_tsqa_candidates20_including_seed_assets.jsonl`
- 自然化草案：`.research/natural-tsqa-benchmark-20260520/rewrites20_including_seed_assets/natural_tsqa_rewrites20_including_seed_assets.jsonl`
- Lint：`.research/natural-tsqa-benchmark-20260520/rewrites20_including_seed_assets/natural_tsqa_rewrites20_including_seed_assets_lint.json`

Reviewer 与准入数据：

- Reviewer JSON：`.research/natural-tsqa-benchmark-20260520/reviews20_including_seed_assets/natural_tsqa_rewrites20_including_seed_assets_review.json`
- Reviewer Markdown：`.research/natural-tsqa-benchmark-20260520/reviews20_including_seed_assets/NATURAL_TSQA_CANDIDATES20_REVIEW_20260520_ZH.md`
- Reviewer-positive JSONL：`.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/natural_tsqa_candidates20_reviewed_positive.jsonl`
- Excluded JSONL：`.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/natural_tsqa_candidates20_reviewed_excluded.jsonl`
- Dataset summary：`.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/natural_tsqa_candidates20_reviewed_dataset_summary.json`
- Split SFT：`.research/natural-tsqa-benchmark-20260520/dataset20_including_seed_assets/sft/`

## 候选口径

本次保留两个候选口径：

1. 严格去重口径：排除了已有 pilot/crossdomain/balanced8 样本后，得到 `93` 条。AIOps 只剩 `13` 条，因此无法满足每源 20 条。
2. 评估口径：为满足“每源 20 条”的人工评估目标，允许包含 seed assets，得到 `100` 条，每个源 20 条。

正式扩增建议使用严格去重口径；如果 AIOps 要进入正式 benchmark，需要补足新的 simulator-derived AIOps rows，不能长期依赖 seed assets。

本地未纳入 FinRL，因为当前工作树里没有可直接抽样的 FinRL split JSONL；只找到了自然化 pilot/balanced8 里的图和样例资产。

## 耗时估计

本次测的是从已有 simulator-derived pool 出样到 reviewer-positive 数据集的流水线，不包含重新跑 simulator 生成原始 trace 的时间。

| step | rows | wall time | time/sample |
| --- | ---: | ---: | ---: |
| strict de-duplicated selection | 93 | 5.44s | 0.0585s |
| 20/source selection including seed assets | 100 | 5.03s | 0.0503s |
| deterministic natural rewrite | 100 | 0.14s | 0.0014s |
| GPT reviewer, serial | 100 | 1398.07s | 13.9807s |
| reviewed dataset build | 100 | ~0.18s | ~0.0018s |

按 20/source 评估口径，端到端约为 `1403.42s / 100 = 14.03s/input candidate`。若只计算 reviewer-positive 成品，约为 `1403.42s / 75 = 18.71s/accepted sample`。

扩到 1,000 条时，若仍串行 reviewer，大约需要 3.9 小时；扩到 5,000 条约 19.4 小时。工程上应改成并发 reviewer、断点缓存、先规则过滤再 LLM 审查、并按任务族抽检。

## Reviewer Gate

准入规则沿用 `natural-tsqa-writer`：

- `review_scope == gpt55_candidate`
- `decision == keep`
- `naturalness_score >= 4`
- `answerability_score >= 4`
- `accuracy_risk == low`

总览：

| source | candidates | keep | revise | reject | positive |
| --- | ---: | ---: | ---: | ---: | ---: |
| `aiopslab_official_v3` | 20 | 20 | 0 | 0 | 20 |
| `citylearn` | 20 | 16 | 0 | 4 | 16 |
| `grid2op` | 20 | 16 | 3 | 1 | 16 |
| `traffic` | 20 | 13 | 7 | 0 | 13 |
| `water` | 20 | 10 | 7 | 3 | 10 |
| total | 100 | 75 | 17 | 8 | 75 |

Reviewer 判定的风险分布：`low=77`，`medium=7`，`high=16`。最终 positive 为 `75`，因为有两个 `low risk` 样本仍被标成 `revise`，不进入主数据池。

## Positive Case Study

### AIOps

ID：`aiopslab_official::port_misconfig_seed0_text-service::case001::aiops_official_memory_extrema`

场景：一名 SRE 正在查看 AIOpsLab 微服务遥测窗口。`x0` 是服务 CPU 负载，`x1` 是内存工作集，`x2` 是网络接收速率，`x3` 是网络发送速率。

问题：把这个事故窗口按时间分成早期、中期和后期后，服务内存工作集的最高点出现在什么位置？

选项：A. 中期 / B. 后期 / C. 没有清晰极值 / D. 早期

Gold：D，早期。

证据：服务内存工作集最高约为 `412,876.80`，出现在窗口第 `2` 步附近，位置在窗口前段。

Reviewer：`keep`，naturalness `5`，answerability `5`，risk `low`。

评价：这是当前最稳的样式。问题自然，证据直接，早/中/后划分清楚。缺点是任务仍偏极值定位，推理深度有限。

### CityLearn

ID：`citylearn_broad::citylearn_challenge_2022_phase_1_start4096_h2048_b5::w1280_1792::city_trend_total_load`

场景：建筑能耗控制器正在查看一个 512 步的 CityLearn 窗口。`x0` 是建筑总用电需求。若问题使用早期/中期/后期选项，则按时间顺序把窗口三等分。

问题：这个窗口中主要监测信号整体如何变化？

选项：A. 下降 / B. 基本平稳 / C. 混合变化 / D. 上升

Gold：D，上升。

证据：`Total building load x0 ends clearly higher than it begins across this window.`

Reviewer：`keep`，naturalness `4`，answerability `5`，risk `low`。

评价：可用，但证据中文仍未完全本地化。后续 rewrite 规则应强制翻译 `evidence_zh`，并把“主要监测信号”改成“建筑总用电需求”，降低歧义。

### Grid2Op

ID：`grid2op_broad::rte_case14_realistic_chronic4_trace_2048_nooverflow::w768_1280::grid_trend_max_rho`

场景：一名 Grid2Op 电网调度员正在查看电网时序窗口。`x0` 是最大线路负载压力，`x1` 是总需求，`x2` 是发电裕度。压力超过 `1.0` 表示过载风险。

问题：这个电网窗口中的线路负载压力是在上升、下降，还是大致稳定？

选项：A. 上升 / B. 下降 / C. 混合变化 / D. 基本平稳

Gold：D，基本平稳。

证据：线路负载压力起点约 `0.96`，终点约 `0.93`；净变化为 `-0.03`，而波动尺度为 `0.08`，因此判断为基本平稳。

Reviewer：`keep`，naturalness `5`，answerability `5`，risk `low`。

评价：这是适合 benchmark 的基本题型，能测试趋势判断和领域阈值理解。但要避免过多趋势/极值题，必须继续增加 counterfactual、lead-lag、cross-variable 和 domain-context 正例。

### Traffic

ID：`traffic_broad::traffic_scenario_021::traffic_combined_stress_context`

场景：交通工程师正在查看一段交通系统窗口，其中平均车速、排队长度和车道占有率都作为对齐的时间序列记录。更低队列和更高速度通常表示交通流更好。

问题：根据综合交通压力分数和事件时段，这个交通窗口最可能处于哪种运行状态？

选项：A. 中等综合拥堵 / B. 严重综合拥堵 / C. 稳定综合交通状态 / D. 综合状态不清楚

Gold：A，中等综合拥堵。

证据：综合压力分数达到或超过 `6.0` 时视为严重综合拥堵；`3.0` 到 `6.0` 以下视为中等综合拥堵；更低分数视为稳定综合交通状态，除非事件证据不清楚。本窗口综合压力分数为 `3.72`，事件位于中期，严重事件标记为 `true`；因此判断为中等综合拥堵。

Reviewer：`keep`，naturalness `4`，answerability `5`，risk `low`。

评价：这是比单纯趋势/极值更好的 benchmark 样式，因为它要求读者结合规则、数值、事件时段和状态选项。风险是“综合压力分数”如果没有从 simulator state 中透明计算，容易被认为是派生黑箱分数；正式 benchmark 需要在数据卡里解释该分数来源。

### Water

ID：`water_broad::water_scenario_006::water_leak_anomaly`

场景：供水网络运维人员正在查看服务窗口。`x0` 是水压，`x1` 是管道流量，`x2` 是水箱蓄水量。低水压可能表示供水风险。

问题：把这个供水服务窗口按时间分成早期、中期和后期后，最强的疑似漏水压力扰动出现在什么位置？

选项：A. 早期 / B. 后期 / C. 中期 / D. 没有明显疑似漏水扰动

Gold：B，后期。

证据：早期、中期和后期选项按当前局部窗口的时间顺序三等分。疑似漏水扰动检测器把最强事件定位在局部窗口第 `199` 步附近，因此判断为后期。

Reviewer：`keep`，naturalness `4`，answerability `5`，risk `low`。

评价：可用，但“检测器”会引入工具/元数据感。后续更好的写法是把检测器输出转成可读证据，例如“水压在后段出现最强下探，同时流量出现异常抬升”，而不是直接说 detector。

## Failure Case Study

### CityLearn: 规则与 gold 冲突

ID：`citylearn_broad::citylearn_challenge_2022_phase_1_start4096_h2048_b5::w1408_1920::city_domain_demand_context`

问题：按照需求压力分档规则，建筑控制器应把这个窗口视为什么需求压力状态？

证据：低需求压力要求平均负载低于 `3` 且峰值低于 `8`；本窗口平均负载为 `3.72`，峰值为 `9.20`。

Gold：低建筑需求压力。

Reviewer：`reject`，risk `high`。

失败原因：可见规则和数值支持“中等需求压力”，但 support slot/gold 写成“低建筑需求压力”。这类样本必须回源修 deterministic label 或规则，不能靠 reviewer 改文案修复。

### Grid2Op: “没有实质变化”缺阈值

ID：`grid2op_broad_cf::h2048_c-1_t512_line4::post1665_1793::grid_counterfactual_mean_stress`

问题：在这个事件后片段里，断开线路如何改变平均最大线路负载压力？

证据：干预后与事实运行的平均压力差为 `-0.01`，因此判断为没有实质变化。

Reviewer：`revise`，risk `medium`。

失败原因：`-0.01` 可被理解成轻微降低；若要归为“没有实质变化”，必须在题面或证据里说明等价阈值，例如“绝对差小于 0.02 视为近似不变”。

### Traffic: 事件/异常定义不够显式

ID：`traffic_broad::traffic_scenario_035::traffic_incident_anomaly`

问题：这段交通轨迹是否包含明显的事故式扰动；如果有，大致发生在哪一段？

证据：事故检测器没有在这个窗口标记受控事件，因此判断为没有明显交通事件。

Reviewer：`revise`，risk `low`。

失败原因：答案是可答的，但“明显事故式扰动”依赖检测器或阈值；早/中/后也没有在场景中说明边界。可通过补充三等分规则和异常判定证据修复。

### Water: 阶段均值规则与数值矛盾

ID：`water_broad::water_scenario_021::water_event_recovery_context`

问题：按照事件前、中、后三阶段均值规则，事件后的水压状态最符合哪一种判断？

证据：恢复要求事件中水压低于事件前，且事件后高于事件中但不超过事件前。实际数值为事件前 `77.61`，事件中 `77.76`，事件后 `77.60`。

Gold：水压恢复。

Reviewer：`reject`，risk `high`。

失败原因：数值不满足恢复规则。该样本暴露了水系统 event-recovery generator 的 deterministic rule/label 对齐问题。

## 质量判断

可投稿 benchmark 的雏形是可行的，但当前还只能算 pilot batch：

- 优点：多源、多任务族、support-slot grounded、reviewer 能拦下 gold/evidence 冲突，且 positive 样本已经能形成自然 QA 风格。
- 缺口：AIOps 新样本不足；FinRL 暂缺；Water/Traffic 的 event/context 规则需要修；部分中文 evidence 未完全本地化；source 之间通过率不均衡。
- 风险：如果直接把 75 条 positive 扩成 benchmark，不足以支撑 EMNLP 主会 benchmark claim；但作为“benchmark generation pipeline + reviewer-gated pilot”的 evidence，可以进入 paper 的 early dataset construction/case study 部分。

## 下一步扩增规则

1. 先修 deterministic rule/label 对齐：重点是 `city_domain_demand_context`、`water_event_recovery_context`、`water_combined_stress_context`、`traffic_combined_stress_context` 中的规则和 gold 冲突。
2. 增加 pre-review 规则过滤：凡是可见规则与 support slot label 不一致，直接在 deterministic 阶段 reject，不送 GPT reviewer。
3. 强制中文本地化：`question_zh`、`evidence_zh` 不允许保留英文句子。
4. 反事实和“无实质变化”必须显式给阈值：例如 `abs(diff) < epsilon` 才能映射到相近/无实质变化。
5. 对 detector/事件类题目做口语化转写：不要只说“检测器标记”，要说明曲线表现或明示检测器规则。
6. 正式扩增时使用严格去重候选；AIOps 和 FinRL 需要补新的 simulator-derived rows。
7. reviewer 工程改并发和缓存；建议先规则过滤，再对剩余候选全量 reviewer，最后每个 source/task family 抽样人工复核。

