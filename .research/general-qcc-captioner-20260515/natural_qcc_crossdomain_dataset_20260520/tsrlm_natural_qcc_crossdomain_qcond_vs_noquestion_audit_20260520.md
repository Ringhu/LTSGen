# Natural QCC GPU QCond vs No-Question Audit（2026-05-20）

- status: `incomplete_or_blocked`
- summary: q-conditioned 或 no-question GPU smoke 尚未完整完成，不能解释 Q-conditioning gap。
- claim scope: `No q-conditioning training comparison allowed.`
- min gap: `0.05`

## Run Comparison

| run | audit pass | rows | QA acc | empty |
| --- | ---: | ---: | ---: | ---: |
| q-conditioned | `False` | 0 | `None` | `None` |
| no-question | `False` | 0 | `None` | `None` |

## Gap

- qcond minus no-question: `None`

## Guardrail

只有两条 GPU smoke 的单 run audit 都 `audit_pass=true` 时，才能解释 Q-conditioning gap。
如果 no-question 持平或更好，应报告为 Q-conditioning 未被证明，而不是 QCC 成功。
