# Natural QCC Expansion Candidates（2026-05-19）

本目录用于准备 natural QCC 的下一批扩展候选。目标是在 reviewer gate 前先固定候选池，避免只围绕 balanced8 case study 手工扩展。

- schema: `.research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/schema_report.json`
- output: `.research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates.jsonl`
- selected rows: `35`
- missing source files: `15`
- excluded pilot ids: `43`

## Selected By Source

| source | selected | split counts |
| --- | ---: | --- |
| `aiopslab_official_v3` | 35 | `{'dev': 7, 'test': 14, 'train': 14}` |

## Missing Files

| source | split | path |
| --- | --- | --- |
| `grid2op` | `dev` | `.research/general-qcc-captioner-20260515/grid2op_broad_v5_semantic_anchor/grid2op_broad_v5_semantic_anchor_dev.jsonl` |
| `grid2op` | `test` | `.research/general-qcc-captioner-20260515/grid2op_broad_v5_semantic_anchor/grid2op_broad_v5_semantic_anchor_test.jsonl` |
| `grid2op` | `train` | `.research/general-qcc-captioner-20260515/grid2op_broad_v5_semantic_anchor/grid2op_broad_v5_semantic_anchor_train.jsonl` |
| `citylearn` | `dev` | `.research/general-qcc-captioner-20260515/citylearn_broad_semantic_v3_qual/citylearn_broad_semantic_v3_qual_dev.jsonl` |
| `citylearn` | `test` | `.research/general-qcc-captioner-20260515/citylearn_broad_semantic_v3_qual/citylearn_broad_semantic_v3_qual_test.jsonl` |
| `citylearn` | `train` | `.research/general-qcc-captioner-20260515/citylearn_broad_semantic_v3_qual/citylearn_broad_semantic_v3_qual_train.jsonl` |
| `finrl_scaled` | `dev` | `.research/general-qcc-captioner-20260515/finrl_broad_scaled_v1/finrl_broad_scaled_v1_dev.jsonl` |
| `finrl_scaled` | `test` | `.research/general-qcc-captioner-20260515/finrl_broad_scaled_v1/finrl_broad_scaled_v1_test.jsonl` |
| `finrl_scaled` | `train` | `.research/general-qcc-captioner-20260515/finrl_broad_scaled_v1/finrl_broad_scaled_v1_train.jsonl` |
| `water` | `dev` | `.research/general-qcc-captioner-20260515/multisim_qcc_v3_stable_dataflow/water_broad_smoke_v1/water_broad_smoke_v1_dev.jsonl` |
| `water` | `test` | `.research/general-qcc-captioner-20260515/multisim_qcc_v3_stable_dataflow/water_broad_smoke_v1/water_broad_smoke_v1_test.jsonl` |
| `water` | `train` | `.research/general-qcc-captioner-20260515/multisim_qcc_v3_stable_dataflow/water_broad_smoke_v1/water_broad_smoke_v1_train.jsonl` |
| `traffic` | `dev` | `.research/general-qcc-captioner-20260515/multisim_qcc_v3_stable_dataflow/traffic_broad_smoke_v1/traffic_broad_smoke_v1_dev.jsonl` |
| `traffic` | `test` | `.research/general-qcc-captioner-20260515/multisim_qcc_v3_stable_dataflow/traffic_broad_smoke_v1/traffic_broad_smoke_v1_test.jsonl` |
| `traffic` | `train` | `.research/general-qcc-captioner-20260515/multisim_qcc_v3_stable_dataflow/traffic_broad_smoke_v1/traffic_broad_smoke_v1_train.jsonl` |

## Next Step

在包含完整 MultiSim v5 source JSONL 的 A100/3090 数据环境重新运行同一脚本；若 selected rows 达到每域目标，再对输出 JSONL 执行 natural rewrite 和 GPT-5.5 reviewer gate。
