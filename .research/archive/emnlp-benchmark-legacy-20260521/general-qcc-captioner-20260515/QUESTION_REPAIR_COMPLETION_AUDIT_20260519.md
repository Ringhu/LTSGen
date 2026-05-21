# Question Repair Completion Audit (2026-05-19)

## Objective

Start the question-repair step for MultiSim/QCC case-study rows, document the repair in Chinese, and sync the result to GitHub for review.

## Deliverables

- `scripts/generate/repair_multisim_questions.py`
- `.research/general-qcc-captioner-20260515/QUESTION_REPAIR_MULTISIM_20260519_ZH.md`
- `.research/general-qcc-captioner-20260515/question_repair_20260519/repaired_multisim_v5_balanced8_predictions.jsonl`
- `.research/general-qcc-captioner-20260515/question_repair_20260519/repaired_multisim_v5_balanced8_audit.json`
- `.research/general-qcc-captioner-20260515/question_repair_20260519/repaired_multisim_v3_eval_source_dev_sft_smoke64.jsonl`
- `.research/general-qcc-captioner-20260515/question_repair_20260519/repaired_multisim_v3_eval_source_dev_sft_smoke64_audit.json`

## Checks

- Script syntax check: `python3 -m py_compile scripts/generate/repair_multisim_questions.py`
- Case-study repair command:
  `python3 scripts/generate/repair_multisim_questions.py --input .research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/generate_eval_balanced8_clean/predictions.jsonl --output .research/general-qcc-captioner-20260515/question_repair_20260519/repaired_multisim_v5_balanced8_predictions.jsonl --report .research/general-qcc-captioner-20260515/question_repair_20260519/repaired_multisim_v5_balanced8_audit.json`
- SFT smoke repair command:
  `python3 scripts/generate/repair_multisim_questions.py --input .research/general-qcc-captioner-20260515/multisim_qcc_v3_stable_dataflow/multisim_qcc_v3_stable_dataflow/multisim_qcc_v3_stable_dataflow_eval_source_dev_sft.jsonl --output .research/general-qcc-captioner-20260515/question_repair_20260519/repaired_multisim_v3_eval_source_dev_sft_smoke64.jsonl --report .research/general-qcc-captioner-20260515/question_repair_20260519/repaired_multisim_v3_eval_source_dev_sft_smoke64_audit.json --max_rows 64`

## Results

Case-study 48-row audit:

- `clarity_gate_pass`: true
- `missing_context_count`: 0
- `support_slot_numeric_leak_count`: 0
- `repaired`: 41
- `needs_metadata_context`: 5
- `weak_rule`: 2

SFT smoke 64-row audit:

- `clarity_gate_pass`: true
- `missing_context_count`: 0
- `support_slot_numeric_leak_count`: 0
- `repaired`: 62
- `needs_metadata_context`: 2

## Interpretation

The repair step is started and mechanically usable. It does not claim that every row is now paper-ready. Rows marked `needs_metadata_context` need official metadata in the prompt or exclusion from pure TS grounding evaluation. Rows marked `weak_rule` need a clearer threshold/category definition before they should be used as case-study examples.
