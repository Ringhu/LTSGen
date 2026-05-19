# Natural QCC Cross-Domain Objective Completion Audit（2026-05-20）

本审计用于判断当前 active objective 是否已经完成。结论先行：**目标已完成，但结果是负信号**。新的自然 TS-QA 构造、数据资产评估、reviewer gate、SFT 数据准备、no-question control、真实 q-conditioned/no-question TS-RLM QCC smoke、generated-caption QA、caption-quality audit、paired comparison 和 safe manifest 都已完成；但 q-conditioned generated-caption QA 没有超过非 oracle baseline 或 no-question，对应 caption 质量也未过 gate。

因此可以关闭当前“重新走一遍流程并看是否更好”的目标，但不能声称新的数据已经带来 QCC 训练提升。

## 目标拆解

用户目标：

> 按照新的构造数据方式重新走一遍之前流程，看结果能否更好；不仅做数据资产评估，还要在 QCC 的想法上做训练，看看新的数据是否适配 caption 任务，以及在 QA 任务上是否能够有所提升。

拆成可检查 deliverables：

1. 用新的自然 TS-QA 构造方式重新走候选选择、自然化、reviewer、positive dataset、SFT 文件准备流程。
2. 做数据资产评估：question-only、generic caption、statistical caption、oracle evidence caption 等 baseline/probe。
3. 做 QCC caption 训练：训练 question-conditioned captioner，而不只是 oracle/probe。
4. 做 no-question captioner 训练对照，用来判断 question conditioning 是否真的带来训练收益。
5. 生成 trained caption，并用同一 QA 规则评估 generated-caption QA。
6. 审计 generated caption 是否像 evidence caption，而不是只输出答案标签。
7. 判断 QA 是否相对非 oracle baseline 有提升，并判断 q-conditioned 是否超过 no-question。
8. 把小型产物安全同步到 GitHub，不同步模型权重。

## Prompt-to-Artifact Checklist

| requirement | evidence inspected | status |
| --- | --- | --- |
| 新构造方式跨域候选选择 | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_candidates_20260520/natural_qcc_crossdomain_candidates_manifest.json`；selected `n=60`，每个可用 source 各 12 条 | complete for available sources |
| FinRL included if source exists | manifest `missing_files` includes `finrl_broad_scaled_v1_{train,dev,test}.jsonl` missing | blocked, not faked |
| 自然化 rewrite | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/natural_qcc_crossdomain_rewrites.jsonl` and lint report | complete |
| GPT-5.5 reviewer gate | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/natural_qcc_crossdomain_rewrites_review.json`；60 reviewed；55 pass positive gate | complete |
| Positive dataset | `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`；55 rows | complete |
| SFT split files | `sft/natural_qcc_crossdomain_{train,dev,test}_{sft,raw}.jsonl`；train/dev/test = 31/11/13 | complete |
| No-question control SFT files | `sft_no_question/natural_qcc_crossdomain_no_question_{train,dev,test}_{sft,raw}.jsonl`；top-level prompt `Question:` marker count = 0 | complete |
| 数据资产 probe | `probe_eval/natural_qcc_probe_results.json` | complete |
| Oracle/non-oracle baselines | oracle `1.0000`; generic `0.0182`; statistical `0.0000`; question-only `0.1273` | complete |
| Semantic QA bridge diagnostic | `probe_eval/*_semantic_qa/semantic_qa_metrics.json`; deterministic bridge, no LLM judge, does not alter gold | complete diagnostic |
| Local weak training diagnostic | `local_caption_ranker/{qcond,no_question}/local_caption_ranker_summary.json`; both test QA `0.6154` | complete diagnostic |
| True qcond TS-RLM/Qwen training | `tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/natural_qcc_gpu_smoke_result_audit.json`; `audit_pass=true`, `pipeline_complete=true` | complete negative result |
| True no-question TS-RLM/Qwen training | `tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520/natural_qcc_gpu_smoke_result_audit.json`; `audit_pass=true`, `pipeline_complete=true` | complete negative result |
| Generated trained captions | both `generate_eval_test_clean/predictions.jsonl`; 13 rows each | complete |
| Generated-caption QA | both `generate_eval_test_clean/rule_qa/qa_metrics.json`; qcond/no-question accuracy `0.0000/0.0000` | complete negative result |
| Generated caption-quality audit | both `natural_qcc_caption_quality_audit.json`; qcond/no-question quality gates `false/false` | complete negative result |
| Q-conditioned vs no-question comparison | `tsrlm_natural_qcc_crossdomain_qcond_vs_noquestion_audit_20260520.json`; status `no_qconditioning_gap`, gap `0.0000` | complete negative result |
| Safe result manifest | `natural_qcc_gpu_result_manifest_20260520.json`; `manifest_pass=true`, `unsafe_path_detected=false`, `required_missing=[]` | complete |
| Objective-level completion gate | `natural_qcc_objective_completion_audit_20260520.json`; `objective_complete=true`, status `complete_negative_signal` | complete negative result |
| GitHub sync | current branch `refs/heads/codex/question-repair-20260519-ready`; latest commit after result sync should include GPU small artifacts only | pending final push |

## Inspected Metrics

Data asset probe on 55 reviewer-positive rows:

| condition | accuracy | empty |
| --- | ---: | ---: |
| `natural_oracle` | 1.0000 | 0.0000 |
| `natural_evidence_no_label` | 0.6545 | 0.1636 |
| `generic_caption` | 0.0182 | 0.8909 |
| `statistical_caption` | 0.0000 | 1.0000 |
| `question_only` | 0.1273 | 0.7091 |
| `nearest_caption_question_conditioned` | 0.4615 | 0.3846 |
| `nearest_caption_no_question` | 0.2308 | 0.6154 |

Semantic QA bridge diagnostic:

| diagnostic | strict QA | semantic QA | semantic empty |
| --- | ---: | ---: | ---: |
| `natural_oracle` | 1.0000 | 1.0000 | 0.0000 |
| `natural_evidence_no_label` | 0.6545 | 1.0000 | 0.0000 |
| `nearest_caption_question_conditioned` | 0.4615 | 0.4615 | 0.3077 |
| `nearest_caption_no_question` | 0.2308 | 0.2308 | 0.6154 |

Generated-caption QA from true TS-RLM/Qwen smoke:

| run | generated QA | empty answer | mean caption chars |
| --- | ---: | ---: | ---: |
| `qcond` | 0.0000 | 1.0000 | 56.8 |
| `no_question` | 0.0000 | 1.0000 | 41.2 |

Generated-caption quality:

| run | evidence shape | numeric evidence | answer-label-only | too short | quality gate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `qcond` | 0.3846 | 0.3846 | 0.5385 | 0.5385 | `false` |
| `no_question` | 0.4615 | 0.6154 | 0.3846 | 0.5385 | `false` |

Comparison:

| item | value |
| --- | ---: |
| qcond accuracy | 0.0000 |
| no-question accuracy | 0.0000 |
| qcond minus no-question | 0.0000 |
| required min gap | 0.0500 |
| compare status | `no_qconditioning_gap` |

## Interpretation

- 数据资产层面是强的：oracle 是 `1.0000`，generic/statistical/question-only 都很弱，semantic bridge 也显示自然 evidence 去掉答案标签后仍可被确定性读到 `1.0000`。
- 真实训练层面是负的：qcond 和 no-question generated-caption QA 都是 `0.0000`，没有超过 question-only `0.1273` 或最近邻 qcond probe `0.4615`。
- qcond 没有利用 question conditioning：qcond-vs-no-question gap 是 `0.0000`。
- caption 质量没有达到 QCC evidence-caption 要求：qcond evidence-shape 只有 `0.3846`，answer-label-only rate 是 `0.5385`。
- 本轮闭环回答了用户的问题：新的构造数据方式适合作为可验证数据资产，但当前 55 条 smoke 不足以让 TS-RLM/Qwen 学出有效 QCC caption，也没有带来 QA 提升。

## Completion Decision

Current decision: **complete negative signal**.

已完成：

- 新自然 TS-QA 构造流程和 reviewer-positive 数据集。
- 数据资产评估和 semantic QA bridge 诊断。
- qcond/no-question SFT 数据准备。
- 真实 3090 qcond/no-question TS-RLM/Qwen smoke 训练。
- generated-caption QA、caption-quality audit 和 paired comparison。
- objective-level completion gate 和 safe result manifest。

不能声称：

- 不能声称 QCC 训练成功。
- 不能声称 generated captions 提升 QA。
- 不能声称 question conditioning 在这轮训练里有效。

下一步应先诊断 generated captions 的失败模式，再决定是修目标 caption 格式、扩大数据、改训练 recipe，还是重新设计 QCC objective。
