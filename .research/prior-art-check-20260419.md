# Prior-Art Recheck — 2026-04-19

> Primary Gemini-3.1-pro run returned 429 (model capacity exhausted on the
> Google side). Fell back to WebSearch on 6 targeted angles + 2 deep fetches.

## Target idea (summary)

**Title:** ShapeShift: Diagnosing, Benchmarking, and Fixing Counterfactual
Collapse in Time-Series Language Models.

**Key composite claims:**
1. Diagnosis — CFR metric + cross-family TS-LLM probing.
2. Benchmark — ShapeShift-TS, counterfactual-paired shape-QA dataset.
3. Method — Counterfactual-Pair Reward (CPR): CapRL-like QA accuracy reward +
   paired counterfactual consistency reward for TS captioners.

## Near-match ledger

| Paper | Venue / Date | Similarity | Which contribution overlaps? | Differentiation strategy |
|---|---|---|---|---|
| **Truth-Conditional Captioning of Time Series Data** (Jhamtani & Berg-Kirkpatrick) | EMNLP 2021 (arXiv 2110.01839) | DISTANT RELATIVE | Contribution 3 (caring about factual correctness in TS captioning) | Uses neurosymbolic learned-programs approach with text-only supervision. No RL, no counterfactual pairs, no downstream-QA reward. 5 years older than field's current SFT stack. Cite as foundational neurosymbolic alternative to our RL approach. |
| **TADACap: Time-series Adaptive Domain-Aware Captioning** (Fons et al.) | ICAIF 2024 (arXiv 2504.11441) | DISTANT RELATIVE | Contribution 3 (TS captioning) | Retrieval-based, domain-adaptive, image-level captioning for *plotted* TS in finance. No counterfactual probe, no RL reward, no shape-primitive faithfulness evaluation. Cite as retrieval baseline. |
| **Explanation-Driven Counterfactual Testing (EDCT)** | arXiv 2510.00047 (2025) | DISTANT RELATIVE | Contribution 1 (diagnosis — "Counterfactual Consistency Score") | Vision-language only. **Evaluation-only**, not a training objective. Uses inpainting edits on images (no TS). Our Contribution 3 (CPR training reward) has zero overlap. Cite EDCT as the conceptual parent for our CFR metric in a different modality. |
| **Benchmarking Counterfactual Interpretability in DL Models for TS Classification** | arXiv 2408.12666 (2024) | DISTANT RELATIVE | Contribution 2 (counterfactual + TS) | About XAI-style counterfactual *explanations* for TS classifiers (what minimal input change flips a classifier). We do the opposite: probe whether LLM outputs flip correctly under known-semantic transforms of the input. Cite and clearly distinguish purpose. |
| **TSOrchestr / Conversational Time Series Foundation Models** | arXiv 2512.16022 (2025-12) | DISTANT RELATIVE | Contribution 3 (LLM-as-judge with faithfulness-based reward for TS) | Uses LLM as ensemble orchestrator for forecasting models, with SHAP-based faithfulness reward. Different task entirely (forecasting ensemble weights, not shape-QA captioning). Cite. |
| **TDRM: Smooth Reward Models with Temporal Difference** | arXiv 2509.15110 (2025-09) | DISTANT RELATIVE | Contribution 3 (reward design for LLM RL) | About reward-model smoothness across reasoning steps (PRM angle). Orthogonal. Could cite for broader reward-model background but not a collision. |
| **CapRL** | ICLR 2026 (arXiv 2509.22647) | CLOSE VARIANT | Contribution 3 (accuracy-as-reward for captioning) | Already in lit-review. Vision only. Uses single-image accuracy reward; no paired-counterfactual term. Our novelty is the **paired consistency reward**, which is naturally TS-motivated (time reversal and variance injection admit crisp label flips). Must cite prominently and make CPR-minus-pair-term the key ablation. |
| **TimeMaster** | arXiv 2506.13705 (2025-06) | CLOSE VARIANT | Contribution 3 (RL + TS + LLM) | Already in lit-review. Composite reward = format + classification accuracy + LLM-judged insight quality. No paired-counterfactual term, no caption-for-downstream-QA structure. Must cite prominently. |
| **TRQA** | OpenReview ULQt51DRug | DISTANT RELATIVE | Contribution 2 (TS reasoning benchmark) | Already in lit-review. Task-completion oriented, not counterfactual-pair oriented. Cite and show orthogonality in a side-by-side table. |

## Any identical match?

**No.** No paper combines all three of: (a) TS modality, (b) paired-
counterfactual reward signal *at training time*, (c) downstream frozen
vision-free / text-only LLM QA as the reward verifier. Each two-way
intersection has a published near-neighbor, but the three-way intersection is
unoccupied as of 2026-04.

## Dangerous close variants emerging

The field is converging on this region. Explicit watch-list for the next
6-8 weeks:

- Any ICLR 2026 reviewer-revealed NeurIPS 2026 main-track submission that
  ports CapRL to time-series (highly plausible given CapRL's visibility).
  Submitted 2026-05; abstracts visible mid-2026-05 on OpenReview.
- Any ChatTS v2 / TimeMaster v2 preprint adding counterfactual invariance
  to their training loop. ByteDance and the TimeMaster team are both active.
- TRQA authors expanding the benchmark with input-perturbation splits.

Risk is real but not realized yet. Acceptable risk for 5-6 month ICLR 2027
timeline; moderate-to-high risk for NeurIPS 2026 main track — preferable to
submit a strong preprint before 2026-06 to establish priority.

## Final verdict

**🟢 GREEN with watchlist.** No identical or near-identical published work.
Distant relatives require clear related-work positioning but none invalidate
the three-way composite contribution.

### Recommended amendments before `research-contract`

1. Promote CapRL comparison from "prior work" to **the main ablation arm**:
   Method section must show CapRL-pure-accuracy reward vs CapRL + CPR. The
   delta is our story.
2. Add EDCT (vision) as the CFR-concept-parent citation in the diagnosis
   section, explicitly naming the cross-modality transfer gap.
3. Note TADACap and Truth-Conditional TS Captioning in related-work but
   do not dwell; they are far enough away that a one-paragraph subsection
   suffices.
4. Plan a "priority preprint" by 2026-06-15 to establish timestamp before
   the NeurIPS 2026 review cycle exposes potential competitors.

## Next step

Per `idea-generation` skill handoff rule: proceed to `research-contract`
before any experimental code is written.
