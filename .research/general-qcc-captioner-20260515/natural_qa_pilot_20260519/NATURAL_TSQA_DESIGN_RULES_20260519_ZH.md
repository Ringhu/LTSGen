# Natural TS-QA 设计规律小结（2026-05-19）

这次 pilot 的目标不是扩数据，而是验证一种更自然的 QA 写法：问题要像普通领域用户会问的问题，同时答案仍然能由 deterministic support slots 审计。

## 核心结论

原来的问题常把 verifier 规则、内部时间片段、slot 名称直接塞进 question，例如 `post769_1025`、`intervention-minus-factual`、`which third`、`x0/x1`。这对数据生成很方便，但不像正常 QA。更好的结构是：

```text
场景说明：谁在看这个窗口，变量是什么意思，时间轴怎么对应，什么业务规则重要。
问题：一个自然的领域决策。
选项：普通读者能理解的短答案。
证据：从 support slots 抽出的可验证事实。
审计：保留原始 row id、原始问题、support slots、reviewer 结论。
```

## 这次保留的 6 条模式

| 域 | 自然问题类型 | 原始 slot 任务 | reviewer |
| --- | --- | --- | --- |
| Grid2Op | 断线是否提高线路压力 | counterfactual stress diff | keep, 4/5, low risk |
| CityLearn | 控制器应在哪半段预留更多供能 | first-half vs second-half load | keep, 4/5, low risk |
| FinRL | MRK 回撤风险等级 | max drawdown | keep, 5/5, low risk |
| water | 供水服务状态判断 | pressure/flow resilience context | keep, 4/4, low risk |
| traffic | 自适应信号是否改善排队 | adaptive vs fixed queue mean | keep, 5/5, low risk |
| AIOpsLab | 内存压力是在缓解还是累积 | memory first/second half mean | keep, 5/5, low risk |

## 负面规则

- 不要把内部 ID 放进面向读者的问题：`segment_tag`、`post769_1025`、`bucket06`、`w512_1536`。
- 不要只问“哪一段均值更高”这类裸统计题；要把它转成领域决策。
- 不要在图只有局部 256 步时突然问全局第 512 步，除非场景中解释清楚全局时间和局部图的映射。
- 不要把 `lead-lag` 这种视觉上很接近、统计上也弱分离的题当强 case。
- 不要让 LLM 决定 gold answer。LLM 只能改写和 review，答案必须来自 support slots。
- 不要使用 `material / significant / mixed` 这类需要阈值或多指标依据的选项，除非场景和证据已经给出判定标准。
- 不要把 AIOps 的 app/service/fault/provenance metadata 题伪装成纯时间序列题。

## 正面规则

- 让场景说明承担背景：用户角色、域、变量含义、时间轴、指标方向。
- 让问题只问一个自然决策，例如“是否改善排队”“压力是否累积”“回撤是否严重”。
- 让选项像真实回答，而不是 slot label。
- 让证据短而可验证，直接来自 support slots。
- 对 counterfactual 题必须说明正负号含义。
- 对程度型选项必须说明阈值或给出直观判断依据。
- 对金融题优先使用真实 ticker 和日期，不写“ticker named in the question”。

## Reviewer gate

这次使用 `gpt-5.5` reviewer，但 reviewer 只做质量评审：

- `decision`: `keep / revise / reject`
- `naturalness_score`: 1-5
- `answerability_score`: 1-5
- `accuracy_risk`: `low / medium / high`

建议大规模造数据时只把以下样本放进正例池：

- `decision == keep`
- `naturalness_score >= 4`
- `answerability_score >= 4`
- `accuracy_risk == low`

被判 `revise` 的样本先改写再审；被判 `reject` 的样本不要进 case-study 正例。

## Skill 位置

本地可复用 skill 已安装在：

```text
/home/cris/.codex/skills/natural-tsqa-writer/
```

GitHub 可审阅副本放在：

```text
.research/general-qcc-captioner-20260515/natural_qa_pilot_20260519/skill/
```

