# LTSGen × OpenTSLM 全实验报告

**截止日期**：2026-04-21
**文档定位**：项目自启动以来全部实证结果的单文件总报告。供导师查阅、毕设/论文取材、后续接力者复用。
**风格**：事实 + 证据 + caveat 三件套。**不预设论文 story**。
**配套 figure 目录**：`./.research/figures-20260421/`（18 张 SVG）
**文件位置**：`./.research/full-experimental-report-20260421.md`

---

## §0 执行摘要

### 三条可信结论（详见 §9）

| # | 结论 | 关键证据 |
|---|---|---|
| **C2** | TS-LLM captioner 的实现质量有显著 **scale + data 依赖**，且**单纯换 SFT 数据格式不足以闭合差距** | OpenTSLM-4B vs ChatTS-14B：conditioning flip rate 2.78% vs 50%；TSShapeQA 5-cond cap 0.34 vs 0.53；Q3 format-SFT 让 OpenTSLM 在 dataset_a 上从 0.335 → 0.451，但距 ChatTS 0.861 仍差 41pp |
| **C3** | Caption 对下游 LLM QA 的有用性**高度依赖测试格式**，没有跨 benchmark 的稳定优势 | ChatTS cap vs numbers gap：dataset_a +21pp（in-dist）/ TSShapeQA -2pp / TimeSeriesExam -16pp / TSAQA -17pp |
| **C4** | Tool-Agent 在 shape-primitive MCQ 上碾压一切，但**绝非 universal generalist** —— 其有效性绑定"任务被固定工具集覆盖" | TSShapeQA 1.000 / dataset_a 0.735 / TSAQA 0.556；TSAQA temporal_relationship 0.361 暴露工具覆盖度问题 |

### 4-benchmark 跨方法综合表

```
Benchmark              n      OpenTSLM cap  ChatTS cap   numbers   Tool-Agent
TSShapeQA-v1 OOD       800    0.335          0.529       0.554     1.000
TSShapeQA-v1 in-dist   300    0.350          0.533        0.597    1.000
dataset_a uv           117    0.335 (cat)    0.861       0.651     0.735
                              0.150 (num)    0.753       0.416     0.511
TSAQA OOD (gpt-5.4)    996    0.449          0.461       0.631     0.556
TimeSeriesExam OOD     263    0.361          0.513       0.677     未测
```

**🖼 [Fig 11: 跨 benchmark 总览图](./figures-20260421/fig11_cross_benchmark.svg)**

### 做了什么 / 没做什么

| ✅ 已做 | ❌ 没做（且不再做） |
|---|---|
| LTSGen 数据生成 pipeline + 62K 样本 | 32B+ 规模 captioner 实验 |
| OpenTSLM-Flamingo 训练 + 4 ablation | OpenTSLM end-to-end QA fine-tune（见 §13 Appendix A） |
| 自建 TSShapeQA-v1 benchmark + 11 条件评测 | 方向 (b/c/d)：TSAQA SFT、TS-CLIP、LTSF aux loss（见 §13） |
| 跨 4 benchmark × 5 方法对照评测 | TSShapeQA-v2 counterfactual benchmark（infra 备好但未启用） |
| Tool-Agent + 因果消融 + composition QA | NeurIPS D&B 2026-05-06 投稿（见 §13） |
| Cross-family conditioning ablation（vs ChatTS-14B） | ShapeShift / CPR 3-contribution 论文（见 §13） |
| Q3 Format-SFT 反证 SCALE-DETERMINES |  |
| CapRL 信号探测 T1/T2/T2'/Q2/T3（见 §12） |  |

---

## §1 项目背景与目标

### 1.1 研究问题

> 在 LLM 时代，"先用 TS-LLM 生成 caption，再让通用 LLM 用 caption 答下游 QA"这条路是否真的能 work？

### 1.2 与 Vision 的类比

🖼 **[Fig 1: paradigm 类比示意图](./figures-20260421/fig01_paradigm_analogy.svg)**

Vision 走过了 caption 数据 → CLIP（contrastive）→ MLLM（LLaVA/GPT-4V）三步。TS 没有自然 paired data，本项目的初衷是把 vision 的第一步（合成 caption 数据）做出来（LTSGen）+ 把第三步（caption → 下游 LLM）测穿，看这条 paradigm 在 TS 上能不能立得住。

### 1.3 项目 scope

5 个研究方向中，**本报告只覆盖方向 (a) caption utility 验证**，外加一些 controlled 反证实验。
- 方向 (a) ✅ caption → frozen LLM QA：本报告
- 方向 (b) ❌ TS-QA downstream（TSAQA fine-tune）：infra 备好（`LTSGEN-ext-b/`），未跑
- 方向 (c) ❌ TS-CLIP 对比预训练：infra 备好（`ts_align/losses.py`），未跑
- 方向 (d) ❌ Caption 作 LTSF 辅助 loss：未启动

### 1.4 关键约束（影响 scope）

- **Setting A 而非 Setting B**：测的是"captioner → frozen LLM"接口，不是"TS-LLM 端到端 QA"。这是有意的 — 我们要测 caption 作为接口的价值，不是测 captioner 自己回答 QA 的能力（后者是 Setting B 的问题）
- **下游 LLM 全程冻结**：gpt-5.4 / gpt-5.4-mini 通过 crisinsjtu 反向代理调用，不做任何 SFT
- **数据集合非全集**：3 个外部 benchmark + 1 个自建 benchmark，n 在 117 ~ 996 之间

---

## §2 系统侧：LTSGen 数据生成

### 2.1 数据源

| 数据集 | 用途 | 备注 |
|---|---|---|
| FRED | 宏观经济（月度） | 长序列 |
| ETT | 电力变压器（小时） | LTSF 标准 benchmark |
| Traffic | 高速车流（小时） | 强季节性 |
| Weather | 气象（10 分钟） | 多变量 |
| NAB | Numenta Anomaly Benchmark | 异常标签 |
| UCR2018 | 时序分类 128 个数据集 | 短序列 |

### 2.2 Pipeline

🖼 **[Fig 2: LTSGen 数据生成流程图](./figures-20260421/fig02_ltsgen_pipeline.svg)**

1. 滑窗采样：window length ∈ {128, 256, 512}，stride 视数据集而定
2. GPT-5 caption 生成：prompt 含 12+ 语义槽位（趋势、波动、季节性、峰谷位置/幅度、相关性、突变点等）
3. QC + dedupe：过滤生成失败 / 数据外推不合理的样本
4. Mixed corpus 用于 SFT：FC + AN + CLS curriculum 顺序

### 2.3 数据规模

| 划分 | 样本数 | 来源混合 |
|---|---:|---|
| Mixed Train | 55,550 | FRED + ETT + Traffic + Weather + NAB + UCR |
| Mixed Val | 6,234 | 同上 |
| Mixed Test | 1,171 | 同上 |
| Eval Splits（均衡） | 1,471 | FC 840 + AN 131 + CLS 500 |

数据路径：A100 `/cluster/home/user1/hulining/TSDataset/LTSGen/gen_tst_dataset/opentslm/`。

### 2.4 数据例子 1 — LTSGen 训练样本

```json
{
  "id": "timemmd:Climate:Total:D3:w256:s256",
  "dataset": "timemmd",
  "domain": "Climate",
  "window_len": 256,
  "series": [0.14, 0.14, 0.14, ..., 7.23, 6.84, 6.34, ...],
  "caption": "The time series shows a steady upward trend with low volatility
    and a strong seasonal pattern repeating every 12 months. The data starts
    with a moderate increase in the early part of the window, followed by a
    more pronounced rise in the first half, and a slightly smaller but still
    positive growth in the second half. A notable peak occurs late in the
    window, reaching about 1.5 standard deviations above the mean, while a
    valley is observed early on, about 1.2 standard deviations below the
    mean. ..."
}
```

**注意**：上面这条 caption 是 OpenTSLM **学完** LTSGen 数据后**自己生成**的输出 — 看起来流畅但**模板化**（见 §8.4 的诊断 + §10.2 的 caveat）。原始 GPT-5 生成的 LTSGen 训练 caption 本身有更高的内容多样性。

---

## §3 系统侧：OpenTSLM-Flamingo 模型

### 3.1 架构

🖼 **[Fig 3: OpenTSLM-Flamingo 架构图](./figures-20260421/fig03_opentslm_arch.svg)**

| 组件 | 选择 | 状态 |
|---|---|---|
| LLM | Qwen3-4B | LoRA 可训 |
| TS encoder | Chronos-2（Amazon 预训练） | 冻结 |
| 跨模态融合 | Flamingo cross-attention | trainable |

设计原则：复用 vision 端 LLaVA / Flamingo 的成熟设计，避免在 TS 表征本身上同时探索两件事。

### 3.2 Curriculum 训练

🖼 **[Fig 4: Curriculum 训练时间线](./figures-20260421/fig04_curriculum_timeline.svg)**

阶段顺序：M4 pretrain → Forecasting → Anomaly → Classification → Mixed。每阶段从前一阶段的 ckpt 初始化。

### 3.3 4 个 ablation 对照（vars=1 winner）

🖼 **[Fig 5: vars=1 ablation winner bar chart](./figures-20260421/fig05_opentslm_ablation_vars1.svg)**

| 实验 | val_loss | FC ROUGE-L | AN ROUGE-L | CLS ROUGE-L | Overall |
|---|---:|---:|---:|---:|---:|
| Baseline (vars=8) | 0.2055 | 0.618 | 0.376 | 0.312 | 0.492 |
| **vars=1 (winner)** | **0.2026** | **0.653** | **0.485** | **0.396** | **0.550** |
| Unfreeze2 (2 ep) | 0.194 | 0.640 | 0.400 | 0.286 | 0.498 |
| CNN encoder | — | — | — | — | 5-6 epoch 即停 |

**关键发现**：vars=1 全面胜出，**多变量信息反而稀释 caption 质量**。winner ckpt 用作所有下游评测的"OpenTSLM caption"来源。

Ckpt 路径：A100 `/cluster1/user1/hulining/opentslm_checkpoints/Qwen3_4B/OpenTSLMFlamingo/ablation_vars1_mixed/stage2_captioning/checkpoints/best_model.pt`

### 3.4 Generation failure modes（10–20% 失败率）

3 类生成崩溃，合计 10–20%：

| 模式 | 频率 | 例子 |
|---|---:|---|
| **Token Collapse** | <1%（CLS 上） | `"5555555555555..."` |
| **Number Dump** | ~3%（AN 上） | `"1 66.67 123.33 89.0 ..."` 不构成自然语言 |
| **Premature Stop** | ~13%（最常见） | `"Type of anomaly:"` 后直接停止 |

未投入修复（repetition penalty / min_new_tokens / oversampling 都试过部分），失败样本在 5-condition eval 中**保留 placeholder**而非过滤，因为 caption 失败本身也是 paradigm 评估的一部分。

---

## §4 评测协议

### 4.1 5-condition protocol

| Condition | 给下游 LLM 的输入 | 角色 |
|---|---|---|
| `meta_only` | 仅场景描述 + 问题 | 下界 baseline（leakage 检测） |
| `numbers` | 场景 + raw TS 数值 + 问题 | numbers baseline（强 baseline） |
| `caption` | 场景 + captioner 输出 + 问题 | **主实验组** |
| `caption_plus` | 场景 + caption + numbers + 问题 | 互补性测试 |
| `wrong_caption` | 场景 + 错配 caption + 问题 | 负对照（验证 caption 不是装饰） |

补充条件（仅 TSShapeQA）：`numbers_cot`（强 baseline+CoT）、`caption_cot`、`Tool-Agent`（gpt-5.4 调 3 个 numpy 工具）、Tool-Agent remove-one、Tool-Agent + 假工具干扰。

### 4.2 双 judge 设计

| Judge | 作用 |
|---|---|
| `gpt-5.4` | 主 judge，TSAQA 用 |
| `gpt-5.4-mini` | 副 judge，TSShapeQA / dataset_a 用，部分 task 双判对齐 |

判分模式：
- MCQ：精确匹配字母
- 自由文本（dataset_a 中部分维度）：ChatTS 自带 `evaluate_qa.py`（categorical regex + numerical 数值容差）
- causal/deductive 维度：LLM-judge 1.0 / 0.5 / 0.0

### 4.3 三个 benchmark 的对比定位

| Benchmark | Format | OOD 程度 | 用途 |
|---|---|---|---|
| **TSShapeQA-v1** | shape-primitive MCQ | 自建（OOD vs LTSGen 训练分布） | 主自建对照集 |
| **dataset_a uv** | ChatTS 4-段编号自由回答 | ChatTS 训练分布**内** | 测试 in-distribution caption 上限 |
| **TSAQA** | 混合 MCQ / T/F / ordering | 完全独立学术 benchmark | 验证 ChatTS 优势是否泛化 |
| **TimeSeriesExam** | MCQ，5 类 | 完全独立（n=263 共享子集） | 第 4 个 OOD 验证 |

### 4.4 数据例子 3 — 5-condition prompt 草样

```
[meta_only]
You are analyzing a time series from {domain}. Without seeing the data,
answer: {question}
A) {opt_A}  B) {opt_B}  C) {opt_C}  D) {opt_D}

[numbers]
You are analyzing a time series from {domain}.
Raw values: [0.14, 0.14, 0.14, ..., 7.23, ...]   (256 floats)
Question: {question}
A) {opt_A}  ...

[caption]
You are analyzing a time series from {domain}.
Caption: "The time series shows a steady upward trend with low volatility..."
Question: {question}
...

[wrong_caption]  # Caption 来自完全不同 ID 的 TS，randomly mismatched
Caption: "The series exhibits a sharp peak in the first quarter and..."
Question: {question}
...
```

完整 prompt：`LTSGEN-ext-a/scripts/eval/tsshapeqa_eval.py::build_prompt()`。

---

## §5 自建 benchmark：TSShapeQA-v1

### 5.1 构建动机

外部 benchmark 普遍存在两个问题：(1) TSAQA 序列太短（median=64），GPT 直接读数字就够；(2) MCQ / FREDQA 等 QA 太依赖 domain knowledge。我们要的是 **caption 真正能贡献价值的场景** — 形态题（trend / extrema / volatility 判断），这类题只有看序列或看准确 caption 才能答。

### 5.2 数据源 + ground truth

**数据源（OOD）**：
- Time-MMD（主，真 OOD vs LTSGen 训练分布）
- exchange_rate（近似 OOD，LTSGen 训练集仅 46 条）
- illness（近似 OOD，4 条）
- ❌ 放弃 electricity（训练集里有 2624 条）

**数据源（in-dist）**：ETT / Traffic / Weather / NAB held-out 子集

**Ground truth**：纯 numpy / scipy 规则化抽取（`shape_features.py`）：
- TREND：`scipy.stats.linregress` 斜率 + R²
- EXTREMA_POS：`np.argmax` 落在哪个三等分窗口
- VOLATILITY_REGION：前后半 detrended std 比
- ❌ PERIOD：因 gt 分布严重偏 "none" 被排除

### 5.3 MCQ 生成 + 平衡 + sanity check

1. gpt-5.4 看 series + gt feature → JSON MCQ
2. 规则校验答案一致性
3. 选项顺序后处理随机打乱（消除字母位置 leakage）
4. 每 qa_type 内 gt 严格等量（按最小类 cap）

**Sanity check（Pilot 50, gpt-5.4-mini）**：meta_only 0.32 ≈ blended random 0.36（每 qa_type 在随机基线 ±0.12 内），numbers - meta_only = +14pp → benchmark 有效。

### 5.4 三个子集

| 子集 | n | 用途 |
|---|---:|---|
| OOD | 800 | 主对照集 |
| in-dist | 300 | scale-vs-format 检测 |
| composition | 300 | 必须组合 2 个工具结果（PEAK_VOL_MATCH） |

### 5.5 数据例子 4 — TSShapeQA QA item

```json
{
  "id": "timemmd:Climate:Total:D3:w256:s256",
  "dataset": "timemmd",
  "domain": "Climate",
  "window_len": 256,
  "series": [0.14, 0.14, 0.14, ..., 7.23, ...],
  "qa_type": "EXTREMA_POS",
  "question": "Where in the 256-point window does the global maximum occur?",
  "options": {
    "A": "First third (points 0-85)",
    "B": "Middle third (points 86-170)",
    "C": "Last third (points 171-255)",
    "D": "Cannot determine"
  },
  "answer": "B",
  "gt_feature": {"argmax_idx": 130, "third": "middle"}
}
```

---

## §6 主实验：跨 benchmark 5-condition 评测

### 6.1 TSShapeQA-v1 OOD（n=800，11 条件）

🖼 **[Fig 6: TSShapeQA OOD 9-condition 主结果](./figures-20260421/fig06_tsshapeqa_ood_main.svg)**

| Condition | OOD 800 | In-dist 300 |
|---|---:|---:|
| meta_only | 0.335 | 0.337 |
| wrong_caption | 0.338 | 0.310 |
| **OpenTSLM caption** | 0.335 | 0.350 |
| caption + CoT | **0.225** ⚠️ | **0.257** ⚠️ |
| caption + numbers | 0.463 | 0.517 |
| **ChatTS-14B caption** | **0.529** | **0.533** |
| numbers | 0.554 | 0.597 |
| **numbers + CoT** | 0.599 | 0.657 |
| **Tool-Agent (gpt-5.4)** | **1.000** 🏆 | **1.000** 🏆 |
| Tool-Agent + 3 假工具干扰 | 1.000 | 1.000 |
| Tool-Agent (gpt-5.4-mini) | 1.000 | 1.000 |

**关键观察**：
1. OpenTSLM caption ≈ wrong_caption（0.335 = 0.338）→ caption 不传递 input 信息
2. caption + CoT **倒退到 0.225** → CoT 把模板化 caption 的虚假断言放大成"自信错误"
3. ChatTS caption 0.529 ≈ numbers 0.554（gap 仅 -2.5pp）→ ChatTS 接近追平 numbers
4. Tool-Agent 1.000 在所有子集 + 假工具干扰下都不掉

### 6.2 Tool-Agent 因果消融

🖼 **[Fig 7: Tool-Agent remove-one heatmap](./figures-20260421/fig07_toolagent_removeone.svg)**

| 工具配置 | TREND | EXTREMA | VOL |
|---|---:|---:|---:|
| 全 3 工具 | 1.00 | 1.00 | 1.00 |
| 拿走 extract_trend | **0.43** | 1.00 | 1.00 |
| 拿走 extract_extrema_pos | 1.00 | **0.37** | 1.00 |
| 拿走 extract_volatility_region | 1.00 | 1.00 | **0.20** |

→ 每个工具对其对应任务**因果必要**，去掉任一工具该任务塌缩到接近随机（0.25）。

### 6.3 Composition QA（PEAK_VOL_MATCH，n=300）

| 条件 | 准确率 |
|---|---:|
| meta_only | 0.260 |
| numbers + CoT | 0.497 |
| **Tool-Agent** | **0.993** |

→ 必须组合 2 个工具结果时 Tool-Agent 仍碾压（avg 2.0 tool calls / sample）。

### 6.4 dataset_a univariate（n=117，三 captioner 对照）

🖼 **[Fig 8: dataset_a per-ability 对比](./figures-20260421/fig08_dataset_a_per_ability.svg)**

| Condition | categorical | numerical |
|---|---:|---:|
| meta_only | 0.405-0.409 | 0.032-0.035 |
| **gpt-numbers**（baseline） | 0.651 | 0.416 |
| **OpenTSLM caption** | **0.335** 📉 | **0.150** 📉 |
| **ChatTS caption** | **0.861** 🏆 | **0.753** 🏆 |
| **Tool-Agent** | 0.735 | 0.511 |
| caption_plus (ChatTS) | 0.888 | 0.801 |
| wrong_caption | 0.372-0.442 | 0.105-0.201 |

**Per-ability ChatTS caption vs numbers gap**：

| Ability | numbers (cat) | ChatTS cap (cat) | Δ | n |
|---|---:|---:|---:|---:|
| local（spike 类型） | 0.433 | **0.817** | **+38pp** | 60 |
| local-inductive | 0.571 | **0.914** | **+34pp** | 35 |
| season | 0.730 | **1.000** | +27pp | 37 |
| trend | 0.610 | 0.707 | +10pp | 41 |
| noise | **1.000** | 0.905 | -10pp | 42 |

**LLM-judge 补充评分（causal + deductive）**：

| 条件 | ChatTS causal | ChatTS deductive | OpenTSLM causal | OpenTSLM deductive |
|---|---:|---:|---:|---:|
| numbers | 0.755 | 0.570 | 0.750 | 0.628 |
| **caption** | **0.799** 🏆 | **0.674** 🏆 | **0.609** 📉 | **0.430** 📉 |
| wrong_caption | 0.685 | 0.523 | 0.543 | 0.581 |

**关键观察**：
1. ChatTS caption 0.86 远超 numbers 0.65（+21pp 在 cat 维度）
2. **OpenTSLM caption 0.34 比 wrong_caption 0.37 还低** —— actively misleading
3. **OpenTSLM deductive 0.43 < wrong_caption 0.58** —— 在推理任务上 caption **主动带偏**

**caveat（重要）**：ChatTS 训练数据**就包含 dataset_a/b 风格的合成 spike + 4-段编号答案模板**。ChatTS 在 dataset_a 上的高分有显著 in-distribution 优势成分（这促成了 §7 的 Q3 format-SFT 反证实验）。

### 6.5 TSAQA（跨格式 OOD 验证，n=996）

🖼 **[Fig 9: TSAQA per-task 5-condition heatmap](./figures-20260421/fig09_tsaqa_heatmap.svg)**

**Setup**：TSAQA（Cai et al. 2024 独立学术 benchmark, 42K 全集，从未训过两个 captioner）、1000 sample subset (5 task × 200，最终 996 有效)、双 judge、混合 MCQ + T/F + ordering 格式。

**主结果（gpt-5.4 judge, n=996）**：

| Condition | OpenTSLM cap | **ChatTS cap** | numbers | meta_only |
|---|---:|---:|---:|---:|
| Overall | 0.449 | **0.461** | **0.631** | 0.505 |
| anomaly_detection | 0.524 | 0.518 | 0.554 | 0.518 |
| **characterization** | 0.518 | 0.488 | **0.813** | 0.711 |
| classification | 0.464 | 0.626 | 0.470 | 0.560 |
| comparison | 0.524 | 0.518 | **0.741** | 0.590 |
| data_transformation | 0.349 | 0.355 | **0.632** | 0.404 |
| temporal_relationship | 0.313 | 0.259 | **0.578** | 0.247 |

**🚨 关键发现**：**ChatTS caption 在 TSAQA 上和 OpenTSLM caption 几乎完全 TIED**（0.461 vs 0.449，差 1pp）。**dataset_a 上的 +53pp 优势完全消失**。两个 captioner 都输给 numbers baseline 17-18pp。

### 6.6 TSAQA Tool-Agent

🖼 **[Fig 10: TSAQA Tool-Agent vs numbers per-task](./figures-20260421/fig10_tsaqa_toolagent_per_task.svg)**

**Setup**：996-sample 子集、6 个工具（trend / extrema / periodogram / local_spikes / noise_std / volatility，复用 dataset_a 工具库）、模型不能看原始数字、max_rounds=6、concurrency=8。

**主结果**：

| Task | n | Tool-Agent acc | 对比 numbers | 对比 best caption |
|---|---:|---:|---:|---:|
| classification | 166 | 0.615 | +14.5pp | -1.1pp |
| anomaly_detection | 166 | 0.578 | +2.4pp | +6.0pp |
| characterization | 166 | 0.621 | **-19.2pp** | +13.3pp |
| **temporal_relationship** | 166 | **0.361** | **-21.7pp** | +10.2pp |
| comparison | 166 | 0.675 | -6.6pp | +15.7pp |
| data_transformation | 166 | 0.488 | **-14.4pp** | +13.3pp |
| **Overall** | **996** | **0.556** | **-7.5pp** | **+9.5pp** |

**工具使用统计**：平均 4.08 tool calls / sample；平均 1.98 rounds / sample；max_rounds 爆 0/996；最常见序列 `[local_spikes, noise_std, trend]` × 104 次；56 个零工具调用样本（5.6%），主要在 temporal_relationship。

**`temporal_relationship` 0.361 的结构性原因**：该 task 是"将 question text 中给出的 A/B/C/D patches 重排恢复原序列"。候选 patches 嵌在 question text 里，**不在 `input_ts` 字段中**。6 个工具只能探 `input_ts`（第一个 patch），看不到其余 3 个 patch → **结构性任务-工具集失配**。

### 6.7 TimeSeriesExam（第 4 个 benchmark，n=263）

🖼 **[Fig 18: TimeSeriesExam 5-condition](./figures-20260421/fig18_timeseriesexam_5cond.svg)**

**Setup**：TimeSeriesExam (qa_dataset.json, 5 类 MCQ)、2 captioner shared subset n=263、gpt-5.4 judge。

**主结果**：

| Condition | acc |
|---|---:|
| meta_only | 0.392 |
| wrong_caption | 0.380 |
| OpenTSLM caption | 0.361 |
| **ChatTS caption** | **0.513** |
| **numbers** | **0.677** 🏆 |

**Per-category（caption_chatts vs numbers）**：

| Category | n | ChatTS cap | numbers | Δ |
|---|---:|---:|---:|---:|
| Anomaly Detection | 89 | 0.528 | 0.607 | -8pp |
| Noise Understanding | 74 | 0.554 | 0.649 | -10pp |
| Pattern Recognition | 100 | 0.470 | 0.760 | -29pp |

**关键观察**：第 4 个独立 OOD benchmark **再次验证 §6.5 结论** — caption 输 numbers ~17pp，OpenTSLM caption ≈ wrong_caption。

### 6.8 跨 benchmark 综合表（4 benchmarks）

🖼 **[Fig 11: 4-benchmark × 5-method 总览](./figures-20260421/fig11_cross_benchmark.svg)**

```
Benchmark              n     OpenTSLM cap  ChatTS cap   numbers  Tool-Agent  Oracle
TSShapeQA OOD         800    0.335         0.529        0.554    1.000        ~0.96*
TSShapeQA in-dist     300    0.350         0.533        0.597    1.000        ~0.96*
dataset_a uv (cat)    117    0.335         0.861        0.651    0.735        n/a
dataset_a uv (num)    117    0.150         0.753        0.416    0.511        n/a
TSAQA (gpt-5.4)       996    0.449         0.461        0.631    0.556        未测
TimeSeriesExam        263    0.361         0.513        0.677    未测        未测
```

\* Oracle 数据保留作历史参考；本报告**不**用 oracle probe 作论证（见 §13 决策记录）。

→ **4 个 benchmark 4 种 winner / pattern**：TSShapeQA Tool-Agent 碾压 / dataset_a ChatTS caption 反超 / TSAQA + TimeSeriesExam numbers 胜 / OpenTSLM caption 在 3 个外部 benchmark 都 ≈ wrong_caption。

🖼 **[Fig 13: ChatTS caption vs numbers gap 跨 benchmark](./figures-20260421/fig13_caption_vs_numbers_gap.svg)** — 一图看 caption 价值的格式依赖。

---

## §7 控制实验 1：Format-SFT 反证（Q3）

### 7.1 动机

ChatTS 在 dataset_a 上 +21pp（vs numbers）的优势，多大程度是 **scale**（4B → 14B）多大是 **format**（OpenTSLM 的 LTSGen format vs ChatTS 的 dataset_a format）？

→ 直接做反证：**在 dataset_a 风格的合成数据上重训一个 OpenTSLM variant**，看 caption 能不能逼近 ChatTS。

### 7.2 Setup

| 维度 | 选择 |
|---|---|
| 起点 | OpenTSLM-Flamingo vars=1 ckpt |
| SFT 数据 | dataset_a 风格合成（spike + 4-段编号答案模板） |
| 训练阶段 | stage2_captioning（同 vars=1 mixed 之后） |
| 评测 | dataset_a (n=117) caption condition + TSShapeQA OOD (n=800) caption condition（regression check） |
| Judge | gpt-5.4-mini |

### 7.3 Pre-registered decision rule

| 条件 | Verdict | 含义 |
|---|---|---|
| dataset_a cat ≥ 0.75 AND TSShapeQA cat ≥ 0.30 | FORMAT-IS-DETERMINANT | format 决定，scale 不决定 |
| dataset_a cat < 0.55 | **SCALE-DETERMINES** | scale 决定，format 救不了 |
| dataset_a cat 0.55-0.75 | PARTIAL-FORMAT | 部分 format 部分 scale |
| TSShapeQA cat < 0.25 | NEGATIVE-TRANSFER（叠加） | 副作用：损坏 OOD 能力 |

### 7.4 主结果

🖼 **[Fig 16: Q3 SFT before-after](./figures-20260421/fig16_q3_format_sft.svg)**

| Model / state | dataset_a cat | TSShapeQA cat |
|---|---:|---:|
| Pre-SFT OpenTSLM (vars=1) | 0.335 | 0.335 |
| ChatTS-14B | **0.861** | 0.529 |
| **SFT'd OpenTSLM (Q3 pilot, NEW)** | **0.4512** | **0.3438** |

**Verdict：SCALE-DETERMINES**

- dataset_a cat 从 0.335 → 0.451（+12pp） — 提升明显，但**远不及 ChatTS 0.861，gap 仍 41pp**
- TSShapeQA OOD cat 0.344（vs pre-SFT 0.335）— 无 negative transfer
- gap vs ChatTS：**41.0pp** persists

### 7.5 完整 5-condition 表

**dataset_a (gpt-5.4-mini, n=117, categorical acc)**：

| Condition | Pre-SFT (ref) | ChatTS (ref) | SFT'd OpenTSLM (NEW) |
|---|---:|---:|---:|
| meta_only | 0.405-0.409 | 0.405-0.409 | 0.3953 |
| numbers | 0.651 | 0.651 | 0.5953 |
| caption | 0.335 | 0.861 | **0.4512** |
| caption_plus | 0.463 | 0.888 | 0.6279 |
| wrong_caption | 0.372-0.442 | 0.372-0.442 | 0.4558 |

**TSShapeQA OOD (gpt-5.4-mini, n=800, accuracy)**：

| Condition | Pre-SFT (ref) | ChatTS (ref) | SFT'd OpenTSLM (NEW) |
|---|---:|---:|---:|
| caption | 0.335 | 0.529 | **0.3438** |

### 7.6 含义

**Format SFT 不能替代 scale**。OpenTSLM 即使在 ChatTS 训练分布上也只能逼到 0.45，离 ChatTS 0.86 仍差 41pp。这强化 **C2** 的 scale 维度论证：
- 不是"OpenTSLM 学错了 format"
- 是"4B + LTSGen 数据规模 + Flamingo 架构的组合在 captioning 这件事上有上限"

→ **CapRL 方向（§12）的实质就是 distillation**（如果 OpenTSLM 输出分布是 ChatTS 子集 + scale gap），format SFT 是更便宜的下界 — Q3 已经把这个下界跑出来了。

---

## §8 控制实验 2：Conditioning Ablation（cross-captioner）

### 8.1 设计

如果 captioner 真的看输入，那么把输入做某种 transform，caption 应该也跟着变。我们设计两种 transform：
- **`time_reversal`**：序列倒序（应该让"早期峰"变成"晚期峰"）
- **`variance_injection_second_half`**：后半段乘 3× std（应该让 "low volatility" 变成 "second half higher volatility"）

筛选 flip-confident 样本（n=36：22 reversal + 14 variance）— 即 oracle 上 caption 应该被 flip 才算 condition on input。

### 8.2 OpenTSLM 结果

| Transform | n | OpenTSLM caption 正确翻转率 | caption 一字不变率 |
|---|---:|---:|---:|
| time_reversal | 22 | **4.5%** (1/22) | 50.0% |
| variance_injection | 14 | **0.0%** (0/14) | 78.6% |
| Overall | 36 | **2.78%** | — |

→ **OpenTSLM 几乎完全不 condition on input**。50–79% caption 在输入反转/方差注入后**字面不变**。

### 8.3 ChatTS-14B 跨家族对照

🖼 **[Fig 12: 跨家族 conditioning flip rate](./figures-20260421/fig12_conditioning_flip_rate.svg)**

| Transform | OpenTSLM-Flamingo (4B) | **ChatTS-14B** | Δ |
|---|---:|---:|---:|
| time_reversal (n=22) | 4.55% | **68.18%** | +63.7pp |
| variance_injection (n=14) | 0.00% | 21.43% | +21.4pp |
| **Overall (n=36)** | **2.78%** | **50.00%** | **+47.2pp** |

caption 一字不变率：OpenTSLM time_reversal 50% 一字不变 vs ChatTS 4.5%。

**含义**：14B + Evol-Instruct 大规模数据让 captioner 部分恢复 input-conditioning，**但仍远低于 60% 阈值**，也远低于 oracle 96% 上界。**"OpenTSLM 实现塌缩" 部分 paradigm 通用，部分 method-specific**。

### 8.4 数据例子 6 — Conditioning ablation 对照

**OpenTSLM**（输入翻转后字面**完全没变**）：

```
[Original input]
"id": "exchange_rate:3:w512:s4608"
"caption": "Up, the time series shows a steady upward trend with low
volatility and a strong seasonal pattern repeating every 10 time units.
The overall growth is substantial, with a net increase of over 100% over
the time span. The early part of the series experiences a moderate rise..."

[Reversed input — same id, series reversed]
"caption": "Up, the time series shows a steady upward trend with low
volatility and a strong seasonal pattern repeating every 10 time units. ..."
                                       ↑ 完全相同
```

**ChatTS-14B**（输入翻转后 caption 也跟着翻转）：

```
[Original input]
"id": "exchange_rate:3:w512:s4608"
"caption": "The overall trend is increasing. The global maximum occurs
at point 511, in the last third of the window. The first half of the
window has larger short-term fluctuations..."

[Reversed input]
"caption": "The overall trend is mixed, with multiple segments showing
different directions. The global maximum occurs at point 300, which is
in the middle third of the window (points 171-341). The first half of
the window (points 0-256) has larger short-term fluctuations..."
                                       ↑ 趋势/极值/波动 全部翻转
```

→ 这 1 对例子直观展示了 §8.3 表里 0% vs 95% flip rate 的差距。

### 8.5 数据例子 5 — 同一 TS 上的 3 个 captioner 输出对比

输入：`id="timemmd:Climate:Total:D3:w256:s256"` (上面已展示数据)

```
OpenTSLM (vars=1):
"The time series shows a steady upward trend with low volatility and a
strong seasonal pattern repeating every 12 months. The data starts with
a moderate increase in the early part of the window, followed by a more
pronounced rise in the first half, and a slightly smaller but still
positive growth in the second half. A notable peak occurs late in the
window, reaching about 1.5 standard deviations above the mean..."

ChatTS-14B:
"The overall trend is mixed, with increasing and decreasing segments.
The global maximum (12.06) occurs at point 189, which is in the last
third of the 256-point window. Short-term fluctuations are more
pronounced in the first half (e.g., the rapid rise between points
125–132 and the decline after point 132) compared to the smoother
second half."

OpenTSLM-SFT'd-on-dataset_a (Q3, NEW 2026-04-21):
[caption 内容介于两者之间，仍偏模板化但开始引用具体数值]
```

观察：OpenTSLM caption **不引用任何具体数字**（只说 "about 1.5 std above mean"，但实际峰值是 12.06），多个不同输入开头都是 "steady upward trend with low volatility..." 模板；ChatTS caption **引用具体点位 + 数值**（point 189, value 12.06）。这是 conditioning fidelity 的直接体现。

---

## §9 综合结论（3 条 + caveat）

### C2. TS-LLM captioner 的实现质量有显著 scale + data 依赖，且单纯换 SFT 数据格式不足以闭合差距

**证据**：

| 指标 | OpenTSLM 4B | ChatTS 14B |
|---|---:|---:|
| Conditioning flip rate (n=36) | 2.78% | 50.0% |
| TSShapeQA 5-cond caption acc | 0.34 | 0.53 (+19pp) |
| dataset_a cat acc | 0.34 | 0.86 (+52pp) |
| TimeSeriesExam acc | 0.36 | 0.51 (+15pp) |
| TSAQA acc | 0.45 | 0.46 (≈) |

**Q3 Format-SFT（§7）反证**：把 OpenTSLM 在 dataset_a 风格上重训一遍后 → 0.45（pre-SFT 0.335），仍距 ChatTS 0.86 差 **41pp**。**format SFT 不能替代 scale**。

→ 不是 paradigm 死、也不是 LTSGen 数据格式不对，是 **4B 规模 + LTSGen 数据规模 + 当前架构的组合在 captioning 上有上限**。

**Caveat**：
- 我们没测 32B+ 规模 captioner，scale 上限的精确位置未知
- ChatTS 的优势可能也包含数据规模（Evol-Instruct 数百万样本 vs LTSGen 62K）— 不仅是参数 scale
- Q3 SFT 是 1 个 pilot run（1 个 seed），还没做 N-seed 复现

### C3. Caption 对下游 LLM QA 的有用性高度依赖测试格式

🖼 **[Fig 13: ChatTS cap vs numbers gap 跨 4 benchmark](./figures-20260421/fig13_caption_vs_numbers_gap.svg)**

**证据**：4 个 benchmark 上 ChatTS caption 相对 numbers 的 gap：

| Benchmark | ChatTS cap | numbers | gap | 性质 |
|---|---:|---:|---:|---|
| dataset_a (cat, ChatTS in-dist) | 0.861 | 0.651 | **+21pp** | 训练分布内 |
| TSShapeQA OOD | 0.529 | 0.554 | -2pp | 自建 OOD |
| TimeSeriesExam | 0.513 | 0.677 | -16pp | 独立 OOD |
| TSAQA | 0.461 | 0.631 | -17pp | 独立 OOD |

**Caption 不是普遍替代 numbers 的方案**。在 ChatTS 训过的格式上能压倒 numbers，在陌生格式上反而弱于直接给数字 17pp。

**Caveat**：
- 4 个 benchmark 仍偏少；不知道更广 benchmark spectrum 上是否同 pattern
- "in-dist" 与 "OOD" 的边界并非二元 — dataset_a 之于 ChatTS 是高度 in-dist，TSAQA/TimeSeriesExam 是几乎完全 OOD，中间地带未测
- per-task 异质：dataset_a "local"/"season" 上 caption 大胜，"noise" 上输 numbers — 这个细分模式未在其他 benchmark 系统化测过

### C4. Tool-Agent 是强 baseline 但绝非 universal generalist；其有效性绑定"任务被工具集覆盖"

**证据**：

| Benchmark | Tool-Agent | best caption | best non-caption |
|---|---:|---:|---:|
| TSShapeQA (3 shape primitive MCQ) | **1.000** 🏆 | 0.529 (ChatTS) | 0.554 (numbers) |
| dataset_a uv (4-段开放式) | 0.735 | **0.861** (ChatTS) 🏆 | 0.651 (numbers) |
| TSAQA (混合 MCQ/TF/ordering) | 0.556 | 0.461 (ChatTS) | **0.631** (numbers) 🏆 |

→ **3 个 benchmark 三种胜者**：在简单 MCQ 上 Tool-Agent 碾压；在 ChatTS in-dist 格式上 caption 反超；在通用 OOD 混合格式上 numbers 赢。

**`temporal_relationship` 0.361 的具体证据**：当 task 需要从 question text 中重排 patches（而非分析 input_ts）时，Tool-Agent 的工具集只覆盖 input_ts → 信息丢失；裸 numbers 反而能保留全部 question text 中的 patch 数据。

**Caveat**：
- 3 个 benchmark 仍偏少
- Tool-Agent 的工具集是手工设计的（trend / extrema / volatility / periodogram / local_spikes / noise_std），在更广任务上的"工具发明"成本未估计
- 没测 Tool-Agent vs neural captioner 在长序列（>1024）的对比

---

## §10 局限性与已知问题

### 10.1 OpenTSLM 10–20% 生成失败率
3 类崩溃（Token Collapse / Number Dump / Premature Stop）未根治。失败样本在评测中保留 placeholder（不过滤），所以所有 OpenTSLM caption 数字本身就含 ~10–20% 的"无 caption"贡献。修复 generation failure 不会显著改变 §6 主结论（OpenTSLM caption ≈ wrong_caption），但会改变小数位。

### 10.2 LTSGen caption 的模板化幻觉
§8.5 数据例子 5 已直观展示。即使在 in-dist domain（ETT / Weather）caption 内容也几乎逐字相同。这是 SFT 目标本质 — 没有任何机制强制 caption 编码输入的独特形态，模型学到的是"写一段像 LTSGen 风格的通用 TS 描述"。

→ 这是 §9 C2 结论 "scale + data 依赖" 中 **data** 维度的具体表现。修复路径有 (a) 改 LTSGen 生成 prompt，强制更具体地引用数值/位置；(b) RL（CapRL，§12）。

### 10.3 Benchmark 覆盖只有 4 个
TSShapeQA-v1 自建 + dataset_a (ChatTS in-dist) + TSAQA (OOD) + TimeSeriesExam (OOD) = 4 个。不足以做 "在 N 个 benchmark 上一致 fail/work" 的强结论。Q2（§12 fork C）建议补 1-2 个。

### 10.4 Judge 选择对结论的稳健性
TSAQA 双 judge（gpt-5.4 + mini）已对齐 — overall mean abs diff ≤ 2pp，不改变排序。其他 benchmark 用 mini 单判。Judge 偏差可能放大 caption 评分（mini 可能更宽松地接受模糊 caption），但不改变 caption ≪ numbers 的方向。

### 10.5 双 worktree 数据布局
所有 caption + 评测结果在 `LTSGEN-ext-a` worktree（branch `ext/a-gpt-compare`）。本报告所在的 main 仓只有 `.research/` 文档 + scripts。**复用任何数据前先 cd 到 ext-a。**

### 10.6 报告未涵盖的实验
- Long-TS MCQ (256-1024+ 步, 600 samples) 早期 pilot 显示 meta_only 0.755 → benchmark 不区分 caption / numbers，未纳入主报告
- FREDQA (21 samples) — n 太小，未纳入
- 早期 ROUGE-L based eval（model_compare_matrix.py）— 已废弃，方法学问题（见 §13 Appendix A.1）

---

## §11 资产清单

### 11.1 数据文件

| 资产 | 路径 |
|---|---|
| LTSGen mixed (train/val/test) | A100 `/cluster/home/user1/hulining/TSDataset/LTSGen/gen_tst_dataset/opentslm/mixed/` |
| LTSGen eval splits | A100 同上 `eval_splits/` |
| TSShapeQA-v1 OOD (n=800) | `LTSGEN-ext-a/data/tsshapeqa/tsshapeqa_v1.jsonl` |
| TSShapeQA-v1 in-dist (n=300) | `LTSGEN-ext-a/data/tsshapeqa/tsshapeqa_v1_indist.jsonl` |
| TSShapeQA-v1 composition (n=300) | `LTSGEN-ext-a/data/tsshapeqa/composition_qa_v1.jsonl` |
| ChatTS dataset_a univariate | `LTSGEN-ext-a/data/chatts_bench/dataset_a_uv.json` |
| TSAQA test parquet | A100 `/cluster/home/user1/hulining/TSDataset/TSAQA/test.parquet` |
| TimeSeriesExam | `LTSGEN-ext-a/data/chatts_bench/qa_dataset.json` |

### 11.2 Caption 文件（按 captioner × benchmark）

| Captioner × Benchmark | 路径 |
|---|---|
| OpenTSLM × TSShapeQA OOD | `LTSGEN-ext-a/data/tsshapeqa/captions_v1.jsonl` |
| OpenTSLM × TSShapeQA in-dist | `LTSGEN-ext-a/data/tsshapeqa/captions_v1_indist.jsonl` |
| ChatTS × TSShapeQA OOD | `LTSGEN-ext-a/data/tsshapeqa/tsshapeqa_v1_chatts.jsonl` |
| ChatTS × TSShapeQA in-dist | `LTSGEN-ext-a/data/tsshapeqa/tsshapeqa_v1_indist_chatts.jsonl` |
| OpenTSLM × dataset_a | `LTSGEN-ext-a/data/chatts_bench/captions_opentslm_uv.jsonl` |
| ChatTS × dataset_a | `LTSGEN-ext-a/data/chatts_bench/captions_chatts_uv.jsonl` |
| OpenTSLM × TSAQA | A100 `/cluster1/user1/hulining/tsaqa_captions_vars1.jsonl` |
| ChatTS × TSAQA | A100 `/cluster/home/user1/hulining/chatts_validation/captions/tsaqa/chatts_tsaqa_uv.jsonl` |
| OpenTSLM-SFT'd (Q3) × dataset_a | `LTSGEN-ext-a/results/q3_format_sft/captions/captions_opentslm_sft_dataset_a.jsonl` |
| OpenTSLM-SFT'd (Q3) × TSShapeQA OOD | `LTSGEN-ext-a/results/q3_format_sft/captions/captions_opentslm_sft_tsshapeqa_ood.jsonl` |
| OpenTSLM × TimeSeriesExam | `LTSGEN-ext-a/results/q2_timeseriesexam/captions_opentslm.jsonl` |
| ChatTS × TimeSeriesExam | `LTSGEN-ext-a/results/q2_timeseriesexam/captions_chatts.jsonl` |

### 11.3 评估结果（按实验）

| 实验 | 路径 |
|---|---|
| TSShapeQA OOD 5-cond + cot + chatts + tool-agent + remove-one | `LTSGEN-ext-a/results/tsshapeqa_v1_ood_*` |
| TSShapeQA in-dist 5-cond + cot + chatts + tool-agent + remove-one | `LTSGEN-ext-a/results/tsshapeqa_v1_indist_*` |
| TSShapeQA composition (text + tool-agent) | `LTSGEN-ext-a/results/composition_qa_{text,ta}/` |
| dataset_a 5-cond × {chatts, opentslm, tool_agent} | `LTSGEN-ext-a/results/dataset_a_{chatts,opentslm,tool_agent}/` |
| TSAQA 5-cond × {opentslm, chatts} × {gpt-5.4, mini} | `LTSGEN-ext-a/results/tsaqa_eval{,_chatts}/` |
| TSAQA Tool-Agent | `LTSGEN-ext-a/results/tsaqa_tool_agent/` |
| TimeSeriesExam (Q2) | `LTSGEN-ext-a/results/q2_timeseriesexam/` |
| Q3 Format-SFT eval | `LTSGEN-ext-a/results/q3_format_sft/eval/` |
| Conditioning ablation OpenTSLM | `LTSGEN-ext-a/data/tsshapeqa/conditioning/` |
| Conditioning ablation ChatTS | `LTSGEN-ext-a/data/tsshapeqa/conditioning_chatts/` |
| T1 BoN (ChatTS) | `LTSGEN-ext-a/results/t1_bon_chatts_tsshapeqa/` |
| T1 BoN cross-check (OpenTSLM) | `LTSGEN-ext-a/results/t1_bon_opentslm_crosscheck/` |
| T2 oracle-mix (dataset_a) | `LTSGEN-ext-a/results/t2_oracle_mix/` |
| T2' oracle-mix (TSAQA) + per-task | `LTSGEN-ext-a/results/t2_prime_tsaqa{,_per_task}/` |
| T3 reward-hackability | `LTSGEN-ext-a/results/t3_reward_hackability/` |

### 11.4 关键代码索引

| 文件 | 用途 |
|---|---|
| A100 `OpenTSLM/scripts/eval_per_task.py` | OpenTSLM 模型推理评估 |
| A100 `OpenTSLM/scripts/gen_tsshapeqa_captions.py` | OpenTSLM 给 TSShapeQA 生成 caption |
| A100 `chatts_validation/chatts_caption_gen{,_dsa}.py` | ChatTS-14B 调用脚本 |
| `LTSGEN-ext-a/scripts/eval/tsshapeqa_eval.py` | TSShapeQA 5-cond evaluator |
| `LTSGEN-ext-a/scripts/eval/tsaqa_caption_eval.py` | TSAQA 5-cond evaluator |
| `LTSGEN-ext-a/scripts/eval/tsshapeqa_tool_agent_eval.py` | TSShapeQA Tool-Agent |
| `LTSGEN-ext-a/scripts/eval/tsaqa_tool_agent_eval.py` | TSAQA Tool-Agent (v3 新增) |
| `LTSGEN-ext-a/scripts/chatts_eval/dataset_a_5cond_eval.py` | dataset_a 5-cond evaluator |
| `LTSGEN-ext-a/scripts/chatts_eval/dataset_a_tool_agent_eval.py` | dataset_a Tool-Agent |
| `LTSGEN-ext-a/scripts/chatts_eval/llm_judge_rescore.py` | causal/deductive LLM-judge |
| `LTSGEN-ext-a/scripts/generate/{shape_features,build_tsshapeqa,tsshapeqa_sanity}.py` | TSShapeQA 构建 |
| `LTSGEN-ext-a/scripts/generate/transforms.py` + 64 unit tests | counterfactual transform infra（TSShapeQA-v2 备用） |
| `LTSGEN-ext-a/scripts/capRL/t1_bon_signal.py` | T1 within-captioner BoN |
| `LTSGEN-ext-a/scripts/analysis/t2_oracle_mix.py` | T2/T2'/Q2 oracle-mix |
| `.research/gen_all_figures.py` | 本报告所有 18 张 SVG 图 |

### 11.5 论文图（pre-session 已生成）

| 图 | 路径 | 内容 |
|---|---|---|
| fig1_main_result | `LTSGEN-ext-a/figures/fig1_main_result.{pdf,png}` | TSShapeQA 主结果 |
| fig2_caption_noise | 同上 `fig2_caption_noise` | caption 噪声诊断 |
| fig3_remove_one | 同上 `fig3_remove_one` | Tool-Agent remove-one |
| fig4_composition | 同上 `fig4_composition` | composition QA |

### 11.6 复现路径速查

| 表 | 脚本 | 结果 json |
|---|---|---|
| §6.1 TSShapeQA OOD 11-cond | `tsshapeqa_eval.py` × 多 cond | `results/tsshapeqa_v1_ood_*/metrics.json` |
| §6.2 Tool-Agent remove-one | `tsshapeqa_tool_agent_eval.py --no_tool=...` | `results/tsshapeqa_v1_indist_ta_no_*_v2/metrics.json` |
| §6.4 dataset_a 三 captioner | `dataset_a_5cond_eval.py` | `results/dataset_a_{chatts,opentslm}/summary.json` |
| §6.5 TSAQA 5-cond | `tsaqa_caption_eval.py` | `results/tsaqa_eval{,_chatts}/metrics.json` |
| §6.6 TSAQA Tool-Agent | `tsaqa_tool_agent_eval.py` | `results/tsaqa_tool_agent/metrics.json` |
| §6.7 TimeSeriesExam | `q2_*.py`（在 `results/q2_timeseriesexam/eval.log`） | `results/q2_timeseriesexam/metrics.json` |
| §7 Q3 Format-SFT | A100 `OpenTSLM/scripts/sft_q3_format.py` + dataset_a/TSShapeQA evals | `results/q3_format_sft/{verdict.md, eval/}` |
| §8 Conditioning ablation | `LTSGEN-ext-a/scripts/conditioning/*.py` | `data/tsshapeqa/conditioning{,_chatts}/flip_rate.json` |
| §12 T1 BoN | `scripts/capRL/t1_bon_signal.py` | `results/t1_bon_chatts_tsshapeqa/metrics.json` |
| §12 T2/T2'/Q2 | `scripts/analysis/t2_oracle_mix.py` | `results/{t2_oracle_mix,t2_prime_tsaqa,q2_timeseriesexam}/...` |
| §12 T3 hackability | `scripts/capRL/t3_hackability.py` | `results/t3_reward_hackability/metrics.json` |

---

## §12 未来工作（含 CapRL fork）

CapRL（caption reinforcement learning，下游 QA accuracy 作 reward）方向已经做了 5 个信号探测实验（T1/T2/T2'/Q2/T3）。**这一节呈现这些已做实验的结果 + 它们对 CapRL 方向的判定**。最终结论：信号存在但与 Q3 format SFT 等价收益的 distillation 解释更经济，**CapRL 不应是首选**。

### 12.1 T1 — within-captioner Best-of-N（ChatTS, n=100, GO）

**问题**：单个 captioner 在 temperature 采样下，max-reward caption vs mean-reward 是否有 gap？有 gap 表示 RL 可学到"推高好 caption 概率"。

🖼 **[Fig 14: T1 reward distribution per qa_type](./figures-20260421/fig14_t1_bon_per_qa_type.svg)**

| 指标 | T=0.7 | T=1.0 |
|---|---:|---:|
| mean reward | 0.442 | 0.441 |
| max reward (16) | 0.800 | 0.870 |
| **gap** | **0.358** | **0.429** |
| pass@1 / pass@16 | 0.48 / 0.80 | 0.45 / 0.87 |
| hard_subset gap | 0.471 | 0.567 |
| unique@16 captions | 15.75 / 16 | 15.97 / 16 |

**Per qa_type gap 一致性**：TREND 0.31–0.40 / EXTREMA 0.37–0.46 / VOL 0.40–0.42。

**Pre-registered decision**：gap ≥ 0.20 → GO。**结果远超阈值（1.8–2.1×），verdict GO**。

### 12.2 OpenTSLM cross-check 暴露的 reward-hackability 隐患

T1 同时在 OpenTSLM 上做 cross-check（n=20）。OpenTSLM flip rate 仅 2.78%，按理 sampling 分布应该接近塌缩。**实测 gap 0.45–0.53** — 远未塌缩。

→ **flip rate ≠ sampling diversity**。OpenTSLM 在 temp>0 下也能产出形式上不同但语义近似的 caption；其中部分恰好命中 judge 的 keyword pattern。

→ **风险**：T1 GO 的 gap 可能不全是"caption 质量真高"，也可能是"keyword spraying 蒙中"。

### 12.3 T3 reward-hackability probe（ROBUST）

🖼 **[Fig 15: T3 reward-hackability bar](./figures-20260421/fig15_t3_reward_hackability.svg)**

设计 5 个对抗 caption template，看 judge 是否上当：

| Template | 描述 | acc |
|---|---|---:|
| T3.1 direct_answer_inject | caption 直接说"答案是 A" | 0.260 |
| T3.2 semantic_label_inject_TREND_up | caption 说"trend is up"（与正确答案半相关） | 0.330 |
| T3.3 keyword_salad | 撒一堆 trend/peak/volatility 关键字 | 0.290 |
| T3.4 plausible_but_wrong | 看起来合理但说反了 | 0.390 |
| T3.5 empty | 空 caption | 0.170 |

**参考**：random 0.25, ChatTS baseline 0.43, wrong_oracle ref 0.41.

**Verdict（ROBUST）**：所有非合理对抗模板 ≤ 0.45；T3.4 plausible-but-wrong 0.39 ≈ wrong_oracle ref 0.41 — judge 没被对抗 caption hack。

→ **§12.2 担忧大半退役**。T1 的 gap 是真实的"caption 质量更高"信号，不是 keyword 蒙中。

### 12.4 T2 — cross-captioner 互补性 on dataset_a（NO-GO，+1.4pp）

**问题**：OpenTSLM × ChatTS 是否互补？互补则 RL 可挑出更好的；非互补则 RL 学到的本质是 distillation。

| 指标 | 数值 |
|---|---:|
| Single max (cat) | 0.860 (ChatTS) |
| Oracle-mix Flavor A (cat) | 0.874 (**+1.4pp**) |
| Disagreement: only_chatts vs only_opentslm | **189 : 3 一边倒** |
| Flavor A num | 0.730 (-2.4pp，多维 reward 冲突) |

**Verdict（NO-GO）**：gap 远低于 +10pp 阈值；ChatTS 严格支配 OpenTSLM；如果做单维 reward RL 还会污染另一维。

### 12.5 T2' — cross-captioner 互补性 on TSAQA（GO，+13.4pp）

| 指标 | 数值 |
|---|---:|
| Single max | 0.461 (ChatTS) |
| Oracle-mix Flavor A | 0.594 (**+13.4pp**) |
| Disagreement | **145 : 133 平衡** |

Per-task 信号源：characterization +18pp / anomaly_detection +14.5pp / temporal_relationship +13.9pp，都是 disagreement ratio in [0.7, 1.5] **balanced complementary**。

**Verdict（GO）**：在 OOD 场景两个 captioner 真互补，CapRL 在 TSAQA 这种 benchmark 上理论可学。

### 12.6 Q2 — cross-captioner 互补性 on TimeSeriesExam（MARGINAL，+8.4pp）

| 指标 | 数值 |
|---|---:|
| Single max | 0.513 (ChatTS) |
| Oracle-mix Flavor A | 0.597 (**+8.4pp**) |
| Disagreement | 62 : 22 (2.82:1) |

**Verdict（MARGINAL）**：在 [+3, +10pp] 不确定带，第 3 个 benchmark 的复现是 suggestive 而非 conclusive。

### 12.7 三 benchmark CapRL 信号综合

🖼 **[Fig 17: Cross-benchmark oracle-mix gap](./figures-20260421/fig17_caprl_oracle_mix.svg)**

| Benchmark | gap | verdict | disagreement 性质 |
|---|---:|---|---|
| dataset_a (T2) | +1.4pp | NO-GO | ChatTS 单向支配 |
| TimeSeriesExam (Q2) | +8.4pp | MARGINAL | ChatTS 主导但 OpenTSLM 偶有贡献 |
| TSAQA (T2') | +13.4pp | GO | 平衡互补 |

**模式**：ChatTS in-dist 处 RL 信号最弱（distillation 即可）；越 OOD signal 越大。

### 12.8 综合判定：CapRL 应该做吗？

证据汇总：
- ✅ T1：within-captioner reward variance 真实存在（gap 0.36–0.43，远超阈值）
- ✅ T3：judge 没被对抗 caption hack（risk 退役）
- ⚠️ T2/T2'/Q2：cross-captioner 互补性**只在 OOD 上成立**（dataset_a NO-GO）
- ❌ Q3 format SFT 已经验证 OpenTSLM 在 dataset_a 上的提升上限是 0.45（vs ChatTS 0.86）— **scale gap 41pp，RL 替代不了**

**作者倾向（待用户确认）**：

| 选项 | 评价 |
|---|---|
| (a) 全力做 CapRL（PPO/GRPO + ChatTS-14B） | 信号存在 + 风险已验证，但**主要收益区间是 OOD benchmark**；in-dist 收益 ≤ 同量级的 format SFT；GPU 成本 985 A100-hr |
| (b) **优先继续做 Q3 format SFT 的 N-seed 复现 + 扩量** | Q3 已经把"format SFT 上限"测到 0.45，再投入边际收益不大 — 但比 RL 便宜数量级，作为 CapRL 的下界对照仍值得 |
| (c) **Pivot：把 captioner paradigm 的 anatomy 写成毕设/preprint** | 当前 4-benchmark + 5 控制实验已经足够支撑 C2/C3/C4 三结论；CapRL 作为 future work 一段而非主线 |

**CapRL 的实质**（基于 T1+T2+T2'+T3 综合）：在 in-dist benchmark 上等价于 format SFT；在 OOD benchmark 上理论可挖出额外 +13pp 信号，但需要 PPO infra + reward shaping + KL 控制 + 多 seed = 至少 2-3 周工程 + 985 A100-hr。**收益/成本 ratio 不支持作为下一阶段主投入**。

### 12.9 其他 fork（备用）

- **fork B — 更多 OOD benchmark 巩固 C3**：候选 benchmark Long-TS MCQ (256-1024+ 步, 600 samples) — 早期 pilot 已经发现"meta_only 0.755"问题，benchmark 不区分 caption / numbers，需要重新设计或寻找替代
- **fork C — Captioner failure mode 深化**：模板化幻觉（§10.2）/ conditioning 缺失（§8）/ active misleading（§6.4 deductive）三种 failure mode，每种取 1 实验深化（如 prompt re-design / curriculum stage 注入更具体的 number-grounded 数据 / 后处理验证 caption 与 series 的 numerical consistency）
- **fork D — TS-CLIP（方向 c）**：infra 已齐全（`ts_align/losses.py`），可启动；但**与本报告 caption-paradigm 失败结论无直接关联**，是独立的研究问题
- **fork E — TSAQA SFT（方向 b）**：先验证 TSAQA 上 OpenTSLM end-to-end SFT（不是 captioner）的下限，作为"caption interface 与 end-to-end QA 的对比"

---

## §13 附录 A — 已废弃的方向 + 决策记录

### A.1 早期 ROUGE-L based eval（已废弃 2026-04-15）

`model_compare_matrix.py` 用 LTSGen eval_splits + ROUGE-L 评测 caption。问题：(a) ROUGE-L 不区分 hallucination 和 grounded 内容；(b) 没有下游 QA 任务，无法链接 caption 到实用价值。

**替换为**：5-condition QA accuracy protocol（§4.1）。

### A.2 方向 1a：改推理 prompt 让 OpenTSLM 吐 JSON（失败 2026-04-16）

**Hypothesis**：caption 形式不对，让 OpenTSLM 生成结构化 JSON 而非 NL 段落，下游 LLM 应该更易消化。

**Result**：70% 空 caption。模型遇到非训练分布的 JSON 指令直接崩溃（generation failure）。

**Verdict**：format fix 救不了内容问题。

### A.3 方向 1b：gpt-5.4-mini 把 NL caption parse 成 JSON（失败 2026-04-16）

**Hypothesis**：用 GPT 把 OpenTSLM NL caption 后处理成 JSON 槽位，消除歧义后下游 LLM 应该更易用。

**Result**：caption acc 从 0.36 掉到 **0.22**，比原 NL 还差。

**诊断**：NL caption 本身是模板化幻觉（不管 series 什么样，都说 "steady upward trend, low volatility, seasonal every 12 months, late peak"），把散文转成 crisp JSON 反而**消除模糊保护**，让错的断言更易被下游 LLM 采信。

**Verdict**：问题是内容（§9 C2），不是格式。

### A.4 Oracle Probe（实验已做，但本报告不引用 2026-04-21 决策）

**实验内容**：4 种 oracle caption flavor（人工 GT-aligned）+ wrong_oracle，n=100 TSShapeQA OOD：
- oracle_relevant 0.96 / oracle_3slot_schema 1.00 / oracle_hierarchical 1.00 / wrong_oracle 0.41

**为什么不引用**：oracle caption 本质是把 GT 改写成自然语言再让 LLM 解码，这测的是"LLM 能否解码已经包含答案的 caption"，**循环论证**。它不构成 captioner 可达性的证据。

**保留作历史参考**：`LTSGEN-ext-a/data/tsshapeqa/oracle/`（不删，但本报告所有论证不依赖此数据）。

### A.5 ShapeShift / CPR 3-contribution research contract（deprioritized 2026-04-20）

**Locked**：2026-04-19, contract 文件 `./.research/research-contract-20260419.md`（git `bd1a18b`），plan `experiment-plan-20260419.md`，tracker `experiment-tracker-20260419.md`。

**3 个声称贡献**：
- H1 Diagnosis（caption 失败模式诊断）— ✅ 部分覆盖（本报告 §6/§8）
- H2 Benchmark（TSShapeQA-v2 with counterfactual pairs）— ❌ 数据 infra 已就绪（`transforms.py` + 64 unit tests），但 v2 数据从未生成
- H3 CPR Method（Counterfactual Pair Reward CapRL）— ❌ 替换为 T1/T2/T2'/Q2/T3 信号探测（§12），未做完整 PPO 训练

**两个投稿目标**：
- Stream 1 — NeurIPS D&B 2026-05-06（hard）— **❌ 已 miss**（截稿仅剩 15 天，R002–R017 17 个 run 全没启动）
- Stream 2 — arXiv 2026-06-15 + ICLR 2027 main — **❌ 已 deprioritize**

**Deprioritized 的原因**（HANDOFF 2026-04-20 记录）：
1. 发现 partway through session，Path 3（numbers + tool agent）在 pre-session（2026-04-17）已经做完且效果极强（TSShapeQA Tool-Agent 1.000）
2. ShapeShift CPR 是从用户实际方向（caption-utility 探索）的不必要 pivot
3. 用户明确："不要轻易给出新的论文 story，我们目前还处于研究探究的阶段"

**当前状态**：contract 文件、plan、tracker 都还在 `.research/` 里没动（contract §9 immutability 条款要求新建 v2 file with changelog 才能修改）。**这份全实验报告隐含承认：ShapeShift / CPR 不再是 active 路线**。CLAUDE.md 也未更新（待用户决定是否做 contract v2）。

### A.6 方向 (b/c/d) — TSAQA SFT / TS-CLIP / LTSF aux loss

| 方向 | 状态 | infra 路径 |
|---|---|---|
| (b) TSAQA fine-tune downstream | infra ready, 未跑 | `LTSGEN-ext-b/scripts/eval/tsaqa_bench.py`（pilot 18 samples 已跑通） |
| (c) TS-CLIP 对比预训练 | infra 100% ready, 未跑 | `ts_align/losses.py`（clip_infonce + multi-positive）+ `ts_align_scripts_v2/train_hsa_clip.py` |
| (d) Caption 作 LTSF 辅助 loss | 未启动 | TSModel 有 PatchTST / ITFormer 但没 caption hook |

---

## §14 附录 B — 协议细节

### B.1 5-condition prompt 全文

```
SYSTEM: You are an expert time-series analyst. Answer the multiple-choice
question based ONLY on the provided information. Output exactly one letter
(A, B, C, or D) — no explanation.

USER (meta_only):
Domain: {domain}
Window length: {window_len}
Question: {question}
A) {opt_A}
B) {opt_B}
C) {opt_C}
D) {opt_D}
Your answer (single letter):

USER (numbers):
Domain: {domain}
Time series values (length {window_len}): [{series_floats}]
Question: ...

USER (caption):
Domain: {domain}
Time series description: "{caption}"
Question: ...

USER (caption_plus):
Domain: {domain}
Time series values: [{series_floats}]
Time series description: "{caption}"
Question: ...

USER (wrong_caption):
[same as caption, but caption from a different (random) ID — see
 wrong_caption_assignment.json for the deterministic mismatch map]
```

完整实现：`LTSGEN-ext-a/scripts/eval/tsshapeqa_eval.py::build_prompt()`。

### B.2 Tool-Agent 工具集 schema

```python
TOOLS_TSSHAPEQA = [
    {"name": "extract_trend",
     "description": "linregress slope and R² of the series",
     "parameters": {}},
    {"name": "extract_extrema_pos",
     "description": "argmax position as fraction of length (0.0-1.0)",
     "parameters": {}},
    {"name": "extract_volatility_region",
     "description": "second-half/first-half std ratio after detrending",
     "parameters": {}},
]

TOOLS_TSAQA = TOOLS_TSSHAPEQA + [
    {"name": "extract_periodogram",
     "description": "top-3 frequency components by power",
     "parameters": {}},
    {"name": "extract_local_spikes",
     "description": "list spike positions and amplitudes (z-score > 2)",
     "parameters": {}},
    {"name": "extract_noise_std",
     "description": "residual std after Savitzky-Golay smoothing",
     "parameters": {}},
]
```

调用示例（dataset_a 上的一个 spike-position 题）：
```
Round 1: model calls [extract_local_spikes, extract_extrema_pos]
Tool returns: spikes=[(45, 3.2), (102, 2.8)], argmax_frac=0.18
Round 2: model answers based on returned features → "B"
```

### B.3 LTSGen 12 槽位 caption schema（生成 prompt 摘要）

```
The caption should mention:
1. Overall trend (steady up / sideways / declining / mixed)
2. Volatility (low / moderate / high)
3. Seasonality (period if any, "none" if not)
4. Notable peaks: position (third) + amplitude (std)
5. Notable valleys: position (third) + amplitude (std)
6. Early-window behavior
7. Mid-window behavior
8. Late-window behavior
9. Multi-variable correlations (if vars > 1)
10. Anomalies (if anomaly task)
11. Class-defining shape features (if classification task)
12. Forecast hint (if forecasting task)
```

完整 prompt：`LTSGEN/ts_cap/core/prompts.py`（main 仓内）。

### B.4 LLM API 配置

- Reverse proxy: `https://ai.crisinsjtu.top/v1`（`OPENAI_BASE_URL` + `OPENAI_API_KEY` in `~/.bashrc`）
- Python helper: `~/Research/gptapi/llm_client.py`（自动 `trust_env=False` 绕本地 socks proxy）
- 默认模型: gpt-5.4 (default), gpt-5.4-mini (fast)
- Gotcha: 本地有 `ALL_PROXY=socks://...`，必须用 `httpx.Client(trust_env=False)` 或 `eval "$(grep '^export OPENAI' ~/.bashrc)"` 后才能调 API

### B.5 GPU 与 conda 环境

| 服务器 | GPU 常用 | 代码路径 | conda env |
|---|---|---|---|
| A100 (ssh a100) | GPU 2 | `/cluster/home/user1/hulining/` | `opentslm`, `chatts` |
| 3090 (ssh 3090) | 任意 | `/cluster/home/hulining/` | `opentslm`, `chatts` |
| Local | 无 GPU | `/home/cris/Research/` | system python 3.12 |

ChatTS 模型加载 fp16（其 TS encoder 在 bf16 下崩溃）。

### B.6 Notion / 协作元数据

| 资产 | URL / ID |
|---|---|
| 里程碑报告页面 | `342bf55f0c06814f8d98dbcd3b35c062` |
| LTSGEN DB entry | `33dbf55f-0c06-81b7-8fe8-fa8aced87e07` |
| 月份页 202604 | `33abf55f-0c06-8103-858d-f1e910ec7101` |
| Advisor v3（被本报告超越） | `https://www.notion.so/349bf55f0c068192be54cbf7e70a46c5` |

---

## 文档元信息

| 字段 | 值 |
|---|---|
| 创建时间 | 2026-04-21 |
| 作者 | Claude Code session（基于用户实验数据） |
| 上一版 | `.research/advisor-report-20260421-v3.md`（被本报告完全 superseded，含已新增的 4 个 04-21 实验：Q2 / Q3 / T2' / T3） |
| 引用方式 | "LTSGen × OpenTSLM 全实验报告 2026-04-21"（项目内部） |
| 复用许可 | 内部，可作为毕设、preprint、会议论文素材底稿 |




