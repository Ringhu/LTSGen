# Public Raw TSQA v4 复核后扩增方案 2026-05-21

本文档把本轮 hard-but-fair 复核结果转成下一轮数据扩增规则。核心目标不是让 GPT-5.5 因为题面含糊而答错，而是构造可审计、可复现、顶级模型也会在真实时间序列推理上失败的 hard subset。

## 当前结论

- 当前 39 条 / 78 个双语 prompt 中，GPT-5.5 准确率为 `0.9487`，只错 `water_service` 的 4 个 prompt。
- 这 4 个 prompt 经 hard-case reviewer 复审后全部判为 `revise`，`hard_subset_eligible=false`。
- 因此，当前 pilot 不能直接宣称“顶级闭源模型系统性答不上来”；更准确的结论是：当前数据已有模型区分度，但 certified hard subset 仍为 `0`。

本轮复核产物：

- `hard_case_audit_20260521.jsonl`：逐 prompt 聚合 GPT-5.5、GPT-5.4、Qwen3-4B、Qwen2.5-3B 的对错矩阵。
- `PUBLIC_RAW_TSQA_V4_HARD_CASE_AUDIT_20260521_ZH.md`：自动 hard-case 审计报告。
- `hard_candidate_reviewer_20260521.jsonl`：只针对 GPT-5.5 错题的 reviewer 复审结果。
- `PUBLIC_RAW_TSQA_V4_HARD_CANDIDATE_REVIEW_20260521_ZH.md`：候选 hard case 复审报告。
- `qwen_model_asset_audit_20260521.json`：A100 上 Qwen 3B/4B/8B/32B 资产复核。

## Hard-but-Fair 准入标准

新样本不能仅凭 GPT-5.5 答错进入 hard subset。必须同时满足：

1. `support_slots` 和 deterministic verifier 可复算 gold answer。
2. `natural_task_en/zh` 自包含，公开说明足以让模型知道变量含义、时间顺序、窗口边界和必要阈值。
3. reviewer 判断 `decision=keep`，`fair_hard_score >= 4`，`answerability_score >= 4`，`threshold_clarity_score >= 4`，`window_boundary_clarity_score >= 4`，`accuracy_risk=low`。
4. GPT-5.5 在完整原始时序 prompt 下失败或表现不稳定。
5. 错因不能来自隐藏 metadata、未公开分段、阈值含糊、选项陷阱或语言混杂。

## 需要先修的任务族

### water_service

现有 GPT-5.5 错题集中在这里，但 reviewer 认为不能作为 hard case，原因是：

- 题面只说 before-during-after，没有公开事件前/中/后对应的时间索引或分段规则。
- “very low / clearly increases / remains depressed / close to pre-event”等表达没有量化。
- `public_raw_tsqa_v4_00021` 中 post pressure 相对 pre pressure 只低约 4 个单位，模型判为 recovery 是合理题面解读。

修复规则：

- 在自然任务说明中明确分段，例如“前 1/3 是事件前，中间 1/3 是事件中，最后 1/3 是事件后”，或保存显式 `phase` 公共列。
- 给出可操作阈值，例如：
  - persistent leak：`min_pressure < P_low`，`event_flow_change > F_delta`，且 `pre_pressure_mean - post_pressure_mean > P_depressed_delta`。
  - recovery：事件中压力下降，但 `abs(post_pressure_mean - pre_pressure_mean) <= P_recovery_tol`。
  - stable：事件中没有同时触发低压和流量上升，且 post 接近 pre。
- 扩增时优先生成阈值间隔大的样本，再少量加入边界样本；边界样本必须单独标为 `boundary_review`，不能直接进入 hard subset。

### building_energy

这是当前最好的 scaling-sensitive medium pool：GPT-5.5 可解，GPT-5.4 和 Qwen 多数失败。失败点集中在 balanced reserve，即最大净负荷段和第二高段差距不足阈值时，模型容易强行选择 early/middle/late。

扩增规则：

- 保留 balanced reserve，并系统扩增三类：
  - clear early/middle/late winner；
  - balanced near-threshold；
  - adversarial distractor：局部峰值很高但分段均值不高。
- 公开题面必须说明分段方式和 `top_second_gap` 阈值。
- hard subset 只收 GPT-5.5 也失败且 reviewer 确认阈值充分公开的样本。

### service_telemetry

`no dominant symptom` 样本可以作为中等难度，尤其适合测试模型是否会被局部峰值误导。

扩增规则：

- 生成 memory growth、network burst、CPU saturation、no dominant 四类。
- 对 no dominant 加入 hard negatives：单个局部 spike 明显，但不满足持续/比例阈值。
- 公开题面必须说明判定优先级和每个 symptom 的阈值。

### market

`drawdown-priority` 是有价值的规则组合：即使总收益为正，只要最大回撤超过阈值，就应判 severe drawdown risk。

扩增规则：

- 保留 “return vs max drawdown priority”。
- 生成四类：bullish、bearish、sideways、severe drawdown risk。
- hard cases 优先来自“正收益但大回撤”和“负收益但未达 severe drawdown”的反直觉样本。

## Qwen 评测状态

已完成：

- `Qwen2.5-3B-Instruct`：`0.4359`
- `Qwen3-4B-Instruct-2507`：`0.4615`

未完成：

- 8B：A100 上发现旧 `Qwen/Qwen3-8B` vLLM 脚本和结果目录，但未发现可直接加载的本地 HF checkpoint；当前没有活跃 8B 服务。
- 32B：旧脚本指向 `/cluster/home/user1/zzy/model` 或外部 API 路线；当前未确认可加载本地 checkpoint，也没有活跃服务。

原则：

- 不使用别人脚本里的外部 API key。
- 不在本轮临时下载大模型。
- 若后续用户提供 8B/32B 本地 checkpoint 路径或已启动 OpenAI-compatible endpoint，则可直接复用现有 evaluator 跑 full bilingual。

## 下一轮扩增执行顺序

1. 修复 `water_service` 模板，生成 20-40 条候选样本，覆盖 persistent/recovery/stable/manual review。
2. 对新增 water 样本跑 deterministic verifier，并保留完整 `support_slots`。
3. 用 reviewer gate 过滤题面歧义，只保留 `keep` 样本。
4. 用 GPT-5.5 跑完整原始时序 prompt，筛出真实失败样本。
5. 对 GPT-5.5 失败样本再次 reviewer 复核，只有 `hard_subset_eligible=true` 才进入 hard subset。
6. 并行扩增 `building_energy`、`service_telemetry`、`market` 作为 medium/scaling subset。
7. 更新 benchmark 报告时分层呈现：`sanity/easy`、`scaling-sensitive medium`、`certified hard`。

## 论文表述建议

当前不能写成“GPT-5.5 被该 benchmark 大量难倒”。更稳妥的表述是：

- pilot 显示 raw TSQA 能区分 GPT-5.5、GPT-5.4 和 Qwen 系列；
- 初始 GPT-5.5 错题经 reviewer 复核后暴露了 hard-case 认证的重要性；
- 因此本文采用 hard-but-fair generation protocol：simulator/verifier 生成答案，reviewer 排除歧义，顶级模型失败只作为最后的难度证据。

这会把贡献从“造难题”提升为“可审计的困难 benchmark 生成流程”。
