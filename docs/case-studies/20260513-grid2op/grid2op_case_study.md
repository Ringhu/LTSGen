# Grid2Op 中等长度时序 QA 案例分析

这份报告展示当前 Grid2Op simulator-derived（仿真器派生）TS-QA pilot 中选出的代表性案例。所有 ground truth（真值）都来自轨迹数组或 factual/counterfactual（事实/反事实）配对轨迹，LLM 只作为答题模型参与评估，不参与定义正确答案。

## 覆盖范围

| 维度 | 内容 |
| --- | --- |
| 环境 | `rte_case14_realistic` |
| 窗口长度 | 评测集覆盖 `512`、`1024`、`2048`；本报告选取的案例使用 `512/1024` |
| 单轨迹观测案例 | 3 |
| factual/counterfactual（事实/反事实）配对案例 | 2 |
| 展示方法 | `meta_only`、`generic_caption`、`oracle_evidence_caption`、sampled numbers prompt（采样数值提示文本） |

## 主要观察

- 单轨迹的定位题和聚合题差距最大：oracle evidence caption（oracle 证据说明文本）很短且答对，而 sampled numbers prompt（采样数值提示文本）更长却经常答错。
- counterfactual（反事实）案例更适合展示 verifiability（可验证性）和阈值判断；当采样表中刚好包含关键事实时，当前 sampled numbers prompt（采样数值提示文本）也可能答对。
- 逐案例可视化能清楚说明题目真正需要的 evidence（证据）：峰值位置、窗口平均值、第一段/最后一段均值，以及 factual/counterfactual（事实/反事实）干预后的 max-rho 对比。

## 案例

<details>
<summary>案例 01：峰值位置定位：sampled numbers（采样数值）错过后段线路负载峰值</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 案例 ID | `simqa::grid2op_real::rte_case14_realistic_trace_2048_nooverflow::h1024::s0::peak_rho_quarter` |
| 数据来源 | 单条观测轨迹 (`observation`) |
| 窗口长度 | `1024` |
| 任务类型 | 最大线路负载率所在窗口段 (`peak_rho_quarter`) |
| 正确答案 | `A` |
| 正确答案标签 | `第四段` |
| ground truth（真值）来源 | `trace_array` / 仿真器轨迹 |

关键结论：这是最清楚的定位失败样例。真实最大线路负载率出现在第 4 条线路、局部时间步 t=806，属于窗口第四段。generic caption（通用说明文本）没有给出事件位置，sampled numbers prompt（采样数值提示文本）虽然更长，但 32/64/128 三个采样预算都选错了窗口段。

<details>
<summary>时序图</summary>

![simqa::grid2op_real::rte_case14_realistic_trace_2048_nooverflow::h1024::s0::peak_rho_quarter](figures/01_peak_rho_quarter_simqa_grid2op_real_rte_case14_realistic_trace_2048_nooverflow_h1024_s0_peak_rho_.png)

</details>

<details>
<summary>QA 问题</summary>

**问题**

这个 Grid2Op 轨迹窗口中，最大线路负载率出现在第几个窗口段？

**选项**

- A. 轨迹窗口第四段
- B. 轨迹窗口第一段
- C. 轨迹窗口第二段
- D. 轨迹窗口第三段

**正确答案**：`A` - A. 轨迹窗口第四段

</details>

<details>
<summary>caption（说明文本）与 evidence（证据）</summary>

**generic caption（通用说明文本）**

这个 Grid2Op 电网轨迹窗口包含 1024 个时间步上的线路负载率、负载、发电机和潮流变量。

**oracle evidence caption（oracle 证据说明文本）**

最大线路负载率 rho 为 0.999，出现在第 4 条线路、局部时间步 t=806（全局 t=806），属于第四段（后 1/4）。

**可验证事实**

| 验证字段 | 数值 |
| --- | --- |
| `peak_rho` | `0.9990` |
| `peak_local_t` | `806` |
| `peak_global_t` | `806` |
| `peak_line` | `4` |
| `quarter` | `fourth` |

</details>

<details>
<summary>模型回答</summary>

| 输入条件 | 原始条件名 | 预测 | 正确性 | Prompt 字符数 | 选项文本 |
| --- | --- | --- | --- | ---: | --- |
| 仅元信息 | `meta_only` | `D` | 错误 | 382 | D. 轨迹窗口第三段 |
| generic caption（通用说明文本） | `generic_caption` | `C` | 错误 | 521 | C. 轨迹窗口第二段 |
| oracle evidence caption（oracle 证据说明文本） | `oracle_evidence_caption` | `A` | 正确 | 533 | A. 轨迹窗口第四段 |
| sampled numbers（采样数值）32 行 | `numbers_sampled_32` | `D` | 错误 | 12813 | D. 轨迹窗口第三段 |
| sampled numbers（采样数值）64 行 | `numbers_sampled_64` | `D` | 错误 | 25044 | D. 轨迹窗口第三段 |
| sampled numbers（采样数值）128 行 | `numbers_sampled_128` | `D` | 错误 | 49498 | D. 轨迹窗口第三段 |

</details>

<details>
<summary>案例分析</summary>

这是最清楚的定位失败样例。真实最大线路负载率出现在第 4 条线路、局部时间步 t=806，属于窗口第四段。generic caption（通用说明文本）没有给出事件位置，sampled numbers prompt（采样数值提示文本）虽然更长，但 32/64/128 三个采样预算都选错了窗口段。

</details>

</details>

<details>
<summary>案例 02：平均负载聚合：只看采样行不足以恢复窗口级均值</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 案例 ID | `simqa::grid2op_real::rte_case14_realistic_trace_1024::h512::s0::max_avg_load` |
| 数据来源 | 单条观测轨迹 (`observation`) |
| 窗口长度 | `512` |
| 任务类型 | 窗口平均负载最大者 (`max_avg_load`) |
| 正确答案 | `A` |
| 正确答案标签 | `负载 1` |
| ground truth（真值）来源 | `trace_array` / 仿真器轨迹 |

关键结论：这个样例考察整段窗口上的聚合统计。正确证据是负载 1 的窗口平均有功功率最高。generic caption（通用说明文本）和所有 sampled numbers（采样数值）条件都选择了干扰项，说明采样数值行不能稳定替代题目真正需要的窗口级统计量。

<details>
<summary>时序图</summary>

![simqa::grid2op_real::rte_case14_realistic_trace_1024::h512::s0::max_avg_load](figures/02_max_avg_load_simqa_grid2op_real_rte_case14_realistic_trace_1024_h512_s0_max_avg_load.png)

</details>

<details>
<summary>QA 问题</summary>

**问题**

这个 Grid2Op 轨迹窗口中，哪个负载的平均有功功率最高？

**选项**

- A. 负载 1
- B. 负载 2
- C. 负载 5
- D. 负载 0

**正确答案**：`A` - A. 负载 1

</details>

<details>
<summary>caption（说明文本）与 evidence（证据）</summary>

**generic caption（通用说明文本）**

这个 Grid2Op 电网轨迹窗口包含 512 个时间步上的线路负载率、负载、发电机和潮流变量。

**oracle evidence caption（oracle 证据说明文本）**

负载 1 在该窗口中的平均有功功率最高，为 85.189。

**可验证事实**

| 验证字段 | 数值 |
| --- | --- |
| `max_avg_load` | `1` |
| `avg_load_p` | `85.1891` |

</details>

<details>
<summary>模型回答</summary>

| 输入条件 | 原始条件名 | 预测 | 正确性 | Prompt 字符数 | 选项文本 |
| --- | --- | --- | --- | ---: | --- |
| 仅元信息 | `meta_only` | `D` | 错误 | 255 | D. 负载 0 |
| generic caption（通用说明文本） | `generic_caption` | `D` | 错误 | 393 | D. 负载 0 |
| oracle evidence caption（oracle 证据说明文本） | `oracle_evidence_caption` | `A` | 正确 | 341 | A. 负载 1 |
| sampled numbers（采样数值）32 行 | `numbers_sampled_32` | `B` | 错误 | 12668 | B. 负载 2 |
| sampled numbers（采样数值）64 行 | `numbers_sampled_64` | `B` | 错误 | 24875 | B. 负载 2 |
| sampled numbers（采样数值）128 行 | `numbers_sampled_128` | `B` | 错误 | 49298 | B. 负载 2 |

</details>

<details>
<summary>案例分析</summary>

这个样例考察整段窗口上的聚合统计。正确证据是负载 1 的窗口平均有功功率最高。generic caption（通用说明文本）和所有 sampled numbers（采样数值）条件都选择了干扰项，说明采样数值行不能稳定替代题目真正需要的窗口级统计量。

</details>

</details>

<details>
<summary>案例 03：趋势控制样例：简单聚合趋势下 sampled numbers（采样数值）可以答对</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 案例 ID | `simqa::grid2op_real::rte_case14_realistic_trace_2048_nooverflow::h1024::s0::total_load_trend` |
| 数据来源 | 单条观测轨迹 (`observation`) |
| 窗口长度 | `1024` |
| 任务类型 | 前后窗口总负荷趋势 (`total_load_trend`) |
| 正确答案 | `B` |
| 正确答案标签 | `更高` |
| ground truth（真值）来源 | `trace_array` / 仿真器轨迹 |

关键结论：这是一个控制样例。sampled numbers（采样数值）能答对简单的前后段均值趋势问题，但 generic caption（通用说明文本）仍然失败。它提醒我们不要过度声称 raw numbers（原始数值）总是失败；当前观察到的弱点主要集中在定位、聚合和需要精确证据的任务上。

<details>
<summary>时序图</summary>

![simqa::grid2op_real::rte_case14_realistic_trace_2048_nooverflow::h1024::s0::total_load_trend](figures/03_total_load_trend_simqa_grid2op_real_rte_case14_realistic_trace_2048_nooverflow_h1024_s0_total_loa.png)

</details>

<details>
<summary>QA 问题</summary>

**问题**

与第一段相比，最后一段的平均总负荷如何变化？

**选项**

- A. 低于第一段
- B. 高于第一段
- C. 与第一段大致不变
- D. 无法仅从该轨迹窗口判断

**正确答案**：`B` - B. 高于第一段

</details>

<details>
<summary>caption（说明文本）与 evidence（证据）</summary>

**generic caption（通用说明文本）**

这个 Grid2Op 电网轨迹窗口包含 1024 个时间步上的线路负载率、负载、发电机和潮流变量。

**oracle evidence caption（oracle 证据说明文本）**

第一段的平均总负荷为 229.773，最后一段为 263.650，因此最后一段高于第一段。

**可验证事实**

| 验证字段 | 数值 |
| --- | --- |
| `first_quarter_mean_total_load` | `229.7730` |
| `last_quarter_mean_total_load` | `263.6496` |

</details>

<details>
<summary>模型回答</summary>

| 输入条件 | 原始条件名 | 预测 | 正确性 | Prompt 字符数 | 选项文本 |
| --- | --- | --- | --- | ---: | --- |
| 仅元信息 | `meta_only` | `A` | 错误 | 375 | A. 低于第一段 |
| generic caption（通用说明文本） | `generic_caption` | `C` | 错误 | 514 | C. 与第一段大致不变 |
| oracle evidence caption（oracle 证据说明文本） | `oracle_evidence_caption` | `B` | 正确 | 527 | B. 高于第一段 |
| sampled numbers（采样数值）32 行 | `numbers_sampled_32` | `B` | 正确 | 12806 | B. 高于第一段 |
| sampled numbers（采样数值）64 行 | `numbers_sampled_64` | `B` | 正确 | 25037 | B. 高于第一段 |
| sampled numbers（采样数值）128 行 | `numbers_sampled_128` | `B` | 正确 | 49491 | B. 高于第一段 |

</details>

<details>
<summary>案例分析</summary>

这是一个控制样例。sampled numbers（采样数值）能答对简单的前后段均值趋势问题，但 generic caption（通用说明文本）仍然失败。它提醒我们不要过度声称 raw numbers（原始数值）总是失败；当前观察到的弱点主要集中在定位、聚合和需要精确证据的任务上。

</details>

</details>

<details>
<summary>案例 04：反事实阈值：小幅干预刚好跨过过载边界</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 案例 ID | `simqa::grid2op_real_cf::h1024_t128_line0::cf_intervention_overload_severity` |
| 数据来源 | factual/counterfactual（事实/反事实）配对轨迹 (`counterfactual`) |
| 窗口长度 | `1024` |
| 任务类型 | 断线干预后的过载严重度 (`cf_intervention_overload_severity`) |
| 正确答案 | `B` |
| 正确答案标签 | `过载` |
| ground truth（真值）来源 | `trace_array` / 仿真器轨迹 |

关键结论：断开第 0 条线路只带来很小的 max-rho 变化，但 intervention（干预）后的峰值达到 1.024，刚好超过 1.00 过载阈值。低采样预算的 sampled numbers（采样数值）漏掉了这个边界事实；oracle evidence caption（oracle 证据说明文本）直接给出与阈值判断相关的数值。

<details>
<summary>时序图</summary>

![simqa::grid2op_real_cf::h1024_t128_line0::cf_intervention_overload_severity](figures/04_cf_intervention_overload_severity_simqa_grid2op_real_cf_h1024_t128_line0_cf_intervention_overload_severity.png)

</details>

<details>
<summary>QA 问题</summary>

**问题**

在 t=128 断开第 0 条线路后，后续 rollout 中最严重的过载程度是什么？

**选项**

- A. 严重过载，超过 1.20
- B. 发生过载，超过 1.00 但不超过 1.20
- C. 没有超过 1.00 的过载
- D. 无法仅从配对轨迹判断

**正确答案**：`B` - B. 发生过载，超过 1.00 但不超过 1.20

</details>

<details>
<summary>caption（说明文本）与 evidence（证据）</summary>

**generic caption（通用说明文本）**

这组 Grid2Op 配对轨迹包含一条事实 rollout，以及一条在 episode 中断开某条输电线路的反事实 rollout。

**oracle evidence caption（oracle 证据说明文本）**

干预后，后续最大 max-rho 为 1.024，对应超过 1.00 但不超过 1.20 的过载。

**可验证事实**

| 验证字段 | 数值 |
| --- | --- |
| `paired_steps` | `1024` |
| `post_intervention_steps` | `895` |
| `intervention_step` | `128` |
| `line_id` | `0` |
| `factual_line_status_at_intervention` | `1` |
| `intervention_line_status_after` | `0` |
| `mean_abs_total_load_delta_post` | `0.0000` |
| `max_abs_total_load_delta_post` | `0.0000` |
| `mean_max_rho_delta_post` | `0.0090` |
| `max_abs_max_rho_delta_post` | `0.0479` |
| `factual_max_rho_post` | `0.9990` |
| `intervention_max_rho_post` | `1.0240` |
| `intervention_post_peak_max_rho` | `1.0240` |
| `severity` | `overload` |

</details>

<details>
<summary>模型回答</summary>

| 输入条件 | 原始条件名 | 预测 | 正确性 | Prompt 字符数 | 选项文本 |
| --- | --- | --- | --- | ---: | --- |
| 仅元信息 | `meta_only` | `D` | 错误 | 382 | D. 无法仅从配对轨迹判断 |
| generic caption（通用说明文本） | `generic_caption` | `B` | 正确 | 537 | B. 发生过载，超过 1.00 但不超过 1.20 |
| oracle evidence caption（oracle 证据说明文本） | `oracle_evidence_caption` | `B` | 正确 | 534 | B. 发生过载，超过 1.00 但不超过 1.20 |
| sampled numbers（采样数值）32 行 | `numbers_sampled_32` | `C` | 错误 | 7926 | C. 没有超过 1.00 的过载 |
| sampled numbers（采样数值）64 行 | `numbers_sampled_64` | `C` | 错误 | 15220 | C. 没有超过 1.00 的过载 |
| sampled numbers（采样数值）128 行 | `numbers_sampled_128` | `B` | 正确 | 29807 | B. 发生过载，超过 1.00 但不超过 1.20 |
| sampled numbers（采样数值）256 行 | `numbers_sampled_256` | `B` | 正确 | 58981 | B. 发生过载，超过 1.00 但不超过 1.20 |
| sampled numbers（采样数值）512 行 | `numbers_sampled_512` | `B` | 正确 | 117328 | B. 发生过载，超过 1.00 但不超过 1.20 |

</details>

<details>
<summary>案例分析</summary>

断开第 0 条线路只带来很小的 max-rho 变化，但 intervention（干预）后的峰值达到 1.024，刚好超过 1.00 过载阈值。低采样预算的 sampled numbers（采样数值）漏掉了这个边界事实；oracle evidence caption（oracle 证据说明文本）直接给出与阈值判断相关的数值。

</details>

</details>

<details>
<summary>案例 05：反事实方向：必须比较事实轨迹和干预轨迹的峰值</summary>

### 基本信息

| 字段 | 内容 |
| --- | --- |
| 案例 ID | `simqa::grid2op_real_cf::h1024_t128_line5::cf_peak_rho_direction` |
| 数据来源 | factual/counterfactual（事实/反事实）配对轨迹 (`counterfactual`) |
| 窗口长度 | `1024` |
| 任务类型 | 断线干预后的峰值方向变化 (`cf_peak_rho_direction`) |
| 正确答案 | `C` |
| 正确答案标签 | `上升` |
| ground truth（真值）来源 | `trace_array` / 仿真器轨迹 |

关键结论：断开第 5 条线路后，intervention（干预）后的峰值 max-rho 从 factual trace（事实轨迹）的 0.999 上升到 1.138。题目要求在 0.05 容忍阈值下比较 factual/counterfactual（事实/反事实）配对结果。generic caption（通用说明文本）失败的原因是它没有提供两条轨迹的配对结果事实。

<details>
<summary>时序图</summary>

![simqa::grid2op_real_cf::h1024_t128_line5::cf_peak_rho_direction](figures/05_cf_peak_rho_direction_simqa_grid2op_real_cf_h1024_t128_line5_cf_peak_rho_direction.png)

</details>

<details>
<summary>QA 问题</summary>

**问题**

以 0.05 的 max-rho 容忍阈值判断：如果在 t=128 断开第 5 条线路，干预后的峰值最大线路负载率相对事实 rollout 如何变化？

**选项**

- A. 相对事实 rollout 至少下降 0.05 max-rho
- B. 相对事实 rollout 的变化小于 0.05 max-rho
- C. 相对事实 rollout 至少上升 0.05 max-rho
- D. 无法仅从配对轨迹判断

**正确答案**：`C` - C. 相对事实 rollout 至少上升 0.05 max-rho

</details>

<details>
<summary>caption（说明文本）与 evidence（证据）</summary>

**generic caption（通用说明文本）**

这组 Grid2Op 配对轨迹包含一条事实 rollout，以及一条在 episode 中断开某条输电线路的反事实 rollout。

**oracle evidence caption（oracle 证据说明文本）**

事实 rollout 中，干预后峰值 max-rho 为 0.999；在 t=128 断开第 5 条线路后，该值变为 1.138。差值为 +0.139；以 0.05 为容忍阈值，它相对事实 rollout 至少上升 0.05 max-rho。

**可验证事实**

| 验证字段 | 数值 |
| --- | --- |
| `paired_steps` | `1024` |
| `post_intervention_steps` | `895` |
| `intervention_step` | `128` |
| `line_id` | `5` |
| `factual_line_status_at_intervention` | `1` |
| `intervention_line_status_after` | `0` |
| `mean_abs_total_load_delta_post` | `0.0000` |
| `max_abs_total_load_delta_post` | `0.0000` |
| `mean_max_rho_delta_post` | `0.0398` |
| `max_abs_max_rho_delta_post` | `0.1443` |
| `factual_max_rho_post` | `0.9990` |
| `intervention_max_rho_post` | `1.1381` |
| `factual_post_peak_max_rho` | `0.9990` |
| `intervention_post_peak_max_rho` | `1.1381` |
| `post_peak_max_rho_delta` | `0.1391` |
| `mean_post_max_rho_delta` | `0.0398` |

</details>

<details>
<summary>模型回答</summary>

| 输入条件 | 原始条件名 | 预测 | 正确性 | Prompt 字符数 | 选项文本 |
| --- | --- | --- | --- | ---: | --- |
| 仅元信息 | `meta_only` | `A` | 错误 | 568 | A. 相对事实 rollout 至少下降 0.05 max-rho |
| generic caption（通用说明文本） | `generic_caption` | `B` | 错误 | 723 | B. 相对事实 rollout 的变化小于 0.05 max-rho |
| oracle evidence caption（oracle 证据说明文本） | `oracle_evidence_caption` | `C` | 正确 | 824 | C. 相对事实 rollout 至少上升 0.05 max-rho |
| sampled numbers（采样数值）32 行 | `numbers_sampled_32` | `C` | 正确 | 8112 | C. 相对事实 rollout 至少上升 0.05 max-rho |
| sampled numbers（采样数值）64 行 | `numbers_sampled_64` | `C` | 正确 | 15406 | C. 相对事实 rollout 至少上升 0.05 max-rho |
| sampled numbers（采样数值）128 行 | `numbers_sampled_128` | `B` | 错误 | 29993 | B. 相对事实 rollout 的变化小于 0.05 max-rho |
| sampled numbers（采样数值）256 行 | `numbers_sampled_256` | `C` | 正确 | 59167 | C. 相对事实 rollout 至少上升 0.05 max-rho |
| sampled numbers（采样数值）512 行 | `numbers_sampled_512` | `C` | 正确 | 117514 | C. 相对事实 rollout 至少上升 0.05 max-rho |

</details>

<details>
<summary>案例分析</summary>

断开第 5 条线路后，intervention（干预）后的峰值 max-rho 从 factual trace（事实轨迹）的 0.999 上升到 1.138。题目要求在 0.05 容忍阈值下比较 factual/counterfactual（事实/反事实）配对结果。generic caption（通用说明文本）失败的原因是它没有提供两条轨迹的配对结果事实。

</details>

</details>

