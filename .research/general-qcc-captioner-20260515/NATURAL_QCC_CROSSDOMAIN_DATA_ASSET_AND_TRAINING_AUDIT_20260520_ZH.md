# Natural QCC 跨域数据资产与训练前审计（2026-05-20）

本报告记录把新的自然 TS-QA 构造方式从 AIOps-only 扩展到跨域 QCC 的一次闭环检查。当前结论是：数据资产和接口 probe 比第一版更稳，真实 q-conditioned/no-question TS-RLM QCC smoke 也已在 3090 上完成；但 generated-caption QA 没有提升，q-conditioned 没有超过 no-question，caption-quality gate 也未通过。因此本轮应报告为完整闭环的负结果，而不是 QCC 训练成功。

## 产物位置

- candidate pool: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_candidates_20260520/natural_qcc_crossdomain_candidates.jsonl`
- natural rewrites: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/natural_qcc_crossdomain_rewrites.jsonl`
- GPT-5.5 reviewer: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/natural_qcc_crossdomain_rewrites_review.json`
- reviewer report: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/NATURAL_QCC_CROSSDOMAIN_REVIEW_20260520_ZH.md`
- positive dataset: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- SFT files: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft/`
- no-question control SFT files: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft_no_question/`
- probe results: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/probe_eval/natural_qcc_probe_results.json`
- semantic QA bridge diagnostics: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/probe_eval/*_semantic_qa/`
- caption adaptation summary: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_caption_adaptation_summary_20260520.json`
- semantic QA bridge script: `scripts/eval/evaluate_natural_qcc_semantic_predictions.py`
- local caption ranker diagnostic: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/local_caption_ranker/`
- local GPU preflight: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/gpu_smoke_preflight_local.json`
- remote GPU access check: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_remote_gpu_access_check_20260520.json`
- GPU smoke launcher: `scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh`
- paired GPU smoke launcher: `scripts/remote/run_natural_qcc_crossdomain_pair_a100.sh`
- local SSH launcher: `scripts/remote/launch_natural_qcc_crossdomain_pair_ssh.sh`
- GPU result manifest collector: `scripts/eval/collect_natural_qcc_gpu_result_manifest.py`
- generated-caption quality audit: `scripts/eval/audit_natural_qcc_caption_quality.py`
- q-conditioned GPU dry-run/audit dir: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/`
- no-question GPU dry-run/audit dir: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520/`
- qcond-vs-no-question audit: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_qcond_vs_noquestion_audit_20260520.json`
- objective completion gate: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_objective_completion_audit_20260520.json`

## 候选池

使用 `multisim_qcc_v5_aiops_v3/schema_report.json` 作为源 schema，并通过 `--source_root /home/cris/Research/LTSGEN` 从主工作树读取源 JSONL。候选池每个可用 source 选 12 条，共 60 条：

| source | candidates |
| --- | ---: |
| `aiopslab_official_v3` | 12 |
| `citylearn` | 12 |
| `grid2op` | 12 |
| `traffic` | 12 |
| `water` | 12 |

FinRL 没进入本轮候选池，因为本地和当前远端分支都缺少 schema 指向的 `finrl_broad_scaled_v1_{train,dev,test}.jsonl`。这不能用旧 case-study 图片替代；下一轮需要先恢复或重新生成 FinRL 源 JSONL。

## 自然化与 Reviewer Gate

自然化草案 60 条全部通过本地 lint，`issue_counts={}`。第二轮模板修复重点处理了 reviewer 指出的自然性问题：Grid2Op 反事实前后歧义、Grid2Op 压力状态中文缺失、Traffic/Water 事件影响模板残留、Traffic 车道占有率语义、Traffic/Water 跨变量阈值说明、Water leak 选项翻译，以及上下文相关的 `gold_answer_zh`。

GPT-5.5 reviewer 只评估自然性、可答性和准确性风险，不决定 gold answer。

Reviewer 结果：

| item | count |
| --- | ---: |
| reviewed rows | 60 |
| `decision=keep` | 56 |
| `decision=revise` | 2 |
| `decision=reject` | 2 |
| positive gate | 55 |

Positive gate 条件是：`decision=keep`、`naturalness_score>=4`、`answerability_score>=4`、`accuracy_risk=low`。

Positive by source：

| source | positive / candidate |
| --- | ---: |
| `aiopslab_official_v3` | 12 / 12 |
| `citylearn` | 9 / 12 |
| `grid2op` | 12 / 12 |
| `traffic` | 11 / 12 |
| `water` | 11 / 12 |

保留排除的主要原因：

- `city_domain_demand_context`: 2 条存在 support-slot/gold answer 与明示阈值冲突，不能靠改写修复。
- `city_trend_total_load`: 1 条为 medium risk，趋势阈值不够明确。
- `traffic_domain_congestion_context`: 1 条为 medium risk，`unclear traffic state` 的矛盾规则仍不够明确。
- `water_pressure_periodicity`: 1 条为 medium risk，自相关分数低于阈值但 deterministic label 为长周期。

这些 revise/reject 行已写入 `natural_qcc_crossdomain_excluded.jsonl`，没有进入训练正例池。

## Positive Dataset

Reviewer-positive 数据集共 55 条：

| split | rows |
| --- | ---: |
| train | 31 |
| dev | 11 |
| test | 13 |

| source | rows |
| --- | ---: |
| `aiopslab_official_v3` | 12 |
| `citylearn` | 9 |
| `grid2op` | 12 |
| `traffic` | 11 |
| `water` | 11 |

答案分布：`B=20, D=13, C=12, A=10`，最大答案占比 `0.3636`。时序维度为 `3` 和 `4` 混合；训练入口使用 `target_num_vars=4` 和 channel padding。

Schema gate: `true`。

## 数据资产 Probe

在 55 条 positive 数据上运行 `run_natural_qcc_probe.py`，`train -> test` 为 `31 -> 13`。

| condition | accuracy | empty |
| --- | ---: | ---: |
| `natural_oracle` | 1.0000 | 0.0000 |
| `natural_evidence_no_label` | 0.6545 | 0.1636 |
| `generic_caption` | 0.0182 | 0.8909 |
| `statistical_caption` | 0.0000 | 1.0000 |
| `question_only` | 0.1273 | 0.7091 |
| `nearest_caption_question_conditioned` | 0.4615 | 0.3846 |
| `nearest_caption_no_question` | 0.2308 | 0.6154 |

Caption-quality audit for evidence-style probe captions:

| diagnostic | evidence shape | answer-label-only | numeric evidence | quality gate |
| --- | ---: | ---: | ---: | ---: |
| `natural_oracle` | 0.9091 | 0.0000 | 0.9091 | `true` |
| `natural_evidence_no_label` | 0.9091 | 0.0000 | 0.9091 | `true` |
| `nearest_caption_question_conditioned` | 0.7692 | 0.0000 | 0.7692 | `false` |
| `nearest_caption_no_question` | 0.9231 | 0.0000 | 0.9231 | `true` |

Semantic QA bridge diagnostic:

| diagnostic | strict QA | semantic QA | semantic empty |
| --- | ---: | ---: | ---: |
| `natural_oracle` | 1.0000 | 1.0000 | 0.0000 |
| `natural_evidence_no_label` | 0.6545 | 1.0000 | 0.0000 |
| `nearest_caption_question_conditioned` | 0.4615 | 0.4615 | 0.3077 |
| `nearest_caption_no_question` | 0.2308 | 0.2308 | 0.6154 |

解释：

- `natural_oracle=1.0` 说明 reviewer-positive 行在 rule-QA 接口上可验证。
- `generic/statistical/question_only` 很弱，说明自然 evidence caption 是 load-bearing 的。
- `natural_evidence_no_label` 与 `natural_oracle` 都通过 caption-quality gate，说明人工/规则生成的自然 evidence caption 不是答案标签捷径。
- semantic QA bridge 只用确定性短语/数值规则把自然证据映射回选项，不改变 gold answer，也不是 LLM judge。它显示 `natural_evidence_no_label` 的 strict QA `0.6545` 主要是 label bridge 过严造成的低估；去掉答案标签后，自然 evidence 仍可被确定性读到 `1.0000`。
- 最近邻弱探针出现 Q-conditioning QA gap：`0.4615` vs `0.2308`，但 q-conditioned 的 evidence-shape rate 是 `0.7692`，未达到默认 `0.8` quality gate；因此只能报告为弱检索信号，不是正式 QCC 训练成功。
- 最近邻 q-conditioned/no-question 在 semantic QA 下仍分别是 `0.4615` / `0.2308`，说明弱探针的主要问题是取错 evidence caption，而不是 strict evaluator 低估。

## 本地弱训练诊断

由于当前机器没有 GPU/torch，我补充了一个无依赖的本地 caption ranker 诊断：

```bash
python3 scripts/eval/run_natural_qcc_local_caption_ranker.py \
  --data .research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl \
  --out_dir .research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/local_caption_ranker/qcond \
  --train_split train \
  --eval_split test \
  --epochs 30
```

该脚本在 train split 上训练一个小型 option-ranker，再把预测选项写成 generated caption，并用 `evaluate_natural_qcc_predictions.py` 跑相同 rule-QA。

| diagnostic | train QA | test QA | empty |
| --- | ---: | ---: | ---: |
| `local_ranker_qcond` | 0.9677 | 0.6154 | 0.0000 |
| `local_ranker_no_question` | 0.9677 | 0.6154 | 0.0000 |

新增 caption-quality audit 后，本地 ranker 的局限更清楚：

| diagnostic | evidence shape | answer-label-only | numeric evidence | quality gate |
| --- | ---: | ---: | ---: | ---: |
| `local_ranker_qcond` | 0.0000 | 1.0000 | 0.0000 | `false` |
| `local_ranker_no_question` | 0.0000 | 1.0000 | 0.0000 | `false` |

解释：

- 本地弱训练结果高于 `question_only=0.1273`、`generic_caption=0.0182` 和最近邻 q-conditioned `0.4615`，说明这批 reviewer-positive 数据存在可训练的 QA 信号。
- q-conditioned 和 no-question 结果相同，说明这个弱 ranker 主要依赖 source/scene/numeric/option 特征，不能作为 Q-conditioning 方法成功证据。
- caption-quality audit 显示本地 ranker 的输出都是答案标签式 caption，不包含数值证据，因此不能作为 evidence-caption 适配成功证据。
- 该诊断不会替代 TS-RLM/Qwen caption SFT，也不验证 caption factuality；只能作为 GPU 不可达时的训练前 sanity check。

## GPU 训练结果

已在 3090 上用当前分支 archive 运行 paired smoke：

```bash
PROFILE=3090 ROOT_OVERRIDE=/cluster/home/hulining/LTSGEN_codex_question_repair_20260519_ready_archive \
  CUDA_VISIBLE_DEVICES=1 NUM_TRAIN_EPOCHS=1 GRADIENT_ACCUMULATION_STEPS=4 MAX_NEW_TOKENS=48 \
  scripts/remote/run_natural_qcc_crossdomain_pair_a100.sh
```

远端 `/cluster/home/hulining/LTSGEN` 不是 git worktree，且远端 GitHub clone 受失效代理影响；本轮用 `git archive HEAD | ssh ... tar -xf -` 解包到独立临时目录运行。结果同步回本地时只按 manifest pathspec 拉取小文件，未拉取 `final_model`、`pytorch_model.bin`、`.safetensors` 或 checkpoint。

GPU access diagnostic 使用备份 SSH config/key 完成，3090 `head2` 可达，`torch/transformers/peft` 可用，`torch_cuda_device_count=8`。A100 仍未作为本轮训练依赖。

训练配置：

- model: `Qwen/Qwen3-4B`
- profile: `3090`
- GPU: `CUDA_VISIBLE_DEVICES=1`
- epochs: `1`
- qcond train/test rows: `31/13`
- no-question train/test rows: `31/13`
- bridge: `prefix`
- `target_num_vars=4`, `ts_num_vars=4`

Generated-caption QA:

| run | generated QA | empty answer | mean caption chars |
| --- | ---: | ---: | ---: |
| `qcond` | 0.0000 | 1.0000 | 56.8 |
| `no_question` | 0.0000 | 1.0000 | 41.2 |

Generated-caption quality:

| run | evidence shape | numeric evidence | answer-label-only | too short | quality gate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `qcond` | 0.3846 | 0.3846 | 0.5385 | 0.5385 | `false` |
| `no_question` | 0.4615 | 0.6154 | 0.3846 | 0.5385 | `false` |

Paired comparison:

- `qcond_accuracy=0.0000`
- `no_question_accuracy=0.0000`
- `qcond_minus_no_question=0.0000`
- compare status: `no_qconditioning_gap`
- qcond did not beat `question_only=0.1273`, `generic_caption=0.0182`, or no-question.

解释：

- 这批数据的 oracle 和 natural evidence 是可验证的，但 55 条 smoke 规模下，当前 TS-RLM/Qwen 训练没有学出可被 QA bridge 读取的 evidence caption。
- qcond 和 no-question 都是 `0.0`，说明 question conditioning 没有在真实 generated-caption QA 中形成收益。
- qcond caption 里 answer-label-only 率 `0.5385`，且 evidence-shape 只有 `0.3846`；失败不是单纯 evaluator 低估，而是 generated caption 质量不足。
- no-question 的 evidence-shape 略高于 qcond，但 QA 仍为 `0.0`，说明生成出的证据与当前问题/选项未能稳定对齐。

Safe sync:

- `natural_qcc_gpu_result_manifest_20260520.json`: `manifest_pass=true`
- `unsafe_path_detected=false`
- required missing: `[]`
- manifest pathspec contains only small reports, predictions, QA metrics, and audits.

Objective gate:

- `objective_complete=true`
- status: `complete_negative_signal`
- summary: 目标完成，但 q-conditioned generated-caption QA 没有证明优于基线或 no-question 对照。

为了判断 QCC conditioning 本身是否有效，本轮新增并实际运行了 no-question prompt control：

- control assets: `sft_no_question/natural_qcc_crossdomain_no_question_{train,dev,test}_{sft,raw}.jsonl`
- split: train/dev/test = `31/11/13`
- gate: `question_marker_count=0`，`missing_prompt_count=0`
- summary: `sft_no_question/natural_qcc_crossdomain_no_question_summary.json`

## 下一步

1. 先不要把这轮写成正结果；应报告为“数据资产强、训练 smoke 负结果”。
2. 诊断 generated captions：逐条看 qcond/no-question 的 `pred_caption`，区分是格式坍缩、短答标签化、数值证据丢失，还是 evidence 与选项无法桥接。
3. 调整训练目标前先做最小修复：目标 caption 更短、更一致，显式保留 `Evidence:` 前缀和关键数值；同时降低 answer-label-only 诱因。
4. 用同一 55 条数据再跑 2-3 个小 ablation：更长 epoch、只训练 caption evidence/no answer label、或训练时混入自然 evidence no-label 目标。
5. 修复剩余 5 条 excluded 行中暴露的 support-slot/阈值问题；其中 CityLearn demand 与 Water periodicity 需要改 deterministic 规则或重采样，不能只改文字。
6. 恢复或重建 FinRL 源 JSONL 后，把 FinRL 加回同一 reviewer gate。
7. 只有当 smoke 证明 generated-caption QA 和 caption-quality 同时改善，再扩到每域 50-100 条 reviewer-positive。
