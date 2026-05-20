# Natural QCC Expansion Rewrites（2026-05-19）

本目录把扩展候选池改写成自然语言 TS-QA 草案，用于后续 GPT-5.5 reviewer gate。改写只改变场景、问题、选项和证据表述；`gold_answer`、`gold_answer_label` 和 `support_slots` 继续来自原始 deterministic 数据。

## 输入输出

- input: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/candidates/natural_qcc_failure_domain_candidates.jsonl`
- output JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/rewrites/natural_qcc_failure_domain_rewrites.jsonl`
- lint JSON: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/rewrites/natural_qcc_failure_domain_rewrites_lint.json`
- rows: `72`

## 分布

- by source: `{'grid2op': 24, 'traffic': 24, 'water': 24}`
- by split: `{'dev': 12, 'test': 21, 'train': 39}`
- by natural status: `{'candidate': 72}`
- by abstract primitive: `{'None': 24, 'counterfactual_effect': 8, 'domain_context': 8, 'event_impact': 4, 'anomaly': 4, 'event_recovery': 4, 'trend': 2, 'cross_variable_relation': 4, 'lead_lag': 2, 'volatility': 4, 'periodicity': 2, 'window_comparison': 2, 'extrema': 4}`
- by answer: `{'D': 18, 'C': 21, 'A': 15, 'B': 18}`
- lint issue counts: `{'material_without_threshold': 1}`

## 前 12 条样例

- `grid2op` / `grid_trend_max_rho` / `candidate`: 这个电网窗口中的线路负载压力是在上升、下降，还是大致稳定？
- `grid2op` / `grid_counterfactual_mean_stress` / `candidate`: 在这个事件后片段里，断开线路如何改变平均最大线路负载压力？
- `grid2op` / `grid_anomaly_max_rho` / `candidate`: 把这个电网窗口按时间分成早期、中期和后期后，最强的线路负载压力孤立尖峰出现在什么位置？
- `grid2op` / `grid_cross_variable_stress` / `candidate`: 做快速过载复盘时，调度员更应该关注总需求还是发电裕度？
- `grid2op` / `grid_counterfactual_overload_exposure` / `candidate`: 与事实运行相比，在这个事件后片段里，断线干预会让过载暴露更高、更低，还是基本相同？
- `grid2op` / `grid_volatility_total_load` / `candidate`: 运维人员应该把窗口的哪一段视为总需求波动最大的部分？
- `grid2op` / `grid_anomaly_max_rho` / `candidate`: 把这个电网窗口按时间分成早期、中期和后期后，最强的线路负载压力孤立尖峰出现在什么位置？
- `grid2op` / `grid_volatility_total_load` / `candidate`: 运维人员应该把窗口的哪一段视为总需求波动最大的部分？
- `grid2op` / `grid_counterfactual_peak_stress` / `candidate`: 在这个事件后窗口里，断开线路对最大线路负载压力的主要影响是什么？
- `grid2op` / `grid_counterfactual_mean_stress` / `candidate`: 在这个事件后片段里，断开线路如何改变平均最大线路负载压力？
- `grid2op` / `grid_temporal_lead_lag` / `candidate`: 总需求和最大线路负载压力之间是否表现出清晰的先后关系？
- `grid2op` / `grid_extrema_max_rho` / `candidate`: 把这个电网窗口按时间分成早期、中期和后期后，最大线路负载压力的最高点出现在什么位置？

## 使用方式

如果当前 checkout 不包含完整 MultiSim v5 source JSONL，可以用 `--source_root` 指向包含源 JSONL 的工作树或数据机器路径，先重新运行 candidate selector，再运行本脚本：

```bash
python3 scripts/generate/select_natural_qcc_expansion_candidates.py \
  --schema .research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/schema_report.json \
  --source_root /path/to/LTSGEN \
  --out_dir .research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519 \
  --per_source 100 \
  --seed 55

python3 scripts/generate/build_natural_qcc_expansion_rewrites.py \
  --input_jsonl .research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates.jsonl \
  --out_dir .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519

python3 scripts/generate/review_natural_qcc_expansion_rewrites.py \
  --input_jsonl .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites.jsonl \
  --review_json .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/natural_qcc_expansion_rewrites_review.json \
  --review_md .research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519/NATURAL_QCC_EXPANSION_REVIEW_20260519_ZH.md \
  --model gpt-5.5
```

## 下一步

对 `natural_qcc_expansion_rewrites.jsonl` 运行 GPT-5.5 reviewer gate；只保留 `decision=keep`、`naturalness_score>=4`、`answerability_score>=4`、`accuracy_risk=low` 的样本进入正式 natural QCC train/dev/test。
