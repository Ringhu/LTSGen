# Grid2Op Medium-Horizon Case Study

This directory contains the GitHub-renderable case-study report for the current Grid2Op TS-QA pilot.

- [grid2op_case_study.md](grid2op_case_study.md): collapsible report with time-series plots, QA prompts, captions/evidence, and method answers.
- `figures/`: PNG time-series plots for 3 observation cases and 2 counterfactual cases.
- `selected_cases.json`: selected QA records and case specs.
- `manifest.json`: compact manifest for downstream scripts.

The report is meant to support the paper framing that task-conditioned, verifiable evidence captions provide a short and reliable interface, while generic captions and sampled numeric prompts can fail on localization, aggregation, and paired-trace comparison tasks.
