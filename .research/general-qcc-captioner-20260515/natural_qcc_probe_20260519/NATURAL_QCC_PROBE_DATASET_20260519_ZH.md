# Natural QCC Probe Dataset（2026-05-19）

本数据集把通过 GPT-5.5 reviewer gate 的 natural TS-QA 样本转回原 MultiSim 评估器兼容的 JSONL。

- output: `.research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/natural_qcc_probe_positive.jsonl`
- positive rows: `43`
- excluded rows: `5`
- by source: `{'aiopslab_official_v3': 3, 'citylearn': 8, 'finrl_scaled': 8, 'grid2op': 8, 'traffic': 8, 'water': 8}`
- by split: `{'test': 24, 'dev': 19}`

## Source/Split

| source | dev | test |
| --- | ---: | ---: |
| `aiopslab_official_v3` | 0 | 3 |
| `citylearn` | 3 | 5 |
| `finrl_scaled` | 5 | 3 |
| `grid2op` | 5 | 3 |
| `traffic` | 5 | 3 |
| `water` | 1 | 7 |

## Excluded

| source | task | reason |
| --- | --- | --- |
| `aiopslab_official_v3` | `aiops_official_app_context` | This AIOpsLab row requires official metadata rather than numeric telemetry alone. |
| `aiopslab_official_v3` | `aiops_official_case_provenance_context` | This AIOpsLab row requires official metadata rather than numeric telemetry alone. |
| `aiopslab_official_v3` | `aiops_official_service_role_context` | This AIOpsLab row requires official metadata rather than numeric telemetry alone. |
| `aiopslab_official_v3` | `aiops_official_fault_family_detail_context` | This AIOpsLab row requires official metadata rather than numeric telemetry alone. |
| `aiopslab_official_v3` | `aiops_official_fault_context` | This AIOpsLab row requires official metadata rather than numeric telemetry alone. |
