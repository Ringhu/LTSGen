# Public Raw TSQA v4 Hard-but-Fair 复核报告 2026-05-21

## 结论

- 当前完整评测 run 数：`4`；顶级闭源参照模型：`gpt-5.5` / `full_gpt55_public_raw_tsqa_v4_39items_bilingual_nojson`。
- 顶级闭源模型错误 prompt：`4/78`，全部来自 `water_service`。
- hard candidate reviewer 已复审：`4` 条，decision `{'revise': 4}`，eligible `{'false': 4}`。
- 当前可直接认证的 hard subset：`0`。原因：GPT-5.5 错题全部被 reviewer 判为需要修订，主要风险是事件分段和阈值表达不清。
- 因此，现有 pilot 只能证明 benchmark 有模型区分度，不能直接声称“顶级闭源模型系统性答不上来”。下一步应先修复 hard case 的题面证据链，再扩增。

## 完整模型结果

| Run | Provider | Model | Acc. | EN | ZH | Water |
|---|---|---|---:|---:|---:|---:|
| `full_gpt55_public_raw_tsqa_v4_39items_bilingual_nojson` | `openai` | `gpt-5.5` | 0.9487 | 0.9487 | 0.9487 | 0.6000 |
| `full_gpt54_public_raw_tsqa_v4_39items_bilingual` | `openai` | `gpt-5.4` | 0.7308 | 0.7179 | 0.7436 | 0.6000 |
| `full_hf_qwen3_4b_inst_public_raw_tsqa_v4_39items_bilingual` | `hf` | `Qwen3-4B-Instruct-2507` | 0.4615 | 0.4103 | 0.5128 | 0.2000 |
| `full_hf_qwen25_3b_public_raw_tsqa_v4_39items_bilingual` | `hf` | `Qwen2.5-3B-Instruct` | 0.4359 | 0.3846 | 0.4872 | 0.2000 |

## Hard-but-Fair Gate

- `verifier_supported`：gold answer 必须来自 deterministic support slots，且 source seed/probe gate 通过。
- `top_closed_model_wrong`：GPT-5.5 在完整原始时序 prompt 下答错，只作为候选信号。
- `not_certified_hard`：如果错因可能来自窗口分段、阈值含糊、选项表达或隐藏上下文，则不能作为 hard subset。
- `scaling_sensitive_medium`：GPT-5.5 可答对，但 GPT-5.4/Qwen 多数失败；适合作为中等难度或 scaling 分析。

## 决策分布

- by decision: `{'verified_easy_or_medium': 66, 'scaling_sensitive_medium': 8, 'revise_before_hard': 4}`
- top-model wrong by domain: `{'water_service': 4}`

## 顶级模型错题复核

| ID | Lang | Gold | GPT-5.5 Pred | Audit Decision | Reviewer | Eligible | Evidence | Review note |
|---|---|---|---|---|---|---|---|---|
| `public_raw_tsqa_v4_00019` | `en` | `C` | `A` | `revise_before_hard` | `revise` | `false` | pre_pressure_mean=71.24; event_pressure_mean=71.19; post_pressure_mean=72.33; min_pressure=66.21; event_flow_change=-0.... | 该题的自然任务表述看起来合理，但公开提示只说明时序覆盖事件前、中、后窗口，并未明确哪些时间点属于 pre/event/post 分段。金标依赖 pre_pressure_mean、event_pressure_mean、post_pressure_mean 和 event_flow_change 等分段统计，若没有公... |
| `public_raw_tsqa_v4_00019` | `zh` | `服务保持稳定` | `B` | `revise_before_hard` | `revise` | `false` | pre_pressure_mean=71.24; event_pressure_mean=71.19; post_pressure_mean=72.33; min_pressure=66.21; event_flow_change=-0.... | 该题的自然任务只说明时序覆盖扰动前-中-后窗口并按时间排列，但没有公开给出哪些时间点属于事件前、事件中、事件后。金答案依赖 pre/event/post 均值和 event_flow_change 等确定性支持槽；如果模型不知道分段边界，可能会根据局部水压下降和后续回升判断为“扰动后恢复”，这不是纯粹的时间序列推理难... |
| `public_raw_tsqa_v4_00021` | `en` | `A` | `B` | `revise_before_hard` | `revise` | `false` | pre_pressure_mean=71.4; event_pressure_mean=57.82; post_pressure_mean=67.46; min_pressure=51.12; event_flow_change=3.397 | 该题的自然任务整体合理，变量也基本自包含，但关键判定边界不够清楚。题干使用“very low”“clearly increases”“remains depressed”“close to pre-event”等相对表述，没有给出硬阈值。当前证据中事件后水压 67.46 相比事件前 71.40 只低约 3.94，模型... |
| `public_raw_tsqa_v4_00021` | `zh` | `持续漏水压力风险` | `B` | `revise_before_hard` | `revise` | `false` | pre_pressure_mean=71.4; event_pressure_mean=57.82; post_pressure_mean=67.46; min_pressure=51.12; event_flow_change=3.397 | 该题的自然任务整体自洽，变量也足够，但关键判定边界不清楚。公开题面只说“水压降得很低”“流量明显升高”“事件后水压仍明显低于事件前”“接近事件前水平”，没有给出具体阈值或比例边界。支持摘要中事件后水压均值 67.46 相比事件前 71.4 只低约 4 个单位，模型将其理解为“接近事件前”并选择恢复，是合理的题面解读错... |

## Scaling-sensitive 样本

这些样本 GPT-5.5 答对，但至少 3 个完整 run 答错，适合用来画模型能力曲线，不适合声称顶级闭源模型失败。

| ID | Lang | Domain | Gold | Wrong Runs | Evidence |
|---|---|---|---|---|---|
| `public_raw_tsqa_v4_00009` | `en` | `building_energy` | `D` | `3` | early_net_load_mean=5.326; middle_net_load_mean=4.746; late_net_load_mean=5.254; top_second_gap=0.0711 |
| `public_raw_tsqa_v4_00010` | `en` | `building_energy` | `D` | `3` | early_net_load_mean=4.716; middle_net_load_mean=4.246; late_net_load_mean=4.771; top_second_gap=0.05494 |
| `public_raw_tsqa_v4_00011` | `en` | `building_energy` | `D` | `3` | early_net_load_mean=4.954; middle_net_load_mean=4.337; late_net_load_mean=4.807; top_second_gap=0.147 |
| `public_raw_tsqa_v4_00011` | `zh` | `building_energy` | `D` | `3` | early_net_load_mean=4.954; middle_net_load_mean=4.337; late_net_load_mean=4.807; top_second_gap=0.147 |
| `public_raw_tsqa_v4_00012` | `en` | `building_energy` | `D` | `3` | early_net_load_mean=4.833; middle_net_load_mean=4.21; late_net_load_mean=4.698; top_second_gap=0.1352 |
| `public_raw_tsqa_v4_00012` | `zh` | `building_energy` | `D` | `3` | early_net_load_mean=4.833; middle_net_load_mean=4.21; late_net_load_mean=4.698; top_second_gap=0.1352 |
| `public_raw_tsqa_v4_00029` | `en` | `service_telemetry` | `D` | `3` | memory_first_half_mean=9.473e+06; memory_second_half_mean=9.4e+06; memory_growth_ratio=-0.007746; rx_peak_median_ratio=1.385; tx_peak_media... |
| `public_raw_tsqa_v4_00037` | `en` | `market` | `D` | `3` | total_return=0.1695; max_drawdown=-0.3767 |

## Qwen 3B/4B/8B/32B 资产复核

| Target | Status | Path/Route | Note |
|---|---|---|---|
| `3B` | `evaluated` | `/cluster/home/user1/fenghaoran/model/Qwen2.5-3B-Instruct` | 本地 HF checkpoint 可加载，已完成 39 rows / 78 prompts 双语评测。 |
| `4B` | `evaluated` | `/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507` | 本地 HF checkpoint 可加载，已完成 39 rows / 78 prompts 双语评测。 |
| `8B` | `not_local_checkpoint` | `Qwen/Qwen3-8B via old vLLM script; result directories under TSModel are evaluation outputs, not checkpoints` | A100 上发现 run_qwen3-8B.bash 和若干 Qwen3-8B result JSON，但未发现可直接加载的本地 HF checkpoint；不在本轮下载大模型。 |
| `32B` | `not_local_checkpoint` | `old scripts refer to /cluster/home/user1/zzy/model or external DashScope qwen3-32b route` | 常见本地目录未发现可确认的 Qwen 32B HF checkpoint；存在脚本/API 线索但包含外部服务路线或不明模型目录，不作为正式本地 baseline。 |

## 扩增建议

1. 先重写 `water_service`：公开 prompt 必须给出事件分段或明确可由时间索引推断的分段规则，并把 `remains depressed / close to pre-event` 改成可审计阈值。
2. 将 `building_energy` 的 balanced reserve、`aiops` 的 no dominant symptom、`market` 的 drawdown-priority 作为 scaling-sensitive medium pool。
3. 扩增时每个样本先过 deterministic verifier，再过 reviewer gate，最后才用 GPT-5.5 失败率定义 hard subset。
4. 论文中报告 easy/medium/hard 三层，不把当前 39 条直接包装成 hard benchmark。
