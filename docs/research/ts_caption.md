You: 

帮我找近5年有关time series caption的论文

ChatGPT: 

我先帮你查近 5 年里和 “time series caption / 从时间序列生成文本描述” 最相关的论文，优先找论文原文与官方页面，再给你一份按方向整理的清单。

目前能确认到两篇非常核心的：2021 的 *Truth-Conditional Captioning of Time Series Data* 和 2025 的 *TSLM*。我再补一轮，尽量把 2022–2024 之间的相关工作也补全，并区分“直接做 caption”与“把 caption 作为中间表示/配对数据”的论文。

已思考 1m 9s

近 5 年里，**直接做 “time series caption / 用自然语言描述时间序列”** 的论文其实不算多；这个方向在 2024–2025 明显升温。下面我先给你一份**最值得读的论文清单**，再按“直接相关 / 强相关”分开。

## 一、直接相关：time series caption / annotation / description

1.  **Truth-Conditional Captioning of Time Series Data**  
    Harsh Jhamtani, Taylor Berg-Kirkpatrick, 2021，EMNLP 2021。  
    这篇基本算是近几年里最早、最经典的 time series captioning 工作之一。核心思想不是直接端到端生成描述，而是先学习能表达“峰值、下跌、趋势变化”等模式的 latent programs，再基于满足条件的 program 生成文本，因此更强调**faithfulness / factual correctness**。[arXiv+1](https://arxiv.org/abs/2110.01839?utm_source=chatgpt.com)
    
2.  **Decoding Time Series with LLMs: A Multi-Agent Framework for Cross-Domain Annotation**  
    Minhua Lin 等，2024（arXiv）。  
    论文提出 **TESSA**，用多智能体方式为时间序列自动生成**通用注释 + 领域注释**。它更偏 “annotation” 而不是传统 caption，但本质上就是把时间序列转成自然语言描述，而且强调**跨领域**。[arXiv+1](https://arxiv.org/abs/2410.17462?utm_source=chatgpt.com)
    
3.  **Time Series Language Model for Descriptive Caption Generation**  
    Mohamed Trabelsi 等，2025。  
    这是目前最直接、最贴“time series caption”标题的一篇。作者提出 **TSLM**，是专门面向时间序列 captioning 的 encoder-decoder 模型；还用合成数据和 cross-modal retrieval scoring 来缓解配对数据稀缺问题。实验里声称在多个 time series captioning 数据集上优于已有方法。[arXiv+2arXiv+2](https://arxiv.org/abs/2501.01832?utm_source=chatgpt.com)
    
4.  **TADACap: Time-series Adaptive Domain-Aware Captioning**  
    Elizabeth Fons 等，2025。  
    这篇很值得看，因为它把问题推进到**domain-aware captioning**：同样的曲线形状，在金融、医疗等不同领域里文字解释应该不同。方法是 retrieval-based，不需要为新领域大规模重训，适合看“如何把 caption 从 generic shape description 推到语义化解释”。[arXiv+1](https://arxiv.org/abs/2504.11441?utm_source=chatgpt.com)
    
5.  **CaTS-Bench: Can Language Models Describe Numeric Time Series?**  
    Luca Zhou 等，2025。  
    这篇更偏**benchmark**，但非常重要。它把 time series captioning 明确定义成“用自然语言描述数值时间序列”，并构建了一个较大规模、真实世界、带上下文信息的 benchmark，同时还加入了 reasoning/QA。做这个方向的话，这篇很适合用来了解**评测标准和数据构造方式**。[arXiv+1](https://arxiv.org/abs/2509.20823?utm_source=chatgpt.com)
    

## 二、强相关：不是纯 caption，但和 time series 描述/文本对齐高度相关

6.  **Insight Miner: A Time Series Analysis Dataset for Cross-Domain Alignment with Natural Language**  
    Yunkai Zhang 等，2023 workshop 版思路，2025 arXiv 扩展版可见。  
    这条线更偏**time series–language alignment**。核心贡献是构建 **TS-Insights** 数据集，把时间序列窗口和自然语言 insight 配对，用于让多模态模型学会“描述”时间序列。虽然它不完全等于 captioning 方法论文，但对数据构建和对齐训练非常有启发。[OpenReview+1](https://openreview.net/pdf?id=E1khscdUdH&utm_source=chatgpt.com)
    
7.  **Towards Time-Series Reasoning with LLMs**  
    2024。  
    这篇重点是 reasoning，但它显式使用了**time-series captions 作为中间表示**：先让模型生成时间序列 caption，再把 caption 交给更强的语言模型做后续推理。对你理解 “caption 是否能作为时间序列理解的桥梁” 很有帮助。[OpenReview](https://openreview.net/pdf?id=W0UTR3LLwj&utm_source=chatgpt.com)
    

## 三、如果你想快速入门，建议阅读顺序

建议按这个顺序读：

**入门基础**

-   Truth-Conditional Captioning of Time Series Data (2021)
    
-   Decoding Time Series with LLMs / TESSA (2024)
    

**当前主线方法**

-   TSLM (2025)
    
-   TADACap (2025)
    

**评测与数据**

-   CaTS-Bench (2025)
    
-   Insight Miner / TS-Insights
    

## 四、我帮你总结一下这个方向的脉络

这 5 年大致有三条线：

-   **faithful caption generation**：代表是 2021 的 Truth-Conditional，核心是“描述要真实对应时间序列模式”。[arXiv+1](https://arxiv.org/abs/2110.01839?utm_source=chatgpt.com)
    
-   **LLM-based annotation/captioning**：2024–2025 开始明显增多，代表是 TESSA、TSLM。[arXiv+1](https://arxiv.org/abs/2410.17462?utm_source=chatgpt.com)
    
-   **domain-aware / benchmark / alignment**：2025 年开始更成熟，代表是 TADACap、CaTS-Bench、TS-Insights。[arXiv+2arXiv+2](https://arxiv.org/abs/2504.11441?utm_source=chatgpt.com)
    

如果你是要做论文综述，比较合理的判断是：  
**这个方向目前还是小众但在快速发展，2025 年基本是一个明显爆发点。**[arXiv+2arXiv+2](https://arxiv.org/abs/2501.01832?utm_source=chatgpt.com)

我也可以继续帮你整理成一份 **BibTeX + 一句话摘要 + 论文链接** 的表格。

You: 

关于这个方向， 综合你帮我检索到的论文，你觉得还有哪些创新点可以做，能够形成一篇论文

ChatGPT: 

我先把这些论文的方法缺口归纳一下，再给你几个更像“能写成一篇论文”的具体选题，尽量做到题目、方法、数据和实验都能落地。

已思考 24s

可以，而且我觉得这个方向**还有不少能发论文的空位**。综合你前面这几篇工作看，现状大概是：

-   2021 的 **Truth-Conditional Captioning** 把重点放在“描述要和曲线事实一致”，但模型空间还比较小，任务也偏短描述、单序列、低上下文。[arXiv](https://arxiv.org/abs/2110.01839?utm_source=chatgpt.com)
    
-   2024 的 **TESSA** 往前走了一步，开始做跨域 annotation，并区分通用描述和领域描述，但更像“自动标注系统”，不是系统性解决 caption 的可验证性、长文本、多变量和交互式解释。[arXiv](https://arxiv.org/abs/2410.17462?utm_source=chatgpt.com)
    
-   2025 的 **TSLM** 说明大家开始认真做 end-to-end time series captioning，但它自己也强调了数据稀缺问题，主要靠合成数据和检索打分缓解。[arXiv](https://arxiv.org/abs/2501.01832?utm_source=chatgpt.com)
    
-   2025 的 **TADACap** 抓住了“domain-aware”这个关键点，不过它是 retrieval-based，且针对的是 **time-series images** 的 caption，不完全等于对原始数值序列做原生建模。[arXiv](https://arxiv.org/abs/2504.11441?utm_source=chatgpt.com)
    
-   2025 的 **CaTS-Bench** 又说明一个现实：这个方向现在很缺真实世界、上下文感知、能测数值推理能力的 benchmark。[arXiv+1](https://arxiv.org/abs/2509.20823?utm_source=chatgpt.com)
    

所以最有潜力的创新点，不是再做一个“普通 encoder-decoder 生成 caption”，而是去补这些论文共同没彻底解决的问题。

## 我最看好的几个可发论文方向

### 1\. 可验证的 time series captioning

这是我认为**最稳、最容易形成完整论文**的方向。

现有工作已经意识到 caption 容易“说得像，但不一定对”，2021 那篇就是为了解决 factual correctness；CaTS-Bench 也把 factual checks 放进了 benchmark pipeline。[arXiv+1](https://arxiv.org/abs/2110.01839?utm_source=chatgpt.com)  
但目前还没有看到一个很完整的框架：**生成 caption 的同时，输出可执行证据**，比如：

-   “在 t=35 附近出现局部峰值”
    
-   “从 t=10 到 t=25 呈显著上升”
    
-   “波动率在后半段高于前半段”
    

每一句自然语言都能对应到一个**结构化 predicate / executable rationale**，再由 verifier 在原始序列上校验。

这可以做成一篇很完整的论文：

-   方法：`series -> symbolic events -> grounded caption`
    
-   训练：caption supervision + event alignment + verification loss
    
-   评估：除了 BLEU / ROUGE / BERTScore，再加 **factual precision / factual recall / unsupported claim rate**
    
-   卖点：不只是“生成得更像人”，而是“能证明自己没胡说”
    

我认为这是最像顶会论文的问题，因为它同时满足**方法创新 + evaluation innovation + practical value**。[arXiv+1](https://arxiv.org/abs/2110.01839?utm_source=chatgpt.com)

### 2\. 多变量时间序列 captioning

现在多数工作默认输入像一条曲线或单窗口，但真实世界很多场景都是**multivariate time series**：医疗监护、传感器系统、经济指标联动。现有论文对“变量间关系”的表达还不够。TESSA 讲跨域 annotation，CaTS-Bench 讲 context-aware captioning，但都没有把“多变量关系描述”作为主问题展开。[arXiv+1](https://arxiv.org/abs/2410.17462?utm_source=chatgpt.com)

这个方向的关键创新是让模型不仅描述单条曲线趋势，还能说：

-   哪个变量先变、哪个后变
    
-   哪些变量同步变化、反向变化
    
-   某个异常是否由另一个变量的变化伴随出现
    
-   哪个变量是主导解释因素
    

论文题目都可以直接写成：  
**Multivariate Time Series Captioning via Relation-Aware Event Graphs**

方法上可以做：

-   每个变量先提取局部事件
    
-   构建跨变量 event graph
    
-   graph-to-text 生成 caption
    
-   训练时引入 relation consistency loss
    

这个选题的好处是：

-   问题定义自然，审稿人容易懂
    
-   相比“再换一个 backbone”，贡献更明确
    
-   还能顺带构造新 benchmark 子任务
    

### 3\. 长时程、层级化 captioning

目前 caption 往往是短句：上涨、下跌、峰值、波动。但真实分析常常需要**层级化总结**：

-   一句话摘要：整体先升后降
    
-   段落级说明：前半段缓慢上升，中间急跌，后段震荡恢复
    
-   事件级细节：最高点、最低点、拐点、异常段分别在哪里
    

CaTS-Bench 已经说明“上下文 + 推理”很重要，但仍然主要是 sample-level caption/QA。[arXiv](https://arxiv.org/abs/2509.20823?utm_source=chatgpt.com)  
所以你可以做一个 **Hierarchical Time Series Captioning**：

-   level 1：global summary
    
-   level 2：segment summaries
    
-   level 3：event explanations
    

核心创新点在于：

-   **层级规划器**先切分时间段
    
-   **segment captioner** 再写局部
    
-   **aggregator** 保证全文一致、不重复、不矛盾
    

这类论文很容易写出漂亮的 ablation：

-   无层级 vs 有层级
    
-   固定切分 vs 自适应切分
    
-   只生成摘要 vs 摘要+证据
    

如果你想做得更强一点，还能加 **controllability**：用户指定“简短 / 详细 / 面向专家 / 面向普通人”。

### 4\. 面向用户画像的 controllable captioning

TADACap 已经指出“同一条时间序列在不同领域需要不同表达方式”，这是一个非常好的切入点。[arXiv](https://arxiv.org/abs/2504.11441?utm_source=chatgpt.com)  
但我觉得还可以再往前推进，不只是 domain-aware，而是 **audience-aware / goal-aware**：

-   给医生的描述
    
-   给病人的描述
    
-   给交易员的描述
    
-   给管理层的描述
    
-   给机器学习研究者的描述
    

同一条序列，生成文本的粒度、术语、风险表达方式、关注重点都不同。这个方向的论文价值在于，它把任务从“描述曲线”提升成“**为不同决策者生成合适解释**”。

你可以做：

-   控制变量：领域、读者层级、任务目标、长度、保守程度
    
-   方法：prefix/control tokens + retrieval of audience exemplars + RL from preference
    
-   评估：内容对齐 + 风格适配 + 用户偏好胜率
    

这类工作特别适合做用户研究，容易增强论文说服力。

### 5\. 带不确定性和置信度的 captioning

这是一个我觉得**很新但很有价值**的方向。

现在大多数 caption 默认“肯定地说”。但时间序列本身可能很 noisy、窗口很短、趋势不明显。模型其实应该学会说：

-   “可能存在轻微上升趋势，但证据有限”
    
-   “后半段疑似出现异常峰值”
    
-   “该模式对采样频率敏感”
    

现有论文几乎都把 caption 当成单一正确文本，而不是**带 epistemic uncertainty 的科学表述**。Truth-Conditional work 强调真假，但没有系统表达不确定性；CaTS-Bench 也主要评估是否能正确描述，而不是是否会在模糊样本上谨慎表述。[arXiv+1](https://arxiv.org/abs/2110.01839?utm_source=chatgpt.com)

这篇论文可以做成：

-   估计事件存在概率
    
-   把概率映射到 hedging language
    
-   同时输出 calibrated confidence
    
-   评估 calibration 与语言置信是否一致
    

如果你做好，这会很像“可靠生成 / trustworthy AI”方向的工作，审稿人会觉得比单纯追求 Rouge 分更有意义。

### 6\. Caption 作为中间表示，服务下游任务

有些论文已经在往这边靠，比如 time-series reasoning 相关工作，会把 time series 与语言推理连接起来。[OpenReview](https://openreview.net/pdf?id=W0UTR3LLwj&utm_source=chatgpt.com)  
所以一个很有潜力的思路是：**不是只优化 caption 本身，而是证明 caption 是一种有用中间表示**。

比如做一篇：  
**Caption as Latent Program for Time Series Reasoning**

思路是：

-   先把时间序列转成 caption / structured explanation
    
-   再用 caption 去做 QA、异常归因、检索、分类、跨域迁移
    
-   和直接用 time-series encoder 做下游任务比较
    

如果结果表明：

-   caption 提升 zero-shot transfer
    
-   caption 提升可解释检索
    
-   caption 提升 cross-domain generalization
    

那这篇论文就不再只是“小任务”，而是变成“语言化表示对时间序列理解的价值”。这条线有潜力，但要把实验设计得很扎实。[OpenReview+1](https://openreview.net/pdf?id=W0UTR3LLwj&utm_source=chatgpt.com)

### 7\. 构建更严格的数据集与评测

如果你更偏 benchmark / data paper，这个方向也有空间。CaTS-Bench 已经很强，但它的出现本身就说明这个领域还缺统一、严谨、细粒度的 evaluation。[arXiv+1](https://arxiv.org/abs/2509.20823?utm_source=chatgpt.com)

你可以专门做一个更聚焦的数据集，例如：

-   **FactTS-Cap**：面向 factual consistency  
    每条样本附带结构化事实标注：峰、谷、拐点、异常、周期、段间对比。
    
-   **MultiTS-Cap**：面向多变量关系描述  
    每条样本标注变量间 lead-lag、协同/反向关系。
    
-   **UncertainTS-Cap**：面向模糊样本与谨慎表述  
    专门设计“趋势不明显 / 多解释共存”的样本，测试模型是否会过度自信。
    

数据论文的关键不是“我又做了个数据集”，而是：

-   任务定义更清楚
    
-   标注协议更严格
    
-   metric 更贴近真实性
    
-   baseline 分析更系统
    

这个方向对资源要求高一点，但产出也比较稳定。

## 哪几个方向最容易真正做出来

如果从“创新性 + 可实现性 + 成文难度”综合排序，我会这样建议：

**第一梯队**

1.  **可验证的 time series captioning**
    
2.  **多变量时间序列 captioning**
    
3.  **层级化 / 长文本 captioning**
    

这三个最像标准 ML/NLP 论文题目，问题清晰，实验也容易设计。

**第二梯队**  
4\. **用户/领域可控 captioning**  
5\. **带不确定性的 captioning**

这两个更新，但评估会稍难，需要你设计更好的 protocol。

**第三梯队**  
6\. **caption 作为中间表示做推理/迁移**  
7\. **新 benchmark / dataset**

这两个潜力大，但更吃实验规模和数据构建能力。

## 如果是我来选，我会首推这两个题目

### 方案 A

**Verifiable Time Series Captioning with Executable Event Grounding**

为什么我最推荐：

-   正好承接 2021 那篇 truth-conditional 的核心痛点，但方法可以比它更现代、更 general。[arXiv](https://arxiv.org/abs/2110.01839?utm_source=chatgpt.com)
    
-   可以自然结合 2025 benchmark 对 factual checks 的需求。[arXiv](https://arxiv.org/abs/2509.20823?utm_source=chatgpt.com)
    
-   容易讲清楚贡献：  
    不是更会写，而是更可信、更能解释。
    

一个简洁方法框架：

-   event parser：从序列中提取候选事件
    
-   event selector/planner：选择要说的事件
    
-   text generator：生成 caption
    
-   verifier：检查每句是否可由原始序列支持
    
-   training：MLE + contrastive factual loss + verification loss
    

### 方案 B

**Relation-Aware Multivariate Time Series Captioning**

为什么值得做：

-   现实场景强
    
-   目前空位明显
    
-   很容易体现“不是换 backbone，而是任务本身升级了”
    

一个简洁方法框架：

-   per-variable encoder
    
-   cross-variable temporal graph
    
-   relation-aware planner
    
-   hierarchical decoder
    
-   metric：trend correctness + relation correctness + text quality
    

## 你现在最应该避免的选题

我不太建议你做这几种，因为容易显得贡献弱：

-   “把某个更大的 LLM/VLM 拿来直接做 caption”
    
-   “换一种 encoder，再刷几个文本指标”
    
-   “只做 synthetic data augmentation”
    
-   “只做 retrieval trick，但没有新的任务定义或评测”
    

因为 TSLM、TADACap、CaTS-Bench 之后，单纯堆模型已经不太够了。更容易被认可的是：**你提出了一个更本质、更缺失的问题，并给出新评测和新方法一起解决。** [arXiv+2arXiv+2](https://arxiv.org/abs/2501.01832?utm_source=chatgpt.com)

## 我的直接建议

如果你想要一条最像论文、成功率也高的路线，我建议你做：

**“可验证 + 层级化”的 time series captioning**  
一句话就是：  
**让模型不仅会描述时间序列，还能给出分层解释，并且每个描述都能被原始序列验证。**

这个题目兼顾：

-   新问题
    
-   新方法
    
-   新 metric
    
-   强可解释性
    
-   与已有文献形成清晰差异
    

你要的话，我下一步可以直接帮你把这个方向展开成一份**论文 proposal**，包括：  
题目、摘要、方法框架图思路、实验设计、baseline、metrics、可能的数据集和预期贡献。

You: 

我之前在Verifiable Time Series Captioning with Executable Event Grounding这个方案上做了一些推进，但是卡在training上了，当时看到的问题是，生成的时间序列描述大多带有精准的时间序列数值，很难通过训练让模型学到这种数值表示，具体的time series captioning和训练方案都在这个github仓库里，你帮我审查一下这个代码库，告诉我我目前的推进和你给出的方案有哪些偏差，该如何继续改进，还是这个方案确实走不通

ChatGPT: 

我先审查仓库里的训练与 caption 实现，重点核对任务定义、数据与模板、数值表达学习、loss 和生成流程。然后再对照“Verifiable Time Series Captioning + Executable Event Grounding”逐项判断是路线偏了，还是训练方案需要重构。

我这边还没拿到可直接审的仓库链接或代码，所以先按公开实现做针对性排查；目前更像是任务表示和监督把“文本生成”与“精确数值抽取”绑死了，而不一定是路线本身走不通。

You: 

https://github.com/Ringhu/tslm 这是我的仓库

ChatGPT: 

现在已经定位到你的仓库 `Ringhu/tslm` 了，我会按代码链路直接审：先看 README、训练入口、数据/标签与 caption 模板，再查 loss、tokenization 和数值处理。重点判断你目前是路线偏了，还是主要卡在一个可修复的“数值复制/对齐能力没有被单独建模”的训练瓶颈上。

接下来我会把仓库里现有实现、与 Verifiable + Executable Grounding 的差距、以及最值得优先改的几处拆开说，顺带检查是否已经有 verifier / event-grounding 相关模块。

我已经看到两个更具体的断点：仓库里同时存在两套包结构，且 `train_sft.py` 与 `TSReportLM` 的参数接口不同步，说明当前训练链路本身还没完全闭环。

Thought for 31m 58s

我看完仓库后的判断是：**这个方向没死，但你现在这版实现离“Verifiable Time Series Captioning with Executable Event Grounding”还差一个关键转向。** 目前仓库本质上还是一个 **time-series → prefix embeddings → causal LM → free-form caption** 的 SFT baseline；README 也明确把它定位成“minimal skeleton”，并说明当前真正完整的是 PatchTST + PrefixBridge 路径，Chronos-2 和 cross-attention 还是接口 / stub。[GitHub](https://github.com/Ringhu/tslm?utm_source=chatgpt.com)

先说一个我觉得比“训练卡住”还更要紧的工程问题：**你的仓库里同时有 `src/tsrlm` 和顶层 `tsrlm` 两套包目录，而且两边的 `ts_llm.py` 不是同一版。** 根目录文件树里这两套目录都存在；`src/tsrlm/models/ts_llm.py` 还是比较干净的 PatchTST+Prefix 版，而顶层 `tsrlm/models/ts_llm.py` 已经加了 `encoder_type / bridge_type / chronos_model_path`、Chronos-2、xattn 以及一些 debug 改动。脚本里用的是 `from tsrlm...`，所以运行时到底吃哪一版，取决于你的导入路径和安装方式，这会直接影响你对实验现象的判断。[GitHub+4GitHub+4GitHub+4](https://github.com/Ringhu/tslm)

而且顶层那版 `generate()` 现在**明显还留着 debug 覆盖**：它前面算了 `prefix_embeds`，但后面又把 `inputs_embeds` 直接设成 `tok_embeds`、`attn` 设成 `attention_mask`，等于推理时把时序 prefix 整段丢掉了。换句话说，你现在看到的很多生成效果，很可能不是“模型没学会”，而是**推理路径根本没在用时间序列条件**。这件事要优先修，不然你后面对训练方案的判断会被污染。[GitHub](https://raw.githubusercontent.com/Ringhu/tslm/main/tsrlm/models/ts_llm.py)

再说和我之前那个方案的**核心偏差**。我给你的方向是“**先预测可执行事件 / claim，再由 executor 或 renderer 落成文本**”；但你现在代码里的主训练目标仍然是 `text` 这条最终 caption 本身。`collator` 只是把 `text` tokenize 后做标准 `labels`，`TSReportLM.forward()` 也是把 prefix 和文本 embedding 拼起来，然后直接把 `labels` 丢给 causal LM 做普通语言模型 loss；没有 number-specific loss，没有 claim loss，也没有 verifier loss。虽然 `format.md` 已经把 `claims`、`segments`、甚至 “JSON + caption” 这种输出形式写进 schema 了，dataset/collator 也能透传 `claims`，但 adapter 默认导出的仍是 `id / values / text`，`claims` 只是被塞进 `meta`；模型前向本身并没有真正消费这些结构化字段。[GitHub+7GitHub+7GitHub+7](https://github.com/Ringhu/tslm/blob/main/src/tsrlm/data/format.md)

这就解释了你为什么会卡在“**精准数值很难学**”。按当前实现，数字和普通词一样，只是 caption 里的普通 token；loss 也只是 pad-masked 的 token CE。与此同时，训练脚本 / shell 又在用很小的 Qwen3-0.6B，并且 `train_sft.sh` 里默认 `--freeze_llm`，也就是说你主要是在逼一个冻结的小语言模型，仅靠前面的时序 encoder + prefix bridge 去“暗示”它写出精确数字。再加上显式喂给模型的统计量基本只有 `mean/std/min/max/delta_pct/length` 这一类全局特征，没有把“峰值 index”“峰值 value”“局部谷值”等数值锚点变成单独监督，这条路对**精确数值 surface form** 本来就会非常吃力。[GitHub+5GitHub+5GitHub+5](https://github.com/Ringhu/tslm/blob/main/src/tsrlm/data/collator.py)

所以我的结论不是“这个方案走不通”，而是：**“直接让 LM 在 free-form caption 里端到端吐出精确数字”这条子路线，不值得继续当主线死磕；但“grounded / verifiable captioning”本体依然很值得做。** 其实你仓库里已经埋了正确方向的钩子：`claims`、`segments`、以及 `format.md` 里推荐的 “JSON + caption” 输出格式，都是朝那个方向走的。你现在更像是已经搭出了 baseline 的骨架，但训练目标还停留在“普通 caption SFT”这一步。[GitHub+2GitHub+2](https://github.com/Ringhu/tslm/blob/main/src/tsrlm/data/format.md)

我会建议你下一步分两层做。**第一层是先把现有 repo 修到“可相信”**：统一只保留一套 `tsrlm` 包；修掉顶层 `generate()` 里忽略 prefix 的 debug 代码；把 train/eval 里 Chronos/Chronos2、RevIN 开关这些参数统一好，因为 `evaluate.py` 现在的 `encoder_type` choice、`chronos_model_path` 默认值，以及 `use_revin=False` 的写法都和训练端不完全一致。这个阶段先别急着追指标，先确保“训练和推理走的是同一条模型路径”。[GitHub+3GitHub+3GitHub+3](https://github.com/Ringhu/tslm/blob/main/scripts/evaluate.py)

**第二层才是研究上的真正转向**：不要再把“最终自然语言 caption”当唯一监督，而是改成“**结构化 facts/claims 是主监督，caption 是次级渲染目标**”。我建议你直接采用 `format.md` 里已经写出来的 Variant B 思路，把 `text` 改成结构化 JSON，但不要让模型直接生成最终精确浮点字面值，而是生成**可执行槽位**，例如：

```
JSON

{  
  "facts": {  
    "trend": "down",  
    "peak\_idx": 220,  
    "valley\_idx": 23,  
    "delta\_pct\_bin": "-150~-140"  
  },  
  "caption\_template": "整体呈下降趋势，在<PEAK\_IDX>处达到峰值<PEAK\_VAL>，在<VALLEY\_IDX>处达到谷值<VALLEY\_VAL>。"  
}
```

然后由 executor 根据原始序列把 `<PEAK_VAL>`、`<VALLEY_VAL>` 这些槽位**确定性填回去**。这样模型学的是“选对事件 / 选对位置 / 选对槽位”，不是硬背数字字符串。这个改法和你现在的 repo 兼容性其实很好：adapter 负责把 `claims` 正式写到顶层字段里，dataset/collator 负责把 claim target 张量化，model 里加几路 auxiliary head（trend、peak\_idx、valley\_idx、value\_bin、volatility 等），最后 `loss = LM_CE + λ1*trend_loss + λ2*peak_idx_loss + λ3*value_bin_loss + λ4*consistency_loss`。这样才真正接近“Executable Event Grounding”。[GitHub+3GitHub+3GitHub+3](https://github.com/Ringhu/tslm/blob/main/src/tsrlm/data/format.md)

如果你暂时还不想大改，我也建议你至少先做三个诊断实验：第一，把 caption 里的非年份数字全部 placeholder 化，看看模型是否突然变得会写趋势和结构；第二，只训练 JSON facts，不训 free-form caption；第三，保留 caption，但把所有数字改成量化 bin。只要这三个里前两个明显好于原始 caption，你就能很清楚地知道：**你现在的问题不是“模型不会看时间序列”，而是“输出空间设计错了”**。这一步做出来，你就知道该不该继续投资源。

我的最终判断是：**方案本身值得继续，但请停止把“直接生成含精确数字的自然语言 caption”当成主目标。** 你现在最该做的不是继续调 learning rate 或 epoch，而是把任务从“caption generation”重写成“claim prediction + executable rendering + verification”。这会更像一篇真正能站住的论文，而不是一个总被数字细节绊住的 baseline。

你要是愿意，我下一条可以直接按你这个 repo 的文件结构，给你一份**逐文件修改清单**，包括 `prepare_jsonl_adapter.py`、`collator.py`、`ts_llm.py`、`evaluate.py` 分别该怎么改。