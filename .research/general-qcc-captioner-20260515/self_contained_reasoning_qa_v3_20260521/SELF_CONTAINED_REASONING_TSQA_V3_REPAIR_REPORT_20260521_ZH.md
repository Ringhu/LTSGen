# Self-contained Reasoning TSQA v3 Repair Report（2026-05-21）

## 结论

v3 的目标不是重新发明 QA 规则，而是把 v2 中已经自包含的题面保留下来，修复 caption 训练目标泄漏，并把可扩增 seed 与需错误归因样本拆开。

- 全量 v3 rows：60
- positive seed ready：41
- needs error attribution：19
- answer-balanced positive eval：12
- target/caption `Answer label` 类泄漏命中：0
- target/caption `the rule maps this to` 类模板命中：0

## 输入

- v2 rows: `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/self_contained_reasoning_tsqa.jsonl`
- data-only probe: `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/data_only_probe_full60/self_contained_reasoning_tsqa_gpt_data_only_probe.json`

## 输出

- 全量 v3：`.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/self_contained_reasoning_tsqa.jsonl`
- positive ready：`.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/self_contained_reasoning_tsqa_v3_ready.jsonl`
- 需错误归因：`.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/self_contained_reasoning_tsqa_v3_needs_error_attribution.jsonl`
- answer-balanced eval 子集：`.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/self_contained_reasoning_tsqa_v3_balanced_positive_eval.jsonl`
- SFT caption rows：`.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/self_contained_reasoning_tsqa_sft.jsonl`
- summary: `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/self_contained_reasoning_tsqa_v3_summary.json`

## 分布

- all by domain: `{"grid2op": 10, "citylearn": 10, "traffic": 10, "water": 10, "aiopslab": 10, "finrl": 10}`
- ready by domain: `{"grid2op": 9, "citylearn": 4, "traffic": 4, "water": 5, "aiopslab": 9, "finrl": 10}`
- needs attribution by domain: `{"grid2op": 1, "citylearn": 6, "traffic": 6, "water": 5, "aiopslab": 1}`
- all answer distribution: `{"C": 8, "B": 5, "A": 31, "D": 16}`
- ready answer distribution: `{"C": 3, "B": 4, "A": 21, "D": 13}`
- balanced eval answer distribution: `{"D": 3, "A": 3, "C": 3, "B": 3}`

## 修复动作

1. 删除 v2 `target_caption/output/oracle_evidence_caption` 中的答案标签句。
2. 将 caption 改成 evidence-only：给出聚合量、阈值门槛是否满足、优先级检查结果，但不输出选项字母。
3. 保留 `support_slots/options/answer`，gold answer 仍完全由 deterministic slots 决定。
4. 使用输入 data-only probe 结果做初始分流：semantic pass 进入 positive seed；semantic wrong 进入 error attribution。

## 解释

positive seed ready 不是最终 benchmark，只是下一轮扩增的干净起点。需错误归因样本不能直接丢弃，因为 data-only wrong 可能是模型能力或输出解析问题；但在完成归因前，不应把这些样本混入正例扩增。
