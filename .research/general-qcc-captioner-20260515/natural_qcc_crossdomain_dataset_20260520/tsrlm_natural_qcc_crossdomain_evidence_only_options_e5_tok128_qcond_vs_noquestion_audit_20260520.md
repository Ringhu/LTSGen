# Natural QCC GPU QCond vs No-Question Audit（2026-05-20）

- status: `no_qconditioning_gap`
- summary: q-conditioned generated-caption QA 没有超过 no-question 对照，不能作为 QCC conditioning 成功。
- claim scope: `Report as training/interface failure or insufficient conditioning signal.`
- min gap: `0.05`

## Run Comparison

| run | audit pass | rows | QA acc | empty |
| --- | ---: | ---: | ---: | ---: |
| q-conditioned | `True` | 13 | `0.0769` | `0.6923` |
| no-question | `True` | 13 | `0.1538` | `0.6154` |

## Gap

- qcond minus no-question: `-0.0769`

## Guardrail

只有两条 GPU smoke 的单 run audit 都 `audit_pass=true` 时，才能解释 Q-conditioning gap。
如果 no-question 持平或更好，应报告为 Q-conditioning 未被证明，而不是 QCC 成功。
