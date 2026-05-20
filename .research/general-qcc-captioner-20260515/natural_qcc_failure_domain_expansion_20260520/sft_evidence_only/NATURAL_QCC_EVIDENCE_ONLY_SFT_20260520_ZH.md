# Natural QCC Evidence-Only SFT Assets（2026-05-20）

本目录不改变 reviewer-positive 数据，只把 SFT 训练目标从带 `Answer label` 的 oracle caption 改为 evidence-only caption，减少模型只学答案标签的捷径。

- input positive JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/merged/natural_qcc_crossdomain_failure_expanded_positive.jsonl`
- output dir: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/sft_evidence_only`
- include options in qcond prompt: `False`
- train splits: `['train', 'dev']`
- eval split: `test`
- schema gate pass: `True`

## Files

| prompt control | train rows | eval rows | train sft | eval sft |
| --- | ---: | ---: | --- | --- |
| `no_question` | 75 | 29 | `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/sft_evidence_only/natural_qcc_failure_domain_expanded_evidence_only_no_question_train_sft.jsonl` | `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/sft_evidence_only/natural_qcc_failure_domain_expanded_evidence_only_no_question_test_sft.jsonl` |
| `qcond` | 75 | 29 | `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/sft_evidence_only/natural_qcc_failure_domain_expanded_evidence_only_train_sft.jsonl` | `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/sft_evidence_only/natural_qcc_failure_domain_expanded_evidence_only_test_sft.jsonl` |

## Guardrail

该变体只能用 deterministic semantic bridge 评估 evidence 是否支持答案；strict label bridge 预期会低估 evidence-only caption。
如果生成 caption 仍出现答案标签、选项字母或过短碎片，应报告为训练/解码失败。
