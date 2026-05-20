# Natural QCC Expansion Candidates（2026-05-19）

本目录用于准备 natural QCC 的下一批扩展候选。目标是在 reviewer gate 前先固定候选池，避免只围绕 balanced8 case study 手工扩展。

- schema: `.research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/schema_report.json`
- output: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/candidates/natural_qcc_failure_domain_candidates.jsonl`
- selected rows: `72`
- missing source files: `0`
- excluded pilot ids: `60`

## Selected By Source

| source | selected | split counts |
| --- | ---: | --- |
| `grid2op` | 24 | `{'dev': 4, 'test': 8, 'train': 12}` |
| `traffic` | 24 | `{'dev': 2, 'test': 7, 'train': 15}` |
| `water` | 24 | `{'dev': 6, 'test': 6, 'train': 12}` |

## Missing Files

| source | split | path |
| --- | --- | --- |

## Next Step

在包含完整 MultiSim v5 source JSONL 的 A100/3090 数据环境重新运行同一脚本；若 selected rows 达到每域目标，再对输出 JSONL 执行 natural rewrite 和 GPT-5.5 reviewer gate。
