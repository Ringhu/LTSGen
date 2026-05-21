# Literature Scouting Brief — TS→Language Interface (20260419)

## Core Research Question

Is the pipeline "time series → model-generated natural-language caption → frozen LLM → QA" still a viable research direction in 2026, given that we have empirically shown the learned caption carries almost no input-discriminative information, while an *oracle* caption drives downstream QA accuracy from ~32% (meta-only) to 96-100%?

More precisely, I need the field's answer to three nested questions:

1. **Training-objective question.** Existing TS captioners are trained with next-token LM loss on reference captions. This objective has no mechanism that forces the caption to encode input-specific shape. Have recent papers (2024-2026) introduced training objectives that *do* force discriminative grounding of TS→text — e.g., contrastive/InfoNCE on (TS, text) pairs, RL-from-downstream-QA-accuracy, VLM-style pretraining with hard negatives, curriculum with counterfactual supervision?
2. **Architecture question.** Is "TS encoder + cross-attention into frozen/finetuned LLM" (Flamingo-style) still the default for TS-LLM, or has the field moved to patch-tokenized TS directly in the LLM vocabulary (a la Chronos, TimeLLM, Moirai), and do those alternatives avoid the captioning trap?
3. **Benchmark question.** Are there established TS-shape-QA / TS-reasoning benchmarks that specifically isolate "did the model perceive the series" from "did the LLM reason with domain knowledge"? We had to build our own TSShapeQA because existing ones (TSAQA, TS-MCQ, FREDQA) confound the two.

## Known Anchor Works

- **OpenTSLM** (our own implementation, 2026, Qwen3-4B + Chronos-2 + Flamingo cross-attention trained on LTSGen synthetic captions)
- **Chronos / Chronos-2** (Amazon, 2024-2025) — pretrained TS encoder we use
- **TimeLLM** (ICLR 2024, Jin et al.) — reprogramming LLM for TS forecasting via prompt prefix
- **LLaVA / Flamingo** (2022-2024) — vision MLLM templates we inherited
- **TSAQA / Time-MMD** — existing TS-QA benchmarks we tried and found confounded

## Search Scope

- **Time window**: 2024-01 to 2026-04 (most critical), with a back-reference to 2023 foundational works
- **Venue priority**: NeurIPS / ICML / ICLR / KDD / AAAI / ACL / EMNLP main track + strong workshops (TSL @ NeurIPS, AI4TS @ ICML, TS4H). OpenReview-visible submissions count.
- **Code availability**: prefer open-source; flag papers without released code
- **Adjacent fields to probe**:
  - Vision-Language alignment literature for the *negative-result-of-caption* (e.g., has anyone in VLM shown learned captions are template-like and do not help downstream VQA?)
  - Multimodal RL-from-VQA-accuracy (CLIP-score reward, VQA reward for image captioning)
  - Tool-augmented LLMs for structured data reasoning (spreadsheet QA, chart QA — chart QA is the closest analog to TS QA)
  - TS foundation models that skip language entirely (Chronos, Moirai, TimesFM, Lag-Llama)

## What I want back

For each paper found, provide:

- Title, authors, venue, year
- arXiv/OpenReview link
- Code repo link (if any)
- 3-sentence summary: **problem / method / headline result**
- Why it's relevant to (a), (b), (c), or (d) below
- Tag: `[direct competitor | adjacent method | foundational | survey | negative-result]`

Specifically look for papers that touch:

- **(a) TS-to-text / TS captioning beyond LM loss**: contrastive TS-text pretraining, RL-from-QA-accuracy for TS captioning, counterfactual / hard-negative augmentation, shape-grounded supervision
- **(b) TS-LLM alignment without paired caption data**: TS-CLIP-style contrastive, numeric-token-as-prompt, tool-augmented TS agents, retrieval-augmented TS reasoning
- **(c) Shape-aware TS QA / reasoning benchmarks**: any benchmark that isolates perception of the series from domain knowledge. Include TS anomaly reasoning, TS forecasting rationalization, TS visualization (chart) QA
- **(d) Negative results on learned captions**: any paper (TS *or* vision) that explicitly reports generated captions underperforming raw data for downstream QA, and their diagnosis (template collapse, hallucination, lack of discriminativity). Even a single well-cited negative-result paper would change our framing.

**Return format**: markdown table ranked by relevance. Include a short (≤5 bullets) "landscape observation" paragraph at the top summarizing what methodological camps dominate the 2024-2026 TS-LLM literature.

## What I am NOT asking Gemini to do

- Do not propose research ideas (that's the next skill, not this one)
- Do not evaluate our project (you're scouting the field, not reviewing us)
- Do not recommend a pivot direction (leave that to Claude's synthesis step)

Just return the raw landscape and gaps as factual observations.
