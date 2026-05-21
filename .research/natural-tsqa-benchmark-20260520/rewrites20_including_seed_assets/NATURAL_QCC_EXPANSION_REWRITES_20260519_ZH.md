# Natural QCC Expansion Rewrites（2026-05-19）

本目录把扩展候选池改写成自然语言 TS-QA 草案，用于后续 GPT-5.5 reviewer gate。改写只改变场景、问题、选项和证据表述；`gold_answer`、`gold_answer_label` 和 `support_slots` 继续来自原始 deterministic 数据。

## 输入输出

- input: `.research/natural-tsqa-benchmark-20260520/candidates20_including_seed_assets/natural_tsqa_candidates20_including_seed_assets.jsonl`
- output JSONL: `.research/natural-tsqa-benchmark-20260520/rewrites20_including_seed_assets/natural_tsqa_rewrites20_including_seed_assets.jsonl`
- lint JSON: `.research/natural-tsqa-benchmark-20260520/rewrites20_including_seed_assets/natural_tsqa_rewrites20_including_seed_assets_lint.json`
- rows: `100`

## 分布

- by source: `{'aiopslab_official_v3': 20, 'citylearn': 20, 'grid2op': 20, 'traffic': 20, 'water': 20}`
- by split: `{'dev': 17, 'test': 31, 'train': 52}`
- by natural status: `{'candidate': 100}`
- by abstract primitive: `{'extrema': 6, 'trend': 6, 'volatility': 6, 'window_comparison': 6, 'cross_variable_relation': 8, 'None': 40, 'domain_context': 8, 'event_impact': 4, 'anomaly': 2, 'event_recovery': 4, 'counterfactual_effect': 6, 'lead_lag': 2, 'periodicity': 2}`
- by answer: `{'D': 27, 'C': 25, 'A': 22, 'B': 26}`
- lint issue counts: `{'material_without_threshold': 1}`

## 前 12 条样例

- `aiopslab_official_v3` / `aiops_official_memory_extrema` / `candidate`: 把这个事故窗口按时间分成早期、中期和后期后，服务内存工作集的最高点出现在什么位置？
- `aiopslab_official_v3` / `aiops_official_cpu_trend` / `candidate`: 这段事故窗口里，服务 CPU 负载是在上升、下降，还是基本平稳？
- `aiopslab_official_v3` / `aiops_official_network_volatility` / `candidate`: 这个事故窗口中，网络接收速率在哪一段波动最大？
- `aiopslab_official_v3` / `aiops_official_network_volatility` / `candidate`: 这个事故窗口中，网络接收速率在哪一段波动最大？
- `aiopslab_official_v3` / `aiops_official_cpu_trend` / `candidate`: 这段事故窗口里，服务 CPU 负载是在上升、下降，还是基本平稳？
- `aiopslab_official_v3` / `aiops_official_window_memory` / `candidate`: 按 5% 相对差异规则，这个事故窗口中的服务内存占用是前后相近，还是某一半更重？
- `aiopslab_official_v3` / `aiops_official_cpu_trend` / `candidate`: 这段事故窗口里，服务 CPU 负载是在上升、下降，还是基本平稳？
- `aiopslab_official_v3` / `aiops_official_memory_extrema` / `candidate`: 把这个事故窗口按时间分成早期、中期和后期后，服务内存工作集的最高点出现在什么位置？
- `aiopslab_official_v3` / `aiops_official_cross_signal_relation` / `candidate`: 按绝对相关系数 0.30 作为可用耦合阈值，SRE 在这个事故窗口中应该信任哪种遥测关系？
- `aiopslab_official_v3` / `aiops_official_cross_signal_relation` / `candidate`: 按绝对相关系数 0.30 作为可用耦合阈值，SRE 在这个事故窗口中应该信任哪种遥测关系？
- `aiopslab_official_v3` / `aiops_official_window_memory` / `candidate`: 按 5% 相对差异规则，这个事故窗口中的服务内存占用是前后相近，还是某一半更重？
- `aiopslab_official_v3` / `aiops_official_network_volatility` / `candidate`: 这个事故窗口中，网络接收速率在哪一段波动最大？

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
