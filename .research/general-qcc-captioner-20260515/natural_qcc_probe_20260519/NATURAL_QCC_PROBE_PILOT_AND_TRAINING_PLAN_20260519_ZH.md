# Natural QCC Probe Pilot 与后续训练计划（2026-05-19）

## 当前结论

这一步已经把 `natural_qa_balanced8_20260519` 中通过 GPT-5.5 reviewer gate 的自然 TS-QA 样本，接回了 MultiSim/QCC 的 caption-QA 评估接口，并额外生成了 TS-RLM/Qwen smoke SFT 入口。

结论分两层：

1. **数据接口可用**：43 条 reviewer-positive 样本可以转成 evidence-caption QA 样本，`natural_oracle` 在规则 QA 中达到 `1.0000`。
2. **还没有证明 QCC 训练收益**：当前只有 43 条样本，train/dev-as-train 只有 19 条，nearest-caption 小探针只有 `0.1250`，不能作为方法结果。

## 已完成资产

| 资产 | 路径 |
| --- | --- |
| natural QCC positive JSONL | `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/natural_qcc_probe_positive.jsonl` |
| positive 数据报告 | `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/NATURAL_QCC_PROBE_DATASET_20260519_ZH.md` |
| probe QA 结果 | `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/probe_eval/NATURAL_QCC_PROBE_RESULTS_20260519_ZH.md` |
| smoke SFT 数据 | `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/` |
| smoke SFT schema | `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_smoke_sft_schema.json` |
| smoke SFT 说明 | `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/NATURAL_QCC_SMOKE_SFT_ASSETS_20260519_ZH.md` |
| GPU smoke runbook | `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/NATURAL_QCC_GPU_SMOKE_RUNBOOK_20260519_ZH.md` |
| generated caption QA evaluator | `scripts/eval/evaluate_natural_qcc_predictions.py` |
| dataset builder | `scripts/generate/build_natural_qcc_probe_dataset.py` |
| probe evaluator | `scripts/eval/run_natural_qcc_probe.py` |
| smoke SFT builder | `scripts/generate/build_natural_qcc_smoke_sft.py` |
| expansion candidate selector | `scripts/generate/select_natural_qcc_expansion_candidates.py` |
| expansion natural rewrite builder | `scripts/generate/build_natural_qcc_expansion_rewrites.py` |
| expansion GPT-5.5 reviewer | `scripts/generate/review_natural_qcc_expansion_rewrites.py` |

## 当前数字

### 数据规模

| source | positive rows |
| --- | ---: |
| `aiopslab_official_v3` | 3 |
| `citylearn` | 8 |
| `finrl_scaled` | 8 |
| `grid2op` | 8 |
| `traffic` | 8 |
| `water` | 8 |

共 `43` 条 positive，另有 `5` 条 AIOps metadata-only 样本被排除。

### Baseline QA

| condition | n | accuracy | empty |
| --- | ---: | ---: | ---: |
| `natural_oracle` | 43 | 1.0000 | 0.0000 |
| `natural_evidence_no_label` | 43 | 0.6279 | 0.3023 |
| `generic_caption` | 43 | 0.0233 | 0.8837 |
| `statistical_caption` | 43 | 0.0465 | 0.9535 |
| `question_only` | 43 | 0.0000 | 0.8605 |

`natural_evidence_no_label` 低于 `natural_oracle` 主要是评估器问题：自然证据不一定重复 exact option label，规则 QA 会漏读或被对比规则中的 distractor label 干扰。因此正式评估需要保留一个 answer-label verification channel，或升级成语义 QA evaluator；不能把这项直接解释成人类不可答。

### Trainable Caption Probe

| condition | train | eval | accuracy | empty |
| --- | ---: | ---: | ---: | ---: |
| `nearest_caption_question_conditioned` | 19 | 24 | 0.1250 | 0.7500 |
| `nearest_caption_no_question` | 19 | 24 | 0.1250 | 0.7500 |

这是弱训练探针，只验证“训练/评估接口能跑到 QA 端”，不代表 QCC 模型训练结果。

## 为什么这一步仍然有价值

旧的 MultiSim v5 小训练在 48 条 balanced eval 上只有 `0.125`，没有超过 `statistical_caption`。这次 natural pilot 没有直接证明模型变强，但证明了一个关键前提：自然化后的 QA/evidence 仍然能保持 oracle 可验证，同时 generic/statistical/question-only 基线很弱，说明任务没有退化成纯语言先验。

换句话说，现在值得做的是“扩数据 + 真训练”，不是继续只做 case study 展示。

## 下一阶段执行顺序

### NQCC-001：扩展 reviewer-positive 数据

目标：每个 source 至少 `50-100` 条 reviewer-positive，形成真正的 `train/dev/test`。

要求：

- 每个样本保留 scene、自然问题、双语 options、natural evidence、answer label、support slots。
- reviewer 只评自然性、可答性、风险；不能决定 gold answer。
- AIOps metadata-only 和 metadata-context lookup 问题单独建 split 或剔除出主数值时序 benchmark；当前 selector 已排除 `faulty_service` / `fault_layer` 这类不能从时序窗口推出的样本。
- lead-lag、counterfactual、domain-context 题必须保证证据差距足够明显，避免视觉上接近但强行设问。

当前本地 checkout 只能读取 AIOpsLab v3 source，因此扩展候选只物化了 25 条数值时序 AIOps 样本，并已通过 `build_natural_qcc_expansion_rewrites.py` 改写成自然 QA 草案。完整每域扩展需要在包含 Grid2Op、CityLearn、FinRL、water、traffic source JSONL 的数据机器上复跑 selector、natural rewrite 和 GPT-5.5 reviewer gate。

### NQCC-002：重跑数据资产评估

每个 split 都跑：

- `question_only`
- `generic_caption`
- `statistical_caption`
- `natural_oracle`
- `natural_evidence_no_label`

进入训练的最低门槛：

- `natural_oracle` 接近 `1.0`
- `question_only` 明显低于 oracle
- `generic_caption` 不应接近 oracle
- `statistical_caption` 可以作为强数值摘要基线，但不能覆盖大部分 domain-context / counterfactual 题
- answer-letter 分布不能明显偏斜

### NQCC-003：先跑 natural QCC smoke SFT

先在 A100/3090 上用当前 smoke SFT 资产跑最小训练，目的只验证链路：

```bash
python3 tslm/scripts/train_multisim_v5_smoke.py \
  --train_jsonl .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_train_dev_sft.jsonl \
  --eval_jsonl .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_eval_test_sft.jsonl \
  --llm_name_or_path /cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507 \
  --output_dir .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/tsrlm_natural_qcc_probe_smoke_qwen3_4b_20260519 \
  --trust_remote_code \
  --bridge_type prefix \
  --ts_num_vars 4 \
  --target_num_vars 4 \
  --freeze_llm \
  --save_trainable_only \
  --bf16 \
  --num_train_epochs 1 \
  --per_device_train_batch_size 1 \
  --per_device_eval_batch_size 1 \
  --gradient_accumulation_steps 4 \
  --source_group_key merge_source_name
```

注意：本地当前没有上述 Qwen3-4B 路径，因此该命令应在模型缓存存在的 A100/3090 环境执行。这里使用当前仓库 `TSReportLM` 实现真实支持的 `prefix` bridge；`qprefix/local_gated_qprefix` 需要对应代码实现后才能作为架构对照。

训练完成后，用 `tslm/scripts/generate_multisim_v5_smoke.py` 生成 `pred_caption`，再用 `scripts/eval/evaluate_natural_qcc_predictions.py` 评估 QA accuracy。完整命令见 `NATURAL_QCC_GPU_SMOKE_RUNBOOK_20260519_ZH.md`。

### NQCC-004：正式 natural QCC SFT

扩展数据完成后再训练正式模型：

- 输入：自然 scene + question + time series。
- 输出：自然 evidence caption，保留可验证 answer label 或等价 verification channel。
- 对照：旧 slot/exact evidence caption 训练、natural evidence caption 训练、no-question caption 训练。
- 指标：QA accuracy、empty answer rate、caption factuality、unsupported/hallucination rate、domain/task-family breakdown。

### NQCC-005：判断是否进入论文实验

只有满足以下条件，才把 natural QCC 作为正式路线推进：

- trained natural QCC 明显优于 `generic_caption`、`question_only` 和旧 MultiSim v5 smoke。
- 对 `statistical_caption` 至少在 domain-context、counterfactual、lead-lag 等任务族上有增益。
- caption factuality 不因自然化而下降。
- 每个 source 至少有可解释的 heldout 指标，不依赖单一平均数。

## 与 Grid2Op v9 的关系

这条 natural QA/QCC 数据线不启动新的 Grid2Op v9 架构搜索，也不替代 v9 failure analysis。Grid2Op v9 的下一轮 GPU follow-up 仍应等 `.research/failure-analysis-grid2op-v9-20260517.md` 完成后再决定。
