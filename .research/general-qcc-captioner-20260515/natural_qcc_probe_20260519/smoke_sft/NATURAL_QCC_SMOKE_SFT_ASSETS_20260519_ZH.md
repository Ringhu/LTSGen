# Natural QCC Smoke SFT Assets（2026-05-19）

本目录把 reviewer-positive natural QCC probe 样本转换成现有 TS-RLM/Qwen caption SFT 可直接读取的 smoke 训练资产。

## Files

- train raw: `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_train_dev_raw.jsonl`
- train SFT: `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_train_dev_sft.jsonl`
- eval raw: `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_eval_test_raw.jsonl`
- eval SFT: `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_eval_test_sft.jsonl`
- schema report: `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_smoke_sft_schema.json`

## Split Summary

| split role | n | by source | by value dim | max answer share |
| --- | ---: | --- | --- | ---: |
| train/dev-as-train | 19 | `{'citylearn': 3, 'finrl_scaled': 5, 'grid2op': 5, 'traffic': 5, 'water': 1}` | `{'3': 19}` | 0.3158 |
| eval/test-as-eval | 24 | `{'aiopslab_official_v3': 3, 'citylearn': 5, 'finrl_scaled': 3, 'grid2op': 3, 'traffic': 3, 'water': 7}` | `{'4': 3, '3': 21}` | 0.3750 |

## Smoke Training Command

这不是正式训练命令，而是下一步在有 GPU 的机器上验证 natural evidence caption 训练链路的最小入口：

```bash
python3 tslm/scripts/train_multisim_v5_smoke.py \
  --train_jsonl .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_train_dev_sft.jsonl \
  --eval_jsonl .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/smoke_sft/natural_qcc_probe_eval_test_sft.jsonl \
  --llm_name_or_path /cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507 \
  --output_dir .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/tsrlm_natural_qcc_probe_smoke_qwen3_4b_20260519 \
  --trust_remote_code \
  --bridge_type qprefix \
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

## Caveat

当前只有 43 条 positive，其中 train 只有 19 条，且 AIOpsLab 没有 train 正例。因此该资产只能验证训练接口，不应用来报告方法收益。
