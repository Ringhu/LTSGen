# Natural TS-QA Design Rules

## Positive Pattern

Natural TS-QA should look like:

1. A domain user has a practical question.
2. The scene explains the data window and variables.
3. The question asks for a decision or interpretation.
4. Options are ordinary answers, not slot labels.
5. Evidence verifies the gold answer from deterministic slots.

Example:

```text
Scene: A traffic engineer compares an adaptive signal policy against a fixed-signal baseline. Queue length is lower-is-better.
Question: Did the adaptive signal policy improve queueing in this window?
Gold evidence: adaptive mean queue 2.91, fixed baseline 2.56.
```

## Anti-Patterns

- Asking about internal IDs: `post769_1025`, `w512_1536`, `bucket06`, `segment_tag`.
- Mentioning global simulator steps without explaining how they map to the plotted local window.
- Asking lead-lag when the lines are visually close and support slots show weak separation.
- Asking pure metadata questions from numeric traces alone.
- Using thresholds that are not stated in the scene or evidence.
- Options like `mixed effect`, `material change`, or `unclear relation` when only one simple statistic is provided.
- Letting the LLM choose or change the gold answer.

## Domain Rewrite Patterns

### Grid2Op

Prefer operator-facing questions: overload risk, line-disconnection effect, stress increase/decrease, reserve margin.

If using counterfactual traces, state:

- what intervention happened,
- whether the plot is factual, intervention, or intervention-minus-factual,
- whether positive values mean stress increases or decreases,
- how global event time relates to local plot time.

Avoid case studies where lead-lag is visually indistinguishable or the answer is `no clear lead` without strong evidence.

### CityLearn

Prefer building-control questions: when to reserve battery/grid supply, whether demand is rising, whether solar/context changes demand planning.

Do not leave it as “which half has a higher mean” unless the scene turns that comparison into an energy-control decision.

### FinRL

Name the asset directly in the scene, for example `MRK` or `JPM`. Do not say “ticker named in the question.”

Prefer risk/portfolio questions: drawdown severity, volume anomaly, regime review. Define thresholds in scene or evidence when options are severity labels.

Use dates when available; avoid local step indices in reader-facing evidence unless the task is explicitly about local windows.

### Water

Prefer operator-facing service questions: stable service, low-pressure risk, leak-stressed network, recovery after event.

If the answer relies on pressure or flow thresholds, state the threshold or include evidence that makes the label defensible.

### Traffic

Prefer traffic-engineering policy questions: did adaptive control reduce queueing, did congestion worsen, did signal policy help.

State metric direction: lower queue is better, higher speed is better, high occupancy may indicate congestion.

Avoid `mixed effect` unless evidence includes multiple metrics that genuinely disagree.

### AIOpsLab

Prefer SRE triage questions from numeric telemetry: memory pressure building/easing, network burst location, CPU pressure.

Do not use application, service role, fault family, or provenance questions as pure TS-QA unless official metadata is included in the scene.

## Reviewer Pass Criteria

For pilot-quality examples:

- Reviewer decision: `keep`
- Naturalness score: at least 4
- Answerability score: at least 4
- Accuracy risk: `low`
- No unexplained internal IDs in the reader-facing question
- Gold answer traceable to support slots

For large-scale generation, store reviewer output next to each rewritten row and keep rejected/revised rows out of positive case-study sets.
