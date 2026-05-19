# Natural QCC 跨域数据资产与训练前审计（2026-05-20）

本报告记录把新的自然 TS-QA 构造方式从 AIOps-only 扩展到跨域 QCC 的一次闭环检查。目标不是宣称 QCC 训练成功，而是确认数据资产是否更适合 caption 任务，并准备好下一步 GPU SFT。

## 产物位置

- candidate pool: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_candidates_20260520/natural_qcc_crossdomain_candidates.jsonl`
- natural rewrites: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/natural_qcc_crossdomain_rewrites.jsonl`
- GPT-5.5 reviewer: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/natural_qcc_crossdomain_rewrites_review.json`
- reviewer report: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_rewrites_20260520/NATURAL_QCC_CROSSDOMAIN_REVIEW_20260520_ZH.md`
- positive dataset: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`
- SFT files: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/sft/`
- probe results: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/probe_eval/natural_qcc_probe_results.json`
- GPU smoke launcher: `scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh`
- GPU dry-run/audit dir: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_smoke_qwen3_4b_20260520/`

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

自然化草案 60 条全部通过本地 lint，`issue_counts={}`。随后用 GPT-5.5 作为质量 reviewer；reviewer 只评估自然性、可答性和准确性风险，不决定 gold answer。

Reviewer 结果：

| item | count |
| --- | ---: |
| reviewed rows | 60 |
| `decision=keep` | 34 |
| `decision=revise` | 22 |
| `decision=reject` | 4 |
| positive gate | 33 |

Positive gate 条件是：`decision=keep`、`naturalness_score>=4`、`answerability_score>=4`、`accuracy_risk=low`。

Positive by source：

| source | positive / candidate |
| --- | ---: |
| `aiopslab_official_v3` | 12 / 12 |
| `citylearn` | 7 / 12 |
| `grid2op` | 6 / 12 |
| `traffic` | 4 / 12 |
| `water` | 4 / 12 |

主要失败类型：

- CityLearn: domain demand 规则和 support slot/gold answer 冲突；cross-variable 模板残留 Grid2Op 的“发电裕度/线路压力”语义。
- Grid2Op: anomaly/extrema 问法仍偏“最重要事件”槽位；部分 counterfactual 需要更清晰地区分事实运行和干预运行。
- Traffic: 多个任务残留 water 模板；lead-lag 存在 lag 符号和 gold answer 不一致；combined stress 规则与交通语义冲突。
- Water: periodicity 阈值和 gold answer 冲突；lead-lag 残留 Grid2Op 变量；部分 cross-variable 选项需要显式绝对相关阈值。

这些 revise/reject 行已写入 `natural_qcc_crossdomain_excluded.jsonl`，没有进入训练正例池。

## Positive Dataset

Reviewer-positive 数据集共 33 条：

| split | rows |
| --- | ---: |
| train | 18 |
| dev | 6 |
| test | 9 |

| source | rows |
| --- | ---: |
| `aiopslab_official_v3` | 12 |
| `citylearn` | 7 |
| `grid2op` | 6 |
| `traffic` | 4 |
| `water` | 4 |

答案分布：`B=11, A=9, D=8, C=5`，最大答案占比 `0.3333`。时序维度为 `3` 和 `4` 混合；训练入口使用 `target_num_vars=4` 和 channel padding。

Schema gate: `true`。

## 数据资产 Probe

在 33 条 positive 数据上运行 `run_natural_qcc_probe.py`，`train -> test` 为 `18 -> 9`。

| condition | accuracy | empty |
| --- | ---: | ---: |
| `natural_oracle` | 1.0000 | 0.0000 |
| `natural_evidence_no_label` | 0.6667 | 0.2121 |
| `generic_caption` | 0.0000 | 0.9091 |
| `statistical_caption` | 0.0000 | 1.0000 |
| `question_only` | 0.1212 | 0.6970 |
| `nearest_caption_question_conditioned` | 0.6667 | 0.3333 |
| `nearest_caption_no_question` | 0.3333 | 0.5556 |

解释：

- `natural_oracle=1.0` 说明 reviewer-positive 行在 rule-QA 接口上可验证。
- `generic/statistical/question_only` 很弱，说明自然 evidence caption 是 load-bearing 的。
- 最近邻弱探针出现 Q-conditioning gap：`0.6667` vs `0.3333`。这比 AIOps-only 的最近邻 `question=no_question=1.0` 更有价值，说明跨域数据不再只是重复模板记忆。
- 这仍不是正式 QCC 训练结果；test 只有 9 条，不能报告方法提升。

## GPU 训练状态

已新增启动脚本：

```bash
PROFILE=a100 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh
```

3090 可用：

```bash
PROFILE=3090 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh
```

本地 dry-run 已生成完整 pipeline plan，包括 preflight、train、generate、rule-QA。训练命令使用：

- train: `sft/natural_qcc_crossdomain_train_sft.jsonl`
- eval: `sft/natural_qcc_crossdomain_test_sft.jsonl`
- raw eval: `sft/natural_qcc_crossdomain_test_raw.jsonl`
- gold: `natural_qcc_crossdomain_positive.jsonl`
- `bridge_type=prefix`
- `target_num_vars=4`
- `ts_num_vars=4`
- `source_group_key=merge_source_name`

本地 preflight 检查显示数据文件、schema、bridge config、evaluator 都可用；失败原因是本机没有 torch/transformers/peft/CUDA。GPU result audit 当前为：

- `audit_pass=false`
- `status=incomplete_or_blocked`
- generated-caption QA: not available

因此目前不能声称 QCC 训练提升。

## 下一步

1. 在 A100 或 3090 上运行 `scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh`，完成真实 SFT、caption generation 和 generated-caption QA。
2. 训练完成后重新运行 `scripts/eval/audit_natural_qcc_gpu_smoke_result.py --run_dir ... --probe_results ...`。
3. 若 generated-caption QA 超过 `question_only=0.1212` 且最好超过本地非 oracle 最大基线，再记录为 cross-domain smoke 训练正信号。
4. 同时修复 27 条 excluded 行中暴露的模板/slot 问题，特别是 FinRL 源缺失、traffic/water 模板串域、lead-lag 符号和阈值冲突。
5. 下一轮扩到每域 50-100 条 reviewer-positive 后，再做正式训练对比；当前 33 条只适合作为 smoke。
