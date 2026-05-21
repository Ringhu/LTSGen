# Caption Model Longline Manifest 2026-05-21

This branch is the compact model-training branch created during branch
consolidation. It keeps the learned-caption code path and audit context from
`codex/question-repair-20260519-ready` without copying full generated outputs.

After the 2026-05-21 branch cleanup, this branch also restores the small
high-value Natural TS-QA/QCC artifacts that are still needed for caption-model
design review:

- `natural_qcc_case_quality_v1_20260521/`: 12 Chinese-first case studies with
  paired SVG time-series figures, two per domain.
- `self_contained_reasoning_qa_v2_20260521/`: 60 self-contained rule-reasoning
  QA rows, 10 per domain, plus GPT data-only probe report.
- `scenario_first_real_source_smoke_v2_20260521/`: report, audit, and summary
  only. The full 60-row JSONL/SFT/figure dump remains recoverable from history
  but is intentionally not restored here.
- `seed_quality_review_v1_20260521/`: first scripted review of the current
  small seed data, separating QA readiness from caption-training readiness.
- `NATURAL_QCC_RESEARCH_ROUTE_AND_REVIEWER_GATE_20260521_ZH.md`: agreed
  scenario-first Natural QCC route and reviewer gate policy.
- `natural_qcc_case_quality_v2_20260521/`: repaired 12-case Chinese-first
  case-study set, with simulator names removed from reader-facing scenes,
  clearer variable definitions, paired SVG figures, and evidence-only target
  captions.
- `self_contained_reasoning_qa_v3_20260521/`: repaired 60-row
  self-contained seed set. It keeps v2 QA/gold/support slots but removes
  `Answer label` and rule-template phrasing from `target_caption/output`.
- `self_contained_error_attribution_v1_20260521/`: attribution of the 15 GPT
  data-only wrong cases. These are diagnostic failures, not automatic data/gold
  defects.
- `seed_quality_review_v2_20260521/`: reviewer gate re-run over case-quality v2
  and self-contained v3; 72/72 QA-ready and 72/72 caption-train-ready.
- `natural_qcc_v3_seed_repair_report_20260521/`: illustrated Chinese report
  explaining this repair round, with summary figures and links to case-study
  time-series plots.

## Retained In Git

- Training/evaluation/remote scripts for natural QCC GPU smoke and cross-domain
  caption experiments.
- Regression tests for the imported QCC builders and audits.
- Compact reports, summaries, audit JSON/Markdown files, and result
  `*.pathspec` files under `.research/general-qcc-captioner-20260515/`.
- Token-budget and factuality diagnostics small enough to review in git.
- Current Natural TS-QA/QCC design-review seed artifacts that are small enough to
  inspect directly in git.
- The seed-quality reviewer script and regression test used before scaling.
- The agreed research-route and reviewer-gate document that governs future data
  repair, scaling, and training decisions.
- The v3 seed repair generators/reviewer reports needed to reproduce the
  current small smoke-ready seed set.

## Excluded From Git

- Checkpoints and model folders: `final_model/`, `checkpoint-*`,
  `*.safetensors`, `pytorch_model.bin`.
- Full generated prediction dumps from GPU runs.
- Full simulator traces and large intermediate datasets.
- EMNLP-facing benchmark figures and case-study assets; those belong on
  `emnlp-benchmark-pipeline`.
- Superseded early Natural QA pilots and full smoke figure dumps, unless a
  compact report is needed to explain the current caption-model route.

## Main Imported Areas

- `scripts/train/run_natural_qcc_gpu_smoke.py`
- `scripts/remote/run_natural_qcc_*`
- `scripts/eval/audit_natural_qcc_*`
- `scripts/eval/review_natural_qcc_seed_quality.py`
- `scripts/eval/collect_natural_qcc_gpu_result_manifest.py`
- `scripts/generate/build_natural_qcc_*`
- `tslm/scripts/generate_multisim_v5_smoke.py`
- `tslm/scripts/train_multisim_v5_smoke.py`

## Source Branch

The selected training material came from:

- `codex/question-repair-20260519-ready`

The restored Natural TS-QA/QCC review artifacts came from:

- `codex/natural-tsqa-benchmark-assets-20260520`
- `ef081c0` (`Add Natural QCC case quality pilot`)
- `1717200` (`Add self-contained TSQA case study report`)
- `5ed54e4` (`Add real-source Natural QCC smoke set`)

The branch was not merged wholesale. Files were imported by path whitelist so
that benchmark/paper assets and generated GPU outputs remain separated.
