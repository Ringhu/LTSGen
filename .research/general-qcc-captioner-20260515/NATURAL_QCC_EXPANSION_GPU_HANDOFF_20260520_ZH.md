# Natural QCC Expansion GPU Handoff（2026-05-20）

## 目标

本 handoff 只处理一个缺口：把已经通过 GPT-5.5 reviewer 的 AIOpsLab v3 natural QCC expansion 子集，接到真正的 TS-RLM/Qwen caption SFT，并用 generated caption 重新跑 QA。

这一步完成后，才能回答“新构造方式是否适配 caption 任务，以及 QA 是否相对旧流程提升”。当前本地机器只有 4GB GTX 1050Ti，且没有 `/cluster` 挂载或可用 `ssh a100`，所以不能在本机完成训练。

## 已经完成的本地资产

| 资产 | 路径 / 结果 |
| --- | --- |
| reviewer JSON | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites_review.json` |
| reviewer gate | GPT-5.5 审查 25/25，`keep=25`，`accuracy_risk=low=25`，positive gate `25/25` |
| positive dataset | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/natural_qcc_expansion_positive.jsonl`，25 rows |
| split SFT | `sft/natural_qcc_expansion_train_sft.jsonl` 10 rows；`dev_sft` 5 rows；`test_sft` 10 rows |
| schema gate | `schema_gate_pass=true` |
| baseline/probe | `natural_oracle=1.0000`，`generic_caption=0.0000`，`statistical_caption=0.0000`，`question_only=0.2000` |
| nearest probe | question-conditioned/no-question 都是 `1.0000`，说明 AIOps 小子集不能证明 Q-conditioning 收益 |
| local preflight | 数据、prefix bridge、TSRLMConfig、evaluator 通过；本机缺 Qwen3-4B、`torch/transformers/peft` 和 CUDA |
| remote launcher | `scripts/remote/run_natural_qcc_expansion_smoke_a100.sh` |

## 在 A100 上执行

先在远程机器更新到 GitHub 分支头：

```bash
cd /cluster/home/user1/hulining/LTSGEN
git fetch origin
git checkout codex/question-repair-20260519-ready
git pull --ff-only origin codex/question-repair-20260519-ready
```

启动 natural QCC expansion smoke：

```bash
bash scripts/remote/run_natural_qcc_expansion_smoke_a100.sh
```

默认参数：

- `CUDA_VISIBLE_DEVICES=2`
- `ROOT=/cluster/home/user1/hulining/LTSGEN`
- `PY=/cluster/home/user1/anaconda3/envs/opentslm/bin/python3`
- `MODEL=/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507`
- `BRIDGE_TYPE=prefix`
- `NUM_TRAIN_EPOCHS=1`

可覆盖示例：

```bash
CUDA_VISIBLE_DEVICES=0 \
NUM_TRAIN_EPOCHS=3 \
RUN_OVERRIDE=.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/tsrlm_natural_qcc_expansion_smoke_qwen3_4b_ep3_20260520 \
bash scripts/remote/run_natural_qcc_expansion_smoke_a100.sh
```

## 预期产物

默认 run 目录：

`.research/general-qcc-captioner-20260515/natural_qcc_expansion_dataset_20260519/tsrlm_natural_qcc_expansion_smoke_qwen3_4b_20260520/`

应检查：

| 产物 | 含义 |
| --- | --- |
| `preflight.json` | `preflight_pass=true` 才说明远程环境、数据、GPU、模型路径都满足训练条件 |
| `final_model/pytorch_model.bin` | 训练完成后的 trainable checkpoint |
| `generate_eval_test_clean/predictions.jsonl` | test split generated captions |
| `generate_eval_test_clean/metrics.json` | generated caption 基本统计 |
| `generate_eval_test_clean/rule_qa/qa_metrics.json` | generated-caption QA accuracy |
| `natural_qcc_smoke_pipeline_summary.json` | pipeline 是否完整完成，`complete=true` 才可进入结果解读 |

## 完成判据

这一步只在以下条件同时满足时算完成：

1. `natural_qcc_smoke_pipeline_summary.json` 中 `complete=true`。
2. `preflight.json` 中 `preflight_pass=true`。
3. `generate_eval_test_clean/rule_qa/qa_metrics.json` 存在，并报告 test split generated-caption QA。
4. 结果报告中明确比较：
   - generated QCC caption QA；
   - `generic_caption=0.0000`；
   - `statistical_caption=0.0000`；
   - `question_only=0.2000`；
   - `natural_oracle=1.0000`；
   - nearest q/noq 都为 `1.0000` 的重复性 caveat。

如果 generated-caption QA 不能超过 `question_only=0.2000`，应记录为 training/interface 失败，而不是弱化结论。

## 当前不能宣称

- 不能宣称 QCC 训练有效：训练尚未在 GPU 上完成。
- 不能宣称 QA 提升：还没有 generated-caption QA。
- 不能宣称跨域有效：当前真实扩展数据只覆盖 AIOpsLab v3 的 25 条数值时序样本。
- 不能宣称 Q-conditioning 有效：nearest question-conditioned 与 no-question 都是 `1.0000`。

