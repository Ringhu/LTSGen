# Natural QCC v2.2 Token-Budget Fix Diagnostic Completion Audit（2026-05-20）

## Objective

用户要求：按照确认的思路，开始做下一轮测试与诊断。

Concrete deliverables:

1. 实现 token-budget preflight hard gate，防止 target caption 再次被静默截断。
2. 暴露 runner 参数，使下一轮可以跑 `max_text_length/max_prompt_length` 和小样本 overfit。
3. 在 3090 上验证旧配置会 fail、新配置会 pass。
4. 跑一次 v2.2 qcond 5-example overfit 诊断。
5. 收集生成、semantic QA、caption quality、slot factuality 结果。
6. 写中文诊断报告。
7. 同步到 GitHub。

## Prompt-to-Artifact Checklist

| requirement | evidence | status |
| --- | --- | --- |
| token-budget hard gate | `scripts/eval/check_natural_qcc_gpu_smoke_preflight.py` | complete |
| runner 暴露长度/小样本参数 | `scripts/train/run_natural_qcc_gpu_smoke.py` | complete |
| 远程 5-example 脚本 | `scripts/remote/run_natural_qcc_v22_tokenfix_overfit5_3090.sh` | complete |
| 单测覆盖 zero-output gate | `tests/eval/test_check_natural_qcc_gpu_smoke_preflight.py` | complete |
| 旧配置 fail | `token_budget_fix_diagnostics_20260520/preflight_expected_fail_224.json`, `preflight_pass=false` | complete |
| 新配置 pass | `token_budget_fix_diagnostics_20260520/preflight_expected_pass_768.json`, `preflight_pass=true` | complete |
| 5-example overfit pipeline complete | `qcond_overfit5_maxtext768_qwen3_4b/natural_qcc_smoke_pipeline_summary.json`, `complete=true` | complete |
| generated metrics | `qcond_overfit5_maxtext768_qwen3_4b/generate_eval_test_clean/metrics.json` | complete |
| semantic QA | `qcond_overfit5_maxtext768_qwen3_4b/generate_eval_test_clean/rule_qa/semantic_qa_metrics.json` | complete |
| caption quality | `qcond_overfit5_maxtext768_qwen3_4b/natural_qcc_caption_quality_audit.json` | complete |
| slot factuality | `qcond_overfit5_maxtext768_qwen3_4b/natural_qcc_slot_factuality_audit.json` | complete |
| Chinese report | `NATURAL_QCC_V22_TOKEN_BUDGET_FIX_DIAGNOSTIC_REPORT_20260520_ZH.md` | complete |

## Verification Evidence

Local tests:

- `python3 tests/eval/test_check_natural_qcc_gpu_smoke_preflight.py`: passed, 2 tests.
- `python3 tests/eval/test_audit_natural_qcc_gpu_smoke_result.py`: passed, 3 tests.
- `python3 tests/generate/test_build_natural_qcc_evidence_only_sft.py`: passed, 7 tests.
- `python3 tests/tslm/test_generate_multisim_v5_smoke.py`: passed, 3 tests.
- `bash -n scripts/remote/run_natural_qcc_v22_tokenfix_overfit5_3090.sh`: passed.

Remote preflight:

- old config `224/320`: `zero_output_kept=89`, `output_truncated=89`, `eos_only_supervision=89`, `preflight_pass=false`.
- new config `768/384`: `zero_output_kept=0`, `output_truncated=0`, `prompt_truncated=0`, `max_needed_tokens=394`, `preflight_pass=true`.

Remote 5-example overfit:

- generated rows: `5`.
- empty caption rate: `0.0000`.
- caption quality gate: `true`.
- semantic QA: `0.8000`.
- overall slot factuality: `0.2000`.

## Coverage Check

This audit does not treat non-empty generation as strict success. Non-empty generation only proves the EOS-only supervision bug was removed.

This audit also does not treat semantic QA `0.8000` as full overfit success, because slot factuality remains `0.2000` and generated captions include wrong numeric values.

The completion claim is therefore limited to: next-round diagnostic started and completed; token-budget hard gate validated; 5-example overfit exposed the next failure mode.

## Missing Or Weak Points

Not yet complete:

- strict 5-example overfit did not pass.
- no save-load parity probe yet.
- no token-level generation trace yet.
- no 1-example overfit yet.
- no full 89/35 smoke rerun, intentionally blocked by failed strict overfit.

These are next actions, not missing items from the requested “start next round testing and diagnosis” objective.

## Completion Decision

The objective is complete: the next diagnostic round was implemented, run on 3090, evaluated, documented, and prepared for GitHub sync.

