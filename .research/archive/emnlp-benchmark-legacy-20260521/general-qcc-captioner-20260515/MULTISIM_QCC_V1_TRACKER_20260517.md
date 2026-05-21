# MultiSim-QCC-v1 Tracker

| Run ID | Milestone | Purpose | System / Variant | Data / Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| MSQCC-001 | M0 | Lock multi-simulator contract and plan | docs | Grid2Op + CityLearn + FinRL | checklist | MUST | DONE | Contract and plan written before data/training. |
| MSQCC-002 | M1 | Build all-domain mixed data | data builder | `multisim_qcc_v1` | schema gate, domain balance, overlap | MUST | DONE | A100 schema gate true; train 2571 rows = Grid2Op 1153 + CityLearn 770 + FinRL 648; train-vs-heldout overlap 0. |
| MSQCC-003 | M2 | First all-domain smoke training | `local_gated_qprefix` CE | all-domain train/eval | train loss, eval loss | MUST | DONE | A100 GPU0 tmux `ltsgen_msqcc_v1_ce_20260517`; 7713 steps, final eval loss 0.2261, train loss 0.261, final model saved. |
| MSQCC-004 | M3 | Per-domain heldout evaluation | domain evaluators | Grid2Op/CityLearn/FinRL dev/test | QA, empty, per-task | MUST AFTER TRAIN | DONE | Complete: Grid2Op 0.5548, CityLearn 0.3241, FinRL 0.7778; empty 0. |
| MSQCC-005 | M4 | Diagnose first failure modes | analysis | generated captions + QA | worst domain, Grid2Op CF, empty | SHOULD | DONE | Status `ambiguous`: CityLearn is worst-domain; Grid2Op CF has dev/test split artifact; FinRL high score has template/answer-phrase risk. |
| MSQCC-006 | M5 | Slot-loss follow-up | auxiliary slot head | all-domain + slots | slot factuality + QA | NEXT | DEFERRED | Motivated by AS-045/046/047. |
| MSQCC-007 | M5 | SCL follow-up | CE+SCL | all-domain hard negatives | QA + factuality + margins | NEXT | DEFERRED | Only after CE baseline is measured. |
| MSQCC-008 | M6 | New simulator adapter | AIOpsLab/SUMO/WNTR | v2 data | schema gate + oracle gap | NICE | DEFERRED | Do not block v1. |
