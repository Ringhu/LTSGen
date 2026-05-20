# Natural QCC Failure-Domain 数据扩容完成度审计（2026-05-20）

## 审计结论

状态：complete

这轮“开始做数据扩容”的目标已经完成到可同步、可复现、可进入训练对比的程度。最终产物包含候选、natural rewrites、GPT-5.5 reviewer 结果、positive-only 数据集、合并数据、evidence-only SFT 输入、质量审计、semantic QA 和 probe 诊断。

## 完成项

| item | status | evidence |
| --- | --- | --- |
| 聚焦失败域扩容 | pass | `grid2op` 12 -> 31, `traffic` 11 -> 41, `water` 11 -> 31 |
| reviewer gate | pass | 第一批 72 -> 49 positive；第二批 32 -> 20 positive |
| 防重复抽样 | pass | 第二批使用 `--exclude_jsonl`，最终 duplicate id count 为 0 |
| positive-only 合并 | pass | `merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl`, n=124 |
| schema gate | pass | missing required count 为 0 |
| evidence-only SFT | pass | `sft_evidence_only_v2/`, train=89, test=35 |
| no-question control | pass | `sft_evidence_only_v2/*no_question*` |
| target quality audit | pass | quality_gate_pass=true, no answer-label leak, no option-letter leak |
| semantic QA gate | pass | test accuracy=1.0000, empty_answer_rate=0.0000 |
| probe diagnostics | pass | oracle=1.0000, generic=0.0323, question_only=0.0726 |
| large/checkpoint file avoidance | pass | no model/checkpoint artifacts generated |

## 剩余风险

- 这轮只是数据扩容和训练输入准备，不是训练结果。
- 个别 volatility/context caption 没有显式数字，虽然 semantic QA 可答，但后续扩容应提高数字证据覆盖。
- CityLearn/AIOps 没有在本轮继续扩，因为本轮目标是先补失败域；后续如果要做 cross-domain benchmark，还需要补齐它们。

## 建议下一步

使用 `sft_evidence_only_v2/` 直接启动小规模 qcond vs no-question 训练对比，并和 55 条样本的旧基线比较：

- old 55-row evidence-only：qcond 0.2308 vs no-question 0.1538
- new 124-row data：先跑同配置 e5/tok128，再决定是否继续扩到 200-300 条

如果新训练没有提升，应优先分析失败任务族和 caption target，而不是继续扩大样本数。
