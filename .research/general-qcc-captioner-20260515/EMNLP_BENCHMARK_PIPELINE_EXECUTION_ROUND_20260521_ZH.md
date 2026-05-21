# EMNLP Benchmark Pipeline 执行报告（2026-05-21）

## 结论

本轮已经把 `emnlp-benchmark-pipeline` 分支补成一个可继续扩增的 benchmark-generation 工作分支：同步了 longline 分支的 reviewer gate 和质量规范，生成了 `self_contained_reasoning_qa_v3`，跑完 deterministic verifier、reviewer gate、answer balance audit 和 GPT data-only probe。

当前 canonical 口径是：**v3 全量 60 条，41 条可作为 positive seed，19 条进入错误归因队列；caption 泄漏审计为 0；answer-balanced eval 子集为 12 条，A/B/C/D 各 3 条。**

这说明 v2 最大的 caption supervision 泄漏问题已经修掉，但 CityLearn / Traffic / Water 的规则执行仍是扩增前的主要风险。不能直接把全量 60 条都扩增；应优先使用 41 条 positive seed，并对 19 条错例做归因和规则修订。

## 本轮执行了什么

### 1. 同步 longline 的质量标准

已从 `caption-model-longline` 同步到当前分支：

- `.research/general-qcc-captioner-20260515/NATURAL_QCC_RESEARCH_ROUTE_AND_REVIEWER_GATE_20260521_ZH.md`
- `.research/general-qcc-captioner-20260515/seed_quality_review_v1_20260521/`
- `scripts/eval/review_natural_qcc_seed_quality.py`
- `tests/eval/test_review_natural_qcc_seed_quality.py`

同步后的 reviewer gate 与 AGENTS.md / Natural-QCC 质量要求一致：gold answer 只能来自 deterministic support slots；LLM reviewer 只做自然性、可答性、准确性风险和错误归因；`gpt_data_only_wrong` 是诊断信号，不自动删除样本。

### 2. 生成 v3 修复数据

新增脚本：

- `scripts/generate/repair_self_contained_reasoning_tsqa_v3.py`

输入：

- `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/self_contained_reasoning_tsqa.jsonl`
- `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/data_only_probe_full60/self_contained_reasoning_tsqa_gpt_data_only_probe.json`

输出目录：

- `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/`

关键产物：

- `self_contained_reasoning_tsqa.jsonl`：v3 全量 60 条
- `self_contained_reasoning_tsqa_v3_ready.jsonl`：41 条 positive seed
- `self_contained_reasoning_tsqa_v3_needs_error_attribution.jsonl`：19 条需错误归因
- `self_contained_reasoning_tsqa_v3_balanced_positive_eval.jsonl`：12 条 answer-balanced eval 子集
- `self_contained_reasoning_tsqa_sft.jsonl`：41 条 evidence-only caption SFT rows
- `self_contained_reasoning_tsqa_v3_summary.json`
- `SELF_CONTAINED_REASONING_TSQA_V3_REPAIR_REPORT_20260521_ZH.md`

v3 修复动作：

1. 移除 v2 `target_caption/output/oracle_evidence_caption` 中的 `Answer label` 泄漏。
2. 把 caption 改成 evidence-only：写聚合量、阈值门槛是否满足、优先级检查结果，不输出选项字母。
3. 保留 `support_slots/options/answer`，gold answer 仍由 deterministic slots 决定。
4. 使用 full60 data-only probe 结果做 canonical 分流。

## 核心指标

### v3 本地审计

- rows：60
- positive seed ready：41
- needs error attribution：19
- balanced positive eval：12
- `target_answer_label_phrase_hits`：0
- `rule_maps_template_hits`：0
- `target_exact_answer_label_hits`：0
- answer-balanced eval：A=3, B=3, C=3, D=3

分域 positive seed：

| domain | ready / all |
| --- | ---: |
| grid2op | 9 / 10 |
| citylearn | 4 / 10 |
| traffic | 4 / 10 |
| water | 5 / 10 |
| aiopslab | 9 / 10 |
| finrl | 10 / 10 |

### GPT data-only probe

full60 probe 产物：

- `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/data_only_probe_full60/self_contained_reasoning_tsqa_gpt_data_only_probe.json`
- `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/data_only_probe_full60/SELF_CONTAINED_REASONING_TSQA_GPT_DATA_ONLY_PROBE_20260521_ZH.md`

结果：

- semantic accuracy：41/60 = 0.6833
- mean latency：3.803s
- needs full series：0

| domain | semantic correct |
| --- | ---: |
| grid2op | 9 / 10 |
| citylearn | 4 / 10 |
| traffic | 4 / 10 |
| water | 5 / 10 |
| aiopslab | 9 / 10 |
| finrl | 10 / 10 |

balanced8 smoke probe 也跑通，结果为 7/8；唯一错例是模型 reason 算出 gold，但 JSON `answer` 字段填错。

### 错误归因

新增脚本：

- `scripts/eval/summarize_tsqa_probe_error_attribution.py`

产物：

- `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/data_only_probe_full60/self_contained_reasoning_tsqa_gpt_data_only_error_attribution.json`
- `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521/data_only_probe_full60/SELF_CONTAINED_REASONING_TSQA_GPT_DATA_ONLY_ERROR_ATTRIBUTION_20260521_ZH.md`

19 个 semantic wrong 中：

- `reason_supports_gold_output_field_wrong`：14
- `reason_mentions_gold_but_output_wrong`：2
- `reason_does_not_recover_gold`：3

解释：多数错例不是模型不会算，而是 reason 中已经算对或写出 gold，最后 JSON 字段却填了另一个选项。扩增前仍应把它们放入错误归因队列，因为 benchmark 不能依赖 probe 模型的自我矛盾来判定题目质量。

真正优先修的 3 类风险：

1. Grid2Op 有 1 条极小变化样本，模型误认为 low-change gate 不满足，规则措辞需要更明确。
2. CityLearn / Traffic 容易出现 “reason 正确但 answer 字段偏向固定选项” 的输出一致性问题，后续 probe prompt 应增加最终自检约束或二次解析。
3. Water 有少量样本在 ordered rule 上仍会混淆 recovery / stable / manual review，需要把规则优先级写得更短、更硬。

### Reviewer gate

canonical full-probe review 产物：

- `.research/general-qcc-captioner-20260515/seed_quality_review_v3_fullprobe_20260521/`

结果：

- 总 review 条目：72
- decision：69 keep, 3 revise
- QA seed ready：72/72
- caption train ready：70/72
- needs error attribution：19/72
- self-contained v3：60/60 QA-ready, 60/60 caption-train-ready, 19/60 needs error attribution
- Natural-QCC case-quality v1：12/12 QA-ready, 10/12 caption-train-ready

注意：reviewer gate 的 `qa_seed_ready` 只说明题面结构和 deterministic 支撑完整；真正进入正例扩增仍应使用 v3 生成脚本分出的 `v3_positive_seed_ready=True` 子集。

## 验证记录

已通过：

- `python3 -m py_compile scripts/generate/repair_self_contained_reasoning_tsqa_v3.py`
- `python3 -m py_compile scripts/eval/review_natural_qcc_seed_quality.py`
- `python3 -m py_compile scripts/eval/probe_self_contained_reasoning_tsqa_llm.py`
- `python3 -m py_compile scripts/eval/summarize_tsqa_probe_error_attribution.py`
- 手动执行 `tests/eval/test_review_natural_qcc_seed_quality.py` 中 3 个断言函数：通过
- 本地 verifier 断言：
  - 60 条 v3 rows
  - 41 条 ready rows
  - `answer_label == support_slots.answer_label`
  - caption 泄漏 regex 命中为 0
  - balanced eval 子集 A/B/C/D 各 3 条

未能直接运行：

- `python3 -m pytest tests/eval/test_review_natural_qcc_seed_quality.py`

原因：当前环境没有安装 `pytest`。我已用直接导入测试文件并执行三个 test 函数的方式跑过同一组断言。

## 对投稿路线的判断

这轮以后，当前分支已经具备投稿叙事里的一个可展示 pipeline：

1. simulator trace / compact physical values
2. deterministic rule + support slots 生成 gold
3. Natural-QCC reviewer gate
4. data-only probe
5. error attribution
6. clean evidence-only caption target
7. answer-balanced eval slice

但它还不是最终 benchmark。现在最主要的问题不是 caption 泄漏，而是 seed 规模、answer 分布和中间域规则稳定性：

- 全量 answer distribution 仍偏 A：A=31, B=5, C=8, D=16。
- full-probe positive seed 只有 41 条，balanced eval 只有 12 条。
- CityLearn / Traffic / Water 的规则执行鲁棒性不够，扩增前要先修规则表达和 probe prompt。
- 还没有多模型评测矩阵，也没有 human/reviewer 二次审核记录。

因此建议下一步不要立刻大规模生成，而是先做 “v3.1 seed repair + balanced expansion smoke”。

## 下一步建议

1. 先修 19 条 error-attribution queue，尤其是 3 条 `reason_does_not_recover_gold`。
2. 调整 data-only probe prompt：要求先写 `computed_rule_outcome`，再由程序校验 option label，减少 reason 正确但 JSON 字段错。
3. 对 CityLearn / Traffic / Water 重写更短的 ordered rules，把 threshold 和 precedence 拆成枚举步骤。
4. 基于 41 条 ready seed 扩到每域至少 50-100 条，生成时强制 answer-letter balance。
5. 对扩增数据跑同一套 gates：local verifier、data-only probe、reviewer gate、error attribution、answer balance。
6. 再上多模型评测：通用 LLM、TS-LLM、numbers-only、oracle evidence、generic caption、wrong-caption diagnostic。
