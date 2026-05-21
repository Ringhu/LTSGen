# Natural QCC Expansion Candidates（2026-05-19）

本目录用于准备 natural QCC 的下一批扩展候选。目标是在 reviewer gate 前先固定候选池，避免只围绕 balanced8 case study 手工扩展。

- schema: `.research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/schema_report.json`
- output: `.research/natural-tsqa-benchmark-20260520/candidates20/natural_tsqa_candidates20.jsonl`
- selected rows: `93`
- missing source files: `0`
- excluded pilot ids: `103`

## Selected By Source

| source | selected | split counts |
| --- | ---: | --- |
| `aiopslab_official_v3` | 13 | `{'dev': 3, 'test': 5, 'train': 5}` |
| `citylearn` | 20 | `{'dev': 5, 'test': 5, 'train': 10}` |
| `grid2op` | 20 | `{'dev': 3, 'test': 7, 'train': 10}` |
| `traffic` | 20 | `{'dev': 1, 'test': 7, 'train': 12}` |
| `water` | 20 | `{'dev': 6, 'test': 4, 'train': 10}` |

## Missing Files

| source | split | path |
| --- | --- | --- |

## Next Step

在包含完整 MultiSim v5 source JSONL 的 A100/3090 数据环境重新运行同一脚本；若 selected rows 达到每域目标，再对输出 JSONL 执行 natural rewrite 和 GPT-5.5 reviewer gate。
