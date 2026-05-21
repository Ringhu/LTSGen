# ChatTS-14B 验证实验计划 — 2026-04-20

**目的**：用 ChatTS-14B（ByteDance VLDB 2025）作为**第二个 TS-MLLM 家族**，在我们的 TSShapeQA-v1 + 36 条 conditioning ablation 样本上跑一遍同款诊断。
**核心问题**：当前 caption 失败是 "method-specific"（我们 OpenTSLM 实现的问题）还是 "paradigm-fundamental"（synthetic-caption-SFT paradigm 本身不行）？
**硬件**：A100 GPU2（81GB 全空，已确认 2026-04-20 03:30）
**预计总时长**：**1 天可完成主要诊断；1.5 天含写表和论文集成**

---

## Pre-flight 检查（已完成）

| 项 | 结果 |
|---|---|
| A100 GPU2 free VRAM | **81023 / 81920 MiB** ✓ |
| ChatTS-14B HF cache | `~/.cache/huggingface/hub/models--bytedance-research--ChatTS-14B` 完整 ✓ |
| ChatTS 源码 | `/cluster/home/user1/hulining/TSModel/ChatTS/try_demo.py` 提供 HF 推理模板 ✓ |
| ChatTS API 调用方式 | `AutoProcessor(text=[prompt], timeseries=[ts])` + `model.generate()` ✓ |
| 36 ablation 样本 | `LTSGEN-ext-a/data/tsshapeqa/conditioning/series_{original,reversed,variance_injected}.jsonl` 都在 ✓ |
| TSShapeQA-v1 数据 | OOD 800 + in-dist 300，已 OOD 全跑过 OpenTSLM caption 对照 ✓ |
| Caption 解析器 | `LTSGEN-ext-a/scripts/generate/parse_caption_label.py` 已用于 OpenTSLM ✓ |
| 5-condition eval 脚本 | `LTSGEN-ext-a/scripts/eval/tsshapeqa_eval.py` ✓ |
| Conda env | A100 `chatts` env 已存在（CLAUDE.md 列出）；需验证 transformers 版本兼容 |

**唯一未验证**：ChatTS-14B HF model 的 `trust_remote_code` 加载在 transformers 5.4.0 是否兼容。**Phase 0 第一步就测**。

---

## 实验阶段（按依赖顺序）

### Phase 0 — Smoke：ChatTS 加载 + 单样本生成（**估计 30 分钟**）

**目标**：在 A100 GPU2 上把 ChatTS-14B 跑通，生成一条 caption。

**操作**：
1. SSH A100，进入 `chatts` env
2. 写最小脚本 `scripts/eval/chatts_smoke.py`：
   - 加载 `bytedance-research/ChatTS-14B`（trust_remote_code）
   - 读 `series_original.jsonl` 第一条
   - 用 ChatTS 的 `<ts><ts/>` 格式构造 prompt，问"Briefly describe the trend, peak position, and volatility region of this time series."
   - `model.generate(max_new_tokens=200)`
   - 打印 caption + peak GPU 内存

**通过标准**：
- 无 import 错误（trust_remote_code 兼容）
- 生成出非空 caption
- VRAM ≤ 60 GB（留 20+ GB 给 KV cache）

**风险**：
- transformers 5.4.0 可能与 ChatTS 自定义 modeling 文件冲突 → 退路：用 conda env `chatts` 里的旧 transformers 版本
- ChatTS HF model.generate 的接口可能比 demo_vllm.py 的 vLLM 路径慢得多 → Phase 1 需要给到充足时间

**时间**：30 min（含 60s 模型 cold load + debug）

---

### Phase 1 — Conditioning ablation on ChatTS（**最高 information density，估计 2 小时**）

**目标**：复现 OpenTSLM 的 36 样本 × 3 transform 实验，得到 ChatTS 的 caption flip rate。

**操作**：
1. 写 `scripts/eval/chatts_caption_gen.py`：
   - 输入：jsonl（每行 `{id, series, ...}`）
   - 输出：jsonl（每行 `{id, caption}`）
   - prompt 模板与 OpenTSLM 用过的一致（公平对比）
2. 跑 3 次：
   ```
   python chatts_caption_gen.py --in conditioning/series_original.jsonl    --out chatts_caps/conditioning_original.jsonl
   python chatts_caption_gen.py --in conditioning/series_reversed.jsonl    --out chatts_caps/conditioning_reversed.jsonl  
   python chatts_caption_gen.py --in conditioning/series_variance.jsonl    --out chatts_caps/conditioning_variance.jsonl
   ```
3. 用 `parse_caption_label.py` 解析所有 3 套 ChatTS caption 成 `{trend, peak_position, higher_vol_half}` 标签
4. 用 `run_conditioning_ablation.py --analyse` 计算 flip rate

**预估时长**：
- ChatTS-14B bf16 单样本生成 ~5-10s（200 tok @ 30 tok/s + KV-cache warmup）
- 36 × 3 = 108 次生成 ≈ **15-20 分钟**
- Caption parse via gpt-5.4-mini 调用 108 次 ≈ **5 分钟**
- Flip rate compute ≈ **< 1 分钟**
- **总：30-40 分钟**（保守 2 小时含 debug + GPT API rate limit）

**核心输出**：
```
ChatTS-14B vs OpenTSLM-Flamingo conditioning flip rate
Transform                       | OpenTSLM | ChatTS-14B
time_reversal (n=22)            |   4.5%   |   ?
variance_injection (n=14)       |   0.0%   |   ?
Overall (n=36)                  |   2.78%  |   ?
caption_same_rate (字面不变)    |  ~65%    |   ?
```

**判定**：
- ChatTS flip rate **< 10%** → 强证据 paradigm-fundamental → 当前论文负结果**全 paradigm 立得住**
- ChatTS flip rate **30-60%** → method-specific 但仍未 fix → 论文 story 改成 "scale 帮一点但远不够"
- ChatTS flip rate **> 60%** → 我们 OpenTSLM 实现的问题，论文必须重写

---

### Phase 2 — TSShapeQA-v1 full caption gen（**估计 3-5 小时**）

**目标**：在 ChatTS-14B 上生成 OOD 800 + in-dist 300 = 1100 条 caption。

**操作**：
1. 同样的 `chatts_caption_gen.py` 跑 v1 全集
2. 输出 `chatts_caps/tsshapeqa_v1_ood.jsonl` 和 `chatts_caps/tsshapeqa_v1_indist.jsonl`

**预估时长**：
- 1100 样本 × 7s/样本（含 batching=4-8 加速）= **~2 小时**
- 保守 3-5 小时（首次跑 batching 调优 + vLLM 切换风险）

**优化策略**：
- 如果 HF transformers 推理太慢，切换到 ChatTS 提供的 vLLM 入口（`demo_vllm.py`），速度可提升 5-10×
- vLLM 切换需要：先验证 vLLM 兼容版本（demo_vllm.py 注释说要 vllm==0.6.6.post1）

---

### Phase 3 — 5-condition downstream eval（**估计 1 小时**）

**目标**：用 ChatTS caption 替换 OpenTSLM caption，跑 5 条件评估，对比 acc 是否变化。

**操作**：
1. 用 `tsshapeqa_eval.py`：
   - 5 个条件：meta_only, numbers, **caption (来自 ChatTS)**, caption_plus, **wrong_caption (用同样的 ChatTS caption mismatched)**
   - downstream judge: gpt-5.4-mini（与历史对照保持一致）
   - 输出 `results/tsshapeqa_v1_ood_chatts/metrics.json` 和 `results/tsshapeqa_v1_indist_chatts/metrics.json`

**预估时长**：
- 1100 × 5 = 5500 GPT-5.4-mini API 调用
- concurrency=12 + ~1.5s per call ≈ **15-20 分钟**
- 含 rate limit retry 缓冲 → **45 分钟 - 1 小时**

**核心输出**：
```
Condition         | OpenTSLM OOD | ChatTS-14B OOD | Delta
meta_only         |    0.335     |     0.335*     | ≈ same (no model dep)
numbers           |    0.554     |     0.554*     | ≈ same  
OpenTSLM caption  |    0.335     |       —        | —
ChatTS caption    |       —      |       ?        | < 10pp Δ vs OpenTSLM = paradigm-confirmed
caption_plus      |    0.463     |       ?        | 
wrong_caption     |    0.338     |       ?        |
```
*meta_only / numbers 不依赖 captioner 模型，可直接复用历史数字

---

### Phase 4 — 写表 + 论文 §3 集成（**估计 2-3 小时**）

**目标**：把 ChatTS 数据合并到论文 §3 Diagnosis section。

**操作**：
1. 写 `paper/tables/cross_model_caption_diagnosis.tex`：
   - Table A: caption 5-condition eval 跨模型（OpenTSLM-Flamingo / ChatTS-14B / [可选 OpenTSLM-SoftPrompt]）
   - Table B: conditioning flip rate 跨模型
2. 修改 §3 文案，把 "OpenTSLM caption fails" 升级为 "synthetic-caption-SFT TS-MLLMs fail across model families and scales"
3. Reviewer-proofing 段落：明确写出 "we tested 4B (OpenTSLM-Flamingo) and 14B (ChatTS) — same family of failure across both"

---

### Phase 5（可选）— OpenTSLM-SoftPrompt 对照（**估计 0.5-1 天**）

**目标**：再加一个 architecture variant（同 OpenTSLM 论文的另一种实现）。

**前提**：Stanford 是否公开发布了 SoftPrompt 变体的 checkpoint。**需要先在 HF 上查**。

**如果有**：
- HF `StanfordBDHG/OpenTSLM-SoftPrompt-XX`（猜测路径）
- 重复 Phase 1-3 的所有步骤，n=36 conditioning + n=1100 TSShapeQA
- ~6 小时

**如果没有**：
- 跳过；论文 §3 用 "我们另在 ChatTS-14B 上验证" 的措辞，避免重训
- ~0 小时

**Phase 5 是 nice-to-have，不是 must-run。** 主结果只需 OpenTSLM + ChatTS 两个家族就足够回应 reviewer。

---

## 总时间估算

| 阶段 | 乐观 | 保守 |
|---|---|---|
| Phase 0 smoke | 15 min | 30 min |
| Phase 1 conditioning ablation | 30 min | 2 hr |
| Phase 2 full caption gen | 2 hr | 5 hr |
| Phase 3 5-condition eval | 30 min | 1 hr |
| Phase 4 写表 + 论文集成 | 1.5 hr | 3 hr |
| **共计（不含 Phase 5）** | **~4.5 hr** | **~11.5 hr** |

**实际预期**：**1 天（8 小时）能完成主要诊断 + 论文集成草稿**。如果 Phase 2 用 vLLM 加速，再省 2-3 小时。

---

## GPU 资源占用预估

| 时段 | GPU 占用 | 用途 |
|---|---|---|
| Phase 0 + 1 | A100 GPU2 ~30 GB（14B bf16 + KV cache）, ~3 hr | ChatTS inference |
| Phase 2 | A100 GPU2 ~50 GB（with batching）, ~4 hr | ChatTS full inference |
| Phase 3 | 0 GPU（纯 API） | downstream eval |
| Phase 4 | 0 GPU（写作） | — |

**对其他用户冲击**：仅 GPU2，6-7 小时占用。GPU0 已被占（不冲突），GPU1/3 不动。

---

## 关键脚本清单（新增）

需要写 **2 个新脚本**：

1. `LTSGEN-ext-a/scripts/eval/chatts_smoke.py` — Phase 0 烟雾测试，~30 行
2. `LTSGEN-ext-a/scripts/eval/chatts_caption_gen.py` — Phase 1+2 主推理脚本，~150 行
   - 模仿 `gen_tsshapeqa_captions.py`（A100 上 OpenTSLM 用的那个）
   - 把 OpenTSLM 接口换成 ChatTS 的 `processor + model.generate`
   - 支持 batch + tqdm + 增量 checkpoint（崩了能续）

无需重写：`parse_caption_label.py`、`run_conditioning_ablation.py --analyse`、`tsshapeqa_eval.py` 都直接复用。

---

## 风险与 fallback

| 风险 | 影响 | Fallback |
|---|---|---|
| ChatTS-14B + transformers 5.4.0 不兼容 | Phase 0 阻塞 | 切到 conda env `chatts`（旧 transformers）；或用 vLLM 路径 |
| HF transformers 推理速度太慢（< 10 tok/s） | Phase 2 时间膨胀到 12+ hr | 切到 vLLM (demo_vllm.py 模板) |
| ChatTS prompt 格式 不接受我们的 "describe shape" 问法 | caption 退化或拒答 | 用 ChatTS README 推荐的标准模板，多试 2-3 个 |
| ChatTS caption flip rate > 60% | 推翻当前论文负结果 | 当前论文必须重写 — 但这是科学发现而不是失败 |
| GPU2 被其他人抢占（突发） | Phase 中断 | 切到 GPU1 或 GPU3（也基本空），代价：重启推理 |

---

## Decision points 一览

| 时间点 | 等什么数据 | 决定什么 |
|---|---|---|
| Phase 1 完成（~2.5 hr） | ChatTS conditioning flip rate | 论文叙事是否要改 |
| Phase 3 完成（~7.5 hr） | ChatTS 5-condition acc | Table A 数字定稿 |
| Phase 4 结束（~10 hr） | 论文 §3 草稿 | 是否进入 Phase 5（SoftPrompt 加对照） |

---

## 下一步

**等你确认就开工 Phase 0**。我可以：
1. 写 `chatts_smoke.py` + `chatts_caption_gen.py`，本地测试 import path → 然后 push 到 A100 跑
2. 用 SSHFS mount 操作 A100 上的 ChatTS env

**预计 2026-04-20 EOD 之前完成 Phase 0 + Phase 1**，明天 2026-04-21 完成 Phase 2-4。

整个验证实验**比 CPR pilot 便宜 10×**，**比 NeurIPS D&B 论文写作快 5×**，是论文 attack-proofing 的最划算投资。
