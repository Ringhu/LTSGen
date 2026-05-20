# MultiSim-QCC-v1 Summary

Run dir: `.research/general-qcc-captioner-20260515/multisim_qcc_v1/multisim_qcc_v1/tsrlm_multisim_qcc_v1_local_gated_qprefix_ce_qwen3_4b`.
QA subdir: `rule_qa`.

## Domain Table

| Domain | Complete | Dev acc | Test acc | Dev+test acc | Empty | Mean chars |
|---|---:|---:|---:|---:|---:|---:|
| grid2op | True | 0.3824 | 0.7273 | 0.5548 | 0.0000 | 116.8000 |
| citylearn | True | 0.3206 | 0.3275 | 0.3241 | 0.0000 | 85.6000 |
| finrl | True | 0.7917 | 0.7659 | 0.7778 | 0.0000 | 119.9462 |

## Contract Check

```json
{
  "complete": true,
  "status": "ambiguous",
  "scientific_success": false,
  "worst_domain": "citylearn",
  "worst_domain_accuracy": 0.3241,
  "max_empty_answer_rate": 0.0,
  "grid2op_cf_total": 0.5,
  "as047_grid2op_cf_total": 0.1852,
  "non_grid2op_min_accuracy": 0.3241,
  "failure_flags": []
}
```

## Grid2Op Diagnostics

- CF total: `0.5000`
- Lead-lag: `0.9615`
- Non-CF macro: `0.5841`

| Grid2Op task family | N | Accuracy |
|---|---:|---:|
| grid_anomaly_max_rho | 52 | 0.2500 |
| grid_counterfactual_mean_stress | 74 | 0.5000 |
| grid_counterfactual_overload_exposure | 74 | 0.5000 |
| grid_counterfactual_peak_stress | 74 | 0.5000 |
| grid_cross_variable_stress | 52 | 0.6538 |
| grid_domain_stress_context | 52 | 0.9615 |
| grid_extrema_max_rho | 52 | 0.4231 |
| grid_temporal_lead_lag | 52 | 0.9615 |
| grid_trend_max_rho | 52 | 0.3846 |
| grid_volatility_total_load | 52 | 0.5000 |
| grid_window_total_load | 52 | 0.5385 |

## citylearn Task Families

| Task family | N | Accuracy |
|---|---:|---:|
| city_anomaly_total_load | 82 | 0.2683 |
| city_cross_variable_load | 82 | 0.3903 |
| city_domain_demand_context | 82 | 0.2561 |
| city_extrema_total_load | 82 | 0.3293 |
| city_trend_total_load | 82 | 0.3780 |
| city_volatility_total_load | 82 | 0.2805 |
| city_window_total_load | 82 | 0.3658 |

## finrl Task Families

| Task family | N | Accuracy |
|---|---:|---:|
| fin_cross_variable_return | 52 | 1.0000 |
| fin_domain_market_regime | 52 | 0.8461 |
| fin_drawdown_price | 52 | 0.7115 |
| fin_extrema_price | 52 | 0.8269 |
| fin_temporal_lead_lag | 52 | 1.0000 |
| fin_trend_price | 52 | 0.8654 |
| fin_volatility_returns | 52 | 0.9808 |
| fin_volume_anomaly | 52 | 0.1731 |
| fin_window_return | 52 | 0.5961 |
