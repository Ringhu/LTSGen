# ChatTS-14B 验证实验 — 最终结果与论文叙事重写

**Date:** 2026-04-20 18:30 CST
**Compute used:** A100 GPU2，5 阶段全部完成约 **2 小时实际墙钟**（含 SCP、模型加载、推理、eval）
**对手紧逼程度:** 我之前估的"R1 50% 概率"完全错。实际是 **R3 中等改善** + **R2 部分成立**——既不是路线本质死、也不是简单方法 bug，是**scale 起作用，但天花板未及**。

---

## 1. 实验设计

| 维度 | 我们的 OpenTSLM | 对照 ChatTS-14B |
|---|---|---|
| Team | 我们复现 Stanford 论文 | 字节跳动独立团队 |
| LLM scale | Qwen3-**4B** | 自研 **14B**（3.5×） |
| TS encoder | Chronos-2 (frozen) | 自研 TS encoder（同 paradigm） |
| Bridge | Flamingo cross-attention | TS embedding 注入 LLM input |
| 训练数据 | LTSGen 55k 合成 caption | Evol-Instruct **百万级**合成 caption + QA |
| Paradigm | synthetic-caption SFT | **同** paradigm |

**保持一致**：
- TSShapeQA-v1 数据完全一样（OOD 800 + in-dist 300）
- Conditioning ablation 36 个样本完全一样（共用 filter_meta.json）
- Eval judge 都是 gpt-5.4-mini
- prompt template 都问同 3 件事（trend / extrema / volatility）

**所有差异都集中在"实现"侧**：scale + 数据规模 + 训练数据风格。

---

## 2. 主结果（一张表汇总两个 split + 4 个对手）

### 2.1 5-condition downstream QA acc（gpt-5.4-mini judge）

| Split | Source | meta_only | numbers | **caption** | caption_plus | wrong_caption |
|---|---|---:|---:|---:|---:|---:|
| **OOD (n=800)** | OpenTSLM-Flamingo (4B) | 0.335 | 0.554 | 0.335 | 0.463 | 0.338 |
| **OOD (n=800)** | **ChatTS-14B** | 0.338 | 0.536 | **0.529** | 0.532 | 0.370 |
| OOD | Tool-Agent (gpt-5.4) | — | — | — | — | — |
| OOD | **Tool-Agent baseline** | — | — | — | — | **1.000** |
| **in-dist (n=300)** | OpenTSLM-Flamingo (4B) | 0.337 | 0.597 | 0.350 | 0.517 | 0.310 |
| **in-dist (n=300)** | **ChatTS-14B** | 0.337 | 0.600 | **0.533** | 0.533 | 0.340 |
| in-dist | Tool-Agent (gpt-5.4) | — | — | — | — | **1.000** |

**核心发现**：
- ChatTS caption **追平 numbers**（OOD gap < 1pp）；in-dist 仍差 7pp
- ChatTS caption **远超 wrong_caption** +16-19pp（OpenTSLM 是 0pp）
- ChatTS caption **远超 meta_only** +19-20pp
- **caption + numbers 没有进一步加成**（caption 已涵盖 numbers 的关键信息）
- **Tool-Agent 仍是天花板**（1.000）—— 60 行 numpy 仍战胜 14B + 百万合成数据

### 2.2 Per-qa-type 任务对称性

| Split | qa_type | numbers | ChatTS caption | Δ |
|---|---|---:|---:|---:|
| OOD | TREND | 0.502 | 0.431 | -7pp |
| OOD | EXTREMA_POS | 0.528 | **0.625** | **+10pp ✅** |
| OOD | VOLATILITY_REGION | 0.579 | 0.530 | -5pp |
| in-dist | TREND | 0.510 | 0.500 | -1pp |
| in-dist | EXTREMA_POS | 0.500 | **0.630** | **+13pp ✅** |
| in-dist | VOLATILITY_REGION | 0.790 | 0.470 | **-32pp ⚠️** |

**Caption 在 EXTREMA 上 BEAT numbers！** Volatility 上输得最惨。Trend 基本持平。
**含义**：caption 不是单调好或单调坏；它在**需要"阅读理解"位置/形态特征**的任务上有独特优势，在**需要"统计计算"波动**的任务上输给数字。

### 2.3 Conditioning Ablation 翻转率（Phase 1）

| Transform | OpenTSLM-Flamingo | **ChatTS-14B** | Δ |
|---|---:|---:|---:|
| time_reversal (n=22) | 4.5% | **68.18%** | **+63.7pp 🔥** |
| variance_injection (n=14) | 0.0% | 21.43% | +21.4pp |
| **Overall (n=36)** | **2.78%** | **50.0%** | **+47.2pp** |

**caption 字面不变率**（衡量是否在用模板）：
- OpenTSLM time_reversal 反转后 **50%** caption 一字不变
- ChatTS time_reversal 反转后 **5%** caption 一字不变（改写率 95%）

**ChatTS 真在 condition on input**，只是仍未到 oracle 96% 那个理论上界。

---

## 3. 实验解读

### 3.1 之前的强声明被部分推翻

我们 PROBE_DECISION_2026-04-17 写的：
> "OpenTSLM 当前 caption 几乎完全不 condition on input"
> "interface 可行但 OpenTSLM 实现塌缩，救它需要架构 + 数据 + loss 三改"

ChatTS 数据**部分推翻**这个判断：
- ❌ "caption 路线本质上不行" —— 错。**14B + Evol-Instruct 让 caption 可用**（追平 numbers）
- ❌ "我们 OpenTSLM 实现的失败可以推广到所有 SFT-on-synthetic-caption" —— 错。**ChatTS 是 counterexample**
- ✅ "interface 上界很高（oracle 96-100%）" —— **仍正确**（无论何种 captioner）
- ✅ "Tool-Agent 比所有 captioner 都强" —— **仍正确**（1.000 vs ChatTS 0.53）

### 3.2 Refined 三层 interface 等级图

ChatTS 数据让我们能**清晰画出 caption 路线的三个 tier**：

```
Tier 0: meta_only (LLM 先验)              acc 0.34   flip 0%
   ↓ +scale=4B + LTSGen synthetic
Tier 1: OpenTSLM-Flamingo caption         acc 0.34   flip 2.78%
   ↓ +scale=14B + Evol-Instruct
Tier 2: ChatTS-14B caption                acc 0.53   flip 50%
   ↓ + RL on QA-accuracy reward (CapRL)         (UNTESTED)
Tier 2.5?: CPR-trained captioner           ?
   ↓ + structured grounding (oracle ceiling)
Tier 3: Oracle caption                    acc 0.96-1.00   flip ~100%

Parallel track:
Tier ★: Tool-Agent (no captioner)         acc 1.00   flip-irrelevant
```

### 3.3 任务对称性是新发现

这是 ChatTS 实验意外暴露的：**caption 在不同 qa_type 上能力不均**。

- **EXTREMA-POS**：caption > numbers + 10-13pp。LLM 容易理解"peak at position X" 这种叙事性 GPS 信息，反而在 raw numbers 里要做 argmax 计算
- **VOLATILITY**：caption < numbers - 5 to -32pp。波动分析需要算方差，叙事描述天然模糊（"first half choppy" 比 "var=0.34 vs 0.21" 信息少）
- **TREND**：基本持平。两种表示都能传递趋势

**含义**：**caption 不是单一信号——它是 "human-readable annotation"，在某些任务结构上 inherently 更适合**。

### 3.4 caption_plus 没有 1+1 > 2 的协同

| Source | numbers | caption | caption_plus | Δ vs 单一最好 |
|---|---:|---:|---:|---:|
| ChatTS OOD | 0.536 | 0.529 | 0.532 | -0.4pp |
| ChatTS in-dist | 0.600 | 0.533 | 0.533 | -7pp |

**caption + numbers 没比单独任一好**。说明：
- 当 caption 已含 EXTREMA 信息，再给数字也没多少新信息可提取
- LLM 没法把两路信号智能融合（直接二选一）

---

## 4. 论文叙事的明确变化

### 旧叙事（PROBE_DECISION 锁定的）
> *Captions Are Not the Interface: Why Raw Numbers + Tools Beat Learned TS-MLLM Captions*

### 新叙事（数据强制要求）
> *Three Tiers of TS-LLM Interface: Synthetic Captions, Scale, and Tools*

或者更激进的：
> *Captions Can Work — But Tools Still Win: A Three-Tier Analysis of TS-LLM Interfaces*

### 新 Story Arc

1. **§3 Diagnosis**：
   - 跨 model family 测 conditioning flip rate（OpenTSLM 4B 2.78% vs ChatTS 14B 50%）
   - 关键发现："synthetic caption SFT 在 4B + 简单数据集合下塌缩；在 14B + Evol-Instruct 下部分恢复"
   - oracle ceiling 无论 captioner 强弱都是 96-100% — interface 本身一直可行
2. **§4 Benchmark TSShapeQA**：3 + 1 qa_types，OOD 800 + in-dist 300（已有，不动）
3. **§5 Tier Analysis**（新章节，原 method section 改）：
   - 表 1：5-condition 跨 captioner（OpenTSLM / ChatTS / Oracle）
   - 表 2：Tool-Agent 1.000 跨 split + 跨 LLM scale + 跨 distractor
   - **新发现：caption 任务对称性（EXTREMA + / VOL -）**
4. **§6 Discussion**：
   - 三层架构的 generalization
   - **caption RL（CapRL/CPR）作为 future work** 的桥梁，连接 Tier 2 → Tier 2.5
   - Tool-agent 永远是干净 baseline（即使 caption 完美，tool 也省 inference 成本）

---

## 5. 对你研究问题的最终答案

> **"caption 是否能够帮助下游 LLM QA？"**

**直接回答：是的，前提是模型够大、数据够好**。

具体证据：
- ChatTS-14B 的 caption 在 OOD 上做到 0.529，**追平直接给数字（0.536）**
- 在 EXTREMA 子任务上 **超越数字 +10-13pp**
- 这是 14B + Evol-Instruct 数据后的结果；4B + LTSGen 完全做不到（0.335，等同 meta_only）
- **远未触及 oracle 上界**（0.96+），还有 **40+pp gap**

但更关键的"对比 tool-agent"：
- Tool-Agent 1.000，caption 最佳 0.53，**永远输 47pp 以上**
- "更便宜的方案能拿满分"对应"贵且不到 60% 的方案"，**实用论调上 caption 难赢**

---

## 6. 5 条潜在救援路径，根据 Phase 1-3 数据**重排序**

| 路径 | 当前数据支持？ | 预期上限 | 推荐度 |
|---|---|---|---|
| **Scale 救** (4B → 14B → 32B → ?) | ✅ ChatTS 证明 +47pp 可达 | 不知（ChatTS 已是 14B） | 🟡 可能撞天花板 |
| **CapRL/CPR RL 救** | 🟢 ChatTS 50% flip 还有 50pp 可填 | 接近 oracle 96% | 🔥 最有 paper 潜力 |
| **Caption + Tool 混合** | 🟢 caption 在 EXTREMA 上更强，可能 LLM 自适应路由 | 比纯 tool 略好？ | 🟡 待测 |
| **多模型 ensemble** | ❌ 没必要（tool 已 1.0） | 1.000 | ❌ 无价值 |
| **Long-TS 推 caption 优势** | ❌ 当前 256-512 步 caption 已能达 0.53 | 不知 | 🟡 future |

---

## 7. 立刻能做的 3 件事

### A. **改写 Stream 1 论文叙事**（D2-D3，2 天）
- §3 diagnosis 章节加 ChatTS 跨模型对比表
- §5 tier analysis 章节扩展（caption 任务对称性）
- 把 NeurIPS D&B 论文从"caption 不行"改成"三层 interface 对比 + caption 在大模型下的有限 work + tool-agent 仍是 baseline 之王"

### B. **跑 CPR pilot（D4-D7，4 天）**
- 在 ChatTS-14B（不是我们的 OpenTSLM）上跑 CapRL-style RL
- pilot 目标：把 ChatTS conditioning flip 从 50% 推到 70%+
- 如果 work，就是论文的 §6 future work 实证；如果不 work，仍能写"我们尝试了"

### C. **caption + tool 混合实验**（D5-D6，2 天）
- 给 GPT 同时提供 ChatTS caption + tool-call 选项
- 看它何时调 tool / 何时信 caption
- 如果出现"按任务自适应"，是论文的 bonus

---

## 8. 资产清单

新增（今天 2026-04-20）：
- `chatts_validation/chatts_smoke.py` (A100)
- `chatts_validation/chatts_caption_gen.py` (A100)
- `chatts_validation/captions/conditioning_{original,reversed,variance_injected}.jsonl` (A100, 各 36 条)
- `chatts_validation/captions/tsshapeqa_v1_chatts.jsonl` (A100, 800 条)
- `chatts_validation/captions/tsshapeqa_v1_indist_chatts.jsonl` (A100, 300 条)
- `LTSGEN-ext-a/data/tsshapeqa/conditioning_chatts/` (本地, parsed + flip_rate.json)
- `LTSGEN-ext-a/data/tsshapeqa/tsshapeqa_v1{,_indist}_chatts.jsonl` (本地)
- `LTSGEN-ext-a/results/tsshapeqa_v1_{ood,indist}_chatts/metrics.json` (本地)

---

**一句话总结**：ChatTS 数据**升级了我们的科学叙事**——caption 在足够 scale 下确实能达到 numbers 水平，但仍输给 tool-agent 47pp。论文从"caption 不行"变成"三层 interface 对比 + tools 仍是赢家"，故事更丰富、更难被 reviewer 攻击。
