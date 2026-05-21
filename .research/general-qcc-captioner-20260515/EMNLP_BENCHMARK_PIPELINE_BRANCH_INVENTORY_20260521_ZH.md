# EMNLP Benchmark Pipeline Branch Inventory（2026-05-21）

本文件记录 `emnlp-benchmark-pipeline` 分支的整理状态。目标是让后续工作集中在当前 benchmark generation 路线：natural TS-QA / simulator-derived QA / self-contained reasoning QA，而不是继续混用旧的 Multisim slot-style 训练资产。

## 1. 分支核对结论

已检查的相关分支：

| branch | 结论 |
| --- | --- |
| `codex/natural-tsqa-benchmark-assets-20260520` | 已完全包含在本分支历史中；merge-base 是 `1717200 Add self-contained TSQA case study report`。上一轮 v2 数据、case study、生成脚本和 probe 脚本都在本分支。 |
| `codex/question-repair-20260519-ready` | 主要包含较早的 question repair、numeric grounding repair、caption-model training diagnostics。不是当前 benchmark pipeline 主线，未整体导入。 |
| `caption-model-longline` | 保留 caption model longline / GPU / caption-quality 资产；这些属于模型训练分支，不应混入 benchmark pipeline。 |
| `shared-qcc-base` | 共享代码基础；本分支在其之上恢复 benchmark/data/paper-facing assets。 |

当前结论：用户最近关心的生成数据资产已经在 `emnlp-benchmark-pipeline`，不需要从别的分支补回 `self_contained_reasoning_qa_v2_20260521` 或对应脚本。

## 2. 当前主线资产

当前应优先使用以下目录和文件：

| 路径 | 用途 |
| --- | --- |
| `.research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/` | 当前 self-contained reasoning TS-QA v2 seed set，含 60 条、case study、generation spec、data-only GPT probe。 |
| `.research/general-qcc-captioner-20260515/scenario_first_real_source_smoke_v2_20260521/` | real-source scenario-first natural QCC smoke set，覆盖 Grid2Op/CityLearn/Traffic/Water/AIOpsLab/FinRL。 |
| `.research/general-qcc-captioner-20260515/scenario_first_multidomain_smoke_v2_20260520/` | six-domain scenario-first smoke set。 |
| `.research/general-qcc-captioner-20260515/natural_qcc_case_quality_v1_20260521/` | 12-case quality pilot，用于自然性和 case quality 审核。 |
| `.research/general-qcc-captioner-20260515/natural_qa_pilot_20260519/` | 早期自然 TS-QA 风格样例和 skill 设计参考。 |
| `.research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519/` | balanced natural QA pilot，可作为 reviewer 标准参考，但不是当前扩增主线。 |
| `.research/natural-tsqa-benchmark-20260520/` | natural TS-QA benchmark seed/candidates/reviews/rewrites 汇总资产。 |
| `scripts/generate/build_self_contained_reasoning_tsqa.py` | 当前 self-contained reasoning TS-QA 生成脚本。 |
| `scripts/eval/probe_self_contained_reasoning_tsqa_llm.py` | 当前 data-only LLM probe 脚本。 |

## 3. 已归档资产

以下内容已从主路径移入：

`.research/archive/emnlp-benchmark-legacy-20260521/`

归档原因是它们属于旧 Multisim/QCC 训练、schema alignment、question repair 或 v1 self-contained 中间资产，不应作为当前 EMNLP benchmark 扩增入口。

| 原路径类别 | 归档原因 |
| --- | --- |
| `MULTISIM_QCC_V1_*` root reports | 旧 Multisim QCC v1 训练/报告线。 |
| `MULTISIM_V5_*` root reports and schema audits | 旧 Multisim v5/AIOps 训练与 schema 对齐线。 |
| `QUESTION_REPAIR_*` root reports and `question_repair_20260519/` | 旧 question repair 线，保留作追溯，不作为当前生成入口。 |
| `multisim_qcc_v1/` | 旧训练/模型结果，不是当前 benchmark pipeline seed。 |
| `multisim_qcc_v5_aiops_v3/` | 旧 Multisim v5 训练与 rule-QA 结果，不是当前自然 QA 风格主线。 |
| `multisim_qcc_v5_aiops_v3/case_study_simulator_data_20260518/` | 从 `codex/question-repair-20260519-ready` 找回的旧 simulator-generated data case study；保留作历史参考，不作为当前自然 QA v2 扩增入口。 |
| `self_contained_reasoning_qa_20260521/` | v1 self-contained reasoning 数据，已由 v2 替代。 |

归档不是删除；如需追溯旧报告或复现实验，仍可从 archive 读取。

## 4. 当前分支仍保留但不是优先入口的资产

| 路径 | 说明 |
| --- | --- |
| `aiopslab_official_v1/`, `aiopslab_official_v3/` | AIOps official source/eval assets。暂保留，因为可能用于后续 benchmark source adapter 或 audit。 |
| `finrl_local_ohlcv_smoke_20260521/` | FinRL 本地 OHLCV smoke source。暂保留，因为可能用于金融 domain 扩增。 |
| `natural_qcc_crossdomain_*` | 5 月 20 日 cross-domain natural QCC pipeline 的候选、rewrite、dataset 资产；保留为扩增参考，但当前 self-contained reasoning v2 是更直接的 benchmark seed。 |
| `natural_qcc_probe_20260519/` | 早期 probe dataset，可用作负例/对照参考。 |

## 5. 下一步建议

1. 当前扩增入口固定为 `self_contained_reasoning_qa_v2_20260521`。
2. 先修 Water/CityLearn 的规则表达和 reviewer gate，再做大规模扩增。
3. 扩增脚本继续放在 `scripts/generate/`，probe/eval 继续放在 `scripts/eval/`。
4. 每批新增数据必须配套 summary、review/audit、data-only probe 和 case-study slice。
5. 任何旧 slot-style、训练结果、GPU 输出或 caption-model-only 诊断，默认归档或留在 `caption-model-longline`，不要混进当前主线目录。
