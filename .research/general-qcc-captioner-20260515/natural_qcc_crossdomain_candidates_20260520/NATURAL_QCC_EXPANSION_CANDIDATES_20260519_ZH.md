# Natural QCC Expansion Candidates（2026-05-19）

本目录用于准备 natural QCC 的下一批扩展候选。目标是在 reviewer gate 前先固定候选池，避免只围绕 balanced8 case study 手工扩展。

- schema: `/home/cris/Research/LTSGEN/.research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/schema_report.json`
- output: `.research/general-qcc-captioner-20260515/natural_qcc_crossdomain_candidates_20260520/natural_qcc_crossdomain_candidates.jsonl`
- selected rows: `60`
- missing source files: `3`
- excluded pilot ids: `43`

## Selected By Source

| source | selected | split counts |
| --- | ---: | --- |
| `aiopslab_official_v3` | 12 | `{'dev': 2, 'test': 5, 'train': 5}` |
| `citylearn` | 12 | `{'dev': 2, 'test': 3, 'train': 7}` |
| `grid2op` | 12 | `{'dev': 4, 'test': 2, 'train': 6}` |
| `traffic` | 12 | `{'dev': 1, 'test': 3, 'train': 8}` |
| `water` | 12 | `{'dev': 2, 'test': 1, 'train': 9}` |

## Missing Files

| source | split | path |
| --- | --- | --- |
| `finrl_scaled` | `dev` | `/home/cris/Research/LTSGEN/.research/general-qcc-captioner-20260515/finrl_broad_scaled_v1/finrl_broad_scaled_v1_dev.jsonl` |
| `finrl_scaled` | `test` | `/home/cris/Research/LTSGEN/.research/general-qcc-captioner-20260515/finrl_broad_scaled_v1/finrl_broad_scaled_v1_test.jsonl` |
| `finrl_scaled` | `train` | `/home/cris/Research/LTSGEN/.research/general-qcc-captioner-20260515/finrl_broad_scaled_v1/finrl_broad_scaled_v1_train.jsonl` |

## Next Step

在包含完整 MultiSim v5 source JSONL 的 A100/3090 数据环境重新运行同一脚本；若 selected rows 达到每域目标，再对输出 JSONL 执行 natural rewrite 和 GPT-5.5 reviewer gate。
