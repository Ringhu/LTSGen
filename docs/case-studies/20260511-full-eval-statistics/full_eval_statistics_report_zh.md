# LTSGen 全量评测统计报告：基于 case study 结论的失败模式验证

本报告不统计 27 个 case study 样本本身，而是用 case study 暴露的问题来定义统计项，再回到全量 evaluation artifacts 上计算比例。所有数字来自本地已有评测结果，没有重跑模型。

## 统计口径

- Dataset-A 是多字段开放式答案，逐样本二值化口径为平均 evaluator score >= 0.8；同时保留 mean score。它的 official summary 中 categorical / numerical / reason_STUB 仍是更细的权威指标。
- TSShapeQA-OOD、TSAQA、TimeSeriesExam 是离散 QA，直接使用 prediction artifact 中的 `correct` 字段。
- TSShapeQA-OOD 和 TSAQA 的 numbers baseline 在 OpenTSLM/ChatTS 两个评测文件中各有一次独立运行；整体表使用 OpenTSLM eval 文件中的 canonical numbers，caption harm/help 对 ChatTS 使用 run-matched numbers。
- FREDQA 当前本地没有完整多条件 prediction/eval table，因此只列入 coverage 和 qualitative 结论，不报告准确率。

## 统计项解释与判读规则

| 统计项 | 这个数字是什么 | 可能说明什么 |
| --- | --- | --- |
| OpenTSLM 错、ChatTS 对 | 同一个样本中 OpenTSLM caption 条件答错而 ChatTS caption 条件答对 | 两个 caption 模型存在可利用的差异；如果比例高，说明 OpenTSLM 的 caption 事实保真或格式更弱。 |
| ChatTS 错、OpenTSLM 对 | 同一个样本中 ChatTS caption 条件答错而 OpenTSLM caption 条件答对 | ChatTS 不是系统性可靠；它的简洁描述可能漏掉组合结构、异常类型或任务所需细节。 |
| 两个 caption 都错、numbers 对 | 两个 caption-only 都答错，但直接给原始数值可以答对 | 自由文本 caption 共同丢失了原始时序里的可答题证据，是 caption 压缩失败的直接证据。 |
| 三者都错 | numbers、OpenTSLM caption、ChatTS caption 都答错 | 下游 LLM 仅靠当前输入仍无法解决，可能需要工具、计算、领域规则或更强 prompt。 |
| 两个 caption 都错、tool-agent 对 | 两个 caption-only 都错，但工具代理答对 | 结构化特征抽取可以救回失败，说明问题不是完全不可解，而是缺少合适 evidence interface。 |
| meta_only 对 | 只看题干和选项、不看时间序列也答对 | 可能存在题干/选项/先验 shortcut；这类正确不能直接解释为时序理解。 |
| meta_only 对、numbers 错 | 不看序列反而对，看数字反而错 | 题干 shortcut 或选项 prior 可能比数值证据更容易被模型利用。 |
| caption+numbers harm | numbers 对，但加入 caption 后错 | caption 污染或重加权了原始数值证据，是自由文本中间表示的风险信号。 |
| caption+numbers help | numbers 错，但加入 caption 后对 | caption 提供了 numbers 难以被下游模型直接抽取的结构化提示。 |
| net help-harm | help rate 减去 harm rate | 正值表示 caption 净帮助，负值表示 caption 净伤害；这是判断是否继续使用 caption interface 的关键量。 |

## Artifact Inventory
| 数据集 | 来源 | 可做准确率统计 | 条件 | 每条件样本数 |
| --- | --- | --- | --- | --- |
| TSShapeQA-OOD | opentslm/full6 | yes | caption;caption_plus;meta_only;numbers;numbers_cot;wrong_caption | {"caption": 800, "caption_plus": 800, "meta_only": 800, "numbers": 800, "numbers_cot": 800, "wrong_caption": 800} |
| TSShapeQA-OOD | chatts | yes | caption;caption_plus;meta_only;numbers;wrong_caption | {"caption": 800, "caption_plus": 800, "meta_only": 800, "numbers": 800, "wrong_caption": 800} |
| TSShapeQA-OOD | tool_agent | yes | tool_agent | {"tool_agent": 800} |
| dataset_a | detailed_json | yes_with_threshold | chatts_caption;chatts_caption_plus;chatts_meta_only;chatts_numbers;chatts_wrong_caption;opentslm_caption;opentslm_caption_plus;opentslm_meta_only;opentslm_numbers;opentslm_wrong_caption;tool_agent | {"chatts_caption": 116, "chatts_caption_plus": 115, "chatts_meta_only": 116, "chatts_numbers": 116, "chatts_wrong_caption": 117, "opentslm_caption": 115, "opentslm_caption_plus": 115, "opentslm_meta_only": 116, "opentslm_numbers": 117, "opentslm_wrong_caption": 117, "tool_agent": 117} |
| TSAQA | opentslm/full | yes | caption;caption_plus;meta_only;numbers;wrong_caption | {"caption": 996, "caption_plus": 996, "meta_only": 996, "numbers": 996, "wrong_caption": 996} |
| TSAQA | chatts | yes | caption;caption_plus;meta_only;numbers;wrong_caption | {"caption": 996, "caption_plus": 996, "meta_only": 996, "numbers": 996, "wrong_caption": 996} |
| TSAQA | tool_agent | yes | tool_agent | {"tool_agent": 996} |
| TimeSeriesExam | combined | yes | caption_chatts;caption_opentslm;meta_only;numbers;wrong_caption | {"caption_chatts": 263, "caption_opentslm": 263, "meta_only": 263, "numbers": 263, "wrong_caption": 263} |
| FREDQA | qualitative_cases | no | question;captions | {"qualitative_only": 604} |

## 数据集覆盖
| 数据集 | 全量样本数 | 状态 |
| --- | --- | --- |
| TSShapeQA-OOD | 800 | 完整逐样本 eval |
| dataset_a | 117 | 完整逐样本 eval，但为多项评分 |
| TSAQA | 996 | 完整逐样本 eval |
| TimeSeriesExam | 263 | 完整逐样本 eval，缺 caption_plus/tool |
| FREDQA | 604 | 只有 qualitative/caption artifact，无完整多条件 eval |

## 全局输入条件对比
| 数据集 | 条件 | n | 正确率/二值正确率 | mean score |
| --- | --- | --- | --- | --- |
| TSShapeQA-OOD | meta_only | 800 | 33.5% | 0.335 |
| TSShapeQA-OOD | numbers | 800 | 55.4% | 0.554 |
| TSShapeQA-OOD | opentslm_caption | 800 | 33.5% | 0.335 |
| TSShapeQA-OOD | chatts_caption | 800 | 52.9% | 0.529 |
| TSShapeQA-OOD | opentslm_caption_plus | 800 | 46.2% | 0.463 |
| TSShapeQA-OOD | chatts_caption_plus | 800 | 53.2% | 0.532 |
| TSShapeQA-OOD | tool_agent | 800 | 100.0% | 1.000 |
| dataset_a | meta_only | 116 | 13.8% | 0.388 |
| dataset_a | numbers | 117 | 19.7% | 0.520 |
| dataset_a | opentslm_caption | 115 | 11.3% | 0.317 |
| dataset_a | chatts_caption | 116 | 48.3% | 0.652 |
| dataset_a | opentslm_caption_plus | 115 | 20.9% | 0.469 |
| dataset_a | chatts_caption_plus | 115 | 56.5% | 0.670 |
| dataset_a | tool_agent | 117 | 31.6% | 0.547 |
| TSAQA | meta_only | 996 | 50.1% | 0.501 |
| TSAQA | numbers | 996 | 65.0% | 0.650 |
| TSAQA | opentslm_caption | 996 | 44.9% | 0.449 |
| TSAQA | chatts_caption | 996 | 46.1% | 0.461 |
| TSAQA | opentslm_caption_plus | 996 | 59.9% | 0.599 |
| TSAQA | chatts_caption_plus | 996 | 60.4% | 0.604 |
| TSAQA | tool_agent | 996 | 55.6% | 0.556 |
| TimeSeriesExam | meta_only | 263 | 39.2% | 0.392 |
| TimeSeriesExam | numbers | 263 | 67.7% | 0.677 |
| TimeSeriesExam | opentslm_caption | 263 | 36.1% | 0.361 |
| TimeSeriesExam | chatts_caption | 263 | 51.3% | 0.513 |

这张表的核心含义是：`numbers` 是“原始时序信息是否足够”的基线；caption-only 如果低于 numbers，说明自由文本摘要丢失了 answer-supporting evidence；caption_plus 如果低于 numbers，说明 caption 不只是没帮忙，还可能污染原始数值证据；tool-agent 如果高，说明结构化特征抽取能够救回一部分失败。

## 全局交叉统计
| 数据集 | 统计项 | 数量 | 可比较样本数 | 比例 |
| --- | --- | --- | --- | --- |
| TSShapeQA-OOD | OpenTSLM caption 错、ChatTS caption 对 | 278 | 800 | 34.8% |
| TSShapeQA-OOD | ChatTS caption 错、OpenTSLM caption 对 | 123 | 800 | 15.4% |
| TSShapeQA-OOD | 两个 caption 都错、numbers 对 | 122 | 800 | 15.2% |
| TSShapeQA-OOD | numbers / OpenTSLM caption / ChatTS caption 三者都错 | 132 | 800 | 16.5% |
| TSShapeQA-OOD | 两个 caption 都错、tool-agent 对 | 254 | 800 | 31.8% |
| TSShapeQA-OOD | 非 tool 条件全错、tool-agent 对 | 0 | 800 | 0.0% |
| TSShapeQA-OOD | meta_only 不看时序也答对 | 268 | 800 | 33.5% |
| TSShapeQA-OOD | meta_only 对、numbers 错 | 36 | 800 | 4.5% |
| TSShapeQA-OOD | meta_only 对、所有时序输入条件错 | 0 | 800 | 0.0% |
| TSShapeQA-OOD | OpenTSLM caption+numbers 伤害 numbers | 133 | 800 | 16.6% |
| TSShapeQA-OOD | OpenTSLM caption+numbers 救回 numbers | 60 | 800 | 7.5% |
| TSShapeQA-OOD | ChatTS caption+numbers 伤害 numbers | 184 | 800 | 23.0% |
| TSShapeQA-OOD | ChatTS caption+numbers 救回 numbers | 181 | 800 | 22.6% |
| dataset_a | OpenTSLM caption 错、ChatTS caption 对 | 49 | 115 | 42.6% |
| dataset_a | ChatTS caption 错、OpenTSLM caption 对 | 6 | 115 | 5.2% |
| dataset_a | 两个 caption 都错、numbers 对 | 5 | 115 | 4.3% |
| dataset_a | numbers / OpenTSLM caption / ChatTS caption 三者都错 | 48 | 115 | 41.7% |
| dataset_a | 两个 caption 都错、tool-agent 对 | 4 | 115 | 3.5% |
| dataset_a | 非 tool 条件全错、tool-agent 对 | 0 | 115 | 0.0% |
| dataset_a | meta_only 不看时序也答对 | 16 | 116 | 13.8% |
| dataset_a | meta_only 对、numbers 错 | 7 | 116 | 6.0% |
| dataset_a | meta_only 对、所有时序输入条件错 | 2 | 116 | 1.7% |
| dataset_a | OpenTSLM caption+numbers 伤害 numbers | 7 | 115 | 6.1% |
| dataset_a | OpenTSLM caption+numbers 救回 numbers | 8 | 115 | 7.0% |
| dataset_a | ChatTS caption+numbers 伤害 numbers | 3 | 115 | 2.6% |
| dataset_a | ChatTS caption+numbers 救回 numbers | 40 | 115 | 34.8% |
| TSAQA | OpenTSLM caption 错、ChatTS caption 对 | 145 | 996 | 14.6% |
| TSAQA | ChatTS caption 错、OpenTSLM caption 对 | 133 | 996 | 13.4% |
| TSAQA | 两个 caption 都错、numbers 对 | 188 | 996 | 18.9% |
| TSAQA | numbers / OpenTSLM caption / ChatTS caption 三者都错 | 216 | 996 | 21.7% |
| TSAQA | 两个 caption 都错、tool-agent 对 | 135 | 996 | 13.6% |
| TSAQA | 非 tool 条件全错、tool-agent 对 | 0 | 996 | 0.0% |
| TSAQA | meta_only 不看时序也答对 | 499 | 996 | 50.1% |
| TSAQA | meta_only 对、numbers 错 | 120 | 996 | 12.0% |
| TSAQA | meta_only 对、所有时序输入条件错 | 28 | 996 | 2.8% |
| TSAQA | OpenTSLM caption+numbers 伤害 numbers | 113 | 996 | 11.3% |
| TSAQA | OpenTSLM caption+numbers 救回 numbers | 63 | 996 | 6.3% |
| TSAQA | ChatTS caption+numbers 伤害 numbers | 109 | 996 | 10.9% |
| TSAQA | ChatTS caption+numbers 救回 numbers | 82 | 996 | 8.2% |
| TimeSeriesExam | OpenTSLM caption 错、ChatTS caption 对 | 62 | 263 | 23.6% |
| TimeSeriesExam | ChatTS caption 错、OpenTSLM caption 对 | 22 | 263 | 8.4% |
| TimeSeriesExam | 两个 caption 都错、numbers 对 | 49 | 263 | 18.6% |
| TimeSeriesExam | numbers / OpenTSLM caption / ChatTS caption 三者都错 | 57 | 263 | 21.7% |
| TimeSeriesExam | meta_only 不看时序也答对 | 103 | 263 | 39.2% |
| TimeSeriesExam | meta_only 对、numbers 错 | 14 | 263 | 5.3% |
| TimeSeriesExam | meta_only 对、所有时序输入条件错 | 8 | 263 | 3.0% |

## Caption Help/Harm 净效应
| 数据集 | 条件 | help数 | harm数 | 可比较样本数 | help率 | harm率 | 净效应 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TSAQA | OpenTSLM caption+numbers | 63 | 113 | 996 | 6.3% | 11.3% | -5.0% |
| TSAQA | ChatTS caption+numbers | 82 | 109 | 996 | 8.2% | 10.9% | -2.7% |
| TSAQA | OpenTSLM caption-only | 83 | 283 | 996 | 8.3% | 28.4% | -20.1% |
| TSAQA | ChatTS caption-only | 111 | 281 | 996 | 11.1% | 28.2% | -17.1% |
| TSShapeQA-OOD | OpenTSLM caption+numbers | 60 | 133 | 800 | 7.5% | 16.6% | -9.1% |
| TSShapeQA-OOD | ChatTS caption+numbers | 181 | 184 | 800 | 22.6% | 23.0% | -0.4% |
| TSShapeQA-OOD | OpenTSLM caption-only | 78 | 253 | 800 | 9.8% | 31.6% | -21.9% |
| TSShapeQA-OOD | ChatTS caption-only | 199 | 205 | 800 | 24.9% | 25.6% | -0.7% |
| TimeSeriesExam | OpenTSLM caption-only | 12 | 95 | 263 | 4.6% | 36.1% | -31.6% |
| TimeSeriesExam | ChatTS caption-only | 24 | 67 | 263 | 9.1% | 25.5% | -16.3% |
| dataset_a | OpenTSLM caption+numbers | 8 | 7 | 115 | 7.0% | 6.1% | 0.9% |
| dataset_a | ChatTS caption+numbers | 40 | 3 | 115 | 34.8% | 2.6% | 32.2% |
| dataset_a | OpenTSLM caption-only | 5 | 15 | 115 | 4.3% | 13.0% | -8.7% |
| dataset_a | ChatTS caption-only | 36 | 8 | 116 | 31.0% | 6.9% | 24.1% |
判读：净效应为正说明该 caption 条件整体救回的样本多于伤害的样本；净效应为负说明 caption 作为辅助信息会带来净损失。

这些交叉统计对应 case study 的主要结论：
- `OpenTSLM 错、ChatTS 对` 和反向统计衡量两个 caption 模型是否互补。
- `两个 caption 都错、numbers 对` 衡量自由文本 caption 是否共同丢失了原始序列里本来可用的证据。
- `三者都错` 表示当前下游 LLM 即使看 numbers 也没有解决，通常需要更强工具、不同 prompt 或任务本身更难。
- `meta_only 对` 及其变体衡量 benchmark shortcut：如果不看时序也能答对，相关准确率不能简单解释为时序理解。
- `caption+numbers harm/help` 是判断 caption 是否值得作为中间表示的关键：harm 高说明 caption 会误导 numbers，help 高说明 caption 提供了 numbers 难以直接利用的结构信息。

## TSShapeQA-OOD

**任务含义**：纯时序形态 MCQ，主要测趋势、极值位置和波动区域。这里最能检验 caption 是否保留 answer-supporting shape evidence。


**输入条件整体表现**

| 条件 | n | 答对数 | 答对率/二值正确率 | mean score |
| --- | --- | --- | --- | --- |
| meta_only | 800 | 268 | 33.5% | 0.335 |
| numbers | 800 | 443 | 55.4% | 0.554 |
| numbers_cot | 800 | 479 | 59.9% | 0.599 |
| opentslm_caption | 800 | 268 | 33.5% | 0.335 |
| opentslm_caption_plus | 800 | 370 | 46.2% | 0.463 |
| chatts_caption | 800 | 423 | 52.9% | 0.529 |
| chatts_caption_plus | 800 | 426 | 53.2% | 0.532 |
| tool_agent | 800 | 800 | 100.0% | 1.000 |


**这些数字代表什么**

- `meta_only`：只看题干和选项，不看任何时间序列。高准确率意味着 benchmark 可能存在题干/选项/领域先验 shortcut。

- `numbers`：直接给原始数值，是判断 caption 是否有必要的基线。

- `opentslm_caption` / `chatts_caption`：只给自然语言描述，衡量 caption 自身是否保留可答题证据。

- `caption_plus`：caption 和 numbers 同时给出；如果低于 numbers，说明 caption 会污染或误导数值证据。

- `tool_agent`：显式抽取结构化特征或工具结果；高分表示失败可能来自缺少工具/结构化特征，而不是下游 LLM 完全不能答。


**关键交叉统计**

| 统计项 | 数量 | 可比较样本数 | 比例 |
| --- | --- | --- | --- |
| OpenTSLM caption 错、ChatTS caption 对 | 278 | 800 | 34.8% |
| ChatTS caption 错、OpenTSLM caption 对 | 123 | 800 | 15.4% |
| 两个 caption 都错、numbers 对 | 122 | 800 | 15.2% |
| numbers / OpenTSLM caption / ChatTS caption 三者都错 | 132 | 800 | 16.5% |
| 两个 caption 都错、tool-agent 对 | 254 | 800 | 31.8% |
| 非 tool 条件全错、tool-agent 对 | 0 | 800 | 0.0% |
| meta_only 不看时序也答对 | 268 | 800 | 33.5% |
| meta_only 对、numbers 错 | 36 | 800 | 4.5% |
| meta_only 对、所有时序输入条件错 | 0 | 800 | 0.0% |
| OpenTSLM caption+numbers 伤害 numbers | 133 | 800 | 16.6% |
| OpenTSLM caption+numbers 救回 numbers | 60 | 800 | 7.5% |
| ChatTS caption+numbers 伤害 numbers | 184 | 800 | 23.0% |
| ChatTS caption+numbers 救回 numbers | 181 | 800 | 22.6% |


**该数据集的直接结论**

- OpenTSLM caption 的整体准确率接近 meta_only，说明它没有稳定保留趋势/极值/波动这些最基础的形态证据。

- ChatTS caption 明显优于 OpenTSLM caption，但仍低于 tool-agent；这支持“自然语言 caption 比结构化特征更不稳定”的结论。

- 如果 `caption_plus_harm` 不低，说明即使原始数值足够，错误 caption 也会改变下游判断。


**按任务类型的补充表**

| 任务类型 | 条件 | n | 正确率 | mean score |
| --- | --- | --- | --- | --- |
| EXTREMA_POS | meta_only | 267 | 30.0% | 0.300 |
| EXTREMA_POS | numbers | 267 | 51.7% | 0.517 |
| EXTREMA_POS | opentslm_caption | 267 | 33.3% | 0.333 |
| EXTREMA_POS | chatts_caption | 267 | 62.5% | 0.625 |
| EXTREMA_POS | tool_agent | 267 | 100.0% | 1.000 |
| TREND | meta_only | 267 | 24.7% | 0.247 |
| TREND | numbers | 267 | 52.1% | 0.521 |
| TREND | opentslm_caption | 267 | 22.8% | 0.228 |
| TREND | chatts_caption | 267 | 43.1% | 0.431 |
| TREND | tool_agent | 267 | 100.0% | 1.000 |
| VOLATILITY_REGION | meta_only | 266 | 45.9% | 0.459 |
| VOLATILITY_REGION | numbers | 266 | 62.4% | 0.624 |
| VOLATILITY_REGION | opentslm_caption | 266 | 44.4% | 0.444 |
| VOLATILITY_REGION | chatts_caption | 266 | 53.0% | 0.530 |
| VOLATILITY_REGION | tool_agent | 266 | 100.0% | 1.000 |

## dataset_a

**任务含义**：ChatTS 风格的领域解释 benchmark，包含 local、season、trend、local-inductive、causal、deductive 等能力。逐样本答对/答错用平均 evaluator score >= 0.8 二值化，同时报告 mean score。


**输入条件整体表现**

| 条件 | n | 答对数 | 答对率/二值正确率 | mean score |
| --- | --- | --- | --- | --- |
| meta_only | 116 | 16 | 13.8% | 0.388 |
| numbers | 117 | 23 | 19.7% | 0.520 |
| opentslm_caption | 115 | 13 | 11.3% | 0.317 |
| opentslm_caption_plus | 115 | 24 | 20.9% | 0.469 |
| chatts_caption | 116 | 56 | 48.3% | 0.652 |
| chatts_caption_plus | 115 | 65 | 56.5% | 0.670 |
| tool_agent | 117 | 37 | 31.6% | 0.547 |


**这些数字代表什么**

- `meta_only`：只看题干和选项，不看任何时间序列。高准确率意味着 benchmark 可能存在题干/选项/领域先验 shortcut。

- `numbers`：直接给原始数值，是判断 caption 是否有必要的基线。

- `opentslm_caption` / `chatts_caption`：只给自然语言描述，衡量 caption 自身是否保留可答题证据。

- `caption_plus`：caption 和 numbers 同时给出；如果低于 numbers，说明 caption 会污染或误导数值证据。

- `tool_agent`：显式抽取结构化特征或工具结果；高分表示失败可能来自缺少工具/结构化特征，而不是下游 LLM 完全不能答。


**关键交叉统计**

| 统计项 | 数量 | 可比较样本数 | 比例 |
| --- | --- | --- | --- |
| OpenTSLM caption 错、ChatTS caption 对 | 49 | 115 | 42.6% |
| ChatTS caption 错、OpenTSLM caption 对 | 6 | 115 | 5.2% |
| 两个 caption 都错、numbers 对 | 5 | 115 | 4.3% |
| numbers / OpenTSLM caption / ChatTS caption 三者都错 | 48 | 115 | 41.7% |
| 两个 caption 都错、tool-agent 对 | 4 | 115 | 3.5% |
| 非 tool 条件全错、tool-agent 对 | 0 | 115 | 0.0% |
| meta_only 不看时序也答对 | 16 | 116 | 13.8% |
| meta_only 对、numbers 错 | 7 | 116 | 6.0% |
| meta_only 对、所有时序输入条件错 | 2 | 116 | 1.7% |
| OpenTSLM caption+numbers 伤害 numbers | 7 | 115 | 6.1% |
| OpenTSLM caption+numbers 救回 numbers | 8 | 115 | 7.0% |
| ChatTS caption+numbers 伤害 numbers | 3 | 115 | 2.6% |
| ChatTS caption+numbers 救回 numbers | 40 | 115 | 34.8% |


**该数据集的直接结论**

- ChatTS caption 在该数据集明显更强，但这是 ChatTS 训练分布内格式，不能直接外推为通用 caption 能力。

- OpenTSLM 在领域解释、local-inductive 和 deductive 上弱，说明训练目标没有让 caption 学会“哪些语义会被 QA 使用”。

- tool-agent 对局部/周期/趋势特征有帮助，但对 causal/deductive 这类领域语义推理并不充分。


**按任务类型的补充表**

| 任务类型 | 条件 | n | 正确率 | mean score |
| --- | --- | --- | --- | --- |
| causal | meta_only | 38 | 42.1% | 0.658 |
| causal | numbers | 38 | 42.1% | 0.702 |
| causal | opentslm_caption | 36 | 36.1% | 0.597 |
| causal | chatts_caption | 37 | 56.8% | 0.782 |
| causal | tool_agent | 38 | 42.1% | 0.623 |
| deductive | meta_only | 22 | 0.0% | 0.000 |
| deductive | numbers | 23 | 4.3% | 0.043 |
| deductive | opentslm_caption | 23 | 0.0% | 0.000 |
| deductive | chatts_caption | 23 | 4.3% | 0.043 |
| deductive | tool_agent | 23 | 8.7% | 0.101 |
| local,local-inductive,noise | meta_only | 1 | 0.0% | 0.333 |
| local,local-inductive,noise | numbers | 1 | 0.0% | 0.333 |
| local,local-inductive,noise | opentslm_caption | 1 | 0.0% | 0.488 |
| local,local-inductive,noise | chatts_caption | 1 | 100.0% | 0.944 |
| local,local-inductive,noise | tool_agent | 1 | 100.0% | 0.944 |
| local,local-inductive,season,trend | meta_only | 1 | 0.0% | 0.375 |
| local,local-inductive,season,trend | numbers | 1 | 0.0% | 0.500 |
| local,local-inductive,season,trend | opentslm_caption | 1 | 0.0% | 0.000 |
| local,local-inductive,season,trend | chatts_caption | 1 | 100.0% | 0.958 |
| local,local-inductive,season,trend | tool_agent | 1 | 100.0% | 0.833 |
| local,local-inductive,trend,season | meta_only | 1 | 0.0% | 0.125 |
| local,local-inductive,trend,season | numbers | 1 | 0.0% | 0.125 |
| local,local-inductive,trend,season | opentslm_caption | 1 | 0.0% | 0.155 |
| local,local-inductive,trend,season | chatts_caption | 1 | 100.0% | 0.934 |
| local,local-inductive,trend,season | tool_agent | 1 | 0.0% | 0.417 |
| local,noise,local-inductive,trend | meta_only | 1 | 0.0% | 0.125 |
| local,noise,local-inductive,trend | numbers | 1 | 0.0% | 0.451 |
| local,noise,local-inductive,trend | opentslm_caption | 1 | 0.0% | 0.314 |
| local,noise,local-inductive,trend | chatts_caption | 1 | 100.0% | 0.913 |
| local,noise,local-inductive,trend | tool_agent | 1 | 100.0% | 0.826 |
| local,noise,season | meta_only | 3 | 0.0% | 0.222 |
| local,noise,season | numbers | 3 | 0.0% | 0.640 |
| local,noise,season | opentslm_caption | 3 | 0.0% | 0.339 |
| local,noise,season | chatts_caption | 3 | 100.0% | 0.876 |
| local,noise,season | tool_agent | 3 | 33.3% | 0.667 |
| local,noise,trend | meta_only | 1 | 0.0% | 0.333 |
| local,noise,trend | numbers | 1 | 0.0% | 0.502 |
| local,noise,trend | opentslm_caption | 1 | 0.0% | 0.006 |
| local,noise,trend | chatts_caption | 1 | 100.0% | 0.955 |
| local,noise,trend | tool_agent | 1 | 0.0% | 0.445 |
| local,season,local-inductive,trend | meta_only | 1 | 0.0% | 0.375 |
| local,season,local-inductive,trend | numbers | 1 | 0.0% | 0.500 |
| local,season,local-inductive,trend | opentslm_caption | 1 | 0.0% | 0.250 |
| local,season,local-inductive,trend | chatts_caption | 1 | 100.0% | 0.958 |
| local,season,local-inductive,trend | tool_agent | 1 | 100.0% | 0.833 |
| local,trend,noise,season | meta_only | 1 | 0.0% | 0.000 |
| local,trend,noise,season | numbers | 1 | 0.0% | 0.625 |
| local,trend,noise,season | opentslm_caption | 1 | 0.0% | 0.125 |
| local,trend,noise,season | chatts_caption | 1 | 100.0% | 0.863 |
| local,trend,noise,season | tool_agent | 1 | 0.0% | 0.609 |
| local,trend,season | meta_only | 2 | 0.0% | 0.500 |
| local,trend,season | numbers | 2 | 100.0% | 0.952 |
| local,trend,season | opentslm_caption | 2 | 0.0% | 0.528 |
| local,trend,season | chatts_caption | 2 | 50.0% | 0.812 |
| local,trend,season | tool_agent | 2 | 0.0% | 0.486 |
| local-inductive,local,noise | meta_only | 1 | 0.0% | 0.333 |
| local-inductive,local,noise | numbers | 1 | 0.0% | 0.333 |
| local-inductive,local,noise | opentslm_caption | 1 | 0.0% | 0.792 |
| local-inductive,local,noise | chatts_caption | 1 | 100.0% | 0.944 |
| local-inductive,local,noise | tool_agent | 1 | 100.0% | 0.944 |
| local-inductive,local,season,noise | meta_only | 1 | 0.0% | 0.500 |
| local-inductive,local,season,noise | numbers | 1 | 0.0% | 0.500 |
| local-inductive,local,season,noise | opentslm_caption | 1 | 0.0% | 0.656 |
| local-inductive,local,season,noise | chatts_caption | 1 | 100.0% | 0.958 |
| local-inductive,local,season,noise | tool_agent | 1 | 100.0% | 0.958 |
| local-inductive,noise,trend | meta_only | 1 | 0.0% | 0.167 |
| local-inductive,noise,trend | numbers | 1 | 0.0% | 0.565 |
| local-inductive,noise,trend | opentslm_caption | 1 | 0.0% | 0.415 |
| local-inductive,noise,trend | chatts_caption | 1 | 0.0% | 0.364 |
| local-inductive,noise,trend | tool_agent | 1 | 0.0% | 0.772 |
| local-inductive,season,noise,local | meta_only | 1 | 0.0% | 0.500 |
| local-inductive,season,noise,local | numbers | 1 | 0.0% | 0.500 |
| local-inductive,season,noise,local | opentslm_caption | 1 | 0.0% | 0.597 |
| local-inductive,season,noise,local | chatts_caption | 1 | 100.0% | 0.958 |
| local-inductive,season,noise,local | tool_agent | 1 | 100.0% | 0.958 |
| local-inductive,season,noise,trend | meta_only | 1 | 0.0% | 0.375 |
| local-inductive,season,noise,trend | numbers | 1 | 0.0% | 0.750 |
| local-inductive,season,noise,trend | opentslm_caption | 1 | 0.0% | 0.500 |
| local-inductive,season,noise,trend | chatts_caption | 1 | 100.0% | 0.958 |
| local-inductive,season,noise,trend | tool_agent | 1 | 100.0% | 0.958 |


完整任务类型表见 CSV；这里仅展示前 80 行。

## TSAQA

**任务含义**：独立 mixed-format QA，包含 classification、anomaly_detection、characterization、temporal_relationship、comparison、data_transformation。它用于检查 caption 在 OOD QA 格式上的泛化。


**输入条件整体表现**

| 条件 | n | 答对数 | 答对率/二值正确率 | mean score |
| --- | --- | --- | --- | --- |
| meta_only | 996 | 499 | 50.1% | 0.501 |
| numbers | 996 | 647 | 65.0% | 0.650 |
| opentslm_caption | 996 | 447 | 44.9% | 0.449 |
| opentslm_caption_plus | 996 | 597 | 59.9% | 0.599 |
| chatts_caption | 996 | 459 | 46.1% | 0.461 |
| chatts_caption_plus | 996 | 602 | 60.4% | 0.604 |
| tool_agent | 996 | 554 | 55.6% | 0.556 |


**这些数字代表什么**

- `meta_only`：只看题干和选项，不看任何时间序列。高准确率意味着 benchmark 可能存在题干/选项/领域先验 shortcut。

- `numbers`：直接给原始数值，是判断 caption 是否有必要的基线。

- `opentslm_caption` / `chatts_caption`：只给自然语言描述，衡量 caption 自身是否保留可答题证据。

- `caption_plus`：caption 和 numbers 同时给出；如果低于 numbers，说明 caption 会污染或误导数值证据。

- `tool_agent`：显式抽取结构化特征或工具结果；高分表示失败可能来自缺少工具/结构化特征，而不是下游 LLM 完全不能答。


**关键交叉统计**

| 统计项 | 数量 | 可比较样本数 | 比例 |
| --- | --- | --- | --- |
| OpenTSLM caption 错、ChatTS caption 对 | 145 | 996 | 14.6% |
| ChatTS caption 错、OpenTSLM caption 对 | 133 | 996 | 13.4% |
| 两个 caption 都错、numbers 对 | 188 | 996 | 18.9% |
| numbers / OpenTSLM caption / ChatTS caption 三者都错 | 216 | 996 | 21.7% |
| 两个 caption 都错、tool-agent 对 | 135 | 996 | 13.6% |
| 非 tool 条件全错、tool-agent 对 | 0 | 996 | 0.0% |
| meta_only 不看时序也答对 | 499 | 996 | 50.1% |
| meta_only 对、numbers 错 | 120 | 996 | 12.0% |
| meta_only 对、所有时序输入条件错 | 28 | 996 | 2.8% |
| OpenTSLM caption+numbers 伤害 numbers | 113 | 996 | 11.3% |
| OpenTSLM caption+numbers 救回 numbers | 63 | 996 | 6.3% |
| ChatTS caption+numbers 伤害 numbers | 109 | 996 | 10.9% |
| ChatTS caption+numbers 救回 numbers | 82 | 996 | 8.2% |


**该数据集的直接结论**

- numbers 明显强于两个 caption-only 条件，说明 mixed QA 中自由文本摘要丢失了大量可计算证据。

- tool-agent 比 caption-only 强，但弱于 numbers，说明当前工具集覆盖了一部分结构化特征，却不能替代完整序列信息。

- meta_only 在部分 task 上很高，尤其要警惕 characterization/comparison 等任务的题干或选项 shortcut。


**按任务类型的补充表**

| 任务类型 | 条件 | n | 正确率 | mean score |
| --- | --- | --- | --- | --- |
| anomaly_detection | meta_only | 166 | 54.8% | 0.548 |
| anomaly_detection | numbers | 166 | 56.0% | 0.560 |
| anomaly_detection | opentslm_caption | 166 | 52.4% | 0.524 |
| anomaly_detection | chatts_caption | 166 | 51.8% | 0.518 |
| anomaly_detection | tool_agent | 166 | 57.8% | 0.578 |
| characterization | meta_only | 166 | 72.9% | 0.729 |
| characterization | numbers | 166 | 82.5% | 0.825 |
| characterization | opentslm_caption | 166 | 51.8% | 0.518 |
| characterization | chatts_caption | 166 | 48.8% | 0.488 |
| characterization | tool_agent | 166 | 62.0% | 0.620 |
| classification | meta_only | 166 | 52.4% | 0.524 |
| classification | numbers | 166 | 48.8% | 0.488 |
| classification | opentslm_caption | 166 | 46.4% | 0.464 |
| classification | chatts_caption | 166 | 62.7% | 0.627 |
| classification | tool_agent | 166 | 61.4% | 0.614 |
| comparison | meta_only | 166 | 59.0% | 0.590 |
| comparison | numbers | 166 | 78.9% | 0.789 |
| comparison | opentslm_caption | 166 | 52.4% | 0.524 |
| comparison | chatts_caption | 166 | 51.8% | 0.518 |
| comparison | tool_agent | 166 | 67.5% | 0.675 |
| data_transformation | meta_only | 166 | 36.1% | 0.361 |
| data_transformation | numbers | 166 | 63.3% | 0.633 |
| data_transformation | opentslm_caption | 166 | 34.9% | 0.349 |
| data_transformation | chatts_caption | 166 | 35.5% | 0.355 |
| data_transformation | tool_agent | 166 | 48.8% | 0.488 |
| temporal_relationship | meta_only | 166 | 25.3% | 0.253 |
| temporal_relationship | numbers | 166 | 60.2% | 0.602 |
| temporal_relationship | opentslm_caption | 166 | 31.3% | 0.313 |
| temporal_relationship | chatts_caption | 166 | 25.9% | 0.259 |
| temporal_relationship | tool_agent | 166 | 36.1% | 0.361 |

## TimeSeriesExam

**任务含义**：异常、噪声、模式识别类概念题。当前 artifact 没有 caption+numbers 和 tool-agent 条件。


**输入条件整体表现**

| 条件 | n | 答对数 | 答对率/二值正确率 | mean score |
| --- | --- | --- | --- | --- |
| meta_only | 263 | 103 | 39.2% | 0.392 |
| numbers | 263 | 178 | 67.7% | 0.677 |
| opentslm_caption | 263 | 95 | 36.1% | 0.361 |
| chatts_caption | 263 | 135 | 51.3% | 0.513 |


**这些数字代表什么**

- `meta_only`：只看题干和选项，不看任何时间序列。高准确率意味着 benchmark 可能存在题干/选项/领域先验 shortcut。

- `numbers`：直接给原始数值，是判断 caption 是否有必要的基线。

- `opentslm_caption` / `chatts_caption`：只给自然语言描述，衡量 caption 自身是否保留可答题证据。

- `caption_plus`：caption 和 numbers 同时给出；如果低于 numbers，说明 caption 会污染或误导数值证据。

- `tool_agent`：显式抽取结构化特征或工具结果；高分表示失败可能来自缺少工具/结构化特征，而不是下游 LLM 完全不能答。


**关键交叉统计**

| 统计项 | 数量 | 可比较样本数 | 比例 |
| --- | --- | --- | --- |
| OpenTSLM caption 错、ChatTS caption 对 | 62 | 263 | 23.6% |
| ChatTS caption 错、OpenTSLM caption 对 | 22 | 263 | 8.4% |
| 两个 caption 都错、numbers 对 | 49 | 263 | 18.6% |
| numbers / OpenTSLM caption / ChatTS caption 三者都错 | 57 | 263 | 21.7% |
| meta_only 不看时序也答对 | 103 | 263 | 39.2% |
| meta_only 对、numbers 错 | 14 | 263 | 5.3% |
| meta_only 对、所有时序输入条件错 | 8 | 263 | 3.0% |


**该数据集的直接结论**

- numbers 最强，ChatTS caption 次之，OpenTSLM caption 接近或低于 meta_only，说明概念型异常/模式题仍需要具体数值证据。

- ChatTS 和 OpenTSLM 存在互补反例，但总体仍不能替代 numbers。


**按任务类型的补充表**

| 任务类型 | 条件 | n | 正确率 | mean score |
| --- | --- | --- | --- | --- |
| Anolmaly Detection | meta_only | 89 | 38.2% | 0.382 |
| Anolmaly Detection | numbers | 89 | 60.7% | 0.607 |
| Anolmaly Detection | opentslm_caption | 89 | 30.3% | 0.303 |
| Anolmaly Detection | chatts_caption | 89 | 52.8% | 0.528 |
| Noise Understanding | meta_only | 74 | 37.8% | 0.378 |
| Noise Understanding | numbers | 74 | 64.9% | 0.649 |
| Noise Understanding | opentslm_caption | 74 | 32.4% | 0.324 |
| Noise Understanding | chatts_caption | 74 | 55.4% | 0.554 |
| Pattern Recognition | meta_only | 100 | 41.0% | 0.410 |
| Pattern Recognition | numbers | 100 | 76.0% | 0.760 |
| Pattern Recognition | opentslm_caption | 100 | 44.0% | 0.440 |
| Pattern Recognition | chatts_caption | 100 | 47.0% | 0.470 |

## Dataset-A 官方分项指标
| 条件 | 分项指标 | n | score |
| --- | --- | --- | --- |
| meta_only | categorical | 116 | 40.5% |
| meta_only | numerical | 116 | 3.2% |
| meta_only | reason_STUB | 116 | 35.2% |
| numbers | categorical | 117 | 63.3% |
| numbers | numerical | 117 | 38.0% |
| numbers | reason_STUB | 117 | 44.1% |
| opentslm_caption | categorical | 115 | 33.5% |
| opentslm_caption | numerical | 115 | 15.0% |
| opentslm_caption | reason_STUB | 115 | 36.1% |
| opentslm_caption_plus | categorical | 115 | 52.6% |
| opentslm_caption_plus | numerical | 115 | 40.0% |
| opentslm_caption_plus | reason_STUB | 115 | 40.6% |
| chatts_caption | categorical | 116 | 86.1% |
| chatts_caption | numerical | 116 | 75.3% |
| chatts_caption | reason_STUB | 116 | 53.0% |
| chatts_caption_plus | categorical | 115 | 88.8% |
| chatts_caption_plus | numerical | 115 | 80.1% |
| chatts_caption_plus | reason_STUB | 115 | 53.6% |
| tool_agent | categorical | 117 | 73.5% |
| tool_agent | numerical | 117 | 51.1% |
| tool_agent | reason_STUB | 117 | 44.7% |
这张表保留 Dataset-A 原始 evaluator summary 的分项口径。`categorical` 主要看类别是否正确，`numerical` 看位置/幅度等数值是否接近，`reason_STUB` 是领域解释 stub 分数。它比逐样本 `correct@0.8` 更适合分析具体能力来源。
## Dataset-A 按能力类型的 mean score / correct@0.8
| 能力 | 条件 | n | correct@0.8 | mean score |
| --- | --- | --- | --- | --- |
| causal | meta_only | 38 | 42.1% | 0.658 |
| causal | numbers | 38 | 42.1% | 0.702 |
| causal | opentslm_caption | 36 | 36.1% | 0.597 |
| causal | chatts_caption | 37 | 56.8% | 0.782 |
| causal | tool_agent | 38 | 42.1% | 0.623 |
| deductive | meta_only | 22 | 0.0% | 0.000 |
| deductive | numbers | 23 | 4.3% | 0.043 |
| deductive | opentslm_caption | 23 | 0.0% | 0.000 |
| deductive | chatts_caption | 23 | 4.3% | 0.043 |
| deductive | tool_agent | 23 | 8.7% | 0.101 |
| local | meta_only | 42 | 0.0% | 0.034 |
| local | numbers | 42 | 14.3% | 0.307 |
| local | opentslm_caption | 42 | 2.4% | 0.200 |
| local | chatts_caption | 42 | 78.6% | 0.813 |
| local | tool_agent | 42 | 38.1% | 0.559 |
| local-inductive | meta_only | 30 | 0.0% | 0.022 |
| local-inductive | numbers | 30 | 6.7% | 0.326 |
| local-inductive | opentslm_caption | 30 | 0.0% | 0.263 |
| local-inductive | chatts_caption | 30 | 60.0% | 0.743 |
| local-inductive | tool_agent | 30 | 40.0% | 0.655 |
| noise | meta_only | 42 | 28.6% | 0.449 |
| noise | numbers | 42 | 35.7% | 0.690 |
| noise | opentslm_caption | 42 | 26.2% | 0.378 |
| noise | chatts_caption | 42 | 66.7% | 0.776 |
| noise | tool_agent | 42 | 38.1% | 0.642 |
| season | meta_only | 37 | 86.5% | 0.865 |
| season | numbers | 37 | 78.4% | 0.784 |
| season | opentslm_caption | 37 | 35.1% | 0.366 |
| season | chatts_caption | 37 | 100.0% | 0.998 |
| season | tool_agent | 37 | 91.9% | 0.919 |
| trend | meta_only | 41 | 7.3% | 0.395 |
| trend | numbers | 41 | 65.9% | 0.798 |
| trend | opentslm_caption | 41 | 4.9% | 0.153 |
| trend | chatts_caption | 41 | 63.4% | 0.779 |
| trend | tool_agent | 41 | 36.6% | 0.660 |
这张表用于定位 Dataset-A 中哪些能力依赖领域语义。local/season/trend 更接近形态抽取，local-inductive/causal/deductive 更依赖把形态映射到业务含义或规则推理。
## 任务级高风险摘要

**meta_only shortcut 最明显的任务**
| 数据集 | 任务 | 数量 | 可比较样本数 | 比例 |
| --- | --- | --- | --- | --- |
| TSAQA | characterization | 121 | 166 | 72.9% |
| TSAQA | comparison | 98 | 166 | 59.0% |
| TSAQA | anomaly_detection | 91 | 166 | 54.8% |
| TSAQA | classification | 87 | 166 | 52.4% |
| TSShapeQA-OOD | VOLATILITY_REGION | 122 | 266 | 45.9% |
| dataset_a | causal | 16 | 38 | 42.1% |
| TimeSeriesExam | Pattern Recognition | 41 | 100 | 41.0% |
| TimeSeriesExam | Anolmaly Detection | 34 | 89 | 38.2% |

**两个 caption 都错但 numbers 对的任务**
| 数据集 | 任务 | 数量 | 可比较样本数 | 比例 |
| --- | --- | --- | --- | --- |
| TSAQA | comparison | 46 | 166 | 27.7% |
| TSAQA | data_transformation | 45 | 166 | 27.1% |
| TSAQA | temporal_relationship | 44 | 166 | 26.5% |
| TimeSeriesExam | Pattern Recognition | 25 | 100 | 25.0% |
| TSShapeQA-OOD | TREND | 66 | 267 | 24.7% |
| TSAQA | characterization | 35 | 166 | 21.1% |
| TSShapeQA-OOD | VOLATILITY_REGION | 45 | 266 | 16.9% |
| TimeSeriesExam | Anolmaly Detection | 14 | 89 | 15.7% |

**OpenTSLM caption+numbers harm 最明显的任务**
| 数据集 | 任务 | 数量 | 可比较样本数 | 比例 |
| --- | --- | --- | --- | --- |
| TSShapeQA-OOD | TREND | 58 | 267 | 21.7% |
| TSAQA | characterization | 34 | 166 | 20.5% |
| TSShapeQA-OOD | VOLATILITY_REGION | 46 | 266 | 17.3% |
| TSAQA | comparison | 25 | 166 | 15.1% |
| TSAQA | classification | 19 | 166 | 11.4% |
| TSAQA | temporal_relationship | 19 | 166 | 11.4% |
| TSShapeQA-OOD | EXTREMA_POS | 29 | 267 | 10.9% |
| dataset_a | causal | 3 | 36 | 8.3% |

**ChatTS caption+numbers harm 最明显的任务**
| 数据集 | 任务 | 数量 | 可比较样本数 | 比例 |
| --- | --- | --- | --- | --- |
| TSShapeQA-OOD | VOLATILITY_REGION | 90 | 266 | 33.8% |
| TSShapeQA-OOD | TREND | 66 | 267 | 24.7% |
| TSAQA | characterization | 37 | 166 | 22.3% |
| TSAQA | comparison | 22 | 166 | 13.3% |
| TSAQA | classification | 20 | 166 | 12.0% |
| TSShapeQA-OOD | EXTREMA_POS | 28 | 267 | 10.5% |
| TSAQA | temporal_relationship | 13 | 166 | 7.8% |
| TSAQA | data_transformation | 11 | 166 | 6.6% |

**numbers/caption 三者都错的任务**
| 数据集 | 任务 | 数量 | 可比较样本数 | 比例 |
| --- | --- | --- | --- | --- |
| dataset_a | deductive | 21 | 23 | 91.3% |
| TSAQA | data_transformation | 53 | 166 | 31.9% |
| TimeSeriesExam | Noise Understanding | 21 | 74 | 28.4% |
| TSAQA | temporal_relationship | 47 | 166 | 28.3% |
| TimeSeriesExam | Anolmaly Detection | 25 | 89 | 28.1% |
| TSAQA | anomaly_detection | 41 | 166 | 24.7% |
| TSAQA | classification | 39 | 166 | 23.5% |
| TSShapeQA-OOD | EXTREMA_POS | 62 | 267 | 23.2% |
这些任务级统计用于决定下一步诊断优先级：shortcut 高的任务不适合直接支持时序理解 claim；caption harm 高的任务适合做 evidence grounding；三者都错的任务更适合工具/领域推理模块。

## FREDQA 说明

FREDQA 当前可用 qualitative 样本数为 604。本地 artifact 包含问题、选项、解释和 caption，但没有完整的 meta/numbers/OpenTSLM/ChatTS/tool-agent 多条件预测表。因此，本报告不对 FREDQA 报准确率。case study 中的 FREDQA 结论只能作为领域背景推理的 qualitative evidence：宏观经济问题经常需要永久收入假说、反事实窗口计算、地区产业结构、劳动市场净变化公式等外部语义，不能仅靠自由文本时序形态摘要保证正确。

## 面向导师讨论的全局结论

1. **自由文本 caption 不是稳定中间表示。** 在多个数据集上，caption-only 低于 numbers；更重要的是，caption+numbers 存在 harm case，说明 caption 会改变下游模型对原始数值的判断。
2. **OpenTSLM 的主要问题是事实保真不足。** 在纯形态和概念题上，它经常不比 meta_only 好太多；这支持 case study 中的 hallucinated seasonality、wrong trend、wrong extrema 观察。
3. **ChatTS 更强但不代表通用解决。** ChatTS 在 TSShapeQA、Dataset-A、TimeSeriesExam 上通常更好，但 Dataset-A 有训练分布内优势；在 TSAQA 这种 OOD mixed QA 上，ChatTS caption-only 仍明显低于 numbers。
4. **meta_only shortcut 必须单独报告。** TSAQA 和 Dataset-A 的部分任务 meta_only 已经很高，说明某些结果不能直接解释为时序理解能力。
5. **tool-agent 的价值取决于任务是否被工具覆盖。** TSShapeQA 中工具几乎完全解决问题；TSAQA 中 tool-agent 高于 caption 但低于 numbers；Dataset-A 中工具能提取局部特征，但不能完全解决 causal/deductive 语义。
6. **下一步训练方向不应只是让 caption 更流畅。** 更合理的是把 caption 约束成结构化 feature schema，并加入 evidence checking / feature grounding / task-aware filtering。对于 transformation、comparison、causal/deductive 题，还需要显式计算或领域推理模块。

## 输出文件

- `unified_sample_outcomes.csv`：全量逐样本条件结果。
- `dataset_condition_accuracy.csv`：按数据集和输入条件的整体统计。
- `task_condition_accuracy.csv`：按数据集、任务类型和输入条件的统计。
- `dataset_pairwise_patterns.csv`：按数据集的交叉失败模式统计。
- `task_pairwise_patterns.csv`：按任务类型的交叉失败模式统计。
- `dataset_a_ability_stats.csv`：Dataset-A 按 ability 的评分统计。
- `dataset_a_official_component_summary.csv`：Dataset-A 官方分项 evaluator 指标。
- `caption_net_effect.csv`：caption help/harm 净效应。
- `figures/`：统计图。