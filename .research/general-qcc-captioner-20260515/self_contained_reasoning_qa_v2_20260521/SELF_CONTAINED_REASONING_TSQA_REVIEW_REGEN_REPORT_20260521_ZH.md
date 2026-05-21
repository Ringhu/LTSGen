# Self-contained Reasoning TSQA Review & Regeneration Report（2026-05-21）

## 结论

这条 benchmark 方向可行，但当前数据生成规范必须从“自然时序 QA”进一步收紧为“自包含、可复核、需要规则推理的时序 QA”。我用 `~/Research/gptapi` 路径优先调用现有 LLM client；当前本地缺少其依赖时，脚本 fallback 到同一 OpenAI-compatible endpoint 的 urllib 调用。Probe 全程只给模型题面、变量定义、规则、选项和时序表，不给 evidence caption、support slots 或 simulator 背景。

主要结果：

| 数据版本 | 输入给 solver 的时序 | rows | GPT data-only acc | 主要问题 |
| --- | --- | ---: | ---: | --- |
| v1 | 原始物理量长序列 | 60 | 0.4000 | 256 行表格聚合太重；负类容易被误选；部分规则/列含义不够清楚 |
| v2 final | compact block physical features | 60 | 0.7500 | CityLearn/Water 仍有 final-answer 字段与 reason 不一致、阈值边界表达需继续收紧 |

v2 的 15 个错例中，有 13 个错例的 `reason` 已经显式说出了 gold label，但 JSON 里的 `answer`/`answer_label` 写错。这说明题目本身已经更可推理，但 MCQ benchmark 还需要强制答案一致性或后处理校验。

## 原始问题 Review

上一版问题的核心问题不是“背景不自然”，而是 benchmark 目标还不够明确：

1. 很多 QA 仍像直接读时序：趋势、极值、窗口均值，本身不要求多步推理。
2. 背景中出现 simulator 名称或领域假设，通用 LLM/TS-LLM 不能只靠题面和时序表答题。
3. 原始 `values` 有时是归一化值，support slots 是物理量，容易造成“题面可读但数据不可复现”。
4. 256 行原始表格对通用 LLM 是算术负担，错误不一定反映时序推理能力。
5. 负类和优先级规则没有写死时，模型会选择“最像的正类”，而不是严格按阈值输出。

## 重新生成规范

v2 数据遵守以下约束：

1. 题面自包含：场景、变量含义、时间块划分、决策规则都在 question context 内。
2. 不要求知道 Grid2Op、CityLearn、AIOpsLab、FinRL 或任何 simulator 背景。
3. `values` 使用 solver-visible 的 compact block physical features；原始物理长序列保留在 `raw_compact_values` 供审计。
4. 每题需要至少一个派生/聚合推理步骤：三段均值、比例阈值、峰值/中位数、最大回撤、优先级规则等。
5. support slots 只用于审计和生成 evidence，不作为 solver 输入。
6. 明确负类规则：阈值未满足时不要选择最接近的正类。

当前 v2 数据资产：

| Artifact | Path |
| --- | --- |
| v2 QA JSONL | `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/self_contained_reasoning_tsqa.jsonl` |
| v2 SFT JSONL | `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/self_contained_reasoning_tsqa_sft.jsonl` |
| v2 summary | `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/self_contained_reasoning_tsqa_summary.json` |
| v2 generation spec | `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/SELF_CONTAINED_REASONING_TSQA_V2_GENERATION_SPEC_20260521_ZH.md` |
| v2 GPT probe | `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/self_contained_reasoning_tsqa_gpt_data_only_probe.json` |
| v2 GPT probe report | `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/SELF_CONTAINED_REASONING_TSQA_GPT_DATA_ONLY_PROBE_20260521_ZH.md` |
| generator | `scripts/generate/build_self_contained_reasoning_tsqa.py` |
| data-only probe | `scripts/eval/probe_self_contained_reasoning_tsqa_llm.py` |

## 数据概况

v2 当前是 60 条 smoke/regeneration set：

| domain | rows | task |
| --- | ---: | --- |
| grid2op | 10 | counterfactual risk by block mean / threshold share |
| citylearn | 10 | net-load reserve planning by temporal thirds |
| traffic | 10 | congestion shock / recovery with precedence rule |
| water | 10 | pressure-flow recovery / leak triage |
| aiopslab | 10 | telemetry symptom triage |
| finrl | 10 | return + drawdown regime classification |

注意：当前为了诊断可读性，选项语义顺序是固定的，所以 answer-letter 不平衡：A=31, B=5, C=8, D=16。正式 benchmark 不能直接用这个分布，扩增阶段必须做 answer-letter balancing。

## GPT Data-only Probe

设置：

- model: `gpt-5.4-mini`
- v1: 60 rows，原始物理量长序列
- v2 final: 60 rows，compact block physical features
- prompt 输入：scene, decision_rule, variables, question, options, time_series_table
- prompt 排除：natural evidence caption, support slots, simulator background, outside knowledge

v2 by-source 结果：

| source | acc |
| --- | ---: |
| grid2op | 1.0000 |
| aiopslab | 0.9000 |
| finrl | 0.9000 |
| traffic | 0.8000 |
| citylearn | 0.5000 |
| water | 0.4000 |
| overall | 0.7500 |

Interpretation:

1. v2 比 v1 明显更可答，说明“自包含背景 + compact physical features + 显式规则”是正确方向。
2. Grid2Op/FinRL/AIOps/Traffic 已经接近可作为扩增模板。
3. CityLearn/Water 仍需人工 reviewer 重点审核，因为模型常在 reason 中算对，但最终 JSON 字段写错。
4. 这类 benchmark 应报告两个指标：strict MCQ accuracy，以及 reason/gold consistency diagnostic。最终主分数仍应以 MCQ 为准。

## 剩余问题

1. **答案字段不一致**：v2 final 的 15 个错例中，13 个错例 reason 提到 gold label，但 `answer` 写错。需要在 reviewer 里加入“reason-final answer consistency”检查。
2. **CityLearn 负类易错**：gap < 0.30 时应 balanced，但模型会被最大 third 诱导。需要让题目更像“是否有显著峰段”，而不是“哪个时段最高”。
3. **Water 规则仍复杂**：leak/recovery/stable 同时涉及 pressure drop、flow increase、post recovery、rule precedence，适合作为 hard split，但不适合作为早期 easy split。
4. **答案字母不平衡**：当前 smoke set 不能直接作为正式 benchmark 结果集。
5. **模型面还不足**：目前只跑了一个通用 LLM。投稿前至少需要 4-6 个通用 LLM + 2-3 个 TS-LLM/TS adapter baseline。

## 扩增建议

下一步用 simulator + reviewer 做三阶段扩增：

1. **Easy/Medium/Hard 分层**
   - Easy: 单派生量 + 明确阈值，如 Grid2Op risk、FinRL return/drawdown。
   - Medium: 分段比较 + 负类，如 CityLearn reserve、Traffic recovery。
   - Hard: 多条件优先级，如 Water leak/recovery、AIOps symptom triage。

2. **Reviewer gate**
   - local deterministic gate: support slot 与 answer 一致。
   - LLM data-only probe gate: GPT 只看题面和 values，至少一个强模型能在小样本上达到 >80%。
   - consistency gate: reason 中的 final conclusion 必须与 returned answer label 一致。
   - background gate: scene/question 不出现 simulator 名称，不要求平台知识。

3. **正式数据扩增目标**
   - 每 domain 先扩到 100-200 条，六 domain 共 600-1200 条。
   - 保持 answer-letter balanced，每个 domain 内 A/B/C/D 接近均匀。
   - 每条保留 `raw_full_values`、`solver_values`、`support_slots`、`reviewer_decision`、`llm_probe_result`。
   - 报告 meta-only、question-only、numbers/compact-values-only、oracle evidence caption、generic caption 等 baseline。

## 投稿可行性判断

如果只做 benchmark generation，不做模型训练，这个方向可以投稿 workshop/short-style benchmark paper；要投主会，需要尽快补齐：

1. 规模：至少 600+ 高质量样本，最好 1000+。
2. 多模型评测：通用 LLM、TS-LLM、numbers-only、oracle evidence、generic caption。
3. 人工/LLM reviewer 协议：证明数据不是 slot lookup，而是自包含推理 QA。
4. 错误分析：按 domain、reasoning skill、horizon、compact vs raw input 分析。
5. 可复现 pipeline：simulator trace -> compact features -> rule answer -> natural QA -> reviewer -> benchmark split。

当前 v2 smoke 结果支持继续做，但不建议直接把这 60 条作为最终 benchmark。它更适合作为扩增规范和 reviewer gate 的 seed set。
