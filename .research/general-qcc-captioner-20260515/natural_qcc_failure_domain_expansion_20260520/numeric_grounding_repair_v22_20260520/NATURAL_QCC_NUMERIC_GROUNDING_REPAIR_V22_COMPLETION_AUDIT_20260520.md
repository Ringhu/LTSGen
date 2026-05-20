# Natural QCC Numeric Grounding Repair v2.2 Completion Audit（2026-05-20）

Objective: 按“下一步先修 numeric grounding”的路线，开始做修复，并留下可运行、可审计、可继续训练的产物。

## Checklist

| requirement | evidence | status |
| --- | --- | --- |
| Add a deterministic slot factuality gate | `scripts/eval/audit_natural_qcc_slot_factuality.py` | done |
| Cover the gate with tests | `tests/eval/test_audit_natural_qcc_slot_factuality.py`; `python3 tests/eval/test_audit_natural_qcc_slot_factuality.py` passed 5 tests | done |
| Quantify v2.1 generated numeric grounding failure | `v21_qcond_slot_factuality_audit.json`, `v21_no_question_slot_factuality_audit.json` | done |
| Keep v2.1 target as sanity check | `v21_target_slot_factuality_audit.json`: overall slot factuality `1.0000` | done |
| Add a repair data path without leaking support slot values into prompt | `--numeric_grounding_repair` in `scripts/generate/build_natural_qcc_evidence_only_sft.py`; tests check required fields are named and slot values are not copied into prompt | done |
| Generate v2.2 repair SFT assets | `sft_evidence_only_v22/`; summary says all `124`, train+dev `89`, test `35`, schema gate `true` | done |
| Validate v2.2 target caption shape | `target_caption_quality_audit.json`: quality gate `true`, evidence shape `1.0000`, answer-label-only `0.0000` | done |
| Validate v2.2 target answerability | `target_semantic_qa/semantic_qa_metrics.json`: accuracy `1.0000` | done |
| Validate v2.2 target slot factuality | `target_slot_factuality_audit.json`: overall slot factuality `1.0000` | done |
| Write Chinese repair report | `NATURAL_QCC_NUMERIC_GROUNDING_REPAIR_V22_REPORT_20260520_ZH.md` | done |

## Key Results

| run | overall slot factuality | slot value pass | slot value recall | direction pass | horizon pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| v2.1 target | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| v2.1 qcond generated | 0.1143 | 0.1143 | 0.1486 | 0.5357 | 0.7500 |
| v2.1 no-question generated | 0.1143 | 0.1143 | 0.0811 | 0.6154 | 0.8400 |
| v2.2 target | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

## Scope

This completes the data/gate repair step. It does not claim v2.2 model improvement because v2.2 training has not been run yet.
