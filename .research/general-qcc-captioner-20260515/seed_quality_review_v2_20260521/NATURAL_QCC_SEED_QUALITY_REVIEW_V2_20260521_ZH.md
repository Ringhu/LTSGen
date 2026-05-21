# Natural-QCC Seed Quality Review v2（2026-05-21）

## 结论

这轮 review 的核心结论是：当前输入 seed 已通过 QA-ready 和 caption-train-ready 两个 gate，可以进入小规模扩增/训练 smoke。

- 总 review 条目：72
- QA seed ready：72/72
- caption train ready：72/72
- needs error attribution：15/72
- decision counts：{'keep': 72}

最重要的变化是：`self_contained_reasoning_qa_v3` 已移除 `Answer label` 和规则模板句，`natural_qcc_case_quality_v2` 已补清读者场景、变量解释和中英文 caption 对齐。GPT data-only 错误仍保留为错误归因信号。

## 一句话判断

- **QA seed ready**：72/72。
- **caption train ready**：72/72。
- **GPT data-only 错误不自动删题**：15 条需要错误归因。

## 修复队列

| 队列 | 数量 | 含义 | 下一步 |
| --- | ---: | --- | --- |
| case-study 可展示 seed | 12 | `natural_qcc_case_quality_v2` 中基本可给人看的 case | 若仍有 minor issue，则人工复核后使用 |
| case-study caption-ready seed | 12 | 12 条 case 中 caption 监督基本可用的条目 | 可作为 v3 caption 写法模板 |
| self-contained QA 可用但 caption 需清洗 | 0 | 题面/规则/数据基本可答，但 target caption 不合格 | 删除 `Answer label`，把规则模板改成自然 evidence caption |
| self-contained QA 需重写 | 0 | deterministic QA gate 仍不通过 | 先修题面/变量/规则，再重新 review |

## 分集合结果

| seed set | n | decision | QA ready | caption train ready |
| --- | ---: | --- | ---: | ---: |
| `natural_qcc_case_quality_v2` | 12 | {'keep': 12} | 12 | 12 |
| `self_contained_reasoning_qa_v3` | 60 | {'keep': 60} | 60 | 60 |

## 分域结果

| domain | n | decision | QA ready | caption train ready |
| --- | ---: | --- | ---: | ---: |
| `aiopslab` | 12 | {'keep': 12} | 12 | 12 |
| `citylearn` | 12 | {'keep': 12} | 12 | 12 |
| `finrl` | 12 | {'keep': 12} | 12 | 12 |
| `grid2op` | 12 | {'keep': 12} | 12 | 12 |
| `traffic` | 12 | {'keep': 12} | 12 | 12 |
| `water` | 12 | {'keep': 12} | 12 | 12 |

## 主要问题

- `domain_known_review_priority`: 20
- `gpt_data_only_wrong`: 15
- `known_task_weakness`: 4
- `caption_conclusion_implicit`: 1

解释：

- `target_caption_answer_label_leak`：caption 目标里显式写了答案标签，这会把 evidence caption 训练成答案复述，不符合 evidence-only QCC。
- `caption_too_rule_template_like`：caption 更像规则执行结果，而不是先描述时序形态再解释判断。
- `gpt_data_only_wrong`：强 LLM 只看题面和数据时答错；这只是诊断信号，需要归因，不能单独证明题目不可答。
- `vague_variable_definition`：变量仍写成上下文/辅助信号，普通回答者不知道怎么用。

## natural_qcc_case_quality_v2 逐条结论

| domain | task | decision | QA ready | caption ready | 主要建议 |
| --- | --- | --- | ---: | ---: | --- |
| `grid2op` | `grid_counterfactual_overload_exposure` | `keep` | 1 | 1 | 可作为高质量 case seed；扩增时保持当前场景-规则-问题-caption 结构。 |
| `grid2op` | `grid_domain_stress_context` | `keep` | 1 | 1 | 可作为高质量 case seed；扩增时保持当前场景-规则-问题-caption 结构。 |
| `citylearn` | `city_domain_demand_context` | `keep` | 1 | 1 | 阈值是当前 case 临时写入的经验阈值，仍需改成数据生成规范里的正式业务规则。 |
| `citylearn` | `city_window_total_load` | `keep` | 1 | 1 | 可作为高质量 case seed；扩增时保持当前场景-规则-问题-caption 结构。 |
| `traffic` | `traffic_domain_congestion_context` | `keep` | 1 | 1 | 可作为高质量 case seed；扩增时保持当前场景-规则-问题-caption 结构。 |
| `traffic` | `traffic_event_recovery_context` | `keep` | 1 | 1 | 可作为高质量 case seed；扩增时保持当前场景-规则-问题-caption 结构。 |
| `water` | `water_domain_resilience_context` | `keep` | 1 | 1 | 漏损压力状态的判定依赖最低水压、平均水压、流量的组合，但题面还没有给出足够明确的优先级规则。 |
| `water` | `water_leak_counterfactual_pressure` | `keep` | 1 | 1 | 选项里的“影响方向混合”不够自然，建议改成更业务化的复核/无明显变化选项。 |
| `aiopslab` | `aiops_official_cross_signal_relation` | `keep` | 1 | 1 | 可作为高质量 case seed；扩增时保持当前场景-规则-问题-caption 结构。 |
| `aiopslab` | `aiops_official_memory_extrema` | `keep` | 1 | 1 | 这题主要问峰值位置，推理深度偏弱，可保留作 easy split，但不应作为主打 case。 |
| `finrl` | `fin_domain_market_regime` | `keep` | 1 | 1 | 可作为高质量 case seed；扩增时保持当前场景-规则-问题-caption 结构。 |
| `finrl` | `fin_drawdown_price` | `keep` | 1 | 1 | 可作为高质量 case seed；扩增时保持当前场景-规则-问题-caption 结构。 |

其中最适合先给你人工看的 case：

- `grid2op` / `grid_counterfactual_overload_exposure`
- `grid2op` / `grid_domain_stress_context`
- `citylearn` / `city_domain_demand_context`
- `citylearn` / `city_window_total_load`
- `traffic` / `traffic_domain_congestion_context`
- `traffic` / `traffic_event_recovery_context`
- `water` / `water_domain_resilience_context`
- `water` / `water_leak_counterfactual_pressure`
- `aiopslab` / `aiops_official_cross_signal_relation`
- `aiopslab` / `aiops_official_memory_extrema`
- `finrl` / `fin_domain_market_regime`
- `finrl` / `fin_drawdown_price`

## self_contained_reasoning_qa_v3 逐条结论

这批 self-contained 样本的主要作用是扩增 seed，不是 case-study 展示稿。GPT data-only 答错的样本需要错误归因，但不再被自动排除。

| domain | task | decision | QA ready | caption ready | 主要建议 |
| --- | --- | --- | ---: | ---: | --- |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `water` | `self_contained_water_service_recovery` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `water` | `self_contained_water_service_recovery` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `water` | `self_contained_water_service_recovery` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `water` | `self_contained_water_service_recovery` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `water` | `self_contained_water_service_recovery` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `water` | `self_contained_water_service_recovery` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `water` | `self_contained_water_service_recovery` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `water` | `self_contained_water_service_recovery` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `water` | `self_contained_water_service_recovery` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `water` | `self_contained_water_service_recovery` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `keep` | 1 | 1 | 进入 data-only 错误归因：先判断是模型输出不一致、模型能力不足、规则歧义还是特征不足；不要自动删除。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `keep` | 1 | 1 | 可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。 |

## Self-contained QA 需重写样本分布

- 暂无 QA 需重写样本。

## 下一步修复顺序

1. 先修 caption target：从 self-contained 的 `target_caption/output` 中移除 `Answer label`，改成 evidence-only。
2. 对 GPT data-only 错误做归因：区分模型输出不一致、模型能力不足、规则歧义和特征不足。
3. 重写 Natural-QCC case-quality 中的模糊变量：尤其是 `上下文/辅助信号/背景价格信号`。
4. 用本脚本作为 reviewer gate，只有 QA ready 和 caption train ready 都通过的样本才进入扩增和 qcond/no-question 训练。

## 产物

- review JSONL: `.research/general-qcc-captioner-20260515/seed_quality_review_v2_20260521/natural_qcc_seed_quality_review_v2.jsonl`
- summary JSON: `.research/general-qcc-captioner-20260515/seed_quality_review_v2_20260521/natural_qcc_seed_quality_review_v2_summary.json`
- report: `.research/general-qcc-captioner-20260515/seed_quality_review_v2_20260521/NATURAL_QCC_SEED_QUALITY_REVIEW_V2_20260521_ZH.md`

