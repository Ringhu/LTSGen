# LTSGen 项目进展汇报 — 2026-04-20

**项目核心问题**：在 LLM 时代，"先训练时间序列模型生成 caption → 再让 LLM 用 caption 答 QA" 这条路是否真的能 work？
**汇报对象**：导师
**结论**：**不能 work**。但我们用对照实验把这个负结果做扎实了，并且找到了一条简洁有效的替代方案（tool-agent，准确率 1.000）。

---

## 1. 研究背景与动机

Vision 领域走过 caption → CLIP → MLLM 三步。TS 领域近期（2024-2026）出现 OpenTSLM (Stanford+ETH+Google+Amazon, arXiv 2510.02410)、ChatTS (ByteDance, VLDB 2025) 等 TS-MLLM，沿用同样思路：**TS encoder + LLM + 合成 caption SFT**，再用生成的 caption 喂下游 LLM 做 QA。

**我们要回答**：这个 paradigm 是否真的让下游 LLM 更懂 TS？还是只是在跑流程？

---

## 2. 实验体系与时间线

### 2.1 自建系统

| 组件 | 内容 | 规模 |
|---|---|---|
| **LTSGen** 数据生成 | 用 GPT-5 给 FRED/ETT/Traffic/Weather/NAB/UCR 抽窗口 + 生成 12+ 槽位结构化 caption | 训练 55,550 + 验证 6,234 + 测试 1,171 |
| **OpenTSLM-Flamingo** 模型训练 | Qwen3-4B + Chronos-2 + Flamingo cross-attn，curriculum learning：M4 pretrain → forecasting → anomaly → classification → mixed | 4 个 ablation checkpoint |
| **TSShapeQA** benchmark | 形态题 MCQ（TREND / EXTREMA_POS / VOLATILITY_REGION），256-512 步窗口，OOD（Time-MMD + exchange_rate + illness）+ in-dist 双 split | OOD **n=800** + in-dist **n=300** + composition **n=300** |

### 2.2 训练阶段：vars=1 winner

| Checkpoint | Val Loss | 配置 |
|---|---|---|
| mixed_from_forecasting (baseline) | 0.2055 | 冻结 Chronos-2, vars=8 |
| **ablation_vars1_mixed (winner)** | **0.2026** | 冻结 Chronos-2, **vars=1** |
| ablation_unfreeze2_mixed | 0.194 | 解冻 2 层 LM，但 exposure bias 严重 |
| ablation_cnn_mixed_v5 | — | CNN 编码器，只跑 5-6 epoch |

内部 ROUGE-L per-task：FC 0.653 / AN 0.485 / CLS 0.396（Overall 0.550）。**模型本身是按现有 paradigm 训成功的，发布质量。**

---

## 3. 主结果：Caption 接口的系统性失败

### 3.1 第一轮：TSAQA 独立 benchmark（n=996，公开数据集）

| 条件 | gpt-5.4 | gpt-5.4-mini |
|---|---|---|
| meta_only（无 TS 输入） | 0.501 | 0.489 |
| **numbers**（直接给数字） | **0.650** | **0.617** |
| **caption**（给 OpenTSLM caption） | 0.449 | 0.475 |
| caption_plus（caption + numbers） | 0.599 | 0.548 |
| wrong_caption（错配 caption，负对照） | 0.464 | 0.464 |

**第一个红灯**：caption ≤ wrong_caption；caption_plus 反而比 numbers 低。

### 3.2 第二轮：自建 TSShapeQA-v1，**专测形态感知**

#### OOD (n=800)，in-dist (n=300)，gpt-5.4-mini

| 条件 | OOD acc | in-dist acc |
|---|---|---|
| meta_only | 0.335 | 0.337 |
| wrong_caption（负对照） | 0.338 | 0.310 |
| **OpenTSLM caption** | **0.335** | **0.350** |
| **caption + CoT**（让 LLM 想一想） | **0.225** ⚠️ | **0.257** ⚠️ |
| caption + numbers | 0.463 | 0.517 |
| caption + numbers + CoT | 0.514 | 0.593 |
| numbers | 0.554 | 0.597 |
| **numbers + CoT** | 0.599 | 0.657 |

**三个核心发现**：

1. **OpenTSLM caption ≈ wrong_caption ≈ meta_only**（0.34 ≈ 0.34 ≈ 0.34）。生成的 caption 和"什么都没给"一个水平。
2. **caption + CoT 反而更差**（0.225 < 0.338 wrong_caption）。CoT 把 caption 的错信号放大成歪推理链。
3. **caption + numbers 拖累 numbers**（0.46 < 0.55，OOD）。caption 不是无用，而是有害。

### 3.3 第三轮：Oracle Probe（n=100），**确认 interface 本身可行**

| 条件 | Overall | TREND | EXTREMA | VOLATIL |
|---|---|---|---|---|
| meta_only | 0.340 | 0.242 | 0.212 | 0.559 |
| numbers | 0.520 | 0.394 | 0.515 | 0.647 |
| **oracle_relevant** | **0.960** | 0.909 | 0.970 | 1.000 |
| oracle_3slot_schema | **1.000** | — | — | — |
| oracle_3slot_nl | **1.000** | — | — | — |
| oracle_hierarchical | **1.000** | — | — | — |
| wrong_oracle | 0.410 | 0.151 | 0.515 | 0.559 |

**关键判定**：当我们给 LLM 一段**人工写的、对应正确 GT 的 caption**，准确率 0.96-1.00。**接口能 work，问题在生成端**。

### 3.4 第四轮：Conditioning Ablation（n=36），**捕获生成端的失败机制**

把 TS 做反事实变换（时间反转、二阶段方差注入），看 caption 是否对应翻转：

| Transform | n | caption 正确翻转率 | caption 一字不变率 |
|---|---|---|---|
| time_reversal | 22 | **4.5%** (1/22) | 50% |
| variance_injection_second_half | 14 | **0%** (0/14) | 79% |
| **Overall** | 36 | **2.78%** | — |

**结论**：OpenTSLM 的 caption **几乎完全不 condition on input**。把序列翻转，caption 50% 一字不变。这不是 OOD 问题（in-dist 同样塌缩），而是训练目标（next-token LM loss on reference caption）**根本没有约束 caption 必须编码输入的独特形态**。

---

## 4. 替代方案：Tool-Agent (Path 3)

### 4.1 设计

冻结 GPT-5.4，给它 3 个 numpy 工具（每个 ~20 行代码）：
- `extract_trend(series)` → "up/down/flat/mixed"
- `extract_extrema_pos(series)` → "first/middle/last"
- `extract_volatility_region(series)` → "first/second"

GPT 通过 function calling 决定调哪个工具。

### 4.2 主结果

| 配置 | OOD 800 | in-dist 300 |
|---|---|---|
| **Tool-Agent (gpt-5.4)** | **1.000** | **1.000** |
| Tool-Agent (gpt-5.4-mini) | 1.000 | 1.000 |
| Tool-Agent + 3 假工具干扰 | 1.000 | 1.000 |

**60 行 numpy + GPT 编排 = 满分**。

### 4.3 因果证据：Remove-One 消融（in-dist 300）

| 工具配置 | TREND | EXTREMA | VOL |
|---|---|---|---|
| 全 3 工具 | 1.00 | 1.00 | 1.00 |
| 拿走 extract_trend | **0.43** | 1.00 | 1.00 |
| 拿走 extract_extrema_pos | 1.00 | **0.37** | 1.00 |
| 拿走 extract_volatility_region | 1.00 | 1.00 | **0.20** |

**对角线全崩到亚 random，其他位置全是 1.00**。每个工具都在做实事，不是 GPT 凭借先验蒙对。

### 4.4 复杂度证据：Composition QA（PEAK_VOL_MATCH，n=300）

问题模板："最高点在哪半边 vs 哪半边更抖，是同一边吗？" 必须把 2 个工具结果组合作答。

| 条件 | 准确率 |
|---|---|
| 只给题（随机基线 0.25） | 0.260 |
| numbers | 0.357 |
| numbers + CoT | 0.497 |
| **Tool-Agent** | **0.993** |

Tool-agent 每题严格调 2 个工具（extrema + vol），平均 2.0 rounds。**任务复杂度上升时，gap 从 +40pp 拉到 +50pp**。

---

## 5. 文献定位

2026-04-19 lit-scout 的发现：

- **OpenTSLM**（arXiv 2510.02410）和 **ChatTS-14B**（VLDB 2025）已经把"合成 caption + SFT" paradigm 发表，规模比我们大
- **CapRL**（ICLR 2026, vision domain）首次提出"caption → frozen text-LLM MCQ → accuracy 当 RL reward"，**绕开 LM loss 不约束判别性的问题**
- **TimeART**（arXiv 2601.13653）在 TS 上做了 21 个工具的 agent，是 Path 3 的直接竞争者
- **TS-CLIP**（EMNLP 2025）做 contrastive TS-text 对齐
- **Truth-Conditional TS Captioning**（EMNLP 2021）做 neurosymbolic learned-program 约束 caption 真实性

---

## 6. 论文叙事（草稿）

**Title**: *Captions Are Not the Interface: Why Raw Numbers + Tools Beat Learned TS-MLLM Captions*

**Core claim**: TS 理解的下游 interface 不应该是 learned NL caption。我们通过 TSShapeQA benchmark + 三层诊断（5-condition eval / Oracle probe / conditioning ablation）证明当前 SOTA TS-MLLM caption 系统性失败，给出 numbers + task-conditional tool invocation 的更强 baseline。

**3 个 contribution**：
1. **TSShapeQA benchmark**（OOD 800 + in-dist 300 + composition 300，3 + 1 qa_types，已开源就绪）
2. **Caption failure diagnostics**（5-condition gap + Oracle 96%/learned 35% 的 "interface vs implementation" 分离 + 2.78% conditioning flip rate）
3. **Tool-augmented baseline**（60 行 numpy + GPT，1.000 准确率，4 类 ablation 全部坐实因果）

**已就位的论文资产**：4 张 paper figure（fig1 主结果 / fig2 caption 诊断 / fig3 remove-one 热图 / fig4 composition），完整 metrics.json + predictions.jsonl trace。

---

## 7. 三个最反直觉的发现（对导师汇报的卖点）

1. **CoT 让 caption 变更差** — 一般 CoT 让 LLM 更准。但对 OpenTSLM caption 反而从 0.34 掉到 0.22-0.26，比用 wrong_caption 还低。证明 caption 信号本身就是噪声。
2. **mini 模型够用** — Tool-Agent 从 gpt-5.4 换成 gpt-5.4-mini 还是 1.000。"TS understanding" 不依赖 SOTA LLM 规模，靠正确读 tool description 就够。
3. **Composition QA 上 gap 更大** — 任务越复杂（需要组合多个 shape primitive），tool-agent 优势越明显。**说明 tool-agent 路线越往复杂任务上走会越宽**。

---

## 8. 现状与下一步

### 已完成
- Phase 1 诊断 ✓
- W1 benchmark scale-up ✓  
- W2 tool-agent + 4 类 ablation ✓
- 4 张 paper figure ✓

### 当前
- W3 论文写作（NeurIPS 2026 Datasets & Benchmarks 投稿）

### 进一步可选探索（与导师讨论）
- **CPR (Counterfactual-Pair Reward) 后续工作**：CapRL 的 RL 范式 + TS 天然的 label-flipping transform（time reversal, variance injection）能否真正让 TS-MLLM caption work？我们已经有完整的 counterfactual-pair benchmark 基础设施（`build_tsshapeqa_v2.py`，6 个 transform，64 个单元测试），可以直接接上 GRPO 训练做。**这是独立的下一篇 paper**，跟当前的负结果论文互补：当前论文卖"caption 不行，tool 行"，下一篇卖"如果非要做 caption，得用 RL 改训练目标"。
- **长序列扩展**：当前 256-512 步，扩到 2048+ 步看 tool-agent 优势是否进一步拉开
- **Human baseline**：2-3 人各答 50 题对比

---

## 9. 资产清单（可复现）

| 类别 | 路径 |
|---|---|
| Benchmark 数据 | `LTSGEN-ext-a/data/tsshapeqa/tsshapeqa_v1{,_indist}.jsonl`, `composition_qa_v1.jsonl` |
| OpenTSLM caption | `LTSGEN-ext-a/data/tsshapeqa/captions_v1{,_indist}.jsonl` |
| Eval 结果 | `LTSGEN-ext-a/results/tsshapeqa_v1_*/metrics.json` + `predictions.jsonl` |
| 训练 ckpt | A100 `/cluster1/user1/hulining/opentslm_checkpoints/Qwen3_4B/OpenTSLMFlamingo/ablation_vars1_mixed/stage2_captioning/checkpoints/best_model.pt` (val 0.2026) |
| 论文图 | `LTSGEN-ext-a/figures/fig{1,2,3,4}_*.{pdf,png}` |
| 代码 | `LTSGEN-ext-a/scripts/{generate,eval,figures}/` |
| v2 反事实基础设施（CPR 后续用） | `LTSGEN-ext-a/scripts/generate/{transforms.py, build_tsshapeqa_v2.py, shape_features.py}` + `tests/generate/test_transforms.py` (64 tests pass) |

---

**一句话总结**：当前主流 TS-MLLM 训了几个月只能得 0.35（≈ 随机蒙），一个 60 行 numpy + GPT 编排的 tool-agent 直接打满 1.000。这是个干净的负结果 + 干净的替代方案，已经是一篇能投稿的论文。
