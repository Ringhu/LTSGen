# Natural QA Balanced8 Lint（2026-05-19）

本产物把 48 条 `balanced_eval_per_source8` 全部改写成自然语言 QA 草案。gold answer 仍来自原始 support slots；LLM/reviewer 不能决定答案。

## 数量

- rows: `48`
- by source: `{'aiopslab_official_v3': 8, 'citylearn': 8, 'finrl_scaled': 8, 'grid2op': 8, 'traffic': 8, 'water': 8}`
- by natural status: `{'exclude_metadata_only': 5, 'candidate': 43}`
- lint issue counts: `{'metadata_only_not_pure_ts': 5}`

## 解释

- `candidate`：可作为自然 TS-QA 候选，仍需 GPT reviewer 或人工审核。
- `exclude_metadata_only`：需要 metadata，不应作为纯时间序列 QA 正例。
- lint issue 是保守提示，不等于错误；用于决定哪些样本要 reviewer 或人工改写。

## 前 12 条样例

- `aiopslab_official_v3` / `aiops_official_app_context` / `exclude_metadata_only`: 这个 AIOpsLab 遥测样本对应哪个官方 metadata 标签？
- `aiopslab_official_v3` / `aiops_official_case_provenance_context` / `exclude_metadata_only`: 这个 AIOpsLab 遥测样本对应哪个官方 metadata 标签？
- `aiopslab_official_v3` / `aiops_official_window_memory` / `candidate`: 按 5% 相对差异规则，这个事故窗口中的服务内存占用是前后相近，还是某一半更重？
- `aiopslab_official_v3` / `aiops_official_window_memory` / `candidate`: 按 5% 相对差异规则，这个事故窗口中的服务内存占用是前后相近，还是某一半更重？
- `aiopslab_official_v3` / `aiops_official_service_role_context` / `exclude_metadata_only`: 这个 AIOpsLab 遥测样本对应哪个官方 metadata 标签？
- `aiopslab_official_v3` / `aiops_official_fault_family_detail_context` / `exclude_metadata_only`: 这个 AIOpsLab 遥测样本对应哪个官方 metadata 标签？
- `aiopslab_official_v3` / `aiops_official_network_volatility` / `candidate`: 运维人员应该把窗口的哪一段视为网络接收速率波动最大的部分？
- `aiopslab_official_v3` / `aiops_official_fault_context` / `exclude_metadata_only`: 这个 AIOpsLab 遥测样本对应哪个官方 metadata 标签？
- `citylearn` / `city_anomaly_total_load` / `candidate`: 把这个窗口按时间分成早期、中期和后期后，最明显的建筑用电需求孤立尖峰出现在什么位置？
- `citylearn` / `city_window_total_load` / `candidate`: 控制器应该在哪一段为更高的平均用电需求做准备？
- `citylearn` / `city_anomaly_total_load` / `candidate`: 尖峰检测器是否在这个窗口发现明显的建筑用电需求孤立尖峰；如果有，它大致位于哪一段？
- `citylearn` / `city_volatility_total_load` / `candidate`: 运维人员应该把窗口的哪一段视为建筑用电需求波动最大的部分？

## 建议

下一步只对 `candidate` 运行 GPT-5.5 reviewer，并把 reviewer gate 作为正例准入条件：`keep`、naturalness >= 4、answerability >= 4、risk low。
