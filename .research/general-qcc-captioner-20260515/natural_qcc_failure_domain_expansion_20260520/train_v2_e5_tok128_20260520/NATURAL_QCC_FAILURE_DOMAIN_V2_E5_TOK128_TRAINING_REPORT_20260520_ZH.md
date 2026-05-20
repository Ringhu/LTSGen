# Natural QCC Failure-Domain v2 同配置训练报告（2026-05-20）

## 结论

基于本轮扩容后的 124 条 reviewer-positive 数据，我用上一轮可比的 `e5/tok128` 配置跑了 q-conditioned 和 no-question 两条 TS-RLM/Qwen3-4B 训练。

结果是：q-conditioned 明显好于 no-question，semantic QA 为 `0.3143` vs `0.1429`，gap 为 `+0.1714`。这比 55 条数据上的旧结果 `0.2308` vs `0.1538` 更强，说明扩容后确实出现了更清楚的问题条件化收益。

但这还不能作为完整方法成功：q-conditioned caption quality gate 没过，evidence_shape_rate 只有 `0.6857`，Grid2Op 和 Water 里仍有不少输出退化成短标签或无数字证据。当前结论应写成：**扩容 + 同配置训练给出了 smoke-level 正信号，但主要瓶颈已经从“是否有 q-conditioning gap”转向“生成的 evidence caption 是否稳定、可核验、非标签化”。**

## 实验设置

| item | value |
| --- | --- |
| 数据 | `merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl` |
| positive rows | 124 |
| train rows | 89 |
| test rows | 35 |
| model | `Qwen/Qwen3-4B` |
| bridge | `prefix` |
| epochs | 5 |
| max_new_tokens | 128 |
| clean_max_sentences | 3 |
| gradient_accumulation_steps | 2 |
| evaluator | deterministic semantic QA |
| GPU | RTX 3090 |

运行目录：

- qcond：`train_v2_e5_tok128_20260520/tsrlm_qcond_e5_tok128_qwen3_4b`
- no-question：`train_v2_e5_tok128_20260520/tsrlm_no_question_e5_tok128_qwen3_4b`
- comparison：`train_v2_e5_tok128_20260520/natural_qcc_failure_domain_expanded_v2_e5_tok128_qcond_vs_noquestion_audit.json`

注意：本地只同步了小型结果文件；`final_model/` 权重保留在远端训练目录，没有提交到 GitHub。

## 主结果

| run | semantic QA | empty answer rate | caption quality gate | evidence shape |
| --- | ---: | ---: | ---: | ---: |
| q-conditioned | 0.3143 | 0.4000 | false | 0.6857 |
| no-question | 0.1429 | 0.7714 | false | 0.3429 |

对比上一轮 55 条样本：

| data | qcond | no-question | gap |
| --- | ---: | ---: | ---: |
| 55-row evidence-only e5/tok128 | 0.2308 | 0.1538 | +0.0770 |
| 124-row failure-domain v2 e5/tok128 | 0.3143 | 0.1429 | +0.1714 |

解释：扩容以后，qcond 从 0.2308 提到 0.3143；no-question 没有同步提升，反而略低。这个差异说明新数据确实更依赖问题条件，不只是模型记住通用 caption 模板。

## 按域结果

| domain | qcond acc | no-question acc | qcond evidence shape |
| --- | ---: | ---: | ---: |
| `aiopslab_official_v3` | 0.0000 | 0.2000 | 1.0000 |
| `citylearn` | 0.5000 | 0.0000 | 1.0000 |
| `grid2op` | 0.3000 | 0.3000 | 0.4000 |
| `traffic` | 0.3333 | 0.0000 | 0.8333 |
| `water` | 0.5000 | 0.1667 | 0.5000 |

可读解释：

- Traffic 是这轮最清楚的 q-conditioning 受益域：qcond 有 4 条 qcond-only 正确，no-question 全域为 0。
- Water 也有收益，但 caption 质量不稳，尤其 `water_flow_volatility` 和 `water_min_pressure_extrema` 有无数字/短标签问题。
- Grid2Op 总分没有超过 no-question，但 qcond 的输出质量略好；失败集中在 extrema、overload exposure、peak stress、window total load 等任务。
- AIOps 的 evidence shape 好，但 QA 没答对，说明不是“caption 不像证据”的问题，而更像语义桥接/数值判断/目标分布不稳定。

## 样本级差异

35 条 test 中：

| category | count |
| --- | ---: |
| qcond only correct | 8 |
| no-question only correct | 2 |
| both correct | 3 |
| both wrong | 22 |

qcond-only 主要来自：

- `traffic_domain_congestion_context`
- `traffic_speed_trend`
- `traffic_counterfactual_event_gap`
- `traffic_window_speed`
- `water_flow_volatility`
- `city_anomaly_total_load`
- `grid_volatility_total_load`

这说明 q-conditioned prompt 至少在“问哪个判断，就生成哪个证据”上已经有了可见收益。

## 主要失败模式

### 1. Caption quality 没过门槛

qcond quality：

- evidence_shape_rate：0.6857
- numeric_evidence_rate：0.6857
- answer_label_only_rate：0.2000
- too_short_rate：0.2000
- failure reasons：answer_label_only 7，no_numeric_evidence 11，too_short 7

典型失败：

- `"The early, middle, and late"`
- `"Factual overload"`
- `"The window is split into three equal time sections ... selects the late part of the window."`

这些输出有时能被 semantic bridge 判到答案，但不像一个可靠的 evidence caption。它们没有充分给出数值、阈值或比较量。

### 2. Grid2Op/Water 仍然容易短标签化

qcond by-source evidence shape：

- Grid2Op：0.4000
- Water：0.5000
- Traffic：0.8333
- AIOps/CityLearn：1.0000

这说明问题不均匀分布在所有域，而是集中在 Grid2Op/Water 的部分 task family，尤其是 extrema、volatility、counterfactual exposure、water pressure/flow 相关任务。

### 3. 生成有 prompt echo / 语言混杂

qcond raw predictions 中有 15 条包含中文字符，4 条有类似 prompt echo 的痕迹，例如输出末尾出现 `"You are a"`。训练目标本身没有中文输出，说明这是生成解码/清洗没有完全截断，或者模型在长生成时学到了上下文残片。

### 4. Semantic QA 仍离 oracle 很远

目标 evidence caption 的 semantic QA 是 1.0000，但训练生成只有 0.3143。差距主要不是数据 gold 不可答，而是模型没有稳定学会生成足够具体的数字证据。

## 优化建议

下一步不建议直接大规模继续扩容。更有效的顺序是：

1. **先修输出格式和清洗**
   - 在生成清洗里截断中文续写、`You are a`、`Scene:`、`Variables:` 等 prompt echo。
   - 增加最小数字证据约束：如果 caption 没有数字或太短，标为 invalid，并可在训练评估中单独统计。
   - 对 `The early, middle, and late` 这类短标签输出加 hard-negative/格式惩罚。

2. **做 Grid2Op/Water targeted repair**
   - 对 Grid2Op extrema/counterfactual exposure/peak stress、Water volatility/extrema 追加小批高质量样本。
   - 每条 target 都必须包含具体数值、窗口位置、比较对象和判断规则。
   - 优先修 test 中失败 task family，而不是平均扩所有域。

3. **训练上加入质量选择或重加权**
   - 对 evidence-shape 失败多的 task family 加权采样。
   - 训练目标可以统一成更固定的两句模板：第一句数值事实，第二句规则/判断，不允许只输出 label。
   - 可以尝试 `max_new_tokens=96` 或更强停止规则，减少长生成后的中英混杂和 prompt echo。

4. **评估上保留三条门槛**
   - semantic QA：是否答对。
   - caption quality：是否像证据。
   - qcond-vs-no-question gap：是否真的利用问题。

只有三者同时过，才适合把它写成主结果；现在只满足了第 1 和第 3 的部分信号，第 2 还没过。

## 建议的下一轮实验

我建议下一轮做一个很小的 v2.1 修复实验：

- 不改模型结构。
- 只修 Grid2Op/Water 的失败 target 和生成清洗。
- 目标是让 qcond caption quality gate 从 `false` 变成 `true`，同时保持或提升 semantic QA。
- 成功阈值可以设为：
  - qcond semantic QA >= 0.30
  - qcond evidence_shape_rate >= 0.80
  - qcond answer_label_only_rate <= 0.10
  - qcond-no-question gap >= 0.10

如果 v2.1 达到这些门槛，再继续扩到 200-300 条才更划算。
