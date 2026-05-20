---
name: natural-tsqa-writer
description: Rewrite simulator-derived time-series QA into natural domain questions while preserving deterministic support-slot answer grounding. Use when creating or reviewing TS-QA/QCC case studies, converting verifier-slot prompts into scene-based natural QA, designing bilingual English/Chinese options, or preparing large-scale natural QA generation rules from simulator traces.
---

# Natural TS-QA Writer

## Purpose

Create time-series QA that reads like a normal domain question while keeping the answer auditable from deterministic support slots. The LLM may rewrite scene/question wording and review naturalness, but it must not decide the gold answer.

## Workflow

1. Start from a row with trace values, domain/source, original question, options, gold answer, and support slots.
2. Reject or revise rows whose answer depends on hidden metadata, unexplained thresholds, internal IDs, or visually ambiguous evidence.
3. Write a short scene that explains domain, variables, time axis, and any required domain rule.
4. Write one natural decision question. Do not expose verifier fields such as `segment_tag`, `window_start`, `post769_1025`, or slot names unless they are translated into user-facing context.
5. Write four human-readable options. Keep the original gold answer mapping, but make each option sound like an answer a domain user would choose.
6. Write evidence from support slots. Include enough numeric evidence to verify the gold answer.
7. Run reviewer gates before scaling: naturalness, answerability, accuracy risk, hidden context, and threshold clarity.

## Output Shape

Use this shape for case-study pilots:

```text
Scene: domain user + task context + variable meanings + time-axis clarification.
Question: one natural decision question.
Options: A-D, short user-facing answers.
Gold: original answer letter and label.
Evidence: support-slot facts that verify the answer.
Audit: original row id, original question, support slots, reviewer decision.
```

For Chinese-first reports, include `Scene EN/场景中文`, `Question EN/问题中文`, bilingual options, and bilingual evidence.

## Design Rules

Read `references/natural_tsqa_design_rules.md` when doing large-scale rewrites, adding new domains, or debugging reviewer failures.

Core rules:

- Make scene text carry context, not the question itself.
- Convert statistics into domain decisions: energy planning, risk review, service triage, policy comparison, stress check.
- Keep global/local time axes explicit when the plot is a local slice of a longer simulator run.
- Avoid asking about lead-lag or weak correlations unless the visual/statistical separation is strong.
- Avoid “material/significant/mixed” options unless the scene states the threshold or evidence has multiple metrics.
- Preserve answer accuracy by mapping options back to deterministic support slots.

## Reviewer Gate

Use an LLM reviewer only as a quality critic. Ask it for:

- `decision`: `keep`, `revise`, or `reject`
- `naturalness_score`: 1-5
- `answerability_score`: 1-5
- `accuracy_risk`: `low`, `medium`, or `high`
- concise Chinese reason and rewrite suggestions

Keep rows only when reviewer decision is `keep`, naturalness and answerability are both at least 4, and accuracy risk is `low`, unless the user explicitly wants borderline examples.
