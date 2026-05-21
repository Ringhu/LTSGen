# Natural QCC 研究路线与 Reviewer Gate（2026-05-21）

## 一句话目标

这条线不是为了证明“caption 永远比数字好”，也不是为了做一个只会查 slot
的时序 QA 数据集。

当前目标是：

> 给定一段真实或 simulator 产生的时序窗口，以及一个具体下游问题，训练模型生成一段自然语言 evidence caption。这个 caption 应该概括与问题相关的时序形态，并给出足以支持答案的证据。

好的 caption 不是泛泛说“曲线上升/下降”，也不是把 support slots 罗列出来。
它应该回答“为什么这段时序支持这个问题的答案”。

## 正确的数据生成主线

数据生成应该是 **场景先行**，不是 **拿着答案找问题**。

推荐流程：

1. **定义领域场景或干预**
   - 先从业务问题出发，例如电网断线、建筑供能预留、交通事故恢复、供水漏损、AIOps 资源压力、金融回撤。
   - 场景要能被领域用户理解，而不是内部任务名。

2. **从 simulator / trace 采集时序窗口**
   - Grid2Op、CityLearn、Traffic、Water、AIOpsLab、FinRL 等来源提供窗口。
   - 这些窗口可以来自真实 trace、official simulator export、干预仿真或历史市场数据。
   - 不应为了凑答案凭空编曲线。

3. **设计自然 QA**
   - 场景说明用户是谁、变量是什么、时间窗口怎么看。
   - 如果需要阈值或业务规则，必须在题目前说清楚。
   - 问题只问一个自然领域决策。
   - 选项必须是普通读者能理解的答案，而不是 support-slot label。

4. **用 deterministic rule 计算 gold answer**
   - 正确答案来自程序、trace、simulator state、反事实差值或明确规则。
   - LLM 可以改写语言，但不能决定答案。
   - support slots 是后台验证和监督工具，不是题目本身。

5. **生成 evidence caption**
   - caption 先描述与问题相关的时序整体形态。
   - 再给少量关键可复核证据。
   - 最后解释为什么这些证据支持答案。
   - caption 不应直接输出选项字母，也不应带 `Answer label`。

6. **通过 reviewer gate 后再扩增和训练**
   - 不通过 gate 的样本不能直接进入正例池。
   - “QA 可用”和“caption 可训练”要分开判断。

## support slots 的位置

support slots 是必要的，但它们不是研究目标。

它们可以用于：

- 生成 gold answer；
- 校验答案和 caption 是否一致；
- 设计 oracle evidence；
- 做 factuality audit；
- 诊断模型是否漏证据或幻觉。

它们不应该用于：

- 直接把 slot 名改成问题；
- 让问题暴露 `segment_tag`、`post257_769`、`x0_mean` 等内部字段；
- 让 caption 变成“均值是多少、阈值是多少、答案是什么”的模板堆叠；
- 让数据生成退化成“拿答案找问题”。

## 好的时序 QA 应该长什么样

一个合格样本至少包含：

- `scene`：领域用户、任务背景、变量含义、时间窗口。
- `decision_rule`：如果答案需要阈值或业务规则，必须写清楚。
- `question`：一个自然、具体、单一的业务问题。
- `options`：四个正常答案选项。
- `gold answer`：由 deterministic rule 得出。
- `values`：回答者能看到的时序或 compact physical features。
- `support_slots`：后台审计字段。
- `evidence_caption`：围绕问题答案的自然语言证据。
- `reviewer_output`：质量审核结论。

## 好的 evidence caption 应该长什么样

好的 caption 需要同时满足两点：

1. **有时序总体描述**
   - 例如“事件后车速没有恢复到事件前水平”，“断线后的压力轨迹长时间处在过载区”，“价格没有明显单边趋势但波动较高”。

2. **有答案相关证据**
   - 给出少量关键数值或关系，例如均值、峰值、比例、前后段差异、反事实差值。
   - 这些证据必须能支持问题的答案。

不好的 caption：

- 只复述答案；
- 只罗列 support slots；
- 带 `Answer label`；
- 带 `supports the answer` 这类训练模板；
- 中英文证据不一致；
- 描述了曲线，但和问题答案无关。

## Reviewer Gate 总体设计

Reviewer gate 不是“让 LLM 决定答案”的裁判。

它是一套分诊系统：

- 数据错了，修数据；
- 题目不自然，重写题；
- caption 污染，清洗 caption；
- GPT data-only 答错但题清楚，进入 hard split 或人工复核；
- 全部通过，才进入扩增和训练。

Reviewer gate 应分三层。

## 第一层：确定性验证 gate

这一层不依赖 LLM。

检查：

- simulator/trace 来源是否清楚；
- `values` 是否存在且维度合理；
- support slots 是否能从时序、trace、simulator state 或规则重新计算；
- gold answer 是否由 deterministic rule 得出；
- answer label 是否和 support slots 一致；
- 选项是否 4 个，gold answer 是否在选项中；
- prompt/caption 中是否泄漏 `Answer label`、内部 ID 或隐藏答案；
- 中文/英文关键字段是否存在。

这一层的目标是防止数据本身错。

## 第二层：自然性与自包含 gate

这一层可以结合规则检查和 LLM reviewer。

检查：

- 场景是否说明用户是谁；
- x0/x1/x2/x3 的业务含义是否明确；
- 时间窗口如何理解是否清楚；
- 阈值、优先级、负类规则是否写在题目前；
- 问题是否像正常业务问题；
- 选项是否像人会选的答案；
- 是否出现 `post257_769`、`segment_tag`、`support slot` 等内部字段；
- 是否要求读者知道 Grid2Op、CityLearn、AIOpsLab 等平台背景。

这一层的目标是防止“可计算但不像自然 QA”。

## 第三层：Caption Quality Gate

这一层只看 evidence caption。

检查：

- caption 是否围绕问题答案；
- caption 是否先描述整体时序形态；
- caption 是否给出少量关键可复核证据；
- caption 是否避免 support slot dump；
- caption 是否避免直接复述答案标签；
- 中文 caption 和英文 caption 是否一致；
- caption 是否有助于回答问题，而不是泛泛描述曲线；
- caption 中是否有 `Answer label`、`supports the answer`、选项字母等污染。

这一层的目标是防止训练目标污染 caption model。

## GPT Data-only Probe 的位置

GPT data-only probe 不是最终判决。

它的做法是：只给模型题面、变量说明、规则、选项和时序表，不给 evidence
caption、support slots 或 gold answer，让模型尝试作答。

如果它答对，说明题面大概率清楚。

如果它答错，只能说明这条样本需要错误归因，不能直接判定题坏。

错误归因要区分：

- 模型算术或推理能力不足；
- 变量解释不清；
- 规则有歧义；
- compact features 不足；
- 选项字母和标签不一致；
- 题目本身是清楚的 hard case。

因此 GPT data-only 的输出应该进入：

- `pass`
- `needs_manual_error_attribution`
- `hard_keep`
- `revise`
- `reject`

而不是简单 `keep/reject`。

## Reviewer 输出应拆成两个 readiness

必须分开判断：

1. `qa_seed_ready`
   - 这条 QA 能不能作为题目 seed。

2. `caption_train_ready`
   - 这条 caption 能不能作为 caption model 的训练目标。

这两个不能混在一起。

例如：

```json
{
  "deterministic_valid": true,
  "qa_seed_ready": true,
  "caption_train_ready": false,
  "decision": "revise",
  "action": "clean_caption_target",
  "naturalness_score": 4,
  "answerability_score": 5,
  "caption_quality_score": 2,
  "accuracy_risk": "low",
  "error_attribution": "caption_answer_leak",
  "notes_zh": "题面和规则可答，但 target_caption 带 Answer label，不能作为 evidence-only caption 训练目标。"
}
```

这类样本不应该删除。它应该保留 QA seed，但清洗 caption target。

## 决策标签

推荐标签：

- `keep`：QA 和 caption 都可用，可进入扩增/训练。
- `revise`：需要重写题面、变量、规则或 caption。
- `reject`：gold 不可复核、题面不可答、或需要隐藏信息。
- `hard_keep`：题目清楚但推理困难，可进入 hard split，不作为 easy seed。
- `clean_caption_target`：QA 可用，但 caption 训练目标污染。
- `needs_manual_error_attribution`：GPT data-only 答错，需要判断是题目问题还是模型能力问题。

## 当前 seed review 的结论

当前已完成：

`.research/general-qcc-captioner-20260515/seed_quality_review_v1_20260521/`

结论：

- 72 条 seed 被 review。
- 57/72 条 `qa_seed_ready`。
- 10/72 条 `caption_train_ready`。
- 12 条 case-study seed 中，9 条基本可展示，10 条 caption target 基本可用。
- 60 条 self-contained seed 中，45 条 QA 本身可用，但 caption target 需要清洗。
- self-contained v2 最大问题是 `target_caption` 全部带 `Answer label`，不能直接作为 evidence-only caption supervision。
- 15 条 self-contained QA 本身需要重写，主要集中在 CityLearn 和 Water。

## 下一步路线

1. 先做 v3 seed repair，不直接扩数据。
2. 清洗 self-contained v2 的 caption target：
   - 去掉 `Answer label`；
   - 去掉规则执行模板；
   - 改成自然 evidence caption。
3. 重写 15 条 QA 本身失败样本：
   - 优先 CityLearn 和 Water；
   - 明确负类、阈值边界、优先级规则；
   - 重新跑 data-only probe 和 reviewer gate。
4. 同步修 12 条 case-study 展示样本：
   - 去掉 simulator 名称；
   - 改清楚模糊变量；
   - 去掉英文 caption 模板句。
5. 通过 reviewer gate 后，再扩到每域 100-200 条。
6. 扩增后再训练 qcond/no-question caption model，并报告：
   - QA accuracy；
   - caption factuality；
   - hallucination / unsupported evidence；
   - oracle/generic/no-question/numbers baselines。

## 当前硬性原则

- 不能把 support slots 当成题目外观。
- 不能让 LLM 决定 gold answer。
- 不能把 GPT data-only 错误直接当作题坏。
- 不能把 `Answer label` 泄漏进 caption 训练目标。
- 不能在 reviewer gate 未过之前扩数据或训练。
