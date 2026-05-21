# Review Card — Idea 7

_Reviewed by gpt-5.4, single-idea isolation._

## Scores

1. **Novelty — 2/5**  
   Applying contrastive decoding to suppress a unimodal prior at inference time is a straightforward transplantation of an existing decoding trick, and the only new element is the time-series captioning target, which is too thin to sustain a strong novelty claim.

2. **Technical feasibility — 4/5**  
   This is very buildable in 2–3 months by one student because it requires no retraining of the backbone, only decoder engineering, prior selection/calibration, and a careful evaluation suite.

3. **Baseline compatibility — 5/5**  
   It fits the existing OpenTSLM pipeline almost perfectly since it uses the frozen checkpoint and only changes inference-time token selection.

4. **Implementation complexity — 2/5**  
   The implementation is comparatively light: dual-model decoding, logit alignment, alpha tuning, and evaluation; this is good for execution but bad for perceived research depth.

5. **Expected improvement magnitude — 2/5**  
   Given your own evidence that the learned captions are nearly input-agnostic under counterfactual perturbation, the more likely outcome is degraded genericity and fluency rather than a true recovery of latent grounding.

6. **Risk of being scooped in the next 6 months — 4/5**  
   This is exactly the kind of low-cost inference-time patch that many groups can try once they notice modality collapse, so even if not already posted, it is highly scoopable.

## Final verdict

**KILL**

The core failure mode is that this idea assumes the model already encodes useful time-series-grounded evidence in token logits or hidden states and that generation collapse is merely a decoding imbalance. Your own pilot evidence does not support that assumption: a **2.78% correct-flip rate under counterfactual perturbation** is much more consistent with missing or extremely weak grounding than with a recoverable prior-overpowering effect. If the model never learned to place TS-sensitive information into the next-token distribution, contrastive decoding will just subtract generic language priors and produce awkward or less fluent nonsense, not grounded shape descriptions.

A top-tier reviewer will also ask the obvious question: **why should inference-time logit subtraction reveal information that supervised training never made behaviorally accessible?** Without strong mechanistic evidence that TS-conditioned signals are present but suppressed, this looks like post hoc decoding alchemy.

## Weaknesses

The strongest reason a reviewer at ICLR 2027 / NeurIPS 2026 would **reject** this paper is that it likely fixes the *symptom* of generic captioning rather than the *cause* of missing grounding, and the central claim is under-motivated by the current evidence. If counterfactual changes barely affect outputs, reviewers will infer that the model did not internalize the relevant TS semantics during training, making decoding-time surgery conceptually misaligned.

A second rejection reason is weak research contribution relative to prior art. Even if it works modestly, the paper may read as “contrastive decoding, but for time-series captions,” which is usually not enough for a main-track acceptance unless the gains are unexpectedly large, robust, and accompanied by convincing analysis of when latent grounding exists.

A third concern is evaluation fragility. If success is shown mainly on the same counterfactual probe used to motivate the method, reviewers may worry that the decoder is merely being pushed toward lexical variability rather than genuine time-series faithfulness; you would need held-out QA, OOD perturbations, and human/automatic faithfulness checks to avoid that criticism.

## Load-bearing result

The single most load-bearing empirical result is this: **contrastive decoding must dramatically increase counterfactual sensitivity without sacrificing downstream usefulness**, ideally moving correct-flip rate from near-zero to something unambiguously nontrivial while also improving shape-QA accuracy over vanilla decoding and over a wrong-caption control. If this does not happen, the whole “latent grounding is present but suppressed by the text prior” hypothesis collapses.

More specifically, you need to show that the decoded caption changes in the *correct semantic direction* under time reversal / variance injection / morphology edits, not merely that the text becomes more diverse. A convincing paper would also need evidence that gains persist across datasets and priors and are not just alpha-tuned artifacts.

## Prior-art collision risk

The most dangerous nearby paper is **CapRL (ICLR 2026)**, even though it is training-time RL rather than inference-time decoding. Reviewers will immediately frame your work against it and may conclude that if one wants grounded captions, reward-based optimization with QA feedback is the principled route, while your method is only a lightweight heuristic patch.

You also need to differentiate from the broader family of **contrastive decoding / decoding-by-subtraction papers in NLP and VLMs** from 2023–2025, because your method may otherwise appear to be a domain transfer with limited conceptual novelty. Among the listed works, **TimeMaster (2506.13705)** is also relevant as a foil: it already argues that better rewards are needed for reasoning-quality captions, which weakens the case that decoding alone can rescue a collapsed SFT model.
