# Natural QCC Failure-Domain 数据扩容报告（2026-05-20）

## 结论

这轮扩容的目标是把原先 55 条 reviewer-positive natural QCC 样本，优先扩到 Grid2Op、Traffic、Water 这些失败/薄弱域上，并保持“自然问题 + 可验证证据 + reviewer gate”的质量约束。

当前结果是：最终 positive pool 达到 124 条，其中 Grid2Op/Traffic/Water 分别为 31/41/31 条；SFT 训练侧为 89 条，测试侧为 35 条。schema gate、target caption quality gate 和 deterministic semantic QA gate 均通过。

这说明数据扩容这一步已经可以收尾，并进入下一步模型训练对比；但它还不是模型方法成功的证据。

## 为什么先扩这些域

原始 55 条 positive 样本分布不均，失败域样本偏少：

| domain | 原始 positive | 扩容后 positive |
| --- | ---: | ---: |
| `aiopslab_official_v3` | 12 | 12 |
| `citylearn` | 9 | 9 |
| `grid2op` | 12 | 31 |
| `traffic` | 11 | 41 |
| `water` | 11 | 31 |

因此本轮没有继续平均扩所有域，而是集中补 Grid2Op/Traffic/Water，尤其补 counterfactual、lead-lag、domain context、event recovery、cross-variable relation 等更接近真实 domain QA 的任务。

## 扩容流程

本轮不是直接把候选都塞进训练集，而是分两批做 reviewer gate：

| batch | 候选 | reviewer 结论 | positive |
| --- | ---: | --- | ---: |
| Grid2Op/Traffic/Water 第一批 | 72 | keep 49 / revise 17 / reject 6 | 49 |
| Traffic/Water 第二批 | 32 | keep 20 / revise 12 / reject 0 | 20 |

第二批使用 `--exclude_jsonl` 排除了原始候选和第一批候选，避免重复抽样。最终合并时 duplicate id count 为 0。

被 reviewer 挡掉的样本主要不是“文字不好看”，而是存在更实质的问题：规则和 gold answer 不一致、阈值隐含、事件阶段描述不清、domain stress 选项边界不明确、或问题仍像 verifier slot 拼接。这说明 reviewer gate 起到了质量过滤作用。

## 最终数据集

最终 positive pool：

- 文件：`merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl`
- 总数：124
- split：train 69 / dev 20 / test 35
- answer distribution：A 23 / B 37 / C 30 / D 34
- duplicate id count：0
- missing required count：0

按域分布：

| domain | positive | train | dev | test |
| --- | ---: | ---: | ---: | ---: |
| `aiopslab_official_v3` | 12 | 5 | 2 | 5 |
| `citylearn` | 9 | 5 | 2 | 2 |
| `grid2op` | 31 | 14 | 7 | 10 |
| `traffic` | 41 | 25 | 4 | 12 |
| `water` | 31 | 20 | 5 | 6 |

SFT 输入：

- qcond train：89
- qcond test：35
- no-question control train：89
- no-question control test：35
- 文件目录：`sft_evidence_only_v2/`
- schema gate：pass
- 训练目标已去掉 `Answer label:` 后缀
- option letter leak：0

## 质量审计

Target caption quality audit（test split, n=35）：

| metric | value |
| --- | ---: |
| evidence_shape_rate | 0.8857 |
| numeric_evidence_rate | 0.8857 |
| answer_label_only_rate | 0.0000 |
| option_letter_leak_rate | 0.0000 |
| jsonish_output_rate | 0.0000 |
| too_short_rate | 0.0000 |
| quality_gate_pass | true |

审计发现 4 条 caption 没有显式 numeric evidence，主要集中在 volatility 这类语义证据描述。它们没有泄漏答案，也没有破坏语义可答性；但后续如果继续扩容，可以优先修这些风格问题，让所有 evidence caption 都尽量带可核验数字。

Deterministic semantic QA（test split, n=35）：

| domain | n | accuracy |
| --- | ---: | ---: |
| `aiopslab_official_v3` | 5 | 1.0000 |
| `citylearn` | 2 | 1.0000 |
| `grid2op` | 10 | 1.0000 |
| `traffic` | 12 | 1.0000 |
| `water` | 6 | 1.0000 |

整体 semantic QA accuracy 为 1.0000，empty answer rate 为 0.0000。这个结果只说明目标 evidence caption 可以被 deterministic semantic bridge 还原到正确答案，不代表训练模型已经学会生成这些 caption。

## Probe 诊断

Probe 结果用于确认数据接口是否合理，不作为最终模型结果：

| condition | accuracy |
| --- | ---: |
| natural oracle | 1.0000 |
| natural evidence without label | 0.5968 |
| generic caption | 0.0323 |
| statistical caption | 0.0000 |
| question only | 0.0726 |
| nearest caption, question-conditioned | 0.2286 |
| nearest caption, no-question | 0.1714 |

这个诊断符合预期：oracle evidence 很强，generic/statistical/question-only 很弱；question-conditioned nearest baseline 比 no-question 高一点，但仍然很弱，说明真正需要训练 captioner 生成问题相关证据。

## 产物索引

- 第一批候选：`candidates/natural_qcc_failure_domain_candidates.jsonl`
- 第一批 reviewer：`rewrites/natural_qcc_failure_domain_rewrites_review.json`
- 第一批 positive：`dataset/natural_qcc_failure_domain_expansion_positive.jsonl`
- 第二批候选：`candidates_tw2/natural_qcc_failure_domain_tw2_candidates.jsonl`
- 第二批 reviewer：`rewrites_tw2/natural_qcc_failure_domain_tw2_rewrites_review.json`
- 第二批 positive：`dataset_tw2/natural_qcc_failure_domain_tw2_expansion_positive.jsonl`
- 最终合并 positive：`merged_v2/natural_qcc_crossdomain_failure_expanded_v2_positive.jsonl`
- 最终 SFT：`sft_evidence_only_v2/`
- 质量审计：`sft_evidence_only_v2/target_caption_quality_audit.json`
- 语义 QA：`sft_evidence_only_v2/target_semantic_qa/semantic_qa_metrics.json`
- Probe：`probe_eval_v2/natural_qcc_probe_results.json`

## 下一步建议

下一步应该做一个小而明确的训练对比，而不是继续无上限扩容：

1. 用 `sft_evidence_only_v2/` 跑上一轮最佳设置的 qcond vs no-question 训练，保持 e5/tok128 配置，和 55 条样本的旧结果直接对比。
2. 评估 test split 的 semantic QA、caption quality、qcond-no-question gap，并按 domain/task family 看失败模式。
3. 如果 v2 比 55 条样本有稳定提升，再把 positive pool 扩到约 200-300 条；如果没有提升，优先修训练目标和任务分布，而不是继续堆样本。
4. 针对本轮审计暴露的 4 条 no-numeric evidence 和 reviewer 高风险类型，增加 rewrite 规则：volatility/context 类问题也必须给出可核验数字、阈值或对比量。

当前最重要的实验问题是：这些更自然、更宽的 evidence-only 样本，能不能让 QCC captioner 真的比 no-question control 学到更多问题条件化信息。
