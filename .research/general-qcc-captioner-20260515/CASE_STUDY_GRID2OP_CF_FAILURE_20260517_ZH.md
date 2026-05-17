# Case Study: Grid2Op 反事实 QCC 失败机制

时间范围：2026-05-16 至 2026-05-17  
项目方向：General QCC, question-conditioned evidence captioning for medium-horizon TS-QA  
当前状态：`not_converged`, selected recipe: `None`  
核心问题：Grid2Op 上的 QCC 模型已经能在部分 non-CF 和 lead-lag 任务上学习到可用模式，但 counterfactual 任务仍然出现系统性 label collapse。最近两天的实验说明，问题不能简化为“反事实样本数不够”或“某个 architecture 不够强”，更像是 CF target evidence 本身没有迫使模型学习 factual-vs-intervention 的比较关系。

关联 artifact：

- Tracker: `.research/general-qcc-captioner-20260515/ARCHITECTURE_SEARCH_TRACKER_20260515.md`
- Corrected gate summary: `.research/general-qcc-captioner-20260515/grid2op_architecture_gate_summary_corrected_20260516/architecture_gate_summary.md`
- v9 failure analysis: `.research/failure-analysis-grid2op-v9-20260517.md`
- AS-043 launch: `.research/general-qcc-captioner-20260515/AS043_CF_UNIQUE_CAPPED_LAUNCH_20260517.md`
- AS-043 result: `.research/general-qcc-captioner-20260515/AS043_CF_UNIQUE_CAPPED_RESULT_20260517.md`
- AS-043 summary: `.research/general-qcc-captioner-20260515/grid2op_architecture_gate_summary_as043_20260517/as043_summary.md`

## 结论先行

这两天的主要结论不是“找到了最佳模型”，而是定位到了一个更具体的失败机制：

1. `local_gated_qprefix + CE` 在 Grid2Op adaptation 上仍是目前最可用的训练路径之一，但不能直接定为最终 recipe。
2. 仅靠调整 CF 与 non-CF 数据比例，不能同时稳定 counterfactual、lead-lag 和普通 non-CF 任务。
3. v9 把 CF 每类样本从 8 增加到 12，没有修复 CF，反而把 CF total 拉到 `0.1852`。
4. AS-043 去掉 rare-label replacement 的重复采样后，overall 和 non-CF 有改善，但 CF total 仍是 `0.1852`，说明“重复采样导致 label prior”只解释了一部分现象。
5. 主要问题更可能在 CF evidence caption 的目标形式：当前 caption 太接近最终答案短语，模型学到的是 canonical effect phrase，而不是 factual trace 和 intervention trace 的差分比较。
6. 下一轮应该优先做 CF target repair，而不是继续 ratio tuning、直接上 SCL、或者继续 v9 curriculum。

换句话说，当前研究问题出在“反事实证据的语言接口不够可验证、不够比较式”，而不是单纯出在模型容量、训练步数或 CF 样本数量。

<details>
<summary>1. 研究问题是什么</summary>

General QCC 的目标不是让模型直接从时间序列里输出答案，而是让模型在给定时间序列窗口和下游问题后，生成一段短的自然语言 evidence caption。这段 caption 应该包含回答问题所需的证据，并且能被 verifier 或 QA evaluator 检查。

在 Grid2Op broad tasks 中，当前任务族大致包括：

- mean stress
- overload exposure
- peak stress
- lead-lag
- counterfactual mean stress
- counterfactual overload exposure
- counterfactual peak stress

前几类任务主要考察统计、极值、趋势、滞后关系等。counterfactual 任务则要求模型理解 intervention 前后的变化，例如干预后压力是否升高、过载暴露是否降低、峰值压力变化方向是什么。

这里的关键难点是：counterfactual evidence caption 不能只是说“更高”或“更低”。它必须表达：

- factual 状态是什么；
- intervention 状态是什么；
- 二者差值或方向关系是什么；
- 这个差异为什么支持某个答案。

最近两天的实验显示，现有 CF caption 目标没有足够强地表达这种比较结构。模型容易把某一类问题映射到一个常见答案短语，而不是根据 trace 做 factual-vs-intervention comparison。

</details>

<details>
<summary>2. 最近两天实际做了什么</summary>

## 2026-05-16: 重新校准架构搜索结果

首先整理并修正了 Grid2Op architecture gate 的对比结果，重点不是看单个 dev/test 数字，而是同时看：

- dev/test/dev+test accuracy；
- CF total；
- lead-lag；
- non-CF macro；
- empty generation；
- SCL train margin 和 heldout QA 是否一致。

关键对比：

| Run | 数据/训练设置 | dev+test | CF total | lead-lag | non-CF macro | 判断 |
|---|---:|---:|---:|---:|---:|---|
| `v6_cf8_ce` | CF 每类 8, CE | `0.4681` | `0.5556` | `0.2308` | `0.4567` | CF 好一些，但 lead-lag 崩 |
| `v8_cf8_noncf256_ce` | CF 每类 8, non-CF 256, CE | `0.5021` | `0.4259` | `0.9615` | `0.5120` | overall 最好，但 CF retention 下降 |
| `v6_cf8_scl` | v6 + SCL | `0.4255` | `0.3704` | `0.0385` | `0.4327` | train margin 好，heldout QA 变差 |
| `v6_cf8_task_gated_ce` | task-gated architecture | `0.4213` | `0.4630` | `0.0385` | `0.4159` | architecture 负结果 |

这个阶段得到的判断是：`local_gated_qprefix + CE` 比 task-gated 和当前 SCL 更稳，但 ratio tradeoff 仍然没有解决。v8 能把 lead-lag 拉起来，却不能充分保持 CF。

## 2026-05-17: v9 failure analysis 和替代 reviewer 路线

v9 的设计是 `cf12_noncf256`，试图在保留 v8 non-CF/lead-lag 能力的同时，通过增加 CF 每类样本数恢复 CF。

结果是负的：

| Run | dev | test | dev+test | CF total | lead-lag | non-CF macro | Gate status |
|---|---:|---:|---:|---:|---:|---:|---|
| `v9_cf12_noncf256_ce` | `0.4596` | `0.4766` | `0.4681` | `0.1852` | `0.9615` | `0.5048` | `cf_not_sample_count` |

原计划需要 GPT-Pro 做正式 failure analysis。由于执行路线卡住，改用替代 reviewer 路线：先由我做一次结构化 review，再把结论写入 `.research/failure-analysis-grid2op-v9-20260517.md`，解除“不能启动后续实验”的 blocker。

替代 review 的主要结论：

- v9 的 CF 失败不是随机噪声，而是系统性 label collapse。
- 增加 CF 样本数没有改善，说明“样本少”不是充分解释。
- 训练集中部分低频 label 通过 replacement 被重复采样，可能制造了 label prior。
- 但更深的问题是 CF target caption 太像答案标签，缺少明确的 factual/intervention 对比证据。

基于这个 review，选择 AS-043 作为下一轮诊断，而不是直接启动 AS-034 curriculum 或 AS-035 SCL。

## 2026-05-17: AS-043 rare-label unique-capped diagnostic

AS-043 的问题设定：

> 如果 v9 的 CF collapse 主要来自 rare-label replacement 重复采样，那么把 CF 每类样本 cap 在 unique source rows 上，应该能明显恢复 CF total。

AS-043 保持 v9 风格的 `non_cf_count=256` 和 requested `cf_per_label=12`，但新增 `--cap_at_unique`，避免低频 CF label 被重复扩增。

实现改动：

- 修改 `scripts/generate/build_grid2op_adaptation_v6_cf_contrastive.py`
- 新增参数 `--cap_at_unique`
- 默认行为不变，只有 AS-043 显式开启该参数

AS-043 最终结论是负/部分支持：

- overall 和 non-CF macro 改善；
- lead-lag 维持高；
- 但 CF total 仍是 `0.1852`，没有达到预设 `>=0.35` 的诊断成功线；
- rare-label replacement 只解释了部分 collapse，不是主因。

</details>

<details>
<summary>3. 最近两天构造的数据</summary>

## v9: `cf12_noncf256`

用途：测试“增加 CF 每类样本数是否能在 v8 non-CF/lead-lag 配比下恢复 CF”。

核心设置：

- CF requested per label: 12
- non-CF count: 256
- 训练目标：Grid2Op adaptation, `local_gated_qprefix + CE`
- 结果：CF total 掉到 `0.1852`

暴露出的问题：

- 部分 rare CF label 的 unique source rows 不足，例如 `lower overload exposure` 和 `lower after intervention`。
- replacement sampling 可能让少数 label 被重复出现，形成训练 prior。
- heldout 上这些低方向 label 并不一定出现，导致模型在 dev/test 上输出错误的 canonical label。

## AS-034: curriculum stage2 数据，已构造但未训练

路径：

`.research/general-qcc-captioner-20260515/grid2op_curriculum_stage2_v1/grid2op_stage2_from_v9_gridonly_cf108_noncf256`

数据事实：

- total train rows: 364
- grid non-CF rows: 256
- grid CF rows: 108
- schema pass
- train/heldout overlap: 0
- answer-like captions: 0

状态：只构造，未训练。

没有启动的原因：v9 failure analysis 尚未完成时，直接 curriculum continuation 会把错误的 CF target prior 继续强化。即使训练成功，也难以解释是 curriculum 有效还是 target/data bug 被放大。

## AS-035: matched SCL hard negatives，已构造但未训练

路径：

`.research/general-qcc-captioner-20260515/grid2op_adaptation_v9_ratio/grid2op_adapt_cf12_noncf256/grid2op_adapt_cf12_noncf256_train_evidence_hard_negatives.jsonl`

数据事实：

- records: 1782
- negatives: 2686
- rows without negatives: 0
- wrong-answer-label negatives: 0
- schema gate pass

状态：只构造，未训练。

没有启动的原因：此前 v6 SCL 已经出现“train hard-negative margin 很强，但 heldout QA 下降”的现象。v9 CE 本身不是可信 recipe，在这种基础上继续 SCL 可能只是优化错误的目标形式。

## AS-043: `cf12cap_noncf256` unique-capped 数据

远端数据路径：

`/cluster/home/user1/hulining/LTSGEN/.research/general-qcc-captioner-20260515/grid2op_adaptation_v10_cf_unique_capped/grid2op_adapt_cf12cap_noncf256`

构造命令：

```bash
python3 scripts/generate/build_grid2op_adaptation_v6_cf_contrastive.py \
  --src_root .research/general-qcc-captioner-20260515/grid2op_adaptation_v5_cf_compact \
  --out_root .research/general-qcc-captioner-20260515/grid2op_adaptation_v10_cf_unique_capped \
  --source_run_name grid2op_adapt_128 \
  --run_name grid2op_adapt_cf12cap_noncf256 \
  --cf_per_label 12 \
  --non_cf_count 256 \
  --seed 46 \
  --format_version grid2op_adaptation_v10_cf_unique_capped \
  --cap_at_unique
```

数据事实：

| Item | Value |
|---|---:|
| train rows | 1773 |
| grid non-CF rows | 256 |
| grid CF rows | 99 |
| requested CF per label | 12 |
| `lower after intervention` used unique rows | 9 |
| `lower overload exposure` used unique rows | 6 |
| train/heldout overlap | 0 |
| train base/heldout base overlap | 0 |
| duplicate train ids | 0 |
| answer-like captions | 0 |

这个数据集直接回答一个诊断问题：如果 v9 失败主要来自 replacement duplication，AS-043 应该恢复 CF。实际没有恢复，所以 replacement duplication 不是主因。

</details>

<details>
<summary>4. 最近两天涉及的训练模型</summary>

## 已训练或已评估的主要模型

| Model/run | 数据 | Architecture/loss | 状态 | 关键结果 |
|---|---|---|---|---|
| `v8_cf8_noncf256_ce` | Grid2Op adaptation v8 | `local_gated_qprefix + CE`, Qwen3-4B frozen path | 已训练，作为 corrected gate 参照 | dev+test `0.5021`, CF `0.4259`, lead-lag `0.9615`, non-CF `0.5120` |
| `v9_cf12_noncf256_ce` | Grid2Op adaptation v9 | `local_gated_qprefix + CE`, Qwen3-4B frozen path | 已训练，失败分析对象 | dev+test `0.4681`, CF `0.1852`, lead-lag `0.9615`, non-CF `0.5048` |
| `as043_cf12cap_noncf256_ce` | Grid2Op adaptation v10 unique-capped | `local_gated_qprefix + CE`, Qwen3-4B frozen path | 已训练，诊断实验 | dev+test `0.5000`, CF `0.1852`, lead-lag `0.9615`, non-CF `0.5409` |

## AS-043 训练细节

远端 run dir：

`/cluster/home/user1/hulining/LTSGEN/.research/general-qcc-captioner-20260515/grid2op_adaptation_v10_cf_unique_capped/grid2op_adapt_cf12cap_noncf256/tsrlm_grid2op_adapt_cf12cap_noncf256_local_gated_qprefix_ce_qwen3_4b`

训练配置和日志摘要：

| Item | Value |
|---|---:|
| GPU | A100 GPU0 |
| tmux session | `ltsgen_as043_cf12cap_20260517` |
| epochs | 5 |
| train rows | 1773 |
| train runtime | 2733 sec |
| train loss | 0.2736 |
| final eval loss | 0.2926 |
| empty generation on dev/test | 0 |

AS-043 说明训练本身没有明显工程失败：loss 正常下降，生成不是空输出，lead-lag 和 non-CF 也能保持。但 CF 仍然 collapse，因此问题更像是目标和监督信号不对，而不是训练脚本坏了。

## 已准备但没有训练的模型路线

| Planned run | 数据 | 没有启动的原因 |
|---|---|---|
| AS-034 curriculum continuation | `grid2op_stage2_from_v9_gridonly_cf108_noncf256` | v9 target failure 未解释前，continuation 可能强化错误 prior |
| AS-035 matched SCL | v9 hard negatives | 旧 SCL 已显示 train margin 与 heldout QA 脱钩，v9 CE 又不是可信 base |

</details>

<details>
<summary>5. 失败现象具体是什么</summary>

v9 和 AS-043 的 CF 失败不是“偶尔答错”，而是每个 CF family 内出现非常稳定的短语坍缩。

## v9 的 CF collapse

v9 的整体 CF total 是 `0.1852`。failure matrix 显示模型对不同 counterfactual family 输出固定方向的 effect phrase：

- counterfactual mean stress: 倾向输出 `lower after intervention`
- counterfactual overload exposure: 倾向输出 `lower overload exposure`
- counterfactual peak stress: 倾向输出 `larger upward spike`

这类输出看起来像“学到了一个答案模板”，而不是读出了 factual 与 intervention trace 的差分。

## AS-043 的 CF collapse

AS-043 去掉了 replacement duplication，但 CF total 仍是 `0.1852`。collapse 模式发生了变化，但没有消失：

| CF family | AS-043 behavior | Accuracy |
|---|---|---:|
| `grid_counterfactual_mean_stress` | 几乎都预测 `higher after intervention` | `0.5000` |
| `grid_counterfactual_overload_exposure` | 几乎都预测 `lower overload exposure` | `0.0000` |
| `grid_counterfactual_peak_stress` | 几乎都预测 `larger downward dip` | `0.0000` |

这个结果很关键：如果 replacement duplication 是主因，那么 unique-capped 后应该显著恢复 CF。但实际只是 mean-stress 从一个 collapse phrase 换到另一个 collapse phrase，并部分命中；overload 和 peak 仍然完全失败。

因此，AS-043 支持一个更强的判断：模型没有稳定学习 CF comparison，只是在不同数据分布下换了一个 canonical CF phrase。

</details>

<details>
<summary>6. 问题到底出在哪里</summary>

## 问题 1: CF caption 目标太像答案短语

当前 compact CF evidence 往往把重点压缩到最终 effect phrase，例如“干预后更高/更低”“过载暴露降低/没有实质变化”。这对 QA evaluator 很方便，但对训练 captioner 不够好。

模型可以通过语言 prior 或训练集 label frequency 猜出一个常见短语，而不需要真正表达：

- factual trace 的统计状态；
- intervention trace 的统计状态；
- 二者的差值；
- 差值相对 threshold 或 answer option 的关系。

这违背了 General QCC 的初衷。QCC caption 应该是 answer-supporting evidence，而不是 answer-label paraphrase。

## 问题 2: ratio tuning 在 CF 和 lead-lag 之间制造 tradeoff

v6、v8、v9、AS-043 的对比显示：

- v6 `cf8` 可以让 CF total 到 `0.5556`，但 lead-lag 只有 `0.2308`。
- v8 `cf8_noncf256` 可以让 lead-lag 到 `0.9615`，non-CF macro 到 `0.5120`，但 CF 降到 `0.4259`。
- v9 `cf12_noncf256` 试图加 CF，结果 CF 进一步降到 `0.1852`。
- AS-043 修正 rare-label duplication 后，lead-lag 和 non-CF 更好，但 CF 仍是 `0.1852`。

这说明继续调 CF/non-CF 比例不会自然收敛到一个稳定 recipe。比例变化会改变模型偏好的 phrase prior，但没有迫使它学会 CF comparison。

## 问题 3: rare-label replacement 是局部问题，不是主因

v9 failure analysis 发现某些 low-direction label 的 unique rows 不足，replacement sampling 可能造成重复暴露。AS-043 正是为了验证这一点。

AS-043 的结果是：

- low-frequency duplication 被去掉；
- mean-stress 的 collapse 方向改变，并部分改善；
- overload 和 peak 仍然完全 collapse；
- CF total 没有提升。

因此 rare-label replacement 可以解释“为什么 v9 某些方向特别容易被预测”，但不能解释“为什么模型整体不学 CF comparison”。

## 问题 4: SCL 当前不是优先修复点

SCL 的 train hard-negative 指标看起来很好，例如 v6 SCL 中 positive win rate 达到 `1.0`，mean margin 达到 `2.7325`。但 heldout QA 下降到 `0.4255`，lead-lag 只有 `0.0385`。

这说明当前 hard-negative/SCL 目标与最终 QA 指标没有可靠对齐。若 CF target 本身仍是答案短语式，SCL 可能只是更强地分离一些训练内文本模式，而不是提升真实 evidence grounding。

## 问题 5: architecture 不是最近两天的主 blocker

task-gated 负结果和 local-gated 的相对稳定性说明，architecture 仍然重要，但最近两天的主要瓶颈不在“再换一个 gating module”。

当前更合理的顺序是：

1. 先修 CF target evidence，让 supervision 变成 comparison evidence；
2. 再用同一个 `local_gated_qprefix + CE` 做最小对照；
3. 如果 CF 恢复，再重新比较 qprefix、hybrid、local_gated；
4. 最后才考虑 SCL 或 curriculum。

</details>

<details>
<summary>7. 为什么这不是一个成功结果</summary>

AS-043 的 dev+test 是 `0.5000`，看起来接近 v8 的 `0.5021`，non-CF macro 还更高。但它不能被选为最终 recipe，原因是：

- 预设诊断成功线要求 CF total `>=0.35`，AS-043 只有 `0.1852`；
- overload exposure CF accuracy 是 `0.0`；
- peak stress CF accuracy 是 `0.0`；
- CF failure matrix 显示系统性 phrase collapse；
- 改善主要来自 non-CF，而不是反事实能力恢复。

因此 AS-043 的正确结论是：

> unique-capped sampling 没有解决 CF；ratio-only tuning 应该停止；下一步必须修 CF target evidence。

不能把 AS-043 包装成“总体精度恢复，所以模型可用”。对于 General QCC 论文，counterfactual 是体现 verifiable evidence 和 simulator-derived QA 价值的关键任务之一。如果 CF 不能稳定，当前 Grid2Op branch 还不能支撑方法 claim。

</details>

<details>
<summary>8. 下一轮实验应该怎么做</summary>

推荐下一轮是 AS-044: CF comparison-evidence target repair。

核心改动不是换模型，而是改 CF caption target：

当前问题形式偏向：

> The intervention leads to lower overload exposure.

下一轮应该改成比较式 evidence：

> In the factual rollout, overload exposure is concentrated around line X during the later window. Under the intervention, the same window has fewer overloaded steps and lower maximum loading. This supports a lower overload exposure outcome.

具体要求：

- 保持自然语言 QCC，不引入 inference-time executor；
- caption 中显式写 factual summary；
- caption 中显式写 intervention summary；
- caption 中写 signed difference 或方向比较；
- 避免只输出 answer label 的同义改写；
- CE-only 先跑，不先叠 SCL；
- 使用 `local_gated_qprefix` 作为最小对照 architecture；
- 与 v8/v9/AS-043 在同一 heldout 上比较。

建议 gate：

| Metric | Minimum expected direction |
|---|---|
| CF total | 明显高于 `0.1852`，至少先过 `0.35` |
| lead-lag | 不应掉回 v6/v7 的低水平 |
| non-CF macro | 不应显著低于 `0.49` |
| empty generation | 仍应为 0 |
| CF family matrix | 不应再出现单 family 固定输出一个 phrase |

如果 AS-044 仍失败，则应考虑更强的机制诊断：

- 检查 CF trace 特征本身是否区分度不足；
- 检查 heldout label balance 和 train/heldout support；
- 加 deterministic CF feature slots 作为 auxiliary supervision；
- 重新定义 CF task，使 caption 可被 rule verifier 逐项检查；
- 或者将 Grid2Op CF 从主方法指标降级为 diagnostic benchmark，而不是主 claim 支柱。

</details>

## 当前给论文/项目的影响

这两天的结果对论文方向有一个清晰影响：General QCC 仍然是合理问题，但当前 Grid2Op branch 还没有找到能支撑 claim 的最终训练 recipe。

可以保留的结论：

- Generic captions 对 TS-QA 不稳定；
- Oracle question-conditioned evidence 很强；
- `local_gated_qprefix + CE` 可以在 Grid2Op 上学习到一部分 non-CF 和 lead-lag evidence；
- SCL 的 train margin 不能直接代表 heldout QA；
- 反事实任务暴露了 QCC evidence 是否真正 grounding 的核心问题。

不能声称的结论：

- 不能声称当前 QCC 模型已经解决 Grid2Op broad tasks；
- 不能声称 v9 或 AS-043 是 final recipe；
- 不能声称增加 CF 样本数可以修复 counterfactual；
- 不能声称 SCL 已经验证有效；
- 不能把 `dev+test ~= 0.50` 当成方法成功，因为 CF family 仍然系统性失败。

下一步最小可执行路线：

1. 构造 AS-044 CF comparison-evidence targets。
2. 先跑 `local_gated_qprefix + CE`。
3. 用同一套 dev/test/failure matrix 与 v8、v9、AS-043 对比。
4. 只有当 CF family 不再 collapse，再讨论 architecture rerank、SCL 或 curriculum。

