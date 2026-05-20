# Real-source Natural-QCC Smoke Completion Audit (2026-05-21)

## Goal

把 Natural-QCC 题目生成协议接到每个目标域的真实数据出口上，并让每个域都能生成一定数量的数据。

## Completion Status

Status: `complete`

## What Was Built

- New generator: `scripts/generate/build_scenario_first_real_source_smoke.py`
- New audit gate: `scripts/eval/audit_scenario_first_real_source_smoke.py`
- Smoke artifact directory:
  `.research/general-qcc-captioner-20260515/scenario_first_real_source_smoke_v2_20260521/`
- Dataset:
  `.research/general-qcc-captioner-20260515/scenario_first_real_source_smoke_v2_20260521/real_source_natural_qcc_smoke.jsonl`
- SFT file:
  `.research/general-qcc-captioner-20260515/scenario_first_real_source_smoke_v2_20260521/real_source_natural_qcc_smoke_sft.jsonl`
- Chinese report:
  `.research/general-qcc-captioner-20260515/scenario_first_real_source_smoke_v2_20260521/REAL_SOURCE_NATURAL_QCC_SMOKE_REPORT_20260521_ZH.md`
- Audit JSON:
  `.research/general-qcc-captioner-20260515/scenario_first_real_source_smoke_v2_20260521/real_source_natural_qcc_smoke_audit.json`

## Domain Coverage

| Domain | Rows | Source kind | Adapter/source |
| --- | ---: | --- | --- |
| Grid2Op | 10 | `real_trace_artifact` | local Grid2Op real trace artifact |
| CityLearn | 10 | `real_trace_artifact` | CityLearn trace export artifact |
| Traffic | 10 | `official_simulator_export` | SUMO export artifact |
| Water | 10 | `official_simulator_export` | WNTR export artifact |
| AIOpsLab | 10 | `official_simulator_export` | AIOpsLab Prometheus export artifact |
| FinRL | 10 | `local_historical_ohlcv_smoke` | local real historical OHLCV smoke |

Total: `60` rows.

## Gate Results

Command:

```bash
.venv-simqa/bin/python3 scripts/eval/audit_scenario_first_real_source_smoke.py --per_domain 10
```

Result:

- `pass=true`
- `issue_count=0`
- every domain has at least 10 rows
- `no_controlled_source=true`
- `no_injected_control_signature=true`
- Chinese question/options/evidence fields present
- target caption/output fields non-empty and aligned
- figures exist for all rows
- combined SFT count matches raw row count

## Important Caveat

FinRL is not yet using the remote scaled FinRL artifact described in the earlier A100 dataflow report. The local smoke uses real historical OHLCV data in FinRL-style format because the scaled artifact was not copied locally. This is acceptable for this smoke goal, but the next benchmark-scale step should run the same adapter against the remote scaled FinRL artifact.

## Conclusion

This step fixes the earlier problem where most cross-domain rows came from a controlled generator. The new smoke set is explicitly sourced from real trace artifacts, official simulator exports, or a clearly labeled real historical OHLCV smoke source, with per-domain quantity sufficient for a protocol-level smoke test.
