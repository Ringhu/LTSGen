# Public Raw TSQA v4 Hard Candidate Reviewer 2026-05-21

本报告只复审 GPT-5.5 失败的候选 hard case。Reviewer 只判断题目质量和 hard-case 公平性，不改 gold answer。

## Summary

- reviewer model: `gpt-5.5`
- candidates reviewed: `4`
- decision: `{'revise': 4}`
- hard subset eligible: `{'false': 4}`
- problem tags: `{'unclear_event_boundaries': 1, 'ambiguous_thresholds': 3, 'hidden_segmentation': 1, 'not_fair_hard': 1, '事件分段边界不明确': 1, '阈值表述模糊': 1, '隐藏确定性支持槽': 1, '错误可能来自窗口划分歧义': 1, '不适合hard子集': 1, 'persistent_leak_vs_recovery_boundary': 1, 'subjective_close_to_pre_event': 1, 'hidden_deterministic_rule_not_exposed': 1, 'persistent_vs_recovery_boundary_unclear': 1, 'hidden_deterministic_rule': 1, 'post_event_close_to_pre_event_ambiguous': 1}`

## Reviewed Candidates

| ID | Lang | Decision | Eligible | Scores | Risk | Tags | Reason |
|---|---|---|---|---|---|---|---|
| `public_raw_tsqa_v4_00019` | `en` | `revise` | `false` | hard=2, ans=2, thr=2, win=1 | `high` | `unclear_event_boundaries,ambiguous_thresholds,hidden_segmentation,not_fair_hard` | 该题的自然任务表述看起来合理，但公开提示只说明时序覆盖事件前、中、后窗口，并未明确哪些时间点属于 pre/event/post 分段。金标依赖 pre_pressure_mean、event_pressure_mean、post_pressure_mean 和 event_flow_change 等分段统计，若没有公开边界，模型无法可靠复现这些支持槽。此外，“very low”“clearly increases”“close to pre-event”等阈值也未量化，容易导致模型按局部低压或局部流量变化作出不同判断。顶模误判为持续漏水风险，很可能是由于窗口分段和阈值不清，而不是纯粹的时间序列推理难度。因此当前不适合作为 fair hard 样本。 |
| `public_raw_tsqa_v4_00019` | `zh` | `revise` | `false` | hard=1, ans=2, thr=2, win=1 | `high` | `事件分段边界不明确,阈值表述模糊,隐藏确定性支持槽,错误可能来自窗口划分歧义,不适合hard子集` | 该题的自然任务只说明时序覆盖扰动前-中-后窗口并按时间排列，但没有公开给出哪些时间点属于事件前、事件中、事件后。金答案依赖 pre/event/post 均值和 event_flow_change 等确定性支持槽；如果模型不知道分段边界，可能会根据局部水压下降和后续回升判断为“扰动后恢复”，这不是纯粹的时间序列推理难点，而是窗口边界信息不足造成的歧义。此外，“很低”“明显升高”“明显低于”“接近”等阈值没有量化，稳定与恢复之间的判别也容易受主观解释影响。因此该失败不应作为公平 hard case 直接保留。 |
| `public_raw_tsqa_v4_00021` | `en` | `revise` | `false` | hard=2, ans=2, thr=1, win=3 | `high` | `ambiguous_thresholds,persistent_leak_vs_recovery_boundary,subjective_close_to_pre_event,hidden_deterministic_rule_not_exposed` | 该题的自然任务整体合理，变量也基本自包含，但关键判定边界不够清楚。题干使用“very low”“clearly increases”“remains depressed”“close to pre-event”等相对表述，没有给出硬阈值。当前证据中事件后水压 67.46 相比事件前 71.40 只低约 3.94，模型将其理解为“接近事件前水平并恢复”是合理的，并不一定体现真正的时序推理失败。金标 A 来自确定性支持槽，但公开题干没有暴露足够明确的阈值来排除 B，因此失败更可能来自阈值/类别边界歧义，而不是公平的困难时序推理。 |
| `public_raw_tsqa_v4_00021` | `zh` | `revise` | `false` | hard=2, ans=2, thr=1, win=3 | `high` | `ambiguous_thresholds,persistent_vs_recovery_boundary_unclear,hidden_deterministic_rule,post_event_close_to_pre_event_ambiguous` | 该题的自然任务整体自洽，变量也足够，但关键判定边界不清楚。公开题面只说“水压降得很低”“流量明显升高”“事件后水压仍明显低于事件前”“接近事件前水平”，没有给出具体阈值或比例边界。支持摘要中事件后水压均值 67.46 相比事件前 71.4 只低约 4 个单位，模型将其理解为“接近事件前”并选择恢复，是合理的题面解读错误，而不一定是真正的时间序列推理失败。因此该失败主要来自阈值措辞模糊和 persistent leak/recovery 边界不公开，不适合作为 fair hard 保留。 |
