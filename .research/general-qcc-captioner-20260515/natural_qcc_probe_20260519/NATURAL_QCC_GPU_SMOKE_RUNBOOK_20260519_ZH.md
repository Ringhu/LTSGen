# Natural QCC GPU Smoke Runbook（2026-05-19）

## 目的

这份 runbook 把 natural QCC pilot 从“数据/规则 QA 评估”接到“QCC caption 训练 -> 生成 -> QA 打分”。当前本地没有 Qwen3-4B 模型路径，所以真正训练要在 A100/3090 环境执行。

## 前置资产

| 资产 | 路径 |
| --- | --- |
| train SFT | `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_train_dev_sft.jsonl` |
| eval SFT | `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_eval_test_sft.jsonl` |
| eval raw | `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_eval_test_raw.jsonl` |
| gold all rows | `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/natural_qcc_probe_positive.jsonl` |
| prediction QA evaluator | `scripts/eval/evaluate_natural_qcc_predictions.py` |

## Step 0：环境检查

```bash
test -d /cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507
python3 -m py_compile scripts/eval/evaluate_natural_qcc_predictions.py
python3 scripts/eval/check_natural_qcc_gpu_smoke_preflight.py
```

如果模型路径不存在，不要启动训练；先改成实际缓存路径。

本机 preflight 已执行并失败，失败原因是当前机器没有 `/cluster` 模型路径、没有 `torch/transformers/peft` Python 环境，也没有满足 20GB 门槛的 GPU。数据文件、bridge 支持和 evaluator 入口检查通过。报告见：

`.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/gpu_smoke_preflight.json`

## Step 1：训练 smoke captioner

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

当前本地 `TSReportLM` 只实现了 `prefix` 和 `xattn` bridge；本 smoke 使用 `prefix`。不要把旧报告中的 `qprefix/local_gated_qprefix` 直接传给当前脚本，除非对应实现已经恢复。

预期输出：

```text
.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/tsrlm_natural_qcc_probe_smoke_qwen3_4b_20260519/final_model/
.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/tsrlm_natural_qcc_probe_smoke_qwen3_4b_20260519/multisim_v5_train_smoke_report.json
```

## Step 2：生成 eval captions

```bash
python3 tslm/scripts/generate_multisim_v5_smoke.py \
  --raw_jsonl .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_eval_test_raw.jsonl \
  --checkpoint_dir .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/tsrlm_natural_qcc_probe_smoke_qwen3_4b_20260519/final_model \
  --out_dir .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/tsrlm_natural_qcc_probe_smoke_qwen3_4b_20260519/generate_eval_test_clean \
  --batch_size 1 \
  --max_new_tokens 48 \
  --clean_max_sentences 2
```

预期输出：

```text
.../generate_eval_test_clean/predictions.jsonl
.../generate_eval_test_clean/metrics.json
```

## Step 3：对 generated captions 做 QA 打分

```bash
python3 scripts/eval/evaluate_natural_qcc_predictions.py \
  --predictions_jsonl .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/tsrlm_natural_qcc_probe_smoke_qwen3_4b_20260519/generate_eval_test_clean/predictions.jsonl \
  --gold_jsonl .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/natural_qcc_probe_positive.jsonl \
  --out_dir .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/tsrlm_natural_qcc_probe_smoke_qwen3_4b_20260519/generate_eval_test_clean/rule_qa \
  --caption_field pred_caption \
  --splits test
```

预期输出：

```text
.../rule_qa/qa_predictions.jsonl
.../rule_qa/qa_metrics.json
.../rule_qa/NATURAL_QCC_PREDICTION_QA_20260519_ZH.md
```

## Evaluator Sanity Check

已在本地用同一 evaluator 做过两个 sanity check：

| caption field | expected role | QA accuracy |
| --- | --- | ---: |
| `target_caption` | oracle evidence caption | 1.0000 |
| `generic_caption` | generic baseline | 0.0233 |

对应输出：

- `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/prediction_eval_target_caption/qa_metrics.json`
- `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/prediction_eval_generic_caption/qa_metrics.json`

## 解释方式

这轮 smoke 的目的不是报告最终方法结果，而是确认：

1. natural SFT 文件能被 TS-RLM/Qwen 训练入口读取；
2. 训练后 checkpoint 能生成 evidence captions；
3. generated captions 能被 natural QA evaluator 转成 QA accuracy；
4. 结果是否值得扩展到每域 `50-100` 条 reviewer-positive 的正式数据。

如果 smoke QA 仍接近 `0.125`，优先检查输出是否复读、是否缺 answer-label channel、是否因 19 条 train 过小导致完全无法学习；不要直接判定 natural-QA 路线失败。
