# Natural QCC Expansion Rewrites（2026-05-19）

本目录把扩展候选池改写成自然语言 TS-QA 草案，用于后续 GPT-5.5 reviewer gate。改写只改变场景、问题、选项和证据表述；`gold_answer`、`gold_answer_label` 和 `support_slots` 继续来自原始 deterministic 数据。

## 输入输出

- input: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/candidates_tw2/natural_qcc_failure_domain_tw2_candidates.jsonl`
- output JSONL: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/rewrites_tw2/natural_qcc_failure_domain_tw2_rewrites.jsonl`
- lint JSON: `.research/general-qcc-captioner-20260515/natural_qcc_failure_domain_expansion_20260520/rewrites_tw2/natural_qcc_failure_domain_tw2_rewrites_lint.json`
- rows: `32`

## 分布

- by source: `{'traffic': 16, 'water': 16}`
- by split: `{'dev': 6, 'test': 7, 'train': 19}`
- by natural status: `{'candidate': 32}`
- by abstract primitive: `{'event_impact': 2, 'counterfactual_effect': 6, 'domain_context': 6, 'trend': 2, 'extrema': 2, 'anomaly': 2, 'cross_variable_relation': 2, 'window_comparison': 2, 'lead_lag': 2, 'periodicity': 2, 'volatility': 2, 'event_recovery': 2}`
- by answer: `{'A': 14, 'B': 7, 'D': 7, 'C': 4}`
- lint issue counts: `{}`

## 前 12 条样例

- `traffic` / `traffic_event_impact_relation` / `candidate`: 在这个交通事件窗口内，平均车速和队列长度哪一个变化更强？
- `traffic` / `traffic_counterfactual_event_gap` / `candidate`: 在交通事件窗口内，事实平均车速与匹配基线相比是否有明显差异？
- `traffic` / `traffic_combined_stress_context` / `candidate`: 根据综合交通压力分数和事件时段，这个交通窗口最可能处于哪种运行状态？
- `traffic` / `traffic_speed_trend` / `candidate`: 这个交通窗口中的车速是在改善、恶化，还是大致稳定？
- `traffic` / `traffic_speed_extrema` / `candidate`: 把这个交通窗口按时间分成早期、中期和后期后，最低平均车速出现在什么位置？
- `traffic` / `traffic_incident_anomaly` / `candidate`: 把这个交通窗口按时间分成早期、中期和后期后，最明显的事故式交通扰动出现在什么位置？
- `traffic` / `traffic_cross_congestion_relation` / `candidate`: 做拥堵诊断时，车速与队列长度的耦合更强，还是与车道占有率的耦合更强？
- `traffic` / `traffic_window_speed` / `candidate`: 这个窗口中哪一半的平均车速更高？
- `traffic` / `traffic_combined_stress_context` / `candidate`: 根据综合交通压力分数和事件时段，这个交通窗口最可能处于哪种运行状态？
- `traffic` / `traffic_speed_queue_lead_lag` / `candidate`: 车速变化和排队长度变化之间是否表现出清晰的先后关系？
- `traffic` / `traffic_signal_counterfactual_queue` / `candidate`: 与固定信号基线相比，自适应信号策略是否改善了排队？
- `traffic` / `traffic_domain_congestion_context` / `candidate`: 按照拥堵分档规则，这个交通窗口最符合哪种交通状态？

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
