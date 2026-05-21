# Caption Model Longline Active / Archive Index（2026-05-21）

## 当前分支定位

当前应该聚焦的分支是 `caption-model-longline`。

这个分支不是“所有历史 case study 和 smoke 输出的全集”，而是 caption model
路线的工作分支：保留训练脚本、数据构造脚本、模型诊断报告，以及少量对当前设计判断有用的
Natural TS-QA/QCC 样例。

## 这次检查结论

`caption-model-longline` 已经包含最近工作的主要脚本：

- `scripts/generate/build_natural_qcc_case_quality_v1.py`
- `scripts/generate/build_scenario_first_real_source_smoke.py`
- `scripts/generate/build_self_contained_reasoning_tsqa.py`
- `scripts/eval/audit_scenario_first_real_source_smoke.py`
- `scripts/eval/probe_self_contained_reasoning_tsqa_llm.py`

但 consolidation 提交 `dc5e0fc` 曾经为了精简分支删除了一些新近产物。因此这次从
`codex/natural-tsqa-benchmark-assets-20260520` 恢复了小而关键的报告/样本，避免
“脚本在、报告和图不在”的状态。

## 当前应保留并继续看的文件

### 0. Natural QCC 研究路线与 Reviewer Gate

路径：

`.research/general-qcc-captioner-20260515/NATURAL_QCC_RESEARCH_ROUTE_AND_REVIEWER_GATE_20260521_ZH.md`

保留原因：

- 这是当前和用户对齐后的研究路线说明。
- 明确了数据生成应该是场景先行，而不是拿 support slots 找问题。
- 明确了 reviewer gate 是分诊系统，不是让 LLM 决定答案。
- 明确了 `qa_seed_ready` 和 `caption_train_ready` 必须分开。

这份文档也已经写入 `AGENTS.md`，后续会话应按它执行。

### 1. Natural QCC case quality v1

路径：

`.research/general-qcc-captioner-20260515/natural_qcc_case_quality_v1_20260521/`

保留原因：

- 12 条 case，Grid2Op、CityLearn、Traffic、Water、AIOpsLab、FinRL 每域 2 条。
- 每条有时序图、中文题面、中文选项、中文 caption 和英文 target caption。
- 这是回应“题目必须自足、caption 要围绕答案解释时序证据”的最新小样本。

注意：

- 它是质量讨论样本，不是正式 benchmark。
- 仍然需要继续人工 review，因为用户已经指出 Grid2Op、CityLearn、Traffic、Water、
  AIOpsLab、FinRL 的变量前置介绍、业务规则、caption 对齐还不够稳。

### 2. Self-contained reasoning TSQA v2

路径：

`.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/`

保留原因：

- 60 条，每个域 10 条。
- 题面包含场景、变量定义、规则和 compact physical features。
- GPT data-only probe 在只看题面和时序表、不看 evidence caption 的情况下达到 0.75。
- 它比纯 slot lookup 更接近“普通 QA + 时序推理”的方向。

当前限制：

- 答案字母不平衡，不能直接作为正式 benchmark。
- CityLearn 和 Water 还有规则边界和答案一致性问题。
- 这是扩增规范 seed，不是最终数据集。

### 3. Real-source Natural QCC smoke v2 report-only

路径：

`.research/general-qcc-captioner-20260515/scenario_first_real_source_smoke_v2_20260521/`

当前只保留：

- `REAL_SOURCE_NATURAL_QCC_SMOKE_REPORT_20260521_ZH.md`
- `REAL_SOURCE_NATURAL_QCC_SMOKE_COMPLETION_AUDIT_20260521.md`
- `real_source_natural_qcc_smoke_summary.json`
- `real_source_natural_qcc_smoke_audit.json`

保留原因：

- 它说明 60 条、每域 10 条的 real-source smoke 已经做过。
- 它记录每个域的数据来源：Grid2Op/CityLearn real trace、SUMO、WNTR、AIOpsLab、
  FinRL-style historical OHLCV。

为什么不恢复完整目录：

- 完整目录有 60 张图和多份大 JSONL/SFT，只适合复现实验，不适合放在当前精简分支长期维护。
- 当前用户已指出这批 case 质量不足，所以它只保留为来源和审计记录。

### 4. Seed quality review v1

路径：

`.research/general-qcc-captioner-20260515/seed_quality_review_v1_20260521/`

保留原因：

- 它是当前 12 条 case-study seed 和 60 条 self-contained seed 的质量审计。
- 它把 QA seed 是否可用和 caption target 是否可训练分开判断。
- 当前结论是：72 条里 57 条 QA seed ready，但只有 10 条 caption train ready；
  self-contained v2 的 60 条都需要先清洗 `target_caption`。

用途：

- 作为下一轮 v3 seed 修复清单。
- 作为扩增前 reviewer gate 的第一版实现。
- 防止后续继续把带 `Answer label` 的 caption 当作 evidence-only 训练目标。

## 当前 caption-model 训练相关文件

这些文件继续保留在当前分支，因为它们解释了为什么 v2.2 qcond 训练会空生成，以及后续修复标准：

- `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/`
- `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/`
- `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/`
- `.research/general-qcc-captioner-20260515/NATURAL_QCC_CROSSDOMAIN_DATA_ASSET_AND_TRAINING_AUDIT_20260520_ZH.md`
- `.research/general-qcc-captioner-20260515/NATURAL_QCC_CROSSDOMAIN_OBJECTIVE_COMPLETION_AUDIT_20260520_ZH.md`
- `.research/general-qcc-captioner-20260515/NATURAL_QCC_EXPANSION_GPU_HANDOFF_20260520_ZH.md`

## 归档但不恢复的历史材料

以下材料不建议放回 `caption-model-longline` 主工作面。需要时从历史提交恢复即可。

| 材料 | 历史位置/提交 | 当前处理 |
| --- | --- | --- |
| `natural_qa_pilot_20260519` | `codex/natural-tsqa-benchmark-assets-20260520` | 早期 6 条 pilot，被后续 case-quality/self-contained v2 取代，不恢复 |
| `natural_qa_balanced8_20260519` | `codex/natural-tsqa-benchmark-assets-20260520` | 48 条早期候选，用户已指出自然性和变量解释不足，不恢复 |
| `scenario_first_multidomain_smoke_v2_20260520` | `e768d65` | controlled/source 混合烟测，被 real-source smoke 与 case-quality 取代，不恢复 |
| `scenario_first_real_source_smoke_v2_20260521` 完整图和 JSONL | `5ed54e4` | 只保留报告、summary、audit；完整实验产物不恢复 |
| `aiopslab_official_v1/v3` 大批 JSONL | `codex/natural-tsqa-benchmark-assets-20260520` | 原始/中间数据，不放当前分支 |
| `finrl_local_ohlcv_smoke_20260521` 完整 JSONL | `codex/natural-tsqa-benchmark-assets-20260520` | 原始 smoke 数据，不放当前分支 |
| 旧 `multisim_qcc_v1/v5` 产物 | `codex/natural-tsqa-benchmark-assets-20260520` | 老 slot/verifier 风格，不作为当前 Natural-QCC 主样例 |

## 恢复规则

如果后续确实需要某个归档目录，用下面的方式从历史里按路径恢复，而不是合并整条旧分支：

```bash
git checkout <commit-or-branch> -- <path>
```

恢复原则：

- 优先恢复报告、summary、audit、少量代表图。
- 不恢复 checkpoint、prediction dump、大型 SFT 全量输出。
- 不把早期用户已否定的 case study 重新作为当前质量样例。
- 新增文件放在 `.research/general-qcc-captioner-20260515/<dated-dir>/` 下，并在本索引里登记。

## 当前下一步建议

这个分支已经适合继续做 caption-model 路线，但下一步不应该继续堆旧 smoke 数据。

更合理的顺序是：

1. 以 `self_contained_reasoning_qa_v2_20260521` 为 seed，修 CityLearn/Water 的规则和答案一致性问题。
2. 以 `natural_qcc_case_quality_v1_20260521` 为反例/样例，重新定义“好 caption”的标准。
3. 扩增前先做 reviewer gate：变量解释、规则自足、caption 是否围绕答案、英文/中文 caption 是否一致。
4. 数据过 gate 后再进入 qcond/no-question 训练，而不是先训练再补解释。

当前 reviewer gate 已落地为：

- `scripts/eval/review_natural_qcc_seed_quality.py`
- `tests/eval/test_review_natural_qcc_seed_quality.py`
