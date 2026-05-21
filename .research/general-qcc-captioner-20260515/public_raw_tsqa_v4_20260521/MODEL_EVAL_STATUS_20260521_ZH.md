# Public Raw TSQA v4 模型评测状态 2026-05-21

本文档记录 `public_raw_tsqa_v4_20260521` 当前可复现的模型评测入口、已完成结果和待补项。当前评测使用自然任务说明版本的 prompt：每个样本都有完整英文版和中文版，模型输入为自然任务说明、答案选项、完整原始时序 CSV。

## 数据与评测入口

数据目录：

`.research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521/`

主要文件：

- `canonical_raw_tsqa_v4.jsonl`：39 条 canonical raw TS-QA 样本，保留结构化字段、自然任务字段、support slots 和 gold answer。
- `llm_text_view.jsonl`：LLM 评测视图，包含 `prompt_en` 与 `prompt_zh`，时序被序列化为 CSV 文本。
- `tsllm_array_view.jsonl`：TS-LLM 视图，保留同一自然任务文本、选项和原始数值数组。
- `scripts/eval/evaluate_public_raw_tsqa_llm.py`：OpenAI-compatible LLM 评测脚本。
- `scripts/remote/run_public_raw_tsqa_qwen_eval_a100.sh`：A100 上启动 vLLM/Qwen 并调用同一评测脚本的入口。

本轮修复：

- `prompt_zh` 已改为中文外壳，不再混入 `You are answering...` / `Time series values...`。
- `check_public_raw_tsqa_v4.py` 增加中文 prompt wrapper 检查。
- evaluator 支持逐条写出 `predictions.jsonl` 和 `--resume` 断点续跑。

验证命令：

```bash
python3 scripts/eval/check_public_raw_tsqa_v4.py
python3 -m py_compile scripts/generate/build_public_raw_tsqa_v4.py scripts/eval/check_public_raw_tsqa_v4.py scripts/eval/evaluate_public_raw_tsqa_llm.py
bash -n scripts/remote/run_public_raw_tsqa_qwen_eval_a100.sh
```

已通过结果：sanity check `pass=true`，`n=39`，6 个 domain，错误数 `0`。

## 已完成 GPT-5.4 评测

完整双语评测命令：

```bash
python3 scripts/eval/evaluate_public_raw_tsqa_llm.py \
  --provider openai \
  --model gpt-5.4 \
  --languages both \
  --run_name full_gpt54_public_raw_tsqa_v4_39items_bilingual \
  --concurrency 3 \
  --max_retries 1 \
  --progress_every 10 \
  --max_tokens 160 \
  --resume
```

结果目录：

`.research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521/model_eval_20260521/full_gpt54_public_raw_tsqa_v4_39items_bilingual/`

核心结果：

| Model | Rows | Prompts | Overall Acc. | EN Acc. | ZH Acc. | Empty Answer | Error Count |
|---|---:|---:|---:|---:|---:|---:|---:|
| `gpt-5.4` | 39 | 78 | 0.7308 | 0.7179 | 0.7436 | 0.0000 | 0 |

按 domain：

| Domain | Prompts | Acc. |
|---|---:|---:|
| `power_grid` | 14 | 1.0000 |
| `service_telemetry` | 18 | 0.9444 |
| `market` | 20 | 0.8000 |
| `water_service` | 10 | 0.6000 |
| `building_energy` | 8 | 0.2500 |
| `traffic` | 8 | 0.2500 |

## GPT-5.5 状态

已完成 dry-run，说明 prompt 选择和输出目录生成正常：

```bash
python3 scripts/eval/evaluate_public_raw_tsqa_llm.py \
  --dry_run --provider openai --model gpt-5.5 \
  --max_items 6 --languages both \
  --run_name dryrun_gpt55_public_raw_tsqa_v4
```

单题 JSON-mode 连通测试在当前 OpenAI-compatible 代理上 60 秒超时：

`model_eval_20260521/smoke_gpt55_public_raw_tsqa_v4_1item_en_timeout60/metrics.json`

关闭 JSON mode 后，单题英文 smoke 可跑通，但延迟很高：

`model_eval_20260521/smoke_gpt55_public_raw_tsqa_v4_1item_en_nojson_timeout120/metrics.json`

结果：`n=1`，accuracy `1.0000`，mean latency `68.059s`。

结论：脚本已支持 `gpt-5.5`，当前代理路径可连通，但正式跑应使用低并发、长 timeout、`--resume`，并暂时关闭 JSON response_format。

推荐命令：

```bash
python3 scripts/eval/evaluate_public_raw_tsqa_llm.py \
  --provider openai \
  --model gpt-5.5 \
  --languages both \
  --run_name full_gpt55_public_raw_tsqa_v4_39items_bilingual \
  --concurrency 1 \
  --timeout 1200 \
  --max_retries 1 \
  --progress_every 5 \
  --max_tokens 160 \
  --no_response_format \
  --resume
```

## A100/Qwen 状态

本机不能直接跑 Qwen，因为 `nvidia-smi` 返回：

```text
Failed to initialize NVML: Driver/library version mismatch
NVML library version: 535.309
```

A100 评测脚本已经补齐并通过 `bash -n`：

`scripts/remote/run_public_raw_tsqa_qwen_eval_a100.sh`

默认行为：

- 在 A100 上启动 vLLM OpenAI-compatible server。
- 默认模型路径：`/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507`。
- 默认服务端口：`127.0.0.1:9411`。
- 调用 `evaluate_public_raw_tsqa_llm.py --provider qwenlocal`。
- 默认开启 `--resume`。

推荐 A100 命令：

```bash
ROOT=/cluster/home/user1/hulining/LTSGEN \
PY=/cluster/home/user1/anaconda3/envs/opentslm/bin/python3 \
CUDA_VISIBLE_DEVICES=2 \
MODEL_PATH=/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507 \
SERVED_MODEL_NAME=Qwen3-4B-Instruct-2507 \
RUN_NAME=full_qwen3_4b_public_raw_tsqa_v4_39items_bilingual \
LANGUAGES=both \
MAX_ITEMS=0 \
CONCURRENCY=2 \
scripts/remote/run_public_raw_tsqa_qwen_eval_a100.sh
```

如果 A100 上已有 vLLM 服务：

```bash
USE_EXISTING_SERVER=1 \
HOST=127.0.0.1 \
PORT=9411 \
SERVED_MODEL_NAME=Qwen3-4B-Instruct-2507 \
RUN_NAME=full_qwen3_4b_public_raw_tsqa_v4_39items_bilingual \
LANGUAGES=both \
scripts/remote/run_public_raw_tsqa_qwen_eval_a100.sh
```

## 初步错误观察

GPT-5.4 的 21 个错误集中在：

- `building_energy`：模型经常在 reason 中推出“差距不足 0.30，应采用均衡策略”，但最终输出早段/中段/晚段选项。这是答案字母与推理不一致问题。
- `traffic`：模型把窗口自然三等分后判断出拥堵冲击，但 gold label 是 `No clear congestion shock occurs`。这提示任务说明里的窗口切分和 simulator/support-slot 规则仍需更清楚。
- `market`：少量中文样本出现“推理说未触发严重回撤、应判上行，但 answer 写 D”的一致性错误。
- `water_service`：模型对恢复/持续低压边界有误判，后续扩增时应加入更清晰的恢复阈值和 hard negatives。

这些错误说明当前 benchmark 已能暴露两类能力缺口：原始时序计算错误，以及计算结论到选项字母的指令一致性错误。下一轮数据扩增应优先修复任务歧义，再扩大样本数。

## 下一步

1. 在 A100 上运行 Qwen3-4B 完整双语评测，落盘 `metrics.json` 和 `predictions.jsonl`。
2. 在长 timeout 下补跑 `gpt-5.5`，不要把当前 timeout 记录作为正式能力分数。
3. 对 `building_energy`、`traffic`、`water_service` 做 reviewer 复审：检查规则阈值、窗口切分、gold answer 是否和自然任务完全一致。
4. 扩增数据时加入“推理正确但答案字母不一致”的一致性检查，作为 reviewer gate。
