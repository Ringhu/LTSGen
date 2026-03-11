# 工程地图 | Project Map

## 当前主线 | Active Pipeline

当前实际使用的工程主线是：  
The active engineering path is:

`dataset/ -> ts_cap/ -> gen_tst_dataset/ -> ts_align/ + ts_align_scripts_v2/ -> runs/`

如果你的目标是生成 caption pair 并进行 TS-text alignment 训练，这就是应该遵循的路径。  
If your goal is to generate caption pairs and train TS-text alignment models, this is the path to follow.

## 目录职责 | Directory Roles

- `dataset/`: 分类、预测、异常检测与 FRED 类数据的原始来源。Raw source datasets for classification, forecasting, anomaly detection, and FRED-style data.
- `gen_tst_dataset/`: 训练、评测和人工检查所用的生成 JSONL 数据。Generated JSONL outputs used for training, evaluation, and inspection.
- `ts_cap/`: 当前 caption 生成模块，负责特征、claim 与 dense caption 构建。Active caption generation package that builds features, claims, and dense captions from time-series windows.
- `ts_align/`: 当前 alignment 核心模块，负责 dataset、collate、loss、encoder、metric 与 checkpoint。Core alignment package: dataset loading, collate, losses, encoders, metrics, and checkpoint utilities.
- `ts_align_scripts_v2/`: 当前 HSA-CLIP 风格训练与评测入口。Current train/eval entry modules for HSA-CLIP style alignment.
- `tslm/`: 独立的 `time series -> prefix embeddings -> causal LM -> caption` SFT baseline。Separate SFT baseline for `time series -> prefix embeddings -> causal LM -> caption`.
- `scripts/generate/`: 正式的 caption 生成脚本入口。Official caption-generation shell entry points.
- `scripts/train/`: 正式的 alignment 训练脚本入口。Official alignment-training shell entry points.
- `scripts/eval/`: 正式的 retrieval、grounding 与可视化脚本入口。Official retrieval, grounding, and visualization shell entry points.
- `scripts/utils/`: 小型辅助工具，如 JSONL 预览与 UCR 分片合并。Small helper utilities such as JSONL preview and UCR shard merging.
- `runs/`: 每个版本仅保留最新 checkpoint。Each version directory keeps only the latest checkpoint.

## 生成数据布局 | Generated Data Layout

- `gen_tst_dataset/ucr/train_shards/`: UCR 训练集分片。UCR train shards.
- `gen_tst_dataset/ucr/test_shards/`: UCR 测试集分片。UCR test shards.
- `gen_tst_dataset/ucr/merged/`: 合并后的 UCR 训练/测试集合。Merged UCR train/test datasets.
- `gen_tst_dataset/ucr/archive/`: 旧版 UCR 实验输出。Archived UCR experiment outputs.
- `gen_tst_dataset/forecasting/ett/`: ETT 相关 forecasting 输出。ETT forecasting outputs.
- `gen_tst_dataset/forecasting/electricity/`: Electricity forecasting 输出。Electricity forecasting outputs.
- `gen_tst_dataset/forecasting/weather/`: Weather forecasting 输出。Weather forecasting outputs.
- `gen_tst_dataset/fred/`: 当前 FRED caption 数据。Current FRED caption outputs.
- `gen_tst_dataset/fred/archive/`: 旧版 FRED 派生产物。Archived FRED-derived outputs.
- `gen_tst_dataset/anomaly/nab/`: 当前 NAB anomaly caption 数据。Current NAB anomaly caption outputs.

## 归档内容 | Archived Content

- `archive/legacy_code/`: 已不属于当前主线的旧代码分支。Older code branches no longer part of the active pipeline.
- `archive/experiments/`: 预实验代码与资产。Pre-experiment code and assets kept for reference.
- `archive/legacy_scripts/`: 一次性脚本与早期工具。One-off scripts and early utilities removed from the active surface area.
- `archive/misc/`: 旧输出、重复文件、图像和快照。Old outputs, duplicated files, plots, and snapshots.

## 实操建议 | Practical Recommendation

如果你接下来要继续做 time series caption 数据生成与 alignment 训练，请优先关注下面这些目录：  
If you want to continue building caption data and training alignment models, focus on these directories first:

- `ts_cap/`
- `ts_align/`
- `ts_align_scripts_v2/`
- `scripts/`
- `scripts/eval/`
- `dataset/`
- `gen_tst_dataset/`

具体运行方式见 [USAGE.md](USAGE.md)。  
For concrete run commands, see [USAGE.md](USAGE.md).
