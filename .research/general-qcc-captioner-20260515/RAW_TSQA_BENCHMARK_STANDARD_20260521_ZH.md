# Raw TSQA Benchmark Standard（2026-05-21）

## 目的

本标准固定当前 EMNLP benchmark 线的公开数据格式和评测范式。

核心目标是构建一个 **simulator-grounded raw time-series QA benchmark**：同一条样本只维护一份 canonical 原始时序、问题、选项、答案和审计信息，然后自动导出给不同模型使用的输入视图。

这不是一个“压缩表 QA” benchmark，也不是 slot lookup 数据集。公开题面不应暴露内部摘要特征、support-slot 名称或 verifier 计算过程。

## 基本评测范式

### LLM text-only view

普通 LLM 没有专用时序编码器，因此输入方式是：

1. 将完整原始时序数组序列化成文本，例如 CSV。
2. 把变量说明、自然问题和四个选项放进同一个 prompt。
3. 不提供 support slots、oracle evidence、摘要统计或预计算答案。

LLM 需要直接从文本化原始时序中完成读数、聚合、比较和选择。

### TS-LLM / TS-MLLM view

TS-LLM 或 ChatTS-style 模型可以直接接收数值时序：

1. 原始时序作为 array/tensor 输入。
2. 问题、变量说明和选项作为文本输入。
3. 模型内部可以使用 time-series encoder 和 text encoder 做融合。
4. 不提供 support slots、oracle evidence、摘要统计或预计算答案。

公开问题文本不能假设模型看到的是压缩特征表，也不能说“表格已按块聚合”。

### Oracle evidence view

Oracle evidence 只用于诊断上界或 caption-interface 对照实验。

它可以包含关键聚合量和结论证据，但不能混入 LLM text-only 或 TS-LLM raw-array 主评测。

## 一份 canonical 数据，多种输入视图

每条样本只维护一份 canonical record：

```json
{
  "id": "...",
  "domain": "water_service",
  "time_series": {
    "columns": ["pressure", "flow", "storage"],
    "values": [[...], [...]],
    "time_axis": "ordered before-during-after disturbance window",
    "time_axis_zh": "按时间排序的扰动前-扰动中-扰动后窗口"
  },
  "variable_descriptions_en": {
    "pressure": "service pressure",
    "flow": "pipe flow",
    "storage": "storage context signal"
  },
  "variable_descriptions_zh": {
    "pressure": "服务水压",
    "flow": "管道流量",
    "storage": "蓄水背景信号"
  },
  "context_en": "A water-service operator is reviewing pressure and flow readings around a disturbance event.",
  "context_zh": "供水运维人员正在查看一次扰动事件前后水压和流量读数。",
  "question_en": "Which service state best describes this disturbance window?",
  "question_zh": "这段扰动窗口最符合哪种供水服务状态？",
  "options_en": {
    "A": "persistent leak pressure risk",
    "B": "pressure recovers after disturbance",
    "C": "stable service",
    "D": "manual review needed"
  },
  "options_zh": {
    "A": "持续漏水压力风险",
    "B": "扰动后水压恢复",
    "C": "服务保持稳定",
    "D": "需要人工复核"
  },
  "answer": "B",
  "answer_label": "pressure recovers after disturbance",
  "answer_label_zh": "扰动后水压恢复"
}
```

再从 canonical record 导出：

- `llm_text_view.jsonl`：完整原始时序文本化 prompt。
- `tsllm_array_view.jsonl`：原始时序数组 + 文本问题。
- `oracle_evidence.jsonl`：oracle caption / upper-bound 条件。
- `audit_support.jsonl`：support slots、规则 ID、source row、reviewer gate。

这样 LLM 和 TS-LLM 使用同一条样本、同一个 gold answer、同一个 verifier，只是输入视图不同。

## Public fields

公开 benchmark 至少包含：

| 字段 | 含义 |
| --- | --- |
| `id` | 稳定样本 ID |
| `domain` | 公开领域名，如 `power_grid`, `building_energy`, `traffic`, `water_service`, `service_telemetry`, `market` |
| `time_series.columns` | 原始时序变量名 |
| `time_series.values` | 原始时序数值数组 |
| `time_series.time_axis` / `time_series.time_axis_zh` | 中英文时间顺序说明 |
| `variable_descriptions_en` / `variable_descriptions_zh` | 中英文变量自然语言解释 |
| `context_en` / `context_zh` | 中英文领域背景 |
| `decision_rule_en` / `decision_rule_zh` | 中英文判定规则 |
| `question_en` / `question_zh` | 中英文自然 QA 问题 |
| `options_en` / `options_zh` | 中英文 A-D 四个选项 |
| `answer` | gold letter |
| `answer_label` / `answer_label_zh` | 中英文 gold option text |
| `task_family` | task taxonomy |
| `reasoning_skill_tags` | trend / extrema / temporal comparison / counterfactual effect 等 |

## Audit-only fields

以下字段只进入 audit layer，不进入主评测 prompt：

| 字段 | 用途 |
| --- | --- |
| `source_v3_id` | 回溯 v3 seed |
| `source_row_id` | 回溯 simulator/source sample |
| `source_simulator` | 数据来源 |
| `support_slots` | deterministic verifier 支撑值 |
| `deterministic_rule_id` | 规则版本 |
| `oracle_evidence_caption` | oracle evidence condition |
| `reviewer_gate` | reviewer 结果 |
| `probe_result` | data-only probe / sanity check |
| `raw_generation_trace` | 生成和修复记录 |

## Public prompt 禁止项

公开题面和主评测 prompt 中禁止出现：

- `压缩表`
- `compact table`
- `block feature`
- `support slot`
- `x0_mean`
- `frac_gt_pos_0_05`
- `Answer label`
- `rule maps this to`
- “无需了解任何特定平台背景”
- “LLM/TS-LLM 在有限上下文里看见关键结构”
- simulator 内部 ID，例如 `scenario_first_pilot`, `post257_769`, `window_start`

可以出现：

- 变量自然名，例如 `pressure`, `flow`, `stress_delta`
- 业务阶段，例如 `before`, `during`, `after` 或 `early`, `middle`, `late`
- 简洁阈值规则，例如 “if the top period exceeds the second by at least 0.30”
- 完整原始时序文本或数组

## 规则表达标准

规则需要足够明确，但不能写成程序 spec。

不推荐：

> 压缩表每行对应一个连续时间块。跨行计算 x0 均值、x1 均值、x2 均值和 x3 最大值。若 x0 均值 >= +0.05 且 x1 均值 >= 0.80……

推荐：

> Compare the planned-outage stress series with normal operation. If the average stress difference is clearly positive and most readings are above the positive threshold, classify the outage as increasing stress. If the average is clearly negative and most readings are below the negative threshold, classify it as decreasing stress. If the series stays close to zero with only tiny deviations, classify it as broadly unchanged; otherwise request manual review.

阈值可以保留，因为 benchmark 需要可验证；但变量名和表达必须是 public-domain wording。

## 示例：同一条样本的两种输入视图

### LLM text-only view

```text
Context:
A water-service operator is reviewing pressure and flow readings around a disturbance event.

Variables:
- pressure: service pressure.
- flow: pipe flow.

Time series:
time,pressure,flow
0,68.17,12.10
1,70.18,12.04
...

Question:
Which service state best describes the event window?

Options:
A. persistent leak pressure risk
B. pressure recovers after disturbance
C. stable service
D. manual review needed

Return only the option letter and label.
```

### TS-LLM array view

```json
{
  "timeseries": [[68.17, 12.10], [70.18, 12.04]],
  "columns": ["pressure", "flow"],
  "text": "Which service state best describes the event window? Options: A..."
}
```

两者的 `answer` 和 `support_slots` 完全一致。

## v4 生成要求

下一版 public benchmark 命名为：

`public_raw_tsqa_v4_20260521`

生成要求：

1. 从 v3 positive seed 读取 source raw series，而不是读取 v3 compact `values`。
2. 重新基于 raw series 计算 support slots 和 gold answer。
3. 生成 canonical / LLM text view / TS-LLM array view / oracle evidence / audit support 五份文件。
4. 做本地 sanity check：schema、answer mapping、support-slot consistency、禁用词扫描、answer balance、domain coverage。
5. 生成一份图文报告和 case study，展示 public prompt、时序图、oracle evidence 和 audit trace。
