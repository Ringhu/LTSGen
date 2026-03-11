# LTSGen

## 项目概览 | Overview

`LTSGen` 现在围绕一条主线整理：`原始时间序列数据 -> caption JSONL 生成 -> TS-text alignment 训练 -> retrieval / grounding 评测`。  
`LTSGen` is now organized around one active pipeline: `raw time-series data -> caption JSONL generation -> TS-text alignment training -> retrieval / grounding evaluation`.

## 当前主线目录 | Active Directories

- `dataset/`: 原始数据集。Raw datasets used by the project.
- `gen_tst_dataset/`: 生成后的 JSONL 数据，现已按任务分层。Generated JSONL outputs, now grouped by task.
- `ts_cap/`: 当前使用的 time-series caption 数据生成器。Active time-series caption data generator.
- `ts_align/`: 当前使用的 TS-text alignment 核心包。Active TS-text alignment package.
- `ts_align_scripts_v2/`: 当前训练与评测入口。Current train/eval entry modules.
- `tslm/`: 独立的 caption SFT baseline。Separate SFT baseline for time-series-to-caption generation.
- `scripts/`: 正式脚本入口。Official shell/python entry points.
- `scripts/eval/`: alignment 评测与可视化入口。Official alignment evaluation and visualization entry points.
- `docs/`: 工程地图与研究笔记。Project map and research notes.
- `archive/`: 历史代码、旧实验与杂项归档。Archived legacy code, experiments, and misc artifacts.
- `runs/`: 每个版本只保留最新 checkpoint。Only the latest checkpoint is kept per version.

## 数据产物布局 | Generated Data Layout

- `gen_tst_dataset/ucr/train_shards/`: UCR 训练分片。UCR train shards.
- `gen_tst_dataset/ucr/test_shards/`: UCR 测试分片。UCR test shards.
- `gen_tst_dataset/ucr/merged/`: 合并后的 UCR 数据。Merged UCR datasets.
- `gen_tst_dataset/ucr/archive/`: 旧版或一次性 UCR 产物。Legacy or one-off UCR outputs.
- `gen_tst_dataset/forecasting/`: forecasting 相关产物，按数据源继续划分。Forecasting outputs grouped by source.
- `gen_tst_dataset/fred/`: FRED caption 产物与归档。FRED caption outputs and archived variants.
- `gen_tst_dataset/anomaly/nab/`: NAB anomaly caption 产物。NAB anomaly caption outputs.

## 推荐使用路径 | Recommended Workflow

1. 用 `scripts/generate/` 下的脚本生成 caption JSONL。Use scripts in `scripts/generate/` to build caption JSONL files.
2. 用 `python scripts/utils/merge_ucr_dataset.py` 合并 UCR 训练分片。Use `python scripts/utils/merge_ucr_dataset.py` to merge UCR train shards.
3. 用 `bash scripts/train/train_hsa_clip.sh` 训练 alignment 模型。Use `bash scripts/train/train_hsa_clip.sh` to train the alignment model.
4. 用 `scripts/eval/` 下的脚本做 retrieval、grounding 与可视化。Use the wrappers in `scripts/eval/` for retrieval, grounding, and visualization.

## 重要文档 | Important Docs

- [docs/PROJECT_MAP.md](docs/PROJECT_MAP.md)
- [docs/USAGE.md](docs/USAGE.md)
- [docs/research/ts_caption.md](docs/research/ts_caption.md)
- [docs/research/ts_align.md](docs/research/ts_align.md)
- [docs/research/ltsgen.md](docs/research/ltsgen.md)

## 归档说明 | Archive Policy

旧分支、预实验代码和一次性脚本已经移动到 `archive/`，让根目录只保留当前工程主线。  
Older branches, pre-experiment code, and one-off scripts have been moved into `archive/` so the root reflects the active engineering path only.

## 本地密钥 | Local Keys

现在支持在工程根目录放置 `key.env`，`ts_cap` 会自动加载其中的 API 配置，因此生成脚本不再要求你每次手动 `export`。  
`ts_cap` now supports a project-root `key.env` file and will auto-load API configuration from it, so generation scripts no longer require manual `export` each time.
