# Literature Review: TS → Language Interface for TS Understanding / QA

> Scope: 2024-01 to 2026-04, focused on training objectives, architectures, and benchmarks that speak to the "captioning trap" the LTSGen project hit.
> Compiled 2026-04-19 from Gemini-3.1-pro + WebSearch verification.

## 1. Landscape Map

The 2024-2026 TS-LLM literature has split into **four methodological camps**:

1. **Synthetic-caption SFT** (ChatTS VLDB 2025, OpenTSLM 2510.02410, LTSGen). A strong TS encoder (Chronos / Chronos-2 / frozen patch tokenizer) is bridged to an LLM via soft-prompt or Flamingo cross-attention. The bridge is trained with next-token LM loss on synthetic / GPT-generated captions. This is where the user's project sits. The camp is already crowded: OpenTSLM explicitly publishes our own architecture (Qwen + Chronos-2 + Flamingo cross-attn) and is open-source. ChatTS ships the ByteDance-14B model weights and reports 46% alignment / 25.8% reasoning gains over GPT-4o using synthetic Evol-Instruct QA pairs.

2. **Numeric-tokenization / direct LLM** (Chronos, Chronos-2, TimesFM, Time-LLM, Moirai). TS is tokenized into the LLM's vocabulary or patch-embedded; no natural-language caption is produced. Zero-shot forecasting is the main benchmark. This camp **bypasses the caption question entirely** — but also bypasses the interpretability angle.

3. **Contrastive TS-text alignment** (TS-CLIP EMNLP 2025, TF-C NeurIPS 2022). Maps TS and text into a shared semantic space without generating text. TS-CLIP claims SOTA zero-shot on 51 UCR-like datasets using a "synonym bank" to handle label collapse — solves a very similar problem to the user's wrong_caption = learned_caption collapse.

4. **Tool-augmented TS agents** (TimeART 2601.13653, DCATS 2508.04231, ChatTS agentic mode). LLM delegates numerical reasoning to external tools (forecasting model, anomaly detector, feature extractor). The LLM never needs to perceive the series itself — it needs to route. This is precisely the *Path 3* the user already proposed as their fallback.

**The field is actively migrating from camp 1 to camps 3/4** because caption-SFT hits exactly the template-collapse issue the user diagnosed. The single most important paper for the user's question is **CapRL (ICLR 2026)** — it solves this problem in the vision domain with a principled paradigm that has not yet been applied to TS.

## 2. Direct Competitors

| Title | Venue | Link | Code | Summary | Relevance | Tag |
|---|---|---|---|---|---|---|
| **OpenTSLM: Time-Series Language Models for Reasoning over Multivariate Medical Text- and Time-Series Data** (Stanford + ETH + Google + Amazon, 2025-10) | arXiv preprint, OpenReview | [2510.02410](https://arxiv.org/abs/2510.02410) | [StanfordBDHG/OpenTSLM](https://github.com/StanfordBDHG/OpenTSLM) | Publishes the **exact architecture the user reimplemented** — Flamingo cross-attention + soft-prompt variants over Chronos-style TS encoder + pretrained LLM. Trains on HAR-CoT, Sleep-CoT, ECG-QA-CoT (all medical, all supervised SFT). Reports big gains over GPT-4o on medical TS reasoning. **No ablation on caption utility outside the 5 medical tasks.** | User's baseline IS this paper. Any contribution must clearly exceed it. | `[direct competitor, foundational]` |
| **ChatTS: Aligning Time Series with LLMs via Synthetic Data** (ByteDance, VLDB 2025) | arXiv | [2412.03104](https://arxiv.org/abs/2412.03104) | [HF ChatTS-14B](https://huggingface.co/bytedance-research/ChatTS-14B) | Synthetic attribute-based TS + Evol-Instruct QA, multivariate native. 46% alignment / 25.8% reasoning gain over GPT-4o. Open-source model + dataset. | Same paradigm as LTSGen but much larger + already published. Makes LTSGen's "synthetic caption data" contribution hard to defend as novel. | `[direct competitor]` |
| **TimeMaster: Training Time-Series Multimodal LLMs to Reason via RL** (2025-06) | arXiv | [2506.13705](https://arxiv.org/abs/2506.13705) | *not found* | SFT + GRPO with composite reward (format + classification accuracy + open-ended insight). Base: Qwen2.5-VL-3B. +14.6% over classical, +7.3% over few-shot GPT-4o on TimerBed (6 classification tasks). | **Closest TS analog of CapRL-style RL.** But reward is on classification + LLM-judged "insight quality", not on a disentangled QA-accuracy probe. Open-ended QA-accuracy reward remains unexploited. | `[direct competitor]` |
| **Time-MQA: Time Series Multi-Task QA with Context Enhancement** (ACL 2025) | ACL Anthology | [2503.01875](https://arxiv.org/abs/2503.01875) | [HF TSQA](https://huggingface.co/datasets/Time-MQA/TSQA) | Unifies forecasting / imputation / anomaly / classification / open-ended under QA paradigm. 200k QA pairs. Continual pretraining Mistral-7B / Llama-3-8B / Qwen-2.5-7B on TSQA. | Large QA dataset already exists; user's TSShapeQA is a specialization of the "open-ended reasoning" subset. | `[direct competitor]` |
| **TRQA: Time Series Reasoning QA Benchmark** (OpenReview 2025) | OpenReview | [ULQt51DRug](https://openreview.net/forum?id=ULQt51DRug) | *not found* | 6 tasks split into conventional (anomaly, classification) + advanced (characterization, comparison, transformation, temporal relation). Explicitly tries to decouple perception from reasoning. | Closest published TS benchmark to user's TSShapeQA. Risks direct overlap if the user publishes TSShapeQA. | `[direct competitor]` |

## 3. Adjacent & Foundational Works

| Title | Venue | Link | Summary | Why adjacent | Tag |
|---|---|---|---|---|---|
| **CapRL: Stimulating Dense Image Caption Capabilities via RL** (InternLM, ICLR 2026) | arXiv / OpenReview | [2509.22647](https://arxiv.org/abs/2509.22647) / [code](https://github.com/InternLM/CapRL) | RLVR for captioning: LVLM generates caption → **vision-free LLM** answers MCQ from caption → answer accuracy = reward. Pretraining on CapRL-5M matches Qwen2.5-VL-72B with +8.4% avg gain. | **This is the exact paradigm the user's training pipeline is missing.** Direct template for the "caption loss from downstream QA accuracy" that the user listed as Path 2b. Not yet ported to TS. | `[adjacent method — highly portable]` |
| **TS-CLIP: Time Series Understanding by CLIP** (EMNLP 2025) | ACL Anthology | [aclanthology.org/2025.emnlp-main.231](https://aclanthology.org/2025.emnlp-main.231/) | Contrastive TS↔text with a "synonym bank" to fight label collapse from sparse annotations. Zero-shot SOTA on 51 datasets. Claimed as first TS-text foundation model. | TS-side analog of CLIP. Directly addresses the "wrong_caption ≈ learned_caption" collapse the user observed — but via contrastive loss instead of RL. | `[adjacent method]` |
| **TimeART: Agentic TS Reasoning via Tool-Augmentation** (2601.13653) | arXiv | [2601.13653](https://arxiv.org/html/2601.13653v1) | 21 TS tools (stat methods + lightweight foundation models) orchestrated by an LLM agent for TSQA. | **Publishes the user's proposed Path 3 (numbers + tool agent).** If the user pivots to Path 3, this paper defines the SOTA to beat. | `[direct competitor for Path 3]` |
| **Chronos: Learning the Language of Time Series** (Amazon, 2024) | arXiv | [2403.07815](https://arxiv.org/abs/2403.07815) | Discrete bin-tokenization of TS into a T5 vocabulary, pretrained from scratch. Strong zero-shot forecasting. | User already uses Chronos-2 as encoder. Foundational — defines camp 2. | `[foundational]` |
| **Time-LLM: TS Forecasting by Reprogramming LLMs** (ICLR 2024) | OpenReview | [Unb5CVPtae](https://openreview.net/forum?id=Unb5CVPtae) | Reprograms frozen LLM via patch → text-prototype embeddings + prompt prefix. | Foundational for camp 1. Pre-dates the caption-SFT wave. | `[foundational]` |
| **Towards Time-Series Reasoning with LLMs** (Apple ML Research, 2025) | Apple blog | [link](https://machinelearning.apple.com/research/towards-time) | Empirical survey of LLM TS reasoning failure modes. | Possible citation for "caption fails at shape QA" framing. | `[survey]` |
| **MMTS-Bench / TSRBench / "Math Blind"** (2025-26) | arXiv / ICLR 2026 | [TSRBench GitHub](https://github.com/tianyi-lab/TSRBench) | Multi-task multi-modal TS reasoning benchmarks. Math-Blind (MATHGLANCE) specifically isolates perception from reasoning in MLLMs for diagrams/line-graphs. | Template for a *principled* TS-perception benchmark. | `[adjacent benchmark]` |
| **DCATS: Data-Centric Agent for TS Forecasting** (2508.04231) | arXiv | [2508.04231](https://arxiv.org/html/2508.04231v1) | LLM-as-data-curator for forecasting, bypassing direct TS reasoning. | Adjacent agentic approach. | `[adjacent method]` |

## 4. Observed Gaps / Opportunities

Factual gap observations (idea generation is the next skill, not this one):

- **CapRL's "caption → text-only LLM → MCQ accuracy = reward" has NOT been applied to time series.** TimeMaster uses RL but on classification + "insight quality" judge (not a decoupled QA probe). This is a clean, citeable gap.
- **No published TS-caption paper reports the template-collapse / non-discriminative-caption negative result explicitly with a counterfactual probe** (time-reversal, variance-injection). The user has this data already — it is a publishable diagnostic by itself if packaged correctly.
- **No published benchmark isolates shape-primitive perception (trend / extrema / volatility / period) at 256–1024 step length on OOD real data** the way TSShapeQA does. TRQA and MMTS-Bench cover adjacent territory but with different task decompositions.
- **The "learned caption ≤ wrong caption in-distribution" finding is, to our knowledge, unpublished in TS.** The equivalent in vision (CapRL's motivation, Prism framework) has been published and is now ICLR 2026.
- **Tool-augmented TS agents (TimeART, DCATS) already exist.** Path 3 is viable but is no longer green field. If user pivots there, they need a clear delta — e.g., tool selection via learned shape-feature routing, or shape-QA-specific tool library.
- **Synthetic-caption SFT as a standalone contribution is saturated.** OpenTSLM and ChatTS both published essentially this story at top venues within the past 12 months. LTSGen as "yet another synthetic caption dataset" is unlikely to land.
- **No paper has trained the TS captioner and a downstream text-only QA LLM as a closed loop** where the QA LLM grades the captioner's output. This is the CapRL transplant.

## 5. Anchor Set for Next Phase

Priority papers to deep-read before or during idea-generation:

1. **CapRL (2509.22647)** — read §3 (reward design) and §4 (ablation). Exact template for the most promising pivot.
2. **OpenTSLM (2510.02410)** — read §4 (method) and appendix training details. This is the baseline the user must clearly beat.
3. **TimeMaster (2506.13705)** — read reward composition + GRPO training recipe. Closest TS RL precedent; understand what's already done so the contribution isn't a duplicate.
4. **TS-CLIP (EMNLP 2025)** — read "label collapse" section. Alternative cure for the same disease; possibly complementary loss.
5. **TRQA (OpenReview ULQt51DRug)** — read benchmark construction §3. If the user wants TSShapeQA to count as a contribution, it needs to offer something TRQA does not (e.g., length-controlled perception probing, OOD-only splits, counterfactual probe integration).

---

**Next step:** invoke `idea-generation` skill with this deliverable + the EXPERIMENT_PROGRESS.md kill-test numbers as input. The gap-to-idea mapping should explicitly consider: (i) CapRL transplant to TS captioning, (ii) TS-CLIP-style contrastive retrofit on top of existing OpenTSLM, (iii) diagnostic-paper-only framing that publishes the negative result with the counterfactual probe protocol as a benchmark contribution, (iv) hybrid Path-3 tool agent with learned shape-feature routing.
