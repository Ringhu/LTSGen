# Natural QCC 扩展候选计划（2026-05-19）

## 目的

balanced8 pilot 已经证明 natural evidence caption 可以接回 QA 评估，但 43 条 reviewer-positive 样本不足以支撑 QCC 训练结论。下一步需要从 MultiSim v5 的完整 source JSONL 中选出更大的候选池，再做自然化改写和 GPT-5.5 reviewer gate。

## 当前本地运行结果

命令：

```bash
python3 scripts/generate/select_natural_qcc_expansion_candidates.py --per_source 100
```

本地结果：

| 项目 | 数值 |
| --- | ---: |
| 本地可读取 source | 1 |
| 本地 selected rows | 35 |
| missing source files | 15 |
| selection complete | false |

本机只存在 `aiopslab_official_v3` 的 source JSONL，因此只物化了 35 条 AIOps 候选；Grid2Op、CityLearn、FinRL、water、traffic 的源文件在当前 checkout 不存在，但路径已记录在 manifest 中。

## 产物

| 资产 | 路径 |
| --- | --- |
| selector 脚本 | `scripts/generate/select_natural_qcc_expansion_candidates.py` |
| candidate JSONL | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates.jsonl` |
| candidate SFT JSONL | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates_sft.jsonl` |
| manifest | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/natural_qcc_expansion_candidates_manifest.json` |
| selector report | `.research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519/NATURAL_QCC_EXPANSION_CANDIDATES_20260519_ZH.md` |

## 数据机器上应执行的命令

在包含完整 MultiSim v5 source JSONL 的 A100/3090 数据环境运行：

```bash
python3 scripts/generate/select_natural_qcc_expansion_candidates.py \
  --schema .research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/schema_report.json \
  --out_dir .research/general-qcc-captioner-20260515/natural_qcc_expansion_candidates_20260519 \
  --per_source 100 \
  --seed 55
```

完成条件：

- `missing_files` 为空，或只剩明确不参与的 source；
- Grid2Op、CityLearn、FinRL、water、traffic 每个 source 选出 100 条；
- AIOpsLab v3 由于原始数据只有 60 条，且 metadata-only 已排除，预期最多约 35 条数值/上下文候选；
- candidate pool 覆盖 trend、extrema、volatility、anomaly、periodicity、window/cross-variable、lead-lag、counterfactual、domain-context。

## 后续步骤

1. 对 candidate JSONL 做自然化改写，保持 gold answer 和 support slots 不变。
2. 对自然化结果跑 GPT-5.5 reviewer gate，只保留 `decision=keep`、自然性和可答性均不低于 4、`accuracy_risk=low` 的样本。
3. 用 reviewer-positive 样本重建 train/dev/test natural QCC 数据。
4. 重新跑 `natural_oracle/generic/statistical/question_only` baseline。
5. 再启动 `run_natural_qcc_gpu_smoke.py` 或扩展版正式 SFT。
