### Case 07：Oracle 局部 spike 被幻觉成 seasonality

- 数据集：`dataset_a`
- Case ID：`dataset_a::0000`
- 问题类型：`noise,local,season,local-inductive`
- Dataset-A 能力标签：`noise, local, season, local-inductive`
- 数值摘要：n=256, min=0, max=4.2794, mean=0.016716, std=0.26694, slope=0.00030456, argmax=227, argmin=0
- Dataset-A 标注属性：`[{'std': 0.0, 'type': 'almost no noise'}, [{'amplitude': 4.28, 'position': 226, 'type': 'upward spike'}], {'amplitude': 0.0, 'period': 0.0, 'type': 'no periodic fluctuation'}, [{'amplitude': 4.28, 'explain': 'The database is experiencing significant contention issues related to enqueue resources.', 'position': 226, 'type': 'upward spike'}]]`

![dataset_a::0000](https://raw.githubusercontent.com/Ringhu/LTSGen/balanced-case-study-zh-20260511/docs/case-studies/20260511-balanced-zh/figures/dataset_a_0000.png)

**QA 问题**

- 原文：You are a time series analysis expert. This time series is "##enq: SQ - contention" from Oracle Database System with length of 256: <ts><ts/>, please analyze the time series features and answer the following questions:
1. What are the noise characteristics of this time series? Please choose from ["noisy", "almost no noise"]. Answer format: noisy, the overall noise standard deviation is around 1.5.
2. What are the local characteristic fluctuations of this time series? The optional types of local characteristic fluctuations include: ["continuous downward spike", "continuous upward spike", "decrease after downward spike", "decrease after upward spike", "downward convex", "downward spike", "increase after downward spike", "increase after upward spike", "rapid decline followed by slow rise", "rapid rise followed by slow decline", "shake", "slow decline followed by rapid rise", "slow rise followed by rapid decline", "sudden decrease", "sudden increase", "upward convex", "upward spike", "wide downward spike", "wide upward spike"]. You need to analyze all the characteristic fluctuations that appear in this time series and answer each type, position, and amplitude in the format. Different local characteristic fluctuations should be separated by semicolons. Answer format: shake, position around point 125, amplitude 135.03; small sudden decrease, position around point 102, amplitude 31.05.
3. What is the periodicity of this time series? Please choose from ["no periodic fluctuation", "periodic fluctuation"]. If there is periodic fluctuation, describe the fluctuation frequency and amplitude. Answer format: periodic fluctuation, each period is around 20.58 points, and the amplitude of the periodic fluctuation is around 31.51.
4. What are the local characteristic flu ...[截断]
- 中文翻译：You are a time series analysis expert. This time series is "##enq: SQ - contention" from Oracle Database System with length of 256: <ts><ts/>, please analyze the time series features and answer the following questions:
1. What are the noise characteristics of this time series? Please choose from ["noisy", "almost no noise"]. Answer format: noisy, the overall noise standard deviation is around 1.5.
2. What are the local characteristic fluctuations of this time series? The optional types of local characteristic fluctuations include: ["continuous downward spike", "continuous upward spike", "decrease after downward spike", "decrease after upward spike", "downward convex", "downward spike", "increase after downward spike", "increase after upward spike", "rapid decline followed by slow rise", "rapid rise followed by slow decline", "shake", "slow decline followed by rapid rise", "slow rise followed by rapid decline", "sudden decrease", "sudden increase", "upward convex", "upward spike", "wide downward spike", "wide upward spike"]. You need to analyze all the characteristic fluctuations that appear in this time series and answer each type, position, and amplitude in the format. Different local characteristic fluctuations should be separated by semicolons. Answer format: shake, position around point 125, amplitude 135.03; small sudden decrease, position around point 102, amplitude 31.05.
3. What is the periodicity of this time series? Please choose from ["no periodic fluctuation", "periodic fluctuation"]. If there is periodic fluctuation, describe the fluctuation frequency and amplitude. Answer format: periodic fluctuation, each period is around 20.58 points, and the amplitude of the periodic fluctuation is around 31.51.
4. What are the local characteristic fluctuations of this time series? The optional types of local characteristic fluctuations include: ["continuous downward spike", "continuous upward spike", "decrease after downward spike", "decrease after upward spike", "downward convex", "downward spike", "increase after downward spike", "increase after upward spike", "rapid decline followed by slow rise", "rapid rise followed by slow decline", "sha ...[截断]
- 选项：
-
- 正确答案：`1. almost no noise, the overall noise standard deviation is around 0.00.
2. upward spike, position around point 226, amplitude 4.28
3. no periodic fluctuation
4. upward spike, position around point 226, amplitude 4.28. The database is experiencing significant contention issues related to enqueue resources
`

**生成的 caption 与中文翻译**

**OpenTSLM caption 原文**

The time series shows a flat trend with low volatility and a strong seasonal pattern repeating every 180 time units. There is a noticeable upward phase early in the window followed by a significant downward movement in the first half, then a smaller upward trend in the second half. A peak occurs in the first half with a magnitude of about 1.6 standard deviations from the mean, while a valley is observed early in the window with a magnitude of about 1.7 standard deviations from the mean. The series exhibits strong negative correlation with the "SQ - contention" variable.

**OpenTSLM caption 中文翻译**

该时间序列呈现平稳趋势，波动性较低，并具有每 180 个时间单位重复一次的强季节性模式。窗口早期有明显的上升阶段，随后在前半段出现显著下行走势，之后在后半段出现较小的上升趋势。前半段出现一个峰值，其幅度约为偏离均值 1.6 个标准差；窗口早期观察到一个谷值，其幅度约为偏离均值 1.7 个标准差。该序列与“SQ - contention”变量表现出强负相关。

**ChatTS caption 原文**

1) almost no noise 2) no periodic fluctuation 3) keep steady 4) upward spike, position around point 226, amplitude 4.28

**ChatTS caption 中文翻译**

1) 几乎没有噪声 2) 无周期性波动 3) 保持稳定 4) 向上尖峰，位置约在点 226，幅度 4.28

**不同输入条件下的答案 / 评分**

| 条件 | 平均分 | 分项分数 |
| --- | ---: | --- |
| `opentslm_caption` | 0.25 | local=0.00，local-inductive=0.00，noise=1.00，season=0.00 |
| `opentslm_caption_plus` | 0.95 | local=0.97，local-inductive=0.81，noise=1.00，season=1.00 |
| `opentslm_numbers` | 0.50 | local=0.00，local-inductive=0.00，noise=1.00，season=1.00 |
| `chatts_caption` | 0.96 | local=1.00，local-inductive=0.83，noise=1.00，season=1.00 |
| `chatts_caption_plus` | 0.96 | local=1.00，local-inductive=0.83，noise=1.00，season=1.00 |
| `chatts_numbers` | 0.50 | local=0.00，local-inductive=0.00，noise=1.00，season=1.00 |

**代表性模型回答**

- `opentslm_caption` 原文：1. almost no noise, the overall noise standard deviation is around 0.15.\n2. rapid rise followed by slow decline, position around point 45, amplitude 1.60; rapid decline followed by slow rise, position around point 18, amplitude 1.70; wide upward spike, position around point 120, amplitude 1.10; wide downward spike, position around point 170, amplitude 1.20\n3. periodic fluctuation, each period is around 180 points, and the amplitude of the periodic fluctuation is around 1.40.\n4. rapid rise followed by slow decline, position around point 45, amplitude 1.60. This suggests a brief build-up in the system metric followed by a more gradual relaxation, consistent with a transien ...[截断]
  中文：1. almost no noise, the overall noise standard deviation is around 0.15.\n2. rapid rise followed by slow decline, position around point 45, amplitude 1.60; rapid decline followed by slow rise, position around point 18, amplitude 1.70; wide upward spike, position around point 120, amplitude 1.10; wide downward spike, position around point 170, amplitude 1.20\n3. periodic fluctuation, each period is around 180 points, and the amplitude of the periodic fluctuation is around 1.40.\n4. rapid rise followed by slow decline, position around point 45, amplitude 1.60. This suggests a brief build-up in the system metric followed by a more gradual relaxation, consistent with a transient workload or contention burst; rapid decline followed by slow rise, position around point 18, amplitude 1.70. This indicates a sharp drop followed by gradual recovery, likely reflecting a temporary e ...[截断]
- `opentslm_caption_plus` 原文：1. almost no noise, the overall noise standard deviation is around 0.0\n2. upward spike, position around point 198, amplitude 4.28\n3. no periodic fluctuation\n4. upward spike, position around point 198, amplitude 4.28. A brief isolated surge likely caused by a transient event or short-lived contention burst, after which the series immediately returns to its baseline zero level.
  中文：1. 几乎没有噪声，整体噪声标准差约为 0.0\n2. 向上尖峰，位置约在点 198，幅度 4.28\n3. 无周期性波动\n4. 向上尖峰，位置约在点 198，幅度 4.28。一次短暂的孤立性激增，可能由瞬态事件或短暂的资源竞争突发引起，之后序列立即回到其零基线水平。
- `opentslm_numbers` 原文：1. almost no noise, the overall noise standard deviation is around 0.09.\n2. sudden increase, position around point 194, amplitude 4.28\n3. no periodic fluctuation\n4. sudden increase, position around point 194, amplitude 4.28. A brief isolated contention spike occurred, likely reflecting a short-lived burst of enqueue-related lock or resource contention in the Oracle database; the rest of the series stayed near zero, indicating the event was transient and not part of a sustained pattern.
  中文：1. 几乎没有噪声，整体噪声标准差约为 0.09。
2. 突然增加，位置在约第 194 个点，幅度为 4.28
3. 无周期性波动
4. 突然增加，位置在约第 194 个点，幅度为 4.28。出现了一次短暂的孤立争用峰值，可能反映了 Oracle 数据库中与入队相关的锁或资源争用的短时突发；序列其余部分保持在接近零的水平，表明该事件是暂时性的，并非持续模式的一部分。
- `chatts_caption` 原文：1. almost no noise, the overall noise standard deviation is around 0.15  \n2. upward spike, position around point 226, amplitude 4.28  \n3. no periodic fluctuation  \n4. upward spike, position around point 226, amplitude 4.28. A brief contention surge in the database workload, likely caused by a short-lived spike in concurrent access or lock contention, rapidly increasing before returning toward baseline.
  中文：1. 几乎没有噪声，整体噪声标准差约为 0.15  
2. 向上尖峰，位置约在点 226，幅度 4.28  
3. 无周期性波动  
4. 向上尖峰，位置约在点 226，幅度 4.28。数据库工作负载中出现短暂的争用激增，可能由并发访问或锁争用的短时峰值引起，在恢复到基线附近之前快速上升。
- `chatts_caption_plus` 原文：1. almost no noise, the overall noise standard deviation is around 0.00\n2. upward spike, position around point 226, amplitude 4.28\n3. no periodic fluctuation\n4. upward spike, position around point 226, amplitude 4.28. A brief and isolated surge in SQ contention, likely caused by a short-lived locking or enqueue conflict event, after which the system immediately returned to its steady baseline.
  中文：1. 几乎没有噪声，整体噪声标准差约为 0.00\n2. 向上尖峰，位置约在点 226，幅度 4.28\n3. 无周期性波动\n4. 向上尖峰，位置约在点 226，幅度 4.28。SQ 争用出现短暂且孤立的激增，可能由短暂的锁定或入队冲突事件引起，之后系统立即恢复到稳定基线。
- `chatts_numbers` 原文：1. almost no noise, the overall noise standard deviation is around 0.16.\n2. sudden increase, position around point 203, amplitude 4.279.\n3. no periodic fluctuation.\n4. sudden increase, position around point 203, amplitude 4.279. A brief isolated spike in enqueue contention, likely caused by a short-lived burst of concurrent access or locking pressure, after which the metric immediately returns to near-zero.
  中文：1. 几乎没有噪声，整体噪声标准差约为 0.16。
2. 突然增加，位置在点 203 附近，幅度为 4.279。
3. 无周期性波动。
4. 突然增加，位置在点 203 附近，幅度为 4.279。enqueue 争用出现短暂的孤立尖峰，可能由短暂的并发访问突增或锁压力引起，随后该指标立即恢复到接近零。

**Case 分析**

- 失败标签：Oracle 局部 spike 被幻觉成 seasonality
- 关键结论：真实属性是 point 226 的 upward spike，领域含义是 enqueue 资源争用；OpenTSLM 编造 180-step seasonality 和多处事件，ChatTS 保留了关键局部事实。
