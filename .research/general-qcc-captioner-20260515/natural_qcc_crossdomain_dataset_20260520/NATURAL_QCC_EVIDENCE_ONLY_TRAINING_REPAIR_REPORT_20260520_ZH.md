# Natural QCC Evidence-Only Training Repair Report（2026-05-20）

## 结论

这轮目标是：在不降低当前数据质量的前提下，按已判断的原因逐个修改，并观察训练效果是否提升。

最终结论是：**有小幅正向训练信号，但不是完整方法成功**。最佳配置是 `evidence_only + 5 epochs + max_new_tokens=128`：q-conditioned semantic QA 从 1 epoch 的 `0.0000` 提升到 `0.2308`，同配置 no-question 是 `0.1538`，q-conditioning gap 是 `0.0770`，超过预设 `0.05`。同时 caption quality gate 仍通过。

## 修改与结果

| 修改 | 目的 | 数据质量 | qcond QA | no-question QA | 结论 |
| --- | --- | ---: | ---: | ---: | --- |
| 修复生成后清洗 | 避免 `Answer:` 后证据被截断 | 旧 qcond re-clean quality gate=`True` | `0.0000` | - | 修复格式有效，但不能单独提升 QA |
| evidence-only target | 去掉 `Answer label` 捷径 | target semantic QA=`1.0000`, quality gate=`True` | `0.0000` | `0.0000` | 保住质量，但 1 epoch 不够 |
| 5 epochs + 128 tokens | 排除训练太短/生成太短 | qcond quality gate=`True` | `0.2308` | `0.1538` | 本轮最有效，出现正向 gap |
| qcond prompt 加 options | 检查选项是否是必要条件 | target quality gate=`True` | `0.0769` | `0.1538` | 负向消融，小样本下加 options 没帮助 |

## 数据质量门

- 原始 reviewer-positive 样本仍为 `55` 条，没有扩增低质量样本。
- evidence-only 训练使用 train+dev，共 `42` 条；test eval 为 `13` 条。
- evidence-only target 去掉所有 `Answer label` 后：target semantic QA=`1.0000`，caption quality gate=`True`，answer-label-only rate=`0.0000`。
- options-in-prompt 变体同样保持 target semantic QA=`1.0000` 与 caption quality gate=`True`。

## 最佳 smoke 配置

- run: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_evidence_only_e5_tok128_smoke_qwen3_4b_20260520`
- train rows: `42`
- eval rows: `13`
- semantic QA accuracy: `0.2308`
- empty answer rate: `0.5385`
- caption quality gate: `True`
- evidence-shape rate: `0.9231`
- answer-label-only rate: `0.0769`

对照：

- no-question run: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/tsrlm_natural_qcc_crossdomain_evidence_only_no_question_e5_tok128_smoke_qwen3_4b_20260520`
- no-question semantic QA accuracy: `0.1538`
- qcond minus no-question: `0.0770`
- comparison status: `qconditioning_gap_positive`

## 解释

这说明主要瓶颈不是“问题质量已经无法训练”，而是训练配置太弱、生成长度太短、样本太少。把目标改成 evidence-only 后，模型不会再主要靠答案标签投机；把训练和生成窗口拉长后，它开始生成一部分可被 deterministic semantic bridge 识别的证据。

但结果仍然很弱：test 只有 `13` 条，Grid2Op、Traffic、Water 上仍为 `0.0000`，oracle gap 还很大。因此这只能算 cross-domain smoke-level 正信号，不能宣称 QCC 方法已经成功。

## 下一步

1. 继续保持 evidence-only target，不回到 `Answer label` target。
2. 把 reviewer-positive 样本从 `55` 扩到至少每域、每任务族更均衡的规模。
3. 优先扩充当前 0 分域：Grid2Op、Traffic、Water。
4. 在扩数据前，不建议继续只靠加 options 或改 prompt 堆参数；options-in-prompt 这轮已经是负向消融。
5. 下一轮评估继续同时报告 qcond、no-question、caption quality、semantic QA 和 oracle gap。
