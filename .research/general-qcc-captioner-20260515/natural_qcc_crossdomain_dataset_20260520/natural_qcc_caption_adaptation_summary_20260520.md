# Natural QCC Caption Adaptation Summary（2026-05-20）

本报告把 QA accuracy 与 caption-quality audit 放在同一张表里，避免把答案标签捷径误认为 evidence-caption 训练成功。

- probe results: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/probe_eval/natural_qcc_probe_results.json`
- claim scope: `local_caption_adaptation_diagnostic_not_final_qcc_training`

## Diagnostics

| diagnostic | kind | strict QA | semantic QA | evidence shaped | answer-label-only | quality gate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `natural_oracle` | `oracle_evidence` | 1.0000 | 1.0000 | 0.9091 | 0.0000 | `True` |
| `natural_evidence_no_label` | `oracle_evidence_without_answer_label` | 0.6545 | 1.0000 | 0.9091 | 0.0000 | `True` |
| `nearest_caption_question_conditioned` | `train_split_nearest_caption_probe` | 0.4615 | 0.4615 | 0.7692 | 0.0000 | `False` |
| `nearest_caption_no_question` | `train_split_nearest_caption_probe` | 0.2308 | 0.2308 | 0.9231 | 0.0000 | `True` |
| `local_ranker_qcond` | `local_option_ranker_answer_label_shortcut` | 0.6154 | NA | 0.0000 | 1.0000 | `False` |
| `local_ranker_no_question` | `local_option_ranker_answer_label_shortcut` | 0.6154 | NA | 0.0000 | 1.0000 | `False` |

## Key Read

- nearest q-conditioned QA minus no-question: `0.2307`.
- nearest q-conditioned semantic QA minus no-question: `0.2307`.
- nearest q-conditioned quality minus no-question: `-0.1539`.
- natural evidence no-label strict-to-semantic QA delta: `0.3455`.
- local ranker qcond answer-label-only rate: `1.0`.
- semantic bridge 只诊断自然证据能否被确定性读出，不改变 gold；nearest-caption 是 evidence-shaped 弱探针；local ranker 是答案标签捷径诊断；三者都不能替代 GPU 上的 TS-RLM/Qwen QCC caption SFT。
