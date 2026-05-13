# Real CityLearn Progress
**Date:** 2026-05-13
**Status:** feasibility passed; benchmark protocol not final

## Environment

Remote machine:
- 3090 server

Environment:
- Python: `/cluster/home/hulining/envs/citylearn/bin/python`
- CityLearn: `2.5.0`
- Cache: `/cluster/home/hulining/.cache/citylearn/v2.5.0/`

Available packaged dataset:
- `citylearn_challenge_2022_phase_1`
- files: `Building_1.csv` to `Building_5.csv`, `weather.csv`,
  `pricing.csv`, `carbon_intensity.csv`, `schema.json`
- size under CityLearn cache: about 57MB

## Trace Export

Script:
- `scripts/generate/export_citylearn_trace.py`

Remote outputs:
- `/cluster/home/hulining/LTSGEN/.research/real-citylearn-20260513/citylearn_challenge_2022_phase_1_trace_2048.json`
  - actual horizon: 2048
  - size: 3.7MB
- `/cluster/home/hulining/LTSGEN/.research/real-citylearn-20260513/citylearn_challenge_2022_phase_1_trace_8192.json`
  - actual horizon: 8192
  - size: 15MB

Local small artifact:
- `.research/real-citylearn-20260513/citylearn_challenge_2022_phase_1_trace_2048.json`

Exported variables:
- building: `non_shiftable_load`, `dhw_demand`, `cooling_demand`,
  `heating_demand`, `solar_generation`
- weather: `outdoor_dry_bulb_temperature`, `outdoor_relative_humidity`,
  `diffuse_solar_irradiance`, `direct_solar_irradiance`
- global: `electricity_pricing`, `carbon_intensity`
- derived: `net_electricity_without_storage`

Sanity:
- 2048 and 8192 traces export successfully.
- Core exported values have no missing entries.
- `cooling_demand` and `heating_demand` are all zero in this particular
  packaged slice, so they should not be used for QA without checking another
  dataset or time slice.

## Minimal QA Gate

Script:
- `scripts/generate/build_citylearn_slot_qa.py`

Data:
- `.research/real-citylearn-20260513/citylearn_real_v1_slot/citylearn_real_v1_slot.jsonl`

Sanity:
- 12 items
- answer letters A/B/C/D = 3/3/3/3
- task families:
  - `building_load_value_slot`: 4
  - `quarter_net_electricity_mean_value_slot`: 4
  - `outdoor_temperature_value_slot`: 4
- missing required fields = 0

Gate output:
- `.research/real-citylearn-20260513/citylearn_real_v1_slot/gate_meta_oracle_context_v3/`

Gate result:
- `meta_only`: 0.0833
- `oracle_evidence_caption`: 1.0000

## Core Sweep Smoke

Output:
- `.research/real-citylearn-20260513/citylearn_real_v1_slot/core_sweep_context_v3/`

Overall:

| Condition | Accuracy | Mean prompt chars |
| --- | ---: | ---: |
| `meta_only` | 0.2500 | 1,347.8 |
| `generic_caption` | 0.2500 | 1,532.8 |
| `oracle_evidence_caption` | 1.0000 | 1,426.1 |
| `numbers_sampled_32` | 0.3333 | 9,273.8 |
| `numbers_sampled_64` | 0.4167 | 16,986.8 |
| `numbers_sampled_128` | 0.7500 | 32,408.8 |

By task:
- `building_load_value_slot`: oracle 1.0, sampled-128 0.5
- `outdoor_temperature_value_slot`: oracle 1.0, sampled-128 1.0
- `quarter_net_electricity_mean_value_slot`: oracle 1.0, but `meta_only`
  reached 0.75 on only 4 items

Interpretation:
- CityLearn is feasible as a second simulator source.
- The 2048/8192 horizon requirement is feasible with packaged traces.
- Oracle evidence again works as a compact answer-preserving interface.
- Current 12-item CityLearn QA is only a feasibility smoke, not a final
  benchmark result.
- The quarter net-electricity task needs more samples and better distractor
  balancing before paper-facing use; otherwise it risks option-value priors.

Next:
- Expand CityLearn QA to at least 48-72 items over multiple windows.
- Either fix the quarter aggregation distractors or temporarily restrict the
  clean CityLearn gate to single-point slot tasks.
- Add a CityLearn Chinese case study only after the expanded QA passes
  `meta_only` sanity.
