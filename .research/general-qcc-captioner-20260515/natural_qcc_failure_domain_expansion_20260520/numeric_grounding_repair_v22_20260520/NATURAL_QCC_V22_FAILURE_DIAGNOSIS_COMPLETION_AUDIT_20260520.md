# Natural QCC v2.2 Failure Diagnosis Completion Audit（2026-05-20）

## Objective

用户要求：做一次目前为止的诊断，看看问题出在哪；如果需要 GPT Pro 的回复，可以整理一份 prompt 文档，让用户向 GPT Pro 提问做诊断。

Concrete deliverables:

1. 基于当前已有训练验证产物做诊断，不重复大训练。
2. 找出 v2.2 qcond/no-question 生成失败最可能原因。
3. 说明这个原因由哪些真实文件、脚本和指标支持。
4. 给出下一步最小验证方案。
5. 如有必要，整理可直接给 GPT Pro 的诊断 prompt。
6. 同步到 GitHub。

## Prompt-to-Artifact Checklist

| requirement | evidence | status |
| --- | --- | --- |
| 诊断已有训练验证结果 | `train_v22_e5_tok128_20260520/NATURAL_QCC_V22_TRAINING_VALIDATION_REPORT_20260520_ZH.md` | complete |
| 区分 target 数据与训练生成失败 | `NATURAL_QCC_V22_GENERATION_FAILURE_DIAGNOSIS_20260520_ZH.md` 中 target gate 与 generated failure 分开讨论 | complete |
| 检查训练/生成脚本高风险点 | `train_multisim_v5_smoke.py` collator contract 与 `run_natural_qcc_failure_domain_v22_pair_3090.sh` 未覆盖 `max_text_length` | complete |
| 做轻量 token-budget 诊断 | `natural_qcc_v22_token_budget_diagnosis_20260520.json` | complete |
| 明确主因 | 诊断报告结论为 `training_sequence_budget_failure`：v2.2 qcond output token 全被截断 | complete |
| 解释 qcond 空输出 | 报告说明 qcond 89/89 train rows `output_tokens_kept=0`，模型主要学习 EOS | complete |
| 解释 no-question 残缺模板 | 报告说明 no-question 平均只保留 `27.60` output tokens，13/89 为 0 | complete |
| 给出下一步最小验证 | 报告列出 token-budget gate、`max_text_length>=512`、5-example overfit、train-set generation | complete |
| GPT Pro prompt | `GPT_PRO_PROMPT_NATURAL_QCC_V22_FAILURE_DIAGNOSIS_20260520.md` | complete |

## Real Evidence Inspected

Training validation artifacts:

- qcond generated metrics: empty caption rate `1.0000`, mean caption chars `0.0`, semantic QA `0.0000`.
- no-question generated metrics: empty caption rate `0.1429`, mean caption chars `86.6`, semantic QA `0.0000`.
- target gates: semantic QA `1.0000`, caption quality gate `true`, slot factuality `1.0000`.

Code paths:

- `tslm/scripts/train_multisim_v5_smoke.py`
  - `MultiSimV5Collator` has a class fallback, but the actual parser default passed by `main()` is `--max_text_length 224`.
  - `_encode()` budgets output after prompt and EOS.
- `scripts/train/run_natural_qcc_gpu_smoke.py`
  - runner does not pass `--max_text_length`.
- `scripts/remote/run_natural_qcc_failure_domain_v22_pair_3090.sh`
  - v2.2 paired runner also does not pass `--max_text_length`.
- `tslm/scripts/generate_multisim_v5_smoke.py`
  - qcond raw caption is captured before cleaning; observed raw captions are empty, so cleaning is not the primary cause.

Token-budget diagnostic:

- v2.1 qcond: `zero_output_kept=2/89`, `mean_output_tokens_kept=52.61`.
- v2.2 qcond: `zero_output_kept=89/89`, `mean_output_tokens_kept=0.00`.
- v2.2 no-question: `zero_output_kept=13/89`, `mean_output_tokens_kept=27.60`.

## Coverage Check

This audit does not treat passing smoke audit as model success. Smoke audit only proves that the pipeline ran and produced metrics.

This audit also does not treat target gate success as training success. Target gate success proves that the supervision target is answerable when used directly, not that SFT learned to generate it.

The diagnosis is supported by the intersection of:

- clean target gates;
- failed generated captions;
- empty raw qcond generation;
- collator truncation mechanics;
- tokenizer-based token-budget measurement using the same remote model tokenizer.

## Missing Or Weak Points

No GPU rerun was performed in this diagnostic step. That is intentional: the current evidence already identifies a training input construction problem.

Residual risk:

- There may still be secondary issues in checkpoint save/load, LoRA wrapping, or `inputs_embeds` generation. These cannot explain the v2.2 qcond zero-label-token training condition, but should be checked after the text-budget fix if 5-example overfit still fails.

## Completion Decision

The objective is complete: a diagnosis was produced, the likely failure point is identified with concrete code/data evidence, next validation actions are specified, and an optional GPT Pro prompt was prepared.
