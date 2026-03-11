# 使用说明 | Usage Guide

## 目标 | Goal

这份文档说明当前 `LTSGen` 工程应该如何运行，尤其是主线流程：  
This document explains how to run the current `LTSGen` project, especially the active pipeline:

`时间序列数据 -> caption JSONL 生成 -> UCR 合并 -> TS-text alignment 训练 -> retrieval / grounding 评测`  
`time-series data -> caption JSONL generation -> UCR merge -> TS-text alignment training -> retrieval / grounding evaluation`

## 运行前准备 | Before You Run

1. 在工程根目录安装依赖。Install dependencies from the project root.

```bash
pip install -r requirements.txt
```

2. 如果你要调用 LLM 生成 caption，优先在工程根目录填写 `key.env`；`ts_cap` 会自动加载它。仓库里已经放了一个本地模板 `key.env`，如果你删掉了，也可以从 `key.env.example` 重新复制。你仍然可以手动设置环境变量，但不再是必需的。If you want to use an LLM for caption generation, prefer filling out the project-root `key.env`; `ts_cap` will auto-load it. A local template `key.env` is already present in the repo workspace, and you can recreate it from `key.env.example` if needed. Manual environment variables still work, but they are no longer required.

```bash
# 直接编辑 key.env / edit key.env directly
# 如果你删掉了它 / if you removed it:
# cp key.env.example key.env
```

3. `key.env` 的优先级是“只在当前环境变量没设置时补充默认值”，因此如果你显式 `export` 了某个变量，环境变量会覆盖 `key.env`。`key.env` only fills values that are not already present in the environment, so explicit `export` values still take precedence.

4. 所有 `scripts/*.sh` 现在都会自动解析工程根目录，因此可以从任意当前工作目录执行。All `scripts/*.sh` files now resolve the repository root automatically, so you can run them from any working directory.

5. `scripts/train/train_hsa_clip.sh` 默认使用 `CUDA_VISIBLE_DEVICES=2`，但现在可以直接在命令前覆盖。`scripts/train/train_hsa_clip.sh` defaults to `CUDA_VISIBLE_DEVICES=2`, but you can override it directly at runtime.

```bash
CUDA_VISIBLE_DEVICES=0 bash scripts/train/train_hsa_clip.sh
```

## 官方入口 | Official Entry Points

- `scripts/generate/`: 生成 caption JSONL。Generate caption JSONL files.
- `scripts/utils/merge_ucr_dataset.py`: 合并 UCR train shards。Merge UCR train shards.
- `scripts/train/train_hsa_clip.sh`: 训练主 alignment 模型。Train the main alignment model.
- `scripts/eval/eval_retrieval.sh`: 做 retrieval 评测。Run retrieval evaluation.
- `scripts/eval/eval_grounding.sh`: 做 grounding 评测。Run grounding evaluation.
- `scripts/eval/visualize_alignment.sh`: 导出对齐热力图。Export alignment heatmaps.
- `tslm/`: 可选的 caption SFT baseline。Optional caption SFT baseline.

## 最小主线流程 | Minimal Active Workflow

### 1. 生成 UCR 训练与测试分片 | Generate UCR Train/Test Shards

小规模示例可以先跑 7 个领域脚本：  
For a smaller example, start with the 7-domain scripts:

```bash
bash scripts/generate/gen_ucr_7domains_train.sh
bash scripts/generate/gen_ucr_7domains_test.sh
```

如果你要大规模生成，可以用 full 脚本：  
For broader coverage, use the full scripts:

```bash
bash scripts/generate/gen_ucr_full_train.sh
bash scripts/generate/gen_ucr_full_test.sh
```

说明：  
Notes:

- `gen_ucr_7domains_train.sh` / `gen_ucr_7domains_test.sh` 默认使用 `linkapi + gpt-5`。
- `gen_ucr_full_train.sh` 默认使用 `qwen`。
- `gen_ucr_full_test.sh` 默认使用 `qwenlocal`。
- 如果只想调试非 LLM 结构流程，可以参考 `gen_ett.sh` / `gen_fred.sh` / `gen_nab.sh` 里的 `--disable_llm` 用法。

### 2. 合并 UCR 训练分片 | Merge UCR Train Shards

```bash
python scripts/utils/merge_ucr_dataset.py
```

默认输入和输出：  
Default input and output:

- 输入 `gen_tst_dataset/ucr/train_shards/`
- 输出 `gen_tst_dataset/ucr/merged/ucr_train_merged.jsonl`

只要 `train_shards/` 变化了，就应该重新执行这一步。Whenever `train_shards/` changes, rerun this step.

### 3. 训练 Alignment 模型 | Train the Alignment Model

```bash
bash scripts/train/train_hsa_clip.sh
```

当前默认设置会读取：

- `gen_tst_dataset/ucr/merged/ucr_train_merged.jsonl`
- `gen_tst_dataset/ucr/test_shards/ucr_largekitchenappliances_test.jsonl`

并把 checkpoint 写到：

- `runs/hsa_clip_v2_hybrid/latest.pt`

脚本里默认开启的是 `hybrid` 主干；纯 `patch` baseline 仍保留在注释里。The script defaults to the `hybrid` backbone; the pure `patch` baseline is kept in comments.

### 4. 做 Retrieval 评测 | Run Retrieval Evaluation

```bash
bash scripts/eval/eval_retrieval.sh
```

默认会使用：

- `JSONL=gen_tst_dataset/ucr/test_shards/ucr_largekitchenappliances_test.jsonl`
- `CKPT=runs/hsa_clip_v2_hybrid/latest.pt`

你也可以用环境变量覆盖：  
You can override them with environment variables:

```bash
JSONL=/path/to/eval.jsonl CKPT=/path/to/latest.pt bash scripts/eval/eval_retrieval.sh
```

### 5. 做 Grounding 评测 | Run Grounding Evaluation

```bash
bash scripts/eval/eval_grounding.sh
```

常用可覆盖参数：  
Common overrides:

```bash
MAX_RECORDS=256 TOPK=5 RUN_FULL_CORPUS=1 bash scripts/eval/eval_grounding.sh
```

### 6. 导出对齐可视化 | Export Alignment Visualizations

```bash
bash scripts/eval/visualize_alignment.sh
```

默认图片目录：  
Default image directory:

- `vis_alignment/hsa_clip_v2_hybrid/`

## 其它数据生成脚本 | Other Data Generation Scripts

```bash
bash scripts/generate/gen_ett.sh
bash scripts/generate/gen_fred.sh
bash scripts/generate/gen_nab.sh
```

说明：  
Notes:

- `gen_ett.sh` 输出到 `gen_tst_dataset/forecasting/ett/`
- `gen_fred.sh` 输出到 `gen_tst_dataset/fred/`
- `gen_nab.sh` 默认读取工程上一级目录下的 `NAB/`
- 如果 `NAB` 不在默认位置，可以这样指定：

```bash
NAB_INPUT=/your/path/to/NAB bash scripts/generate/gen_nab.sh
```

## 可选 Baseline：TSLM | Optional Baseline: TSLM

先把 `ts_cap` 生成的 JSONL 转成 SFT 数据：  
First convert `ts_cap` JSONL into SFT data:

```bash
bash tslm/gen_sft_data.sh
```

然后训练 SFT baseline：  
Then train the SFT baseline:

```bash
python tslm/scripts/train_sft.py \
  --train_jsonl tslm/data/test_sft.jsonl \
  --llm_name_or_path /path/to/causal-lm \
  --output_dir tslm/runs/exp_name
```

评测示例：  
Evaluation example:

```bash
python tslm/scripts/evaluate.py \
  --eval_jsonl tslm/data/test_sft.jsonl \
  --checkpoint_dir tslm/runs/exp_name \
  --out_dir tslm/runs/exp_name_eval
```

## 注意事项 | Important Notes

1. `runs/` 现在只保留每个版本的最新 checkpoint，不再保留 `best.pt` 等旧文件。`runs/` now keeps only the latest checkpoint for each version.
2. `gen_tst_dataset/` 里的 JSONL 文件可能很大。查看时优先用 `scripts/utils/preview_jsonl.py`，不要直接整文件打开。Some JSONL files are very large; prefer `scripts/utils/preview_jsonl.py` over opening full files directly.
3. 许多生成脚本会实际消耗 API 调用额度。正式大规模生成前，建议先用小数据集或 `--disable_llm` 跑通流程。Many generation scripts incur real API cost; validate the workflow on a small dataset or with `--disable_llm` first.
4. 如果你修改了数据 schema，就需要同时检查 `ts_cap/`、`ts_align/` 和 `tslm/` 三条链路是否仍兼容。If you change the data schema, re-check compatibility across `ts_cap/`, `ts_align/`, and `tslm/`.
