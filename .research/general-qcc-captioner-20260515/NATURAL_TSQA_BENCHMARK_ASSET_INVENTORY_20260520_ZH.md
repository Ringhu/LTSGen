# Natural TS-QA Benchmark 资产盘点（2026-05-20）

## 目标定位

当前分支用于整理自然语言 TS-QA benchmark 的种子资产，不以 QCC 模型训练为主线。

目标 QA 风格以 `natural_qa_pilot_20260519` 为准：

- `Scene` 说明领域、用户角色、变量含义、时间轴和判定规则。
- `Question` 只问一个自然领域决策。
- `Options` 是普通读者可理解的答案，不是 support-slot label。
- `Gold` 仍由 deterministic support slots / simulator state 决定。
- `Evidence` 给出足够支撑 gold 的可验证事实。
- `Reviewer` 只审核自然性、可答性和准确性风险，不能决定 gold answer。

这和旧 `multisim_qcc_v5_aiops_v3` 的 slot/verifier 风格不同。旧 1980 条是原始候选池和工程底座，不应直接作为论文中的自然 QA benchmark 主数据。

## 当前分支

- 分支：`codex/natural-tsqa-benchmark-assets-20260520`
- 资产来源：`codex/question-repair-20260519-ready`
- 主要用途：后续自然 QA 数据扩增、审核、benchmark 评测。

## 已恢复的自然 QA 样例资产

### 1. 六条高质量 pilot

路径：

`.research/general-qcc-captioner-20260515/natural_qa_pilot_20260519/`

核心文件：

- `NATURAL_TSQA_CASE_PILOT_20260519_ZH.md`
- `NATURAL_TSQA_CASE_PILOT_GPT55_REVIEW_20260519_ZH.md`
- `NATURAL_TSQA_DESIGN_RULES_20260519_ZH.md`
- `natural_tsqa_case_pilot.json`
- `natural_tsqa_case_pilot_gpt55_review.json`
- `figures/*.png`
- `skill/`

覆盖 6 个域：

| source | case |
| --- | --- |
| `grid2op` | 断线后线路压力检查 |
| `citylearn` | 建筑负载调度判断 |
| `finrl_scaled` | MRK 回撤风险复盘 |
| `water` | 供水网络服务状态判断 |
| `traffic` | 交通信号策略队列影响比较 |
| `aiopslab_official_v3` | AIOpsLab 内存压力排查 |

Reviewer 结果：6/6 `keep`，naturalness/answerability 均达到可用标准，accuracy risk 均为 `low`。

### 2. balanced8 自然 QA 候选集

路径：

`.research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/`

核心文件：

- `natural_multisim_v5_balanced8.jsonl`
- `natural_multisim_v5_balanced8_lint.json`
- `natural_multisim_v5_balanced8_review.json`
- `NATURAL_QA_BALANCED8_LINT_20260519_ZH.md`
- `NATURAL_QA_BALANCED8_REVIEW_20260519_ZH.md`
- `NATURAL_QA_BALANCED8_CASE_STUDY_ANALYSIS_20260519_ZH.md`
- `figures/*.svg`

统计：

| item | value |
| --- | ---: |
| total rows | 48 |
| sources | 6 x 8 rows |
| candidate rows | 43 |
| excluded metadata-only rows | 5 |
| main lint issue | `metadata_only_not_pure_ts` |

用途：

- 小规模 case-study bank。
- 检查自然 QA 改写规则。
- 作为后续 full benchmark 扩增的风格模板。

注意：

- AIOps metadata/provenance/app/service/fault-context 题已被标记为不能进入 pure TS-QA 正例池。
- `natural_multisim_v5_balanced8.jsonl` 可作为扩增脚本和 reviewer prompt 的示例输入/输出。

## 已恢复的 cross-domain 扩增资产

### 3. crossdomain candidate 池

路径：

`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_candidates_20260520/`

核心文件：

- `natural_qcc_crossdomain_candidates.jsonl`
- `natural_qcc_crossdomain_candidates_sft.jsonl`
- `natural_qcc_crossdomain_candidates_manifest.json`
- `NATURAL_QCC_EXPANSION_CANDIDATES_20260519_ZH.md`

本地可扫描候选池统计：

| source | available rows |
| --- | ---: |
| `grid2op` | 1791 |
| `citylearn` | 1344 |
| `water` | 504 |
| `traffic` | 504 |
| `aiopslab_official_v3` | 25 |
| total | 4168 |

当前 selected candidate：

| item | value |
| --- | ---: |
| selected rows | 60 |
| per source | 12 |
| sources selected | `aiopslab_official_v3`, `citylearn`, `grid2op`, `traffic`, `water` |

重要缺口：

- 本地 manifest 记录 `finrl_scaled` split 文件缺失，因此当前 crossdomain candidate 暂未纳入 FinRL。
- 如果 benchmark 论文需要 finance 域，需要恢复或重新生成 `finrl_broad_scaled_v1_{train,dev,test}.jsonl`。

### 4. crossdomain rewrites + review

路径：

`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/`

核心文件：

- `natural_qcc_crossdomain_rewrites.jsonl`
- `natural_qcc_crossdomain_rewrites_lint.json`
- `natural_qcc_crossdomain_rewrites_review.json`
- `NATURAL_QCC_EXPANSION_REWRITES_20260519_ZH.md`
- `NATURAL_QCC_CROSSDOMAIN_REVIEW_20260520_ZH.md`

用途：

- 记录从候选 slot/old-QCC row 到自然 QA 表达的中间结果。
- 记录 reviewer 对自然性、可答性、准确性风险的判定。
- 作为大规模扩增时的 prompt/debug 样例。

### 5. crossdomain positive 小数据集

路径：

`.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/`

核心文件：

- `natural_qcc_crossdomain_positive.jsonl`
- `natural_qcc_crossdomain_excluded.jsonl`
- `natural_qcc_crossdomain_dataset_summary.json`
- `NATURAL_QCC_EXPANSION_DATASET_20260519_ZH.md`
- `sft/`
- `sft_no_question/`

Positive 集统计：

| item | value |
| --- | ---: |
| positive rows | 55 |
| excluded rows | 5 |
| schema gate | pass |
| max answer share | 0.3636 |
| value dims | 43 rows 3D, 12 rows 4D |

Positive by source：

| source | rows |
| --- | ---: |
| `aiopslab_official_v3` | 12 |
| `grid2op` | 12 |
| `traffic` | 11 |
| `water` | 11 |
| `citylearn` | 9 |

Answer distribution：

| answer | rows |
| --- | ---: |
| A | 10 |
| B | 20 |
| C | 12 |
| D | 13 |

用途：

- 当前最接近“自然 QA benchmark seed”的小规模正例集。
- 可用于验证 downstream LLM benchmark prompt、评测脚本、QA parser。
- `sft_no_question/` 可用于 question-only/no-question control，不是 benchmark 主数据。

## Probe / 诊断资产

路径：

`.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/`

核心文件：

- `natural_qcc_probe_positive.jsonl`
- `natural_qcc_probe_dataset_summary.json`
- `NATURAL_QCC_PROBE_DATASET_20260519_ZH.md`

统计：

- positive rows: 43

用途：

- 早期自然 QCC/TS-QA probe。
- 可作为脚本回归测试和小样本评估输入。
- 不建议直接作为最终 benchmark 主表，因为它是 probe，不是 full audited release。

## 已恢复的脚本资产

### 数据生成 / 改写 / 审核

- `scripts/generate/build_natural_tsqa_case_pilot.py`
- `scripts/generate/review_natural_tsqa_case_pilot.py`
- `scripts/generate/build_natural_tsqa_balanced8.py`
- `scripts/generate/review_natural_tsqa_balanced8.py`
- `scripts/generate/select_natural_qcc_expansion_candidates.py`
- `scripts/generate/build_natural_qcc_expansion_rewrites.py`
- `scripts/generate/review_natural_qcc_expansion_rewrites.py`
- `scripts/generate/build_natural_qcc_expansion_dataset.py`
- `scripts/generate/merge_natural_qcc_positive_sets.py`
- `scripts/generate/render_natural_qa_case_study.py`

### 评测 / 审计

- `scripts/eval/evaluate_natural_qcc_predictions.py`
- `scripts/eval/evaluate_natural_qcc_semantic_predictions.py`
- `scripts/eval/audit_natural_qcc_slot_factuality.py`
- `scripts/eval/audit_natural_qcc_caption_quality.py`
- `scripts/eval/run_natural_qcc_probe.py`

### 测试

- `tests/eval/test_audit_natural_qcc_caption_quality.py`
- `tests/eval/test_audit_natural_qcc_slot_factuality.py`
- `tests/eval/test_evaluate_natural_qcc_semantic_predictions.py`
- `tests/generate/test_natural_qcc_expansion_utils.py`

## 当前不应作为主资产的内容

以下内容可以保留为诊断参考，但不应作为 benchmark-generation 分支的中心叙事：

- 旧 `multisim_qcc_v5_aiops_v3` 的 1980 条 slot/verifier 风格 QA。
- QCC 模型训练结果、GPU smoke、qprefix/no-question 训练对比。
- 以 evidence caption 训练为目标的 SFT 文件，除非用于构造 baselines 或 ablations。
- AIOps app/service/fault/provenance metadata-only 题，除非单独定义为 metadata-context split。

## 下一步扩增建议

### P0：冻结 benchmark schema

建议新增统一字段：

- `id`
- `source`
- `split`
- `task_family`
- `abstract_primitive`
- `scene_en`, `scene_zh`
- `question_en`, `question_zh`
- `options`
- `answer`
- `answer_label`
- `evidence_en`, `evidence_zh`
- `support_slots`
- `review`
- `source_row_id`
- `values`
- `metadata_mode`: `pure_ts`, `context_ts`, `metadata_context`

### P1：恢复/补齐候选源

- 恢复 `finrl_broad_scaled_v1` split 文件，确保 finance 域进入 crossdomain 扩增。
- 对 AIOps 只保留 telemetry-grounded 题：CPU trend、memory extrema/window、network volatility、cross-signal relation。
- Metadata-only AIOps 题进入单独 split 或直接排除。

### P2：大规模扩增

从 4168 行本地候选池出发，先扩到：

- 5 source baseline: `grid2op`, `citylearn`, `water`, `traffic`, `aiopslab_official_v3`
- 恢复 FinRL 后扩到 6 source。
- 每个 source 先取 200-500 条自然 QA。
- reviewer gate 只保留 `decision=keep`, naturalness >= 4, answerability >= 4, accuracy risk = low。

### P3：benchmark 评测准备

需要补：

- question-only baseline；
- sampled-numbers prompt；
- statistical-caption prompt；
- oracle-evidence prompt；
- 多模型结果表；
- by source / by primitive / by horizon 分析；
- option balance 和 split leakage audit；
- human spot-check summary。

## 推荐论文叙事

题目方向：

`SimTSQA: Simulator-Derived Natural Question Answering for Verifiable Time-Series Reasoning`

核心主张：

> 我们不是直接把 simulator support slots 当成 QA，而是把 simulator-derived evidence 转成自然领域问题，并用 reviewer gate 过滤自然性和可答性，同时保留 deterministic support-slot gold。这个 benchmark 评估 LLM/TS-LLM 是否真的能基于时间序列和场景规则做 grounded temporal reasoning。

