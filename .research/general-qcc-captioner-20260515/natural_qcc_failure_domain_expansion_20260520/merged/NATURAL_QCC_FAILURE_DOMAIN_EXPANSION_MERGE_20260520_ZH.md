# Natural QCC Failure-Domain Expansion Merge（2026-05-20）

本目录合并已经通过 reviewer gate 的 Natural-QCC positive pool。合并脚本不改写问题、不决定 gold answer，只做去重、schema 检查和分布汇总。

## Inputs

- `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520/natural_qcc_crossdomain_positive.jsonl`: `55` rows, source `{'aiopslab_official_v3': 12, 'citylearn': 9, 'grid2op': 12, 'traffic': 11, 'water': 11}`
- `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/dataset/natural_qcc_failure_domain_expansion_positive.jsonl`: `49` rows, source `{'grid2op': 19, 'traffic': 17, 'water': 13}`

## Merged Summary

- output positive JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/merged/natural_qcc_crossdomain_failure_expanded_positive.jsonl`
- rows: `104`
- duplicate id count: `0`
- missing required count: `0`
- by source: `{'aiopslab_official_v3': 12, 'citylearn': 9, 'grid2op': 31, 'traffic': 28, 'water': 24}`
- by split: `{'dev': 17, 'test': 29, 'train': 58}`
- answer distribution: `{'B': 33, 'D': 28, 'A': 16, 'C': 27}`
- schema gate pass: `True`
