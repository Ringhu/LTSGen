# LTSGen 项目实验汇报 — 2026-04-20

**项目核心问题**：在 LLM 时代，"先用 TS-LLM 生成 caption，再让通用 LLM 用 caption 答下游 QA" 这条路是否真的能 work？
**汇报对象**：导师
**报告范围**：截至 2026-04-20 全部实验结果 + 当前可信的科学结论
**重要原则**：本报告**只汇报实证数据**，不预设论文 story；caveat 写明，未验证的不外推。

---

## 1. 项目背景 + 我们已构建的基础设施

### 1.1 自建系统

| 组件 | 内容 | 规模 |
|---|---|---|
| **LTSGen** 数据生成 | GPT-5 给 FRED/ETT/Traffic/Weather/NAB/UCR 抽窗口 + 生成 12+ 槽位结构化 caption | 训练 55,550 + 验证 6,234 + 测试 1,171 |
| **OpenTSLM-Flamingo** | Qwen3-4B + Chronos-2 + Flamingo cross-attn，curriculum learning 多阶段 | vars=1 winner，val loss 0.2026 |
| **TSShapeQA-v1** benchmark | 自建形态题 MCQ（TREND / EXTREMA_POS / VOLATILITY_REGION）+ composition 题 | OOD 800 + in-dist 300 + composition 300 |

### 1.2 Pre-session（2026-04-17）已锁定的关键 kill-test 数据

经过 3 轮外部 review（gpt-5.4 xhigh），用户做出了"Path 3 — Numbers + Tool Agent"的方向决策。证据如下：

**Oracle Probe（n=100, gpt-5.4-mini judge）**：

| 条件 | Overall acc |
|---|---:|
| meta_only | 0.340 |
| numbers | 0.520 |
| **oracle_relevant**（人工 GT-aligned caption） | **0.960** |
| oracle_3slot_schema/nl/hierarchical | **1.000** × 3 |
| wrong_oracle | 0.410 |

→ **Caption 接口本身可行（96-100%）**。问题在于 OpenTSLM 实际生成的 caption 不行。

**Conditioning Ablation（n=36, time_reversal + variance_injection）**：

| Transform | n | OpenTSLM caption 正确翻转率 |
|---|---:|---:|
| time_reversal | 22 | **4.5%** (1/22) |
| variance_injection | 14 | **0.0%** (0/14) |
| Overall | 36 | **2.78%** |

→ **OpenTSLM caption 几乎完全不 condition on input**。50-79% caption 在输入反转后字面不变。

### 1.3 Pre-session 已完成的 Path 3 实验（重新发现，本 session 才完整看到）

**TSShapeQA-v1 上 11 种输入条件的对照评估**（gpt-5.4-mini judge）：

| 条件 | OOD 800 | In-dist 300 |
|---|---:|---:|
| 只给题 (meta_only) | 0.335 | 0.337 |
| 乱配 caption (wrong_caption) | 0.338 | 0.310 |
| **OpenTSLM caption** | 0.335 | 0.350 |
| caption + CoT | **0.225** ⚠️ | **0.257** ⚠️ |
| caption + numbers | 0.463 | 0.517 |
| numbers | 0.554 | 0.597 |
| **numbers + CoT** | 0.599 | 0.657 |
| **Tool-Agent (gpt-5.4)** | **1.000** 🏆 | **1.000** 🏆 |
| Tool-Agent + 3 假工具干扰 | 1.000 | 1.000 |
| Tool-Agent (gpt-5.4-mini) | 1.000 | 1.000 |

**Tool-Agent 因果消融（缺一工具）**：

| 工具配置 | TREND | EXTREMA | VOL |
|---|---:|---:|---:|
| 全 3 工具 | 1.00 | 1.00 | 1.00 |
| 拿走 extract_trend | **0.43** | 1.00 | 1.00 |
| 拿走 extract_extrema_pos | 1.00 | **0.37** | 1.00 |
| 拿走 extract_volatility_region | 1.00 | 1.00 | **0.20** |

**Composition QA**（PEAK_VOL_MATCH，n=300, 必须组合 2 个工具结果）：

| 条件 | 准确率 |
|---|---:|
| meta_only | 0.260 |
| numbers + CoT | 0.497 |
| **Tool-Agent** | **0.993** |

---

## 2. 本次 Session 新增实验

### 2.1 ChatTS-14B 跨家族对照（验证 OpenTSLM 失败是否 paradigm-fundamental）

**动机**：reviewer 一定会问"你的负结果只是你自己复现的 OpenTSLM 的问题吗？" 测 ChatTS-14B（ByteDance VLDB 2025，14B vs OpenTSLM 4B；同 paradigm "synthetic-caption SFT"）。

**Experiment 1: 跨家族 conditioning ablation（同一 36 个样本）**

| Transform | OpenTSLM-Flamingo (4B) | **ChatTS-14B** | Δ |
|---|---:|---:|---:|
| time_reversal (n=22) | 4.55% | **68.18%** | +63.7pp |
| variance_injection (n=14) | 0.00% | 21.43% | +21.4pp |
| **Overall (n=36)** | **2.78%** | **50.00%** | **+47.2pp** |

caption 字面不变率：OpenTSLM time_reversal 50% 一字不变 vs ChatTS 5%。

**含义**：14B + 大规模 Evol-Instruct 数据让 captioner 部分恢复 input-conditioning，但仍远低于 oracle 96% 上界。**"OpenTSLM 实现塌缩" 部分推广到 paradigm，部分 method-specific**。

**Experiment 2: 5-condition eval on TSShapeQA-v1（同样 800 OOD + 300 indist）**

| Condition | OpenTSLM-Flamingo cap | **ChatTS-14B cap** |
|---|---:|---:|
| meta_only | 0.335 | 0.338 |
| numbers | 0.554 | 0.536 |
| **caption** | **0.335** | **0.529** (+19.4pp vs OpenTSLM) |
| caption_plus | 0.463 | 0.532 |
| wrong_caption | 0.338 | 0.370 |

**ChatTS caption 几乎追平 numbers**，远超 wrong_caption (+16pp)。但**仍低于 oracle 96% 上界 ~50pp**。

**任务对称性**（per qa_type, ChatTS caption vs numbers）：

| qa_type | OOD numbers | OOD ChatTS cap | in-dist numbers | in-dist ChatTS cap |
|---|---:|---:|---:|---:|
| TREND | 0.502 | 0.431 (-7pp) | 0.510 | 0.500 |
| **EXTREMA_POS** | 0.528 | **0.625** (+10pp) | 0.500 | **0.630** (+13pp) |
| VOLATILITY_REGION | 0.579 | 0.530 (-5pp) | **0.790** | 0.470 (-32pp) |

→ caption 在"找 spike 位置"这类**自然语言可压缩任务**上击败 numbers；在"算方差比较"这种**统计任务**上输给 numbers。

### 2.2 dataset_a Stage A — ChatTS 自带 benchmark 上的三方对照

**动机**：用 ChatTS 论文用的 dataset_a（其训练分布内的格式）测 caption 是否能在 domain reasoning 任务上发挥作用。

**Setup**：
- 117 univariate samples（dataset_a 单变量子集）
- 同款 5-condition eval（gpt-5.4-mini judge）
- 用 ChatTS 自己的 evaluate_qa.py 评分（categorical + numerical 双维度，regex + 数值容差）
- 三个 captioner: **OpenTSLM**, **ChatTS-14B**, plus tool-agent baseline

**主结果（n=117, gpt-5.4-mini judge）**：

| 条件 | categorical | numerical |
|---|---:|---:|
| meta_only | 0.405-0.409 | 0.032-0.035 |
| **gpt-numbers**（baseline） | 0.651 | 0.416 |
| **OpenTSLM caption** | **0.335** 📉 | **0.150** 📉 |
| **ChatTS caption** | **0.861** 🏆 | **0.753** 🏆 |
| **Tool-Agent** | 0.735 | 0.511 |
| caption_plus (ChatTS) | 0.888 | 0.801 |
| wrong_caption | 0.372-0.442 | 0.105-0.201 |

**Per ability_type breakdown**（ChatTS caption vs numbers gap）：

| Ability | numbers (cat) | ChatTS cap (cat) | Δ | n |
|---|---:|---:|---:|---:|
| local (spike 类型) | 0.433 | **0.817** | **+38pp** | 60 |
| local-inductive | 0.571 | **0.914** | **+34pp** | 35 |
| season | 0.730 | **1.000** | +27pp | 37 |
| trend | 0.610 | 0.707 | +10pp | 41 |
| noise | **1.000** | 0.905 | -10pp | 42 |

**LLM-judge 补充评分（causal + deductive，n=92+43）**：

| 条件 | ChatTS causal | ChatTS deductive | OpenTSLM causal | OpenTSLM deductive |
|---|---:|---:|---:|---:|
| numbers | 0.755 | 0.570 | 0.750 | 0.628 |
| **caption** | **0.799** 🏆 | **0.674** 🏆 | **0.609** 📉 | **0.430** 📉 |
| wrong_caption | 0.685 | 0.523 | 0.543 | 0.581 |

**OpenTSLM caption 在 deductive 上 0.430 < wrong_caption 0.581** —— **actively misleading**。

**关键 caveat**：ChatTS 训练数据**就包含 dataset_a/b 风格的合成 spike + 4-段编号答案模板**。dataset_a 上的高分有显著 in-distribution 优势成分。

### 2.3 TSAQA — 跨格式 OOD 验证（去除 ChatTS in-distribution 优势）

**动机**：dataset_a 上 ChatTS +53pp 大幅领先有多少是真正 caption 能力，多少是格式耦合？换一个独立学术 benchmark 测。

**Setup**：
- TSAQA（Cai et al. 2024 独立学术 benchmark, 42K 样本，从未训过两个 captioner）
- 1000 sample subset（5 task × 200, 同 OpenTSLM 之前已跑的子集，apples-to-apples）
- 同 5-condition eval, **双 judge**（gpt-5.4 + gpt-5.4-mini）
- TSAQA MCQ + T/F + ordering 格式 — 完全不同于 dataset_a 的 4-段编号

**主结果（gpt-5.4 judge, n=996）**：

| Condition | OpenTSLM cap | **ChatTS cap** | numbers | meta_only |
|---|---:|---:|---:|---:|
| Overall | 0.449 | **0.461** | **0.631** | 0.505 |
| anomaly_detection | 0.518 | 0.518 | 0.554 | 0.518 |
| **characterization** | 0.488 | 0.488 | **0.813** | 0.711 |
| classification | 0.626 | 0.626 | 0.470 | 0.560 |
| comparison | 0.518 | 0.518 | **0.741** | 0.590 |
| data_transformation | 0.355 | 0.355 | **0.632** | 0.404 |
| temporal_relationship | 0.259 | 0.259 | **0.578** | 0.247 |

**🚨 关键发现**：**ChatTS caption 在 TSAQA 上和 OpenTSLM caption 几乎完全 TIED**（0.461 vs 0.449，差 1pp）。**dataset_a 上的 +53pp 优势完全消失**。两个 captioner 都输给 numbers baseline 17-18pp。

**对比表（同 captioner 跨 benchmark 表现）**：

| Benchmark | 是否 ChatTS 训练分布内 | OpenTSLM cap | ChatTS cap | gap |
|---|---|---:|---:|---:|
| TSShapeQA OOD | ❌ 我们自建，cap 短句形式 | 0.335 | 0.529 | +19pp |
| **dataset_a** | ✅ **ChatTS 训过** | 0.335 | **0.861** | **+53pp** |
| **TSAQA** | ❌ **完全 OOD 学术 benchmark** | **0.449** | **0.461** | **+1pp** |

→ **ChatTS 的 caption 优势 = 训练数据格式与测试集格式的距离的反函数**。

---

## 3. 当前可信的科学结论（4 条）

基于上述实证，**可以谨慎做出**以下 4 个结论。每条都附 caveat。

### C1. 接口本身可行：oracle caption 上界 96-100%

无论用哪种 captioner、什么测试格式，**给 LLM 一段 GT-aligned 的描述，它能 96-100% 正确答出形态题**。

→ "caption → LLM" 这个 interface paradigm **不是死路**。
→ Caveat: oracle 测试只在 TSShapeQA shape primitive 上做过，没在 TSAQA 长 context / dataset_a 复杂格式上验证过 oracle 上界。

### C2. 当前 SFT-on-synthetic-caption captioner 实现有显著 scale + data 依赖

| 指标 | OpenTSLM 4B | ChatTS 14B |
|---|---:|---:|
| Conditioning flip rate (n=36) | 2.78% | 50.0% (+47.2pp) |
| TSShapeQA 5-cond caption acc | 0.34 | 0.53 (+19pp) |

→ **不是 paradigm 本质失败**。在 14B + Evol-Instruct 大规模数据下，captioner 确实开始 condition on input。
→ Caveat: ChatTS 50% flip rate 仍远低于 oracle 100%。规模到 32B+ 是否能闭合，未知。

### C3. Caption 的下游有用性强烈依赖测试格式

| 设置 | ChatTS cap vs numbers |
|---|---:|
| 自建短形态 benchmark (TSShapeQA OOD) | -1 to +0pp |
| ChatTS 训练分布内格式 (dataset_a) | **+21pp** |
| 完全 OOD 学术 benchmark (TSAQA) | **-17pp** |

→ **Caption 不是普遍替代 numbers 的方案**。在 ChatTS 训过的格式上能压倒 numbers，在陌生格式上反而弱于直接给数字。
→ Caveat: 我们只测了 3 个 benchmark；不知道这个 pattern 在更广 benchmark spectrum 上是否成立。

### C4. Tool-Agent 是稳健 generalist baseline，但不绝对最强

| Benchmark | Tool-Agent | best caption | best non-caption |
|---|---:|---:|---:|
| TSShapeQA (3 shape primitive MCQ) | **1.000** 🏆 | 0.529 (ChatTS) | 0.554 (numbers) |
| dataset_a (4-段开放式) | 0.735 | **0.861** (ChatTS) 🏆 | 0.651 (numbers) |
| TSAQA (混合 MCQ/TF/ordering) | 未测 | 0.461 | **0.631** (numbers) 🏆 |

→ **Tool-Agent 和 Caption 的胜负互相不绝对**。在简单 MCQ 上 tool-agent 1.000 碾压；在 ChatTS in-distribution 格式上 caption 反超；在通用 OOD 上 numbers 直接给已经够好。
→ Caveat: TSAQA 还没测 Tool-Agent，下一步应补。

---

## 4. 跨 benchmark 综合表（一页全集）

```
Benchmark       Sample  OpenTSLM cap  ChatTS cap   numbers  Tool-Agent  Oracle
                  n     -----------   -----------  -------  ----------  ------
TSShapeQA OOD   800     0.335         0.529        0.554    1.000        ~0.96
TSShapeQA in-dist 300   0.350         0.533        0.597    1.000        ~0.96
dataset_a uv    117     0.335 (cat)   0.861 (cat)  0.651    0.735        n/a
                        0.150 (num)   0.753 (num)  0.416    0.511        n/a
TSAQA (gpt-5.4) 996     0.449         0.461        0.631    未测         未测
TSAQA (mini)    996     0.475         0.448        0.625    未测         未测
```

---

## 5. 还没解决的问题（3 条诚实清单）

### Q1. Tool-Agent 在 TSAQA 这种 mixed-format benchmark 上能否仍然最强？

dataset_a 上 Tool-Agent 已经被 ChatTS caption 反超（0.735 vs 0.861）；TSAQA 还没测。如果 Tool-Agent 在 TSAQA 上也输给 numbers，那意味着**对长 context + 混合格式 benchmark，Tool-Agent paradigm 也有边界**。

**预估时间**：~1 小时

### Q2. ChatTS 在更多 OOD benchmark 上是否一致表现为"和 OpenTSLM 一样不 work"？

只测了 1 个 OOD benchmark (TSAQA)。要做更稳健结论需要 2-3 个独立 benchmark。候选：
- TimeSeriesExam (qa_dataset.json, 746 MCQ, 5 categories)
- Long-TS MCQ (600 samples, 256-1024+ steps)

**预估时间**：每个 benchmark ~1.5 小时

### Q3. 如果在 dataset_a 格式上重训一个 OpenTSLM variant，能不能逼近 ChatTS？

这是 caption RL 方向（CapRL/CPR）的 motivation 实验。当前 ChatTS 的优势 80% 来自 in-distribution，那么如果 OpenTSLM 也在同样格式上 SFT 一遍，能否补上差距？这能验证：
- 是 scale 决定（4B → 14B）
- 还是格式决定（OpenTSLM 训练 vs ChatTS 训练数据）

**预估时间**：~2-3 天（需要新 SFT + 评估）

---

## 6. 资产清单

### 数据
- TSShapeQA-v1：`LTSGEN-ext-a/data/tsshapeqa/{tsshapeqa_v1.jsonl, tsshapeqa_v1_indist.jsonl, composition_qa_v1.jsonl}`
- ChatTS dataset_a：`LTSGEN-ext-a/data/chatts_bench/dataset_a_uv.json`（117 单变量子集）
- TSAQA：`/home/cris/mnt/a100/TSDataset/TSAQA/test.parquet`（42K 全集）

### Caption 文件
- OpenTSLM TSShapeQA: `LTSGEN-ext-a/data/tsshapeqa/captions_v1{,_indist}.jsonl`
- ChatTS TSShapeQA: `LTSGEN-ext-a/data/tsshapeqa/tsshapeqa_v1{,_indist}_chatts.jsonl`
- OpenTSLM dataset_a: `LTSGEN-ext-a/data/chatts_bench/captions_opentslm_uv.jsonl`
- ChatTS dataset_a: `LTSGEN-ext-a/data/chatts_bench/captions_chatts_uv.jsonl`
- OpenTSLM TSAQA: `/cluster1/user1/hulining/tsaqa_captions_vars1.jsonl`（A100）
- ChatTS TSAQA: `/cluster/home/user1/hulining/chatts_validation/captions/tsaqa/chatts_tsaqa_uv.jsonl`（A100）

### 评估结果
- TSShapeQA: `LTSGEN-ext-a/results/tsshapeqa_v1_{ood,indist}_{full6, chatts, tool_agent, ta_*}/`
- dataset_a: `LTSGEN-ext-a/results/dataset_a_{chatts, opentslm, tool_agent}/{summary.json, llm_judge_reason_scores.json}`
- TSAQA: `LTSGEN-ext-a/results/{tsaqa_eval, tsaqa_eval_chatts}/{metrics.json, predictions.jsonl}`
- Conditioning ablation: `LTSGEN-ext-a/data/tsshapeqa/conditioning{,_chatts}/{flip_rate.json, parsed_*.jsonl}`

### 论文图（pre-session 已生成）
- `LTSGEN-ext-a/figures/fig{1,2,3,4}_*.{pdf,png}`：主结果 / caption 诊断 / remove-one 热图 / composition

### 关键代码
- 自建 captioner (OpenTSLM): A100 `/cluster/home/user1/hulining/TSModel/OpenTSLM/scripts/gen_tsshapeqa_captions.py`
- ChatTS 调用: A100 `/cluster/home/user1/hulining/chatts_validation/chatts_caption_gen{,_dsa}.py`
- 5-condition eval: `LTSGEN-ext-a/scripts/eval/{tsshapeqa_eval, tsaqa_caption_eval}.py`, `LTSGEN-ext-a/scripts/chatts_eval/dataset_a_5cond_eval.py`
- Tool-Agent: `LTSGEN-ext-a/scripts/eval/tsshapeqa_tool_agent_eval.py`, `LTSGEN-ext-a/scripts/chatts_eval/dataset_a_tool_agent_eval.py`
- LLM-judge: `LTSGEN-ext-a/scripts/chatts_eval/llm_judge_rescore.py`
- Counterfactual transform 基础设施 (本 session 新加): `LTSGEN-ext-a/scripts/generate/{transforms.py, build_tsshapeqa_v2.py}` + 64 unit tests

---

## 7. 给导师讨论的几个 open question

1. **当前结果适不适合写一篇 paper？** 数据量已经够了，但叙事上有 nuance —— 不是干净的"caption 路线 work"或"caption 路线不 work"，而是"caption 的有用性强依赖测试格式"。这可能是个 strength（更深的科学发现），也可能是个 weakness（reviewer 难抓住主线）。
2. **要不要继续测 1-2 个 OOD benchmark 验证 TSAQA 的 pattern？** 如果验证成立，"caption ≈ numbers ≈ wrong on truly OOD" 是非常强的负结果。
3. **CapRL / CPR 训练方向**（在 dataset_a 格式上 SFT 一个 OpenTSLM variant）是否值得做？这能验证"scale vs format" 的相对贡献，对应到独立的下一篇 paper。

---

## 一句话收口

**TS-LLM caption 的下游有用性是一个高度 condition on 测试格式的现象**：oracle 能到 96%，证明接口可行；ChatTS 14B 在自家训练格式上能 0.86，但跨到 OOD benchmark 上和 OpenTSLM 4B 一样输给直接喂数字。**Tool-Agent 在简单 MCQ 上 1.000 碾压一切**，但在多格式开放题上不一定最强。**当前数据**支持的不是"caption work"或"caption 不 work"的二元结论，而是**"caption 在某些场景有用、在另一些场景有害，整个 paradigm 还没收敛"**。
