# Natural QCC Expansion GPT-5.5 Review（2026-05-19）

本报告审查扩展候选池的自然语言 QA 草案。Reviewer 只评估自然性、可答性和准确性风险；gold answer 仍来自 deterministic support slots。

## 总览

- input rows: `25`
- reviewed rows: `25`
- model: `gpt-5.5`
- review scope: `{'gpt55_candidate': 25}`
- decision: `{'keep': 25}`
- source: `{'aiopslab_official_v3': 25}`
- risk: `{'low': 25}`
- positive pool by reviewer gate: `25/25`
- reviewer problem tags: `{'变量名略偏数据集化但已定义': 1, '阈值规则已明示': 1}`

## 正例准入规则

正例池只接受：`review_scope == gpt55_candidate`、`decision == keep`、`naturalness_score >= 4`、`answerability_score >= 4`、`accuracy_risk == low`。

| source | positive | candidate |
| --- | ---: | ---: |
| `aiopslab_official_v3` | 25 | 25 |

## 需要处理的样本

| source | task | decision | naturalness | answerability | risk | reason |
| --- | --- | --- | ---: | ---: | --- | --- |
| - | - | - | - | - | - | 全部 candidate 通过 reviewer gate |

## 逐条审查

| source | split | task | scope | decision | naturalness | answerability | risk | question_zh | reason |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| `aiopslab_official_v3` | `dev` | `aiops_official_cross_signal_relation` | `gpt55_candidate` | `keep` | 4 | 5 | `low` | 按绝对相关系数 0.30 作为可用耦合阈值，SRE 在这个事故窗口中应该信任哪种遥测关系？ | 该样例整体像正常的 SRE 遥测判断问题，变量含义清楚，阈值规则、两组相关系数和选项均在题面或证据中给出，不需要额外元数据即可作答。问题略带规则判定风格，但在运维相关性分析场景中合理；证据明确支持两组相关系数均低于 0.30，因此答案可由给定信息确定。 |
| `aiopslab_official_v3` | `dev` | `aiops_official_window_memory` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 按 5% 相对差异规则，这个事故窗口中的服务内存占用是前后相近，还是某一半更重？ | 问题表述自然，像 SRE 在比较事故窗口内存占用的正常分析问题；变量含义清楚，5% 相对差异规则和前后半段均值都在证据中明确给出，选项也与判断目标一致。无需依赖隐藏元数据或内部时间轴。 |
| `aiopslab_official_v3` | `dev` | `aiops_official_cpu_trend` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 这段事故窗口里，服务 CPU 负载是在上升、下降，还是基本平稳？ | 问题表述像正常的运维场景判断题，变量含义清楚，询问 CPU 负载在事故窗口内的总体趋势。证据明确给出起点、终点和波动尺度均约为 0，可直接支持“基本平稳”的选项，不依赖隐藏元数据或未解释阈值。 |
| `aiopslab_official_v3` | `dev` | `aiops_official_network_volatility` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 这个事故窗口中，网络接收速率在哪一段波动最大？ | 问题表述自然，变量含义在场景中已说明，询问网络接收速率在事故窗口早/中/后三段中的波动情况。证据明确给出三段标准差均为 0.00，并说明支持“三段相近”，因此无需额外元数据或隐含阈值即可作答。选项也符合自然决策问题形式。 |
| `aiopslab_official_v3` | `dev` | `aiops_official_memory_extrema` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 把这个事故窗口按时间分成早期、中期和后期后，服务内存工作集的最高点出现在什么位置？ | 问题表述自然，符合 SRE 查看遥测窗口时会提出的判断问题；变量含义清楚，目标变量 x1 明确为内存工作集。证据直接说明最高点约在窗口第 2 步，并位于前段；选项与“早期/中期/后期/无清晰极值”的判断一致，不需要额外元数据或隐含阈值即可回答。 |
| `aiopslab_official_v3` | `test` | `aiops_official_memory_extrema` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 把这个事故窗口按时间分成早期、中期和后期后，服务内存工作集的最高点出现在什么位置？ | 题目表述自然，像 SRE 查看遥测时会提出的定位极值问题；变量含义清楚，目标变量 x1/内存工作集在场景中已解释。问题中的早期、中期、后期与证据中的“窗口前段”一致，证据明确给出最高点出现在第 1 步附近，并说明属于早期，因此可由给定信息直接回答。不依赖隐藏元数据或未说明阈值。 |
| `aiopslab_official_v3` | `test` | `aiops_official_memory_extrema` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 把这个事故窗口按时间分成早期、中期和后期后，服务内存工作集的最高点出现在什么位置？ | 问题表述像正常的运维遥测分析问题，不是明显的验证槽位提示。场景中清楚定义了 x1 为内存工作集，问题要求判断最高点位于早/中/后三段，证据直接给出最高值出现在第 6 步附近且属于窗口前段，支持槽也提供了窗口范围和极值位置，因此可回答性较好。没有依赖隐藏元数据或未解释的变量含义。 |
| `aiopslab_official_v3` | `test` | `aiops_official_window_memory` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 按 5% 相对差异规则，这个事故窗口中的服务内存占用是前后相近，还是某一半更重？ | 该样例像正常的运维场景判断题，变量含义明确，问题指定了 5% 相对差异规则，证据直接给出前后两半的内存均值，选项也与问题一致。无需依赖隐藏元数据或未解释的时间轴，答案可由给定证据和规则确定。 |
| `aiopslab_official_v3` | `test` | `aiops_official_cross_signal_relation` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 按绝对相关系数 0.30 作为可用耦合阈值，SRE 在这个事故窗口中应该信任哪种遥测关系？ | 该样例读起来像正常的 SRE 遥测分析问题，而不是验证器槽位提示。场景中明确说明了各变量含义，问题给出了 0.30 的可用耦合阈值，证据中也提供了两组相关系数和判定规则，因此无需依赖隐藏元数据即可回答。选项互斥且覆盖主要情形，金答案可由证据和规则直接支持，准确性风险低。 |
| `aiopslab_official_v3` | `test` | `aiops_official_network_volatility` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 这个事故窗口中，网络接收速率在哪一段波动最大？ | 问题表述像正常的 SRE 遥测分析问题，变量含义清楚，询问网络接收速率在窗口三等分中的波动最大位置。证据明确说明窗口被分为早期、中期、后期，并给出三段标准差，能够直接支持答案。没有隐藏元数据、内部 ID 依赖或未解释的时间轴问题。 |
| `aiopslab_official_v3` | `test` | `aiops_official_cross_signal_relation` | `gpt55_candidate` | `keep` | 4 | 5 | `low` | 按绝对相关系数 0.30 作为可用耦合阈值，SRE 在这个事故窗口中应该信任哪种遥测关系？ | 该样例整体像一个正常的 SRE 遥测分析问题，而不是明显的验证器槽位提示。场景中说明了 x0-x3 的含义，问题给出了 0.30 的绝对相关系数阈值，证据进一步提供了 CPU-内存与网络收发两组相关系数以及相近判定规则，因此不需要额外元数据即可回答。选项也基本是人类可读的关系判断。轻微问题是 x0/x1 等变量名和 AIOpsLab 窗口略有数据集化表达，但不影响可答性。 |
| `aiopslab_official_v3` | `test` | `aiops_official_window_memory` | `gpt55_candidate` | `keep` | 4 | 5 | `low` | 按 5% 相对差异规则，这个事故窗口中的服务内存占用是前后相近，还是某一半更重？ | 该样例整体像正常的 SRE 遥测窗口判断问题，而不是明显的 verifier-slot 提示。变量含义清楚，问题明确限定为内存工作集，并给出了 5% 相对差异规则以及前后两半均值，因此可直接根据证据选择答案。没有依赖隐藏元数据或未解释的时间轴；窗口起止支持槽不是解题必需。唯一轻微问题是“5% 相对差异规则”略显模板化，但在场景中已解释，风险低。 |
| `aiopslab_official_v3` | `test` | `aiops_official_cpu_trend` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 这段事故窗口里，服务 CPU 负载是在上升、下降，还是基本平稳？ | 问题表述自然，像 SRE 在查看遥测窗口时会提出的趋势判断问题；场景中已清楚定义 x0 为服务 CPU 负载，证据给出了起点、终点和波动尺度，足以支持“基本平稳”的判断。不依赖隐藏元数据或未解释的时间轴，也没有需要额外阈值解释的程度标签。 |
| `aiopslab_official_v3` | `test` | `aiops_official_network_volatility` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 这个事故窗口中，网络接收速率在哪一段波动最大？ | 问题表述自然，场景中已清楚说明 x2 是网络接收速率；问题询问事故窗口三等分中哪一段波动最大，证据直接给出早期、中期、后期的标准差，足以支持选项判断。没有隐藏元数据、内部 ID 依赖或未解释的时间轴问题。 |
| `aiopslab_official_v3` | `test` | `aiops_official_cpu_trend` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 这段事故窗口里，服务 CPU 负载是在上升、下降，还是基本平稳？ | 该样例读起来像正常的运维遥测趋势判断问题，场景中明确说明了各变量含义，问题直接询问 CPU 负载在事故窗口内的总体趋势。证据给出了起点、终点和波动尺度，足以支持“基本平稳”的判断；没有依赖隐藏元数据、内部 ID 或未解释的时间轴。选项也清晰、互斥，风险较低。 |
| `aiopslab_official_v3` | `train` | `aiops_official_network_volatility` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 这个事故窗口中，网络接收速率在哪一段波动最大？ | 问题表述自然，像 SRE 在查看微服务遥测时会提出的波动性判断问题；变量含义清楚，x2 明确为网络接收速率。证据中明确说明窗口被分为早期、中期、后期三段，并给出三段标准差，因此可直接判断哪一段波动最大。选项也是人类可读的时间段，没有依赖隐藏元数据或未解释阈值。 |
| `aiopslab_official_v3` | `train` | `aiops_official_cross_signal_relation` | `gpt55_candidate` | `keep` | 4 | 5 | `low` | 按绝对相关系数 0.30 作为可用耦合阈值，SRE 在这个事故窗口中应该信任哪种遥测关系？ | 该样例整体像正常的 SRE 遥测判断问题，而不是明显的校验槽位提示。变量含义、相关系数阈值、相近判定规则、两个候选关系的相关系数都在题面或证据中明确给出，因此无需依赖隐藏元数据即可回答。选项也基本自然、可区分。轻微不足是使用 x0-x3 和 AIOpsLab 名称略带数据集痕迹，但变量已解释，不影响可读性和可答性。 |
| `aiopslab_official_v3` | `train` | `aiops_official_network_volatility` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 这个事故窗口中，网络接收速率在哪一段波动最大？ | 问题表述自然，符合 SRE 查看微服务遥测时对网络接收速率波动性的判断场景。变量含义清楚，时间窗口被明确划分为早期、中期、后期三段，证据中给出了三段标准差，足以支持根据波动性最大来选择答案。选项也简洁且与问题一致，没有依赖隐藏元数据或未解释阈值。 |
| `aiopslab_official_v3` | `train` | `aiops_official_memory_extrema` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 把这个事故窗口按时间分成早期、中期和后期后，服务内存工作集的最高点出现在什么位置？ | 问题表述自然，符合 SRE 查看微服务遥测窗口时会提出的判断问题；变量含义清楚，询问的是内存工作集最高点位于窗口早/中/后三段中的哪一段。证据明确给出最高点约在第 14 步，且窗口为 0 到 64，第 14 步属于前段，因此可由场景、选项、证据和支持槽确定答案。未依赖隐藏元数据或未解释的阈值。 |
| `aiopslab_official_v3` | `train` | `aiops_official_memory_extrema` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 把这个事故窗口按时间分成早期、中期和后期后，服务内存工作集的最高点出现在什么位置？ | 问题表述像正常的运维遥测分析问题，变量含义已在场景中说明，询问内存工作集最高点落在窗口早中晚哪一段。证据明确给出最高值出现在窗口第 0 步附近，并说明属于前段；支持槽也给出窗口范围和极值位置，因此可由给定信息确定答案。没有明显隐藏元数据、内部 ID 依赖或未解释的时间轴问题。 |
| `aiopslab_official_v3` | `train` | `aiops_official_cpu_trend` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 这段事故窗口里，服务 CPU 负载是在上升、下降，还是基本平稳？ | 问题表述像正常的 SRE 遥测判断题，变量含义在场景中已解释，询问 CPU 负载在事故窗口内的总体趋势。证据明确给出起点、终点和波动尺度均约为 0，足以支持“基本平稳”的确定性答案；不依赖隐藏元数据、内部阈值或未解释的时间轴。 |
| `aiopslab_official_v3` | `train` | `aiops_official_cpu_trend` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 这段事故窗口里，服务 CPU 负载是在上升、下降，还是基本平稳？ | 问题表述自然，像正常的 SRE 遥测趋势判断问题；场景中清楚定义了 x0 为服务 CPU 负载，问题直接询问 CPU 负载在事故窗口内的总体趋势。证据给出了起点、终点和波动尺度，足以支持“基本平稳”的选项。没有依赖隐藏元数据、内部阈值或未解释的时间轴。 |
| `aiopslab_official_v3` | `train` | `aiops_official_cross_signal_relation` | `gpt55_candidate` | `keep` | 4 | 5 | `low` | 按绝对相关系数 0.30 作为可用耦合阈值，SRE 在这个事故窗口中应该信任哪种遥测关系？ | 该样例整体像正常的 SRE 遥测关系判断问题，而不是明显的 verifier-slot 提示。场景中说明了 x0-x3 的含义，问题给出了 0.30 的可用耦合阈值，证据中明确给出 CPU-内存与网络收发两组相关系数以及相近判定规则，因此可以从给定信息直接判断。没有依赖隐藏元数据或未解释的时间轴，风险较低。唯一小问题是选项 A/D 的中文表述带有“更强”，而英文较简略，但不影响可答性。 |
| `aiopslab_official_v3` | `train` | `aiops_official_window_memory` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 按 5% 相对差异规则，这个事故窗口中的服务内存占用是前后相近，还是某一半更重？ | 问题表述自然，像 SRE 在比较事故窗口内内存占用前后两半的常规判断。场景已说明 x1 是内存工作集，证据明确给出 5% 相对差异规则以及前后两半均值，因此无需隐藏元数据或额外阈值即可作答。选项也与问题匹配。 |
| `aiopslab_official_v3` | `train` | `aiops_official_window_memory` | `gpt55_candidate` | `keep` | 5 | 5 | `low` | 按 5% 相对差异规则，这个事故窗口中的服务内存占用是前后相近，还是某一半更重？ | 问题表述像正常的 SRE 遥测窗口判断题，变量含义明确，关注的是内存工作集 x1。5% 相对差异规则、前后两半均值和选项都已给出，不需要额外元数据或隐藏阈值即可判断。选项互斥且覆盖相近、更高和无法判断等情况，答案可由证据中的确定性数值支持。 |

## 结论

- reviewer gate 是进入正式 natural QCC train/dev/test 之前的准入条件，不替代 deterministic support slots。
- 当前本地输出只覆盖 AIOpsLab 数值时序候选；完整每域结果需要在数据机器上重跑 selector、natural rewrite 和本 reviewer。
