# MultiSim v5 Schema Alignment Completion Report

日期：2026-05-18

## 结论

这轮已经把数据源从单一 Grid2Op 扩展到六类 simulator / domain source，并产出一个统一 QCC/SFT 入口：

- Grid2Op：电网长时序，含真实观测与 counterfactual。
- CityLearn：建筑能耗长时序。
- FinRL scaled：金融市场长时序。
- Water / WNTR：供水网络长时序，官方 simulator export。
- Traffic / SUMO：交通网络长时序，官方 simulator export。
- AIOpsLab official：Kubernetes 微服务故障 telemetry，3090 上真实 AIOpsLab 采集。

统一入口在 A100：

`/cluster/home/user1/hulining/LTSGEN/.research/general-qcc-captioner-20260515/multisim_qcc_v5_schema_aligned/`

本地保留了小报告，不复制 377MB 数据本体：

- `.research/general-qcc-captioner-20260515/multisim_qcc_v5_schema_aligned_schema_report.json`
- `.research/general-qcc-captioner-20260515/multisim_qcc_v5_schema_alignment_audit.json`

## 完成了什么

### 1. AIOpsLab 官方采集链路

新增脚本：

`scripts/generate/collect_aiopslab_official_cases.py`

在 3090 上运行了 3 个 AIOpsLab official cases：

| case | split | CSV 数量 | 状态 |
|---|---:|---:|---|
| `port_misconfig_seed0_user-service` | test | 20 | ok |
| `port_misconfig_seed0_text-service` | dev | 20 | ok |
| `port_misconfig_seed0_post-storage-service` | train | 20 | ok |

3090 原始采集路径：

`/cluster/home/hulining/aiopslab_ltsgen_cases_v1_20260518/`

采集后检查：`wrk2-job` 和 `test-social-network` pods 无残留。

### 2. AIOpsLab 转 QCC schema

新增脚本：

`scripts/generate/convert_aiopslab_metrics_to_qcc.py`

输出路径：

`.research/general-qcc-captioner-20260515/aiopslab_official_v1/`

结果：

- 总行数：36
- split：train/dev/test = 12/12/12
- task family：12 类
- answer balance：A/B/C/D = 9/9/9/9
- split_group leakage：0
- schema_gate_pass：true

AIOpsLab baseline gate：

| condition | accuracy |
|---|---:|
| oracle evidence caption | 1.0000 |
| generic caption | 0.0000 |
| statistical caption | 0.2500 |

`dataflow_v3_pass=true`。这说明 AIOpsLab official 数据不是简单统计摘要就能解决，必须依赖问题相关证据和 simulator context。

### 3. Water / Traffic 官方源核对

Water:

- source kind：`official_simulator_export`
- official target：WNTR
- n=504
- schema_gate_pass=true
- dev+test gate：oracle=1.0000，generic=0.0190，statistical=0.4286

Traffic:

- source kind：`official_simulator_export`
- official target：SUMO
- n=504
- schema_gate_pass=true
- dev+test gate：oracle=1.0000，generic=0.0524，statistical=0.4286

### 4. MultiSim v5 合并入口

新增脚本：

`scripts/generate/merge_multisim_schema_aligned_sources.py`

A100 输出：

`/cluster/home/user1/hulining/LTSGEN/.research/general-qcc-captioner-20260515/multisim_qcc_v5_schema_aligned/`

核心文件：

- `multisim_qcc_v5_schema_aligned_train_sft.jsonl`
- `multisim_qcc_v5_schema_aligned_eval_devtest_sft.jsonl`
- `multisim_qcc_v5_schema_aligned.jsonl`
- `schema_report.json`
- `schema_alignment_audit.json`

合并统计：

| source | rows used |
|---|---:|
| Grid2Op | 384 |
| CityLearn | 384 |
| FinRL scaled | 384 |
| Water / WNTR | 384 |
| Traffic / SUMO | 384 |
| AIOpsLab official | 36 |

总计：

- n=1956
- train/dev/test = 1292/332/332
- task families = 67
- duplicate_id_count = 0
- split_group_leakage_count = 0
- missing_required_field_count = 0
- schema_gate_pass = true

统一入口包含的抽象能力：

- trend（趋势）
- extrema（极值）
- volatility（波动）
- anomaly（异常）
- periodicity（周期）
- window comparison（窗口比较）
- cross-variable relation（跨变量关系）
- lead-lag（领先-滞后关系）
- counterfactual effect（反事实影响）
- domain context（领域上下文）
- event impact / recovery（事件影响 / 恢复）

### 5. 独立 schema audit

新增脚本：

`scripts/eval/audit_multisim_schema_alignment.py`

审计结论：

- `schema_alignment_pass=true`
- `canonical_training_schema_pass=true`
- `missing_required=[]`
- `missing_required_sources_in_v5=[]`
- `official_source_gate`: water=true, traffic=true, aiops_official=true

注意：原始 Grid2Op / CityLearn 文件是历史格式，缺 `statistical_caption`、`abstract_primitive`、`abstract_answer_label`。v5 合并脚本已经在合并入口补齐这些字段，所以训练和后续实验应使用 v5 canonical files，而不是直接读旧源。

## 训练前仍缺什么

现在完成的是数据层面的多源接入和统一 schema，不等于已经完成混合训练。主要剩两个训练层面的阻塞：

1. 不同 simulator 的 channel count 不完全一致。
   - v5 中 1920 行是 3 维 values。
   - AIOpsLab official 36 行是 4 维 values。
   - 当前 `TSSFTDataset` 可读取单行，但普通 collator 在同一个 batch 内通常要求维度一致。
   - 下一步需要 source-aware batch sampler，或者统一输入投影 / padding mask。

2. AIOpsLab official 目前只有 3 个 case。
   - 这足够证明 3090 上真实 AIOpsLab 链路跑通，并能进入统一 schema。
   - 但还不足以支撑泛化结论。
   - 下一轮应扩展到更多 fault family：`revoke_auth`、`scale_pod_zero`，并做更多 seed。

## 下一步建议

下一步不要直接大训练。建议先做一个 MultiSim batch/data-loader smoke：

1. 实现 source-aware batching：
   - 每个 mini-batch 只放同一 `merge_source_name` 或同一 channel count。
   - 先不改模型结构，避免把问题混在一起。

2. 跑 frozen-Qwen3-4B QCC 小训练：
   - train 使用 v5 train SFT。
   - eval 按 source 分开报告，不只看 overall。
   - 重点看 Grid2Op 是否因为加入其他 simulator 而进一步下降，和 Water/Traffic/AIOps 是否能学到非统计型 context。

3. 然后再做模型层改造：
   - source embedding（数据源嵌入）
   - input projection per source（按源输入投影）
   - balanced source sampler（平衡采样）
   - SCL loss 只在同源/同 task family 内构造 hard negatives，避免跨领域伪负样本。

这比直接把所有数据混在一起训练更稳，因为当前最大的已知风险不是数据读不进来，而是跨源维度和任务语义差异会让模型学到错误捷径。
