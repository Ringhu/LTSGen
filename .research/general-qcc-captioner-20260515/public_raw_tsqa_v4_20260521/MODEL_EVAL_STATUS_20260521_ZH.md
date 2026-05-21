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
- `scripts/eval/evaluate_public_raw_tsqa_hf.py`：A100/本地 HuggingFace causal LM 评测脚本，输出格式与 OpenAI evaluator 一致。
- `scripts/eval/compare_public_raw_tsqa_model_evals.py`：扫描所有完整评测 run，生成跨模型 comparison 表。
- `scripts/eval/import_public_raw_tsqa_qwen_eval.py`：导入 A100 回传的 Qwen run 目录或 `.tar.gz`，生成错误摘要并刷新 comparison 表。
- `scripts/remote/discover_public_raw_tsqa_qwen_a100.sh`：A100 端 Qwen 发现脚本，搜索 `hulining/swift` 等目录里的部署示例和 Qwen 模型路径。
- `scripts/remote/preflight_public_raw_tsqa_qwen_a100.sh`：A100 端预检脚本，检查分支、数据、Python/vLLM、GPU、模型路径和端口。
- `scripts/remote/run_public_raw_tsqa_qwen_eval_a100.sh`：A100 上启动 vLLM/Qwen 并调用同一评测脚本的入口。
- `scripts/remote/run_public_raw_tsqa_qwen_suite_a100.sh`：A100 上按模型清单循环评测 Qwen 系列，并生成 suite summary。

本轮修复：

- `prompt_zh` 已改为中文外壳，不再混入 `You are answering...` / `Time series values...`。
- `check_public_raw_tsqa_v4.py` 增加中文 prompt wrapper 检查。
- evaluator 支持逐条写出 `predictions.jsonl` 和 `--resume` 断点续跑。

验证命令：

```bash
python3 scripts/eval/check_public_raw_tsqa_v4.py
python3 -m py_compile scripts/generate/build_public_raw_tsqa_v4.py scripts/eval/check_public_raw_tsqa_v4.py scripts/eval/evaluate_public_raw_tsqa_llm.py scripts/eval/compare_public_raw_tsqa_model_evals.py scripts/eval/import_public_raw_tsqa_qwen_eval.py
bash -n scripts/remote/discover_public_raw_tsqa_qwen_a100.sh scripts/remote/preflight_public_raw_tsqa_qwen_a100.sh scripts/remote/run_public_raw_tsqa_qwen_eval_a100.sh scripts/remote/run_public_raw_tsqa_qwen_suite_a100.sh scripts/remote/package_public_raw_tsqa_qwen_eval_a100.sh
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

随后补充了 no-JSON 小样本 pilot：

| Run | Prompts | Language | Acc. | Mean Latency |
|---|---:|---|---:|---:|
| `pilot_gpt55_public_raw_tsqa_v4_2items_en_nojson` | 2 | EN | 1.0000 | 45.575s |
| `pilot_gpt55_public_raw_tsqa_v4_2items_zh_nojson` | 2 | ZH | 1.0000 | 29.859s |
| `pilot_gpt55_public_raw_tsqa_v4_6items_bilingual_nojson` | 12 | EN+ZH | 1.0000 | 22.782s |

正式 full bilingual no-JSON 评测已完成：

```bash
python3 scripts/eval/evaluate_public_raw_tsqa_llm.py \
  --provider openai \
  --model gpt-5.5 \
  --languages both \
  --run_name full_gpt55_public_raw_tsqa_v4_39items_bilingual_nojson \
  --concurrency 1 \
  --timeout 1200 \
  --max_retries 1 \
  --progress_every 1 \
  --max_tokens 120 \
  --no_response_format \
  --resume
```

结果目录：

`.research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521/model_eval_20260521/full_gpt55_public_raw_tsqa_v4_39items_bilingual_nojson/`

核心结果：

| Model | Rows | Prompts | Overall Acc. | EN Acc. | ZH Acc. | Empty Answer | Error Count |
|---|---:|---:|---:|---:|---:|---:|---:|
| `gpt-5.5` | 39 | 78 | 0.9487 | 0.9487 | 0.9487 | 0.0000 | 0 |

按 domain：

| Domain | Prompts | Acc. |
|---|---:|---:|
| `power_grid` | 14 | 1.0000 |
| `building_energy` | 8 | 1.0000 |
| `traffic` | 8 | 1.0000 |
| `service_telemetry` | 18 | 1.0000 |
| `market` | 20 | 1.0000 |
| `water_service` | 10 | 0.6000 |

结论：脚本已支持 `gpt-5.5`，当前代理路径可完成 full bilingual 评测，但需要低并发、长 timeout、`--resume`，并暂时关闭 JSON response_format。

## 当前跨模型比较表

生成命令：

```bash
python3 scripts/eval/compare_public_raw_tsqa_model_evals.py
```

输出：

- `.research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521/model_eval_20260521/MODEL_EVAL_COMPARISON_20260521.md`
- `.research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521/model_eval_20260521/MODEL_EVAL_COMPARISON_20260521.jsonl`

当前只纳入完整 39 rows / 78 prompts 的正式 run：

| Run | Model | Prompts | Acc. | EN | ZH | Water |
|---|---|---:|---:|---:|---:|---:|
| `full_gpt55_public_raw_tsqa_v4_39items_bilingual_nojson` | `gpt-5.5` | 78 | 0.9487 | 0.9487 | 0.9487 | 0.6000 |
| `full_gpt54_public_raw_tsqa_v4_39items_bilingual` | `gpt-5.4` | 78 | 0.7308 | 0.7179 | 0.7436 | 0.6000 |
| `full_hf_qwen3_4b_inst_public_raw_tsqa_v4_39items_bilingual` | `Qwen3-4B-Instruct-2507` | 78 | 0.4615 | 0.4103 | 0.5128 | 0.2000 |
| `full_hf_qwen25_3b_public_raw_tsqa_v4_39items_bilingual` | `Qwen2.5-3B-Instruct` | 78 | 0.4359 | 0.3846 | 0.4872 | 0.2000 |

## A100/Qwen 状态

A100 SSH 路线已恢复。当前 branch 已同步到远端工作树：

`/cluster/home/user1/hulining/LTSGEN-emnlp-benchmark-pipeline`

已确认的模型路径：

- `/cluster/home/user1/fenghaoran/model/Qwen2.5-3B-Instruct`
- `/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507`
- `/cluster/home/user1/fenghaoran/model/Qwen3.5-4B`
- `/cluster/home/user1/fenghaoran/model/Qwen3-1.7B`
- `/cluster/home/user1/fenghaoran/model/Qwen3-0.6B`

本轮采用 `chatts` 环境直接 HuggingFace 推理，避免 vLLM 环境问题：

`/cluster/home/user1/anaconda3/envs/chatts/bin/python3`

Qwen2.5-3B 完整双语评测命令：

```bash
ssh -o BatchMode=yes -o ClearAllForwardings=yes a100 \
  'cd /cluster/home/user1/hulining/LTSGEN-emnlp-benchmark-pipeline && \
  CUDA_VISIBLE_DEVICES=2 TRANSFORMERS_VERBOSITY=error \
  /cluster/home/user1/anaconda3/envs/chatts/bin/python3 \
  scripts/eval/evaluate_public_raw_tsqa_hf.py \
    --model_path /cluster/home/user1/fenghaoran/model/Qwen2.5-3B-Instruct \
    --model_name Qwen2.5-3B-Instruct \
    --run_name full_hf_qwen25_3b_public_raw_tsqa_v4_39items_bilingual \
    --languages both \
    --max_items 0 \
    --max_new_tokens 120 \
    --torch_dtype bfloat16 \
    --progress_every 5 \
    --resume'
```

Qwen3-4B 完整双语评测命令：

```bash
ssh -o BatchMode=yes -o ClearAllForwardings=yes a100 \
  'cd /cluster/home/user1/hulining/LTSGEN-emnlp-benchmark-pipeline && \
  CUDA_VISIBLE_DEVICES=2 TRANSFORMERS_VERBOSITY=error \
  /cluster/home/user1/anaconda3/envs/chatts/bin/python3 \
  scripts/eval/evaluate_public_raw_tsqa_hf.py \
    --model_path /cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507 \
    --model_name Qwen3-4B-Instruct-2507 \
    --run_name full_hf_qwen3_4b_inst_public_raw_tsqa_v4_39items_bilingual \
    --languages both \
    --max_items 0 \
    --max_new_tokens 120 \
    --torch_dtype bfloat16 \
    --progress_every 5 \
    --resume'
```

Qwen2.5-3B 结果：

| Model | Rows | Prompts | Overall Acc. | EN Acc. | ZH Acc. | Empty Answer | Error Count |
|---|---:|---:|---:|---:|---:|---:|---:|
| `Qwen2.5-3B-Instruct` | 39 | 78 | 0.4359 | 0.3846 | 0.4872 | 0.0000 | 0 |

Qwen3-4B 结果：

| Model | Rows | Prompts | Overall Acc. | EN Acc. | ZH Acc. | Empty Answer | Error Count |
|---|---:|---:|---:|---:|---:|---:|---:|
| `Qwen3-4B-Instruct-2507` | 39 | 78 | 0.4615 | 0.4103 | 0.5128 | 0.0000 | 0 |

Qwen3-4B 按 domain：

| Domain | Prompts | Acc. |
|---|---:|---:|
| `market` | 20 | 0.9000 |
| `power_grid` | 14 | 0.7143 |
| `service_telemetry` | 18 | 0.3333 |
| `water_service` | 10 | 0.2000 |
| `building_energy` | 8 | 0.0000 |
| `traffic` | 8 | 0.0000 |

Qwen2.5-3B 按 domain：

| Domain | Prompts | Acc. |
|---|---:|---:|
| `traffic` | 8 | 1.0000 |
| `power_grid` | 14 | 0.5714 |
| `market` | 20 | 0.5000 |
| `service_telemetry` | 18 | 0.3333 |
| `water_service` | 10 | 0.2000 |
| `building_energy` | 8 | 0.0000 |

vLLM 路线暂未作为正式结果使用。A100 base 环境有 `vLLM 0.10.1.dev`，但启动 Qwen3 server 时触发 `DeepseekVLV2Config` dataclass 错误；`vllm_env` 的 `vLLM 0.4.1` 又不识别 `qwen2` / `qwen3` model type。当前正式 Qwen baseline 采用直接 HF generation，结果文件结构仍与 OpenAI evaluator 对齐。

## 初步错误观察

GPT-5.4 的 21 个错误集中在：

- `building_energy`：模型经常在 reason 中推出“差距不足 0.30，应采用均衡策略”，但最终输出早段/中段/晚段选项。这是答案字母与推理不一致问题。
- `traffic`：模型把窗口自然三等分后判断出拥堵冲击，但 gold label 是 `No clear congestion shock occurs`。这提示任务说明里的窗口切分和 simulator/support-slot 规则仍需更清楚。
- `market`：少量中文样本出现“推理说未触发严重回撤、应判上行，但 answer 写 D”的一致性错误。
- `water_service`：模型对恢复/持续低压边界有误判，后续扩增时应加入更清晰的恢复阈值和 hard negatives。

Qwen3-4B 的错误更集中：`building_energy` 和 `traffic` 全错，`water_service` 只有 0.2000，但 `market` 达到 0.9000、`power_grid` 达到 0.7143。Qwen2.5-3B 与 Qwen3-4B 的 domain profile 明显不同，说明这个 benchmark 已能区分模型在不同时间序列推理原语上的偏差，而不是只给出一个总分。

这些错误说明当前 benchmark 已能暴露三类能力缺口：原始时序计算错误、阈值/边界判断错误，以及计算结论到选项字母的指令一致性错误。但这还不能直接说明当前 pilot 已经是 hard benchmark。

## Hard-but-Fair 复核

本轮新增 hard-case 审计和 reviewer 复核：

- `PUBLIC_RAW_TSQA_V4_HARD_CASE_AUDIT_20260521_ZH.md`
- `hard_case_audit_20260521.jsonl`
- `PUBLIC_RAW_TSQA_V4_HARD_CANDIDATE_REVIEW_20260521_ZH.md`
- `hard_candidate_reviewer_20260521.jsonl`
- `PUBLIC_RAW_TSQA_V4_EXPANSION_REVIEW_20260521_ZH.md`

复核结论：

- GPT-5.5 错题为 `4/78`，全部来自 `water_service`。
- 4 个 GPT-5.5 错题经 reviewer 复审后全部为 `decision=revise`，`hard_subset_eligible=false`。
- 当前可直接认证的 hard subset 为 `0`。
- 现有 pilot 更适合作为模型区分度和流程验证证据；如果要证明顶级闭源模型也真实答不上来，必须先修复 water-service 的事件分段和阈值公开问题，再扩增。

Qwen 3B/4B/8B/32B 资产复核记录在：

`qwen_model_asset_audit_20260521.json`

当前 3B/4B 已完成正式本地 HF 评测；8B/32B 只发现旧脚本、外部 API 线索或结果目录，没有确认到可直接加载的本地 checkpoint，也没有活跃 OpenAI-compatible 服务。本轮不使用外部 key、不下载大模型。

## 下一步

1. 先重写 `water_service` 模板：公开事件前/中/后分段，量化 `very low`、`clearly increases`、`remains depressed`、`close to pre-event`。
2. 用修订后的 water 模板生成 20-40 条候选，先过 deterministic verifier，再过 reviewer gate。
3. 对 reviewer keep 的新样本跑 GPT-5.5，只有 GPT-5.5 失败且 reviewer 再次确认 `hard_subset_eligible=true` 的样本进入 hard subset。
4. 将 `building_energy` balanced reserve、`service_telemetry` no dominant symptom、`market` drawdown-priority 扩成 scaling-sensitive medium pool。
5. 8B/32B 只有在提供可加载本地 checkpoint 或已启动 endpoint 后再补正式评测。
