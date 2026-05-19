# Natural QCC 跨域数据资产与训练前审计（2026-05-20）

本报告记录把新的自然 TS-QA 构造方式从 AIOps-only 扩展到跨域 QCC 的一次闭环检查。当前结论是：数据资产和接口 probe 已经比第一版更稳，但真实 QCC SFT 仍未完成，不能声称 generated-caption QA 有训练提升。

## 产物位置

- candidate pool: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_candidates_20260520/natural_qcc_crossdomain_candidates.jsonl`
- natural rewrites: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/natural_qcc_crossdomain_rewrites.jsonl`
- GPT-5.5 reviewer: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/natural_qcc_crossdomain_rewrites_review.json`
- reviewer report: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/NATURAL_QCC_CROSSDOMAIN_REVIEW_20260520_ZH.md`
- positive dataset: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- SFT files: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft/`
- no-question control SFT files: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft_no_question/`
- probe results: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/probe_eval/natural_qcc_probe_results.json`
- local caption ranker diagnostic: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/local_caption_ranker/`
- local GPU preflight: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/gpu_smoke_preflight_local.json`
- GPU smoke launcher: `scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh`
- q-conditioned GPU dry-run/audit dir: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/`
- no-question GPU dry-run/audit dir: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_no_question_smoke_qwen3_4b_20260520/`
- qcond-vs-no-question audit: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_qcond_vs_noquestion_audit_20260520.json`

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

解释：

- `natural_oracle=1.0` 说明 reviewer-positive 行在 rule-QA 接口上可验证。
- `generic/statistical/question_only` 很弱，说明自然 evidence caption 是 load-bearing 的。
- 最近邻弱探针出现 Q-conditioning gap：`0.4615` vs `0.2308`。这不是正式 QCC 模型，但说明问题条件对 caption 检索有增益。
- `natural_evidence_no_label=0.6545` 低于 oracle，说明自然 evidence 本身可读，但当前 rule-QA evaluator 仍依赖较规范的答案标签；后续可升级 evaluator 或统一 option label。

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

解释：

- 本地弱训练结果高于 `question_only=0.1273`、`generic_caption=0.0182` 和最近邻 q-conditioned `0.4615`，说明这批 reviewer-positive 数据存在可训练的 QA 信号。
- q-conditioned 和 no-question 结果相同，说明这个弱 ranker 主要依赖 source/scene/numeric/option 特征，不能作为 Q-conditioning 方法成功证据。
- 该诊断不会替代 TS-RLM/Qwen caption SFT，也不验证 caption factuality；只能作为 GPU 不可达时的训练前 sanity check。

## GPU 训练状态

已新增启动脚本，默认跑 question-conditioned QCC captioner：

```bash
PROFILE=a100 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh
```

3090 可用：

```bash
PROFILE=3090 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh
```

本地 dry-run 已生成完整 q-conditioned pipeline plan，包括 preflight、train、generate、rule-QA。训练命令使用：

- train: `sft/natural_qcc_crossdomain_train_sft.jsonl`
- eval: `sft/natural_qcc_crossdomain_test_sft.jsonl`
- raw eval: `sft/natural_qcc_crossdomain_test_raw.jsonl`
- gold: `natural_qcc_crossdomain_positive.jsonl`
- `bridge_type=prefix`
- `target_num_vars=4`
- `ts_num_vars=4`
- `source_group_key=merge_source_name`

为了判断 QCC conditioning 本身是否有效，本轮还新增了 no-question prompt control：

- control assets: `sft_no_question/natural_qcc_crossdomain_no_question_{train,dev,test}_{sft,raw}.jsonl`
- split: train/dev/test = `31/11/13`
- gate: `question_marker_count=0`，`missing_prompt_count=0`
- summary: `sft_no_question/natural_qcc_crossdomain_no_question_summary.json`

no-question control 保留相同 time-series values、target caption、gold answer 和 split，只从顶层模型输入 prompt 中移除 downstream question。运行方式：

```bash
MODE=no_question PROFILE=a100 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh
```

或：

```bash
MODE=no_question PROFILE=3090 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh
```

两条 GPU run 都完成后，用以下审计器比较 q-conditioned 与 no-question：

```bash
python3 scripts/eval/audit_natural_qcc_gpu_qcond_vs_noquestion.py
```

当前 qcond-vs-no-question audit 状态为 `incomplete_or_blocked`，因为两条真实 GPU training 尚未完成。

本地 preflight 检查显示数据文件、schema、bridge config、evaluator 都可用；失败原因是本机没有 `torch/transformers/peft` 和满足 20GB 门槛的 CUDA GPU。GPU result audit 当前为：

- `audit_pass=false`
- `status=incomplete_or_blocked`
- generated-caption QA: not available
- baseline max non-oracle: `0.1273`

因此目前不能声称 QCC 训练提升。

## 下一步

1. 在 A100 或 3090 上分别运行 `MODE=qcond` 和 `MODE=no_question` 的 `scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh`，完成两条真实 SFT、caption generation 和 generated-caption QA。
2. 两条 run 完成后分别重新运行 `scripts/eval/audit_natural_qcc_gpu_smoke_result.py --run_dir ... --probe_results ...`。
3. 再运行 `scripts/eval/audit_natural_qcc_gpu_qcond_vs_noquestion.py`，判断 q-conditioned generated-caption QA 是否超过 no-question control。
4. 若 q-conditioned generated-caption QA 超过 `question_only=0.1273`、`generic_caption=0.0182`、`statistical_caption=0.0000`，且超过 no-question control，再记录为 cross-domain smoke 训练正信号。
5. 修复剩余 5 条 excluded 行中暴露的 support-slot/阈值问题；其中 CityLearn demand 与 Water periodicity 需要改 deterministic 规则或重采样，不能只改文字。
6. 恢复或重建 FinRL 源 JSONL 后，把 FinRL 加回同一 reviewer gate。
7. 下一轮扩到每域 50-100 条 reviewer-positive 后，再做正式训练对比；当前 55 条只适合作为 smoke。
