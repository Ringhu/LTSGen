# Natural-QCC Seed Quality Review v1_policy_recheck（2026-05-21）

## 结论

这轮 review 的核心结论是：当前输入 seed 的 QA 结构可以继续用，但 caption 训练目标仍需清洗。

- 总 review 条目：72
- QA seed ready：72/72
- caption train ready：10/72
- needs error attribution：15/72
- decision counts：{'revise': 63, 'keep': 9}

最重要的问题是：`self_contained_reasoning_qa_v2` 中仍有 caption 或题面问题，`natural_qcc_case_quality_v1` 仍需要继续人工 review；不能把 GPT data-only wrong 当成自动 reject。

## 一句话判断

- **QA seed ready**：72/72。
- **caption train ready**：10/72。
- **GPT data-only 错误不自动删题**：15 条需要错误归因。

## 修复队列

| 队列 | 数量 | 含义 | 下一步 |
| --- | ---: | --- | --- |
| case-study 可展示 seed | 9 | `natural_qcc_case_quality_v1` 中基本可给人看的 case | 若仍有 minor issue，则人工复核后使用 |
| case-study caption-ready seed | 10 | 12 条 case 中 caption 监督基本可用的条目 | 可作为 v3 caption 写法模板 |
| self-contained QA 可用但 caption 需清洗 | 60 | 题面/规则/数据基本可答，但 target caption 不合格 | 删除 `Answer label`，把规则模板改成自然 evidence caption |
| self-contained QA 需重写 | 0 | deterministic QA gate 仍不通过 | 先修题面/变量/规则，再重新 review |

## 分集合结果

| seed set | n | decision | QA ready | caption train ready |
| --- | ---: | --- | ---: | ---: |
| `natural_qcc_case_quality_v1` | 12 | {'revise': 3, 'keep': 9} | 12 | 10 |
| `self_contained_reasoning_qa_v2` | 60 | {'revise': 60} | 60 | 0 |

## 分域结果

| domain | n | decision | QA ready | caption train ready |
| --- | ---: | --- | ---: | ---: |
| `aiopslab` | 12 | {'keep': 2, 'revise': 10} | 12 | 2 |
| `citylearn` | 12 | {'revise': 11, 'keep': 1} | 12 | 1 |
| `finrl` | 12 | {'keep': 2, 'revise': 10} | 12 | 2 |
| `grid2op` | 12 | {'revise': 12} | 12 | 1 |
| `traffic` | 12 | {'keep': 2, 'revise': 10} | 12 | 2 |
| `water` | 12 | {'keep': 2, 'revise': 10} | 12 | 2 |

## 主要问题

- `caption_too_rule_template_like`: 60
- `target_caption_answer_label_leak`: 60
- `domain_known_review_priority`: 20
- `gpt_data_only_wrong`: 15
- `simulator_name_in_scene`: 6
- `known_task_weakness`: 4
- `vague_variable_definition`: 3
- `caption_answer_phrase`: 2
- `caption_conclusion_implicit`: 2

解释：

- `target_caption_answer_label_leak`：caption 目标里显式写了答案标签，这会把 evidence caption 训练成答案复述，不符合 evidence-only QCC。
- `caption_too_rule_template_like`：caption 更像规则执行结果，而不是先描述时序形态再解释判断。
- `gpt_data_only_wrong`：强 LLM 只看题面和数据时答错；这只是诊断信号，需要归因，不能单独证明题目不可答。
- `vague_variable_definition`：变量仍写成上下文/辅助信号，普通回答者不知道怎么用。

## natural_qcc_case_quality_v1 逐条结论

| domain | task | decision | QA ready | caption ready | 主要建议 |
| --- | --- | --- | ---: | ---: | --- |
| `grid2op` | `grid_counterfactual_overload_exposure` | `revise` | 1 | 0 | 训练 caption 时去掉“supports the answer”等模板句，保留时序现象和判断依据。 |
| `grid2op` | `grid_domain_stress_context` | `revise` | 1 | 1 | 把 simulator 名称改成普通领域表述，例如“电网运行窗口”“建筑能耗窗口”“路网窗口”。 |
| `citylearn` | `city_domain_demand_context` | `revise` | 1 | 0 | 训练 caption 时去掉“supports the answer”等模板句，保留时序现象和判断依据。 |
| `citylearn` | `city_window_total_load` | `keep` | 1 | 1 | 把 simulator 名称改成普通领域表述，例如“电网运行窗口”“建筑能耗窗口”“路网窗口”。 |
| `traffic` | `traffic_domain_congestion_context` | `keep` | 1 | 1 | 把 simulator 名称改成普通领域表述，例如“电网运行窗口”“建筑能耗窗口”“路网窗口”。 |
| `traffic` | `traffic_event_recovery_context` | `keep` | 1 | 1 | 可作为高质量 case seed；扩增时保持当前场景-规则-问题-caption 结构。 |
| `water` | `water_domain_resilience_context` | `keep` | 1 | 1 | 把 simulator 名称改成普通领域表述，例如“电网运行窗口”“建筑能耗窗口”“路网窗口”。 |
| `water` | `water_leak_counterfactual_pressure` | `keep` | 1 | 1 | 选项里的“影响方向混合”不够自然，建议改成更业务化的复核/无明显变化选项。 |
| `aiopslab` | `aiops_official_cross_signal_relation` | `keep` | 1 | 1 | 把 simulator 名称改成普通领域表述，例如“电网运行窗口”“建筑能耗窗口”“路网窗口”。 |
| `aiopslab` | `aiops_official_memory_extrema` | `keep` | 1 | 1 | 这题主要问峰值位置，推理深度偏弱，可保留作 easy split，但不应作为主打 case。 |
| `finrl` | `fin_domain_market_regime` | `keep` | 1 | 1 | 把 x1/x2/x3 的业务含义写成可操作变量，不能只说上下文或辅助信号。 |
| `finrl` | `fin_drawdown_price` | `keep` | 1 | 1 | 可作为高质量 case seed；扩增时保持当前场景-规则-问题-caption 结构。 |

其中最适合先给你人工看的 case：

- `citylearn` / `city_window_total_load`
- `traffic` / `traffic_domain_congestion_context`
- `traffic` / `traffic_event_recovery_context`
- `water` / `water_domain_resilience_context`
- `water` / `water_leak_counterfactual_pressure`
- `aiopslab` / `aiops_official_cross_signal_relation`
- `aiopslab` / `aiops_official_memory_extrema`
- `finrl` / `fin_domain_market_regime`
- `finrl` / `fin_drawdown_price`

## self_contained_reasoning_qa_v2 逐条结论

这批 self-contained 样本的主要作用是扩增 seed，不是 case-study 展示稿。GPT data-only 答错的样本需要错误归因，但不再被自动排除。

| domain | task | decision | QA ready | caption ready | 主要建议 |
| --- | --- | --- | ---: | ---: | --- |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `grid2op` | `self_contained_grid_counterfactual_risk` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `citylearn` | `self_contained_building_net_load_reserve` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `traffic` | `self_contained_traffic_recovery_reasoning` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `water` | `self_contained_water_service_recovery` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `water` | `self_contained_water_service_recovery` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `water` | `self_contained_water_service_recovery` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `water` | `self_contained_water_service_recovery` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `water` | `self_contained_water_service_recovery` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `water` | `self_contained_water_service_recovery` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `water` | `self_contained_water_service_recovery` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `water` | `self_contained_water_service_recovery` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `water` | `self_contained_water_service_recovery` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `water` | `self_contained_water_service_recovery` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `aiopslab` | `self_contained_aiops_symptom_triage` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |
| `finrl` | `self_contained_finrl_return_drawdown_regime` | `revise` | 1 | 0 | 生成 SFT 前移除 target_caption 中的 Answer label 句子。 |

## Self-contained QA 需重写样本分布

- 暂无 QA 需重写样本。

## 下一步修复顺序

1. 先修 caption target：从 self-contained 的 `target_caption/output` 中移除 `Answer label`，改成 evidence-only。
2. 对 GPT data-only 错误做归因：区分模型输出不一致、模型能力不足、规则歧义和特征不足。
3. 重写 Natural-QCC case-quality 中的模糊变量：尤其是 `上下文/辅助信号/背景价格信号`。
4. 用本脚本作为 reviewer gate，只有 QA ready 和 caption train ready 都通过的样本才进入扩增和 qcond/no-question 训练。

## 产物

- review JSONL: `.research/general-qcc-captioner-20260515/seed_quality_review_v1_policy_recheck_20260521/natural_qcc_seed_quality_review_v1_policy_recheck.jsonl`
- summary JSON: `.research/general-qcc-captioner-20260515/seed_quality_review_v1_policy_recheck_20260521/natural_qcc_seed_quality_review_v1_policy_recheck_summary.json`
- report: `.research/general-qcc-captioner-20260515/seed_quality_review_v1_policy_recheck_20260521/NATURAL_QCC_SEED_QUALITY_REVIEW_V1_POLICY_RECHECK_20260521_ZH.md`

