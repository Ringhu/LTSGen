# Self-contained GPT Data-only Error Attribution v1（2026-05-21）

## 结论

这一步不是让 GPT 决定题目对错，而是解释 GPT data-only probe 为什么答错。
归因结果显示：15 条错误里没有一条被判为确定性 gold/data defect；大部分是模型 reason 已经算到正确语义，但最后输出了错误选项。

- probe 总样本：60
- data-only wrong：15
- data defect：0
- wrong by domain：{'citylearn': 5, 'traffic': 2, 'water': 6, 'aiopslab': 1, 'finrl': 1}
- attribution：{'model_reason_answer_inconsistency': 11, 'model_rule_application_error_with_water_clause_clarity_risk': 3, 'model_rule_application_error': 1}

## 为什么这很重要

如果把 `gpt_data_only_wrong` 直接当成 reject gate，就会误删很多本来规则和 gold 都没问题的样本。
更合理的做法是：它只触发人工归因；只有归因为规则歧义、特征不足或选项映射错误时，才删题或重写 gold。

## 逐条归因

| domain | gold | pred | attribution | decision |
| --- | --- | --- | --- | --- |
| `citylearn` | `reserve early` | `balanced reserve` | `model_reason_answer_inconsistency` | `hard_keep_for_seed` |
| `citylearn` | `reserve late` | `balanced reserve` | `model_reason_answer_inconsistency` | `hard_keep_for_seed` |
| `citylearn` | `reserve early` | `balanced reserve` | `model_reason_answer_inconsistency` | `hard_keep_for_seed` |
| `citylearn` | `reserve late` | `balanced reserve` | `model_reason_answer_inconsistency` | `hard_keep_for_seed` |
| `citylearn` | `reserve early` | `balanced reserve` | `model_reason_answer_inconsistency` | `hard_keep_for_seed` |
| `traffic` | `no clear congestion shock` | `partial recovery` | `model_reason_answer_inconsistency` | `hard_keep_for_seed` |
| `traffic` | `no clear congestion shock` | `congestion recovers` | `model_reason_answer_inconsistency` | `hard_keep_for_seed` |
| `water` | `pressure recovers after disturbance` | `manual review needed` | `model_rule_application_error_with_water_clause_clarity_risk` | `keep_for_seed_but_rewrite_water_rule_wording_before_scaling` |
| `water` | `pressure recovers after disturbance` | `manual review needed` | `model_rule_application_error_with_water_clause_clarity_risk` | `keep_for_seed_but_rewrite_water_rule_wording_before_scaling` |
| `water` | `pressure recovers after disturbance` | `persistent leak pressure risk` | `model_rule_application_error_with_water_clause_clarity_risk` | `keep_for_seed_but_rewrite_water_rule_wording_before_scaling` |
| `water` | `persistent leak pressure risk` | `pressure recovers after disturbance` | `model_reason_answer_inconsistency` | `hard_keep_for_seed` |
| `water` | `stable service` | `pressure recovers after disturbance` | `model_reason_answer_inconsistency` | `hard_keep_for_seed` |
| `water` | `stable service` | `pressure recovers after disturbance` | `model_reason_answer_inconsistency` | `hard_keep_for_seed` |
| `aiopslab` | `no dominant symptom` | `memory leak pattern` | `model_reason_answer_inconsistency` | `hard_keep_for_seed` |
| `finrl` | `bullish regime` | `severe drawdown risk` | `model_rule_application_error` | `keep_for_seed_after_manual_check` |

## Water 的额外说明

Water 错误最多，但这不等于 Water 题都坏了。几个错误是 probe 把“事件后水压反弹到至少 pre-1”理解成不能超过 pre，或者在恢复/稳定/人工复核的优先级上绕错。
因此当前判断是：这些样本可以保留为 seed，但 Water 的大规模扩增规则应写得更硬一些，例如明确“post 高于 pre 也满足恢复阈值”。

## 产物

- attribution JSONL: `.research/general-qcc-captioner-20260515/self_contained_error_attribution_v1_20260521/self_contained_data_only_error_attribution_v1.jsonl`
- summary JSON: `.research/general-qcc-captioner-20260515/self_contained_error_attribution_v1_20260521/self_contained_data_only_error_attribution_v1_summary.json`
- report: `.research/general-qcc-captioner-20260515/self_contained_error_attribution_v1_20260521/SELF_CONTAINED_DATA_ONLY_ERROR_ATTRIBUTION_V1_20260521_ZH.md`

