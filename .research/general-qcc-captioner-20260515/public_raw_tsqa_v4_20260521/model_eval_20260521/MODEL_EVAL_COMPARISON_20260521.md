# Public Raw TSQA v4 Model Evaluation Comparison

- eval_dir: `.research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521/model_eval_20260521`
- full_only: `true`
- runs: `4`

| Run | Provider | Model | Prompts | Acc. | EN | ZH | Water | Empty | Errors | Mean Latency |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `full_gpt55_public_raw_tsqa_v4_39items_bilingual_nojson` | `openai` | `gpt-5.5` | 78 | 0.9487 | 0.9487 | 0.9487 | 0.6000 | 0.0000 | 0 | 18.3180 |
| `full_gpt54_public_raw_tsqa_v4_39items_bilingual` | `openai` | `gpt-5.4` | 78 | 0.7308 | 0.7179 | 0.7436 | 0.6000 | 0.0000 | 0 | 4.5600 |
| `full_hf_qwen3_4b_inst_public_raw_tsqa_v4_39items_bilingual` | `hf` | `Qwen3-4B-Instruct-2507` | 78 | 0.4615 | 0.4103 | 0.5128 | 0.2000 | 0.0000 | 0 | 3.8040 |
| `full_hf_qwen25_3b_public_raw_tsqa_v4_39items_bilingual` | `hf` | `Qwen2.5-3B-Instruct` | 78 | 0.4359 | 0.3846 | 0.4872 | 0.2000 | 0.0000 | 0 | 1.4760 |
