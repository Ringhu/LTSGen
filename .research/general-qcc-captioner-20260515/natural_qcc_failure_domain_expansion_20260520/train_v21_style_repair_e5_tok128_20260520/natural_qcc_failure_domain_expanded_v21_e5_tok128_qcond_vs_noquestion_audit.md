# Natural QCC GPU QCond vs No-Question Audit（2026-05-20）

- status: `qconditioning_gap_positive`
- summary: q-conditioned generated-caption QA 明显高于 no-question 对照，可作为 smoke-level Q-conditioning 正信号。
- claim scope: `Cross-domain smoke only; not a full method claim.`
- min gap: `0.05`

## Run Comparison

| run | audit pass | rows | QA acc | empty |
| --- | ---: | ---: | ---: | ---: |
| q-conditioned | `True` | 35 | `0.3143` | `0.2857` |
| no-question | `True` | 35 | `0.1143` | `0.6571` |

## Gap

- qcond minus no-question: `0.2`

## Guardrail

只有两条 GPU smoke 的单 run audit 都 `audit_pass=true` 时，才能解释 Q-conditioning gap。
如果 no-question 持平或更好，应报告为 Q-conditioning 未被证明，而不是 QCC 成功。
